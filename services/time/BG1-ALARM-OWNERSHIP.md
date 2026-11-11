# CLOCK // BG1-A Ownership Fence

**Status:** Repository-only pre-actuation contract. **No production ownership handoff.**

## Mechanism first

Clock keeps its alarm schedule and ringing state in `Quickshell.dataDir/time-alarms-v2.json`.
A second scheduler must not simply read this file and start ringing; it could
race Quickshell, duplicate the sound and popup, or overwrite STOP/SNOOZE.

`AlarmOwnershipGate.py` is the first **synthetic** arbitration component for
that future handoff. It does not change the existing QML manager or the B0
observer. Both remain exactly as they were before this PR.

The gate uses three separate safeguards:

1. **Explicit alarm scope.** Each gate is bound to the verified absolute
   saved alarm path, owner UID, V2 structure and per-shell data directory.
   The scope uses the canonical *parent directory* rather than a fixed file
   inode, because Quickshell's atomic saves legitimately replace that inode.
2. **Process-bound ownership lease.** With a private `flock`, only one actor
   (`quickshell` or `background`) can acquire the current epoch at a time.
   The lease stores a hash of a random token, the Linux process PID/start
   time, boot ID and monotonic deadline. Renewals and reservations require
   the same live process and token. A lease from a dead process, different
   boot or expired epoch is invalid. A stale actor cannot renew after a
   newer epoch has been issued.
3. **Durable occurrence reservation.** Under the same exclusive lock, each
   tuple of alarm ID, expected due timestamp and schedule digest is hashed
   and stored once as `RESERVED_ONLY`. A crash or lease turnover does not
   delete the reservation. Repeated reservations are rejected. A full or
   corrupt ledger fails closed rather than pruning old claims and permitting
   an unexpected replay.

The gate owns a private sidecar directory
`<verified Quickshell.dataDir>/alarm-ownership-v1/` with an atomic,
fsynced JSON ledger and a separate flock file. It **never writes the saved
alarm document**. It never includes alarm names, notes, sound paths or
plaintext lease tokens in the ledger.

## Critical limits

**A lease is NOT permission to sound an alarm.** Every answer explicitly
includes `actuationEnabled: false`. Reservation only means the occurrence
has been reserved. It is not evidence that sound, notification, or
acknowledgement succeeded. A crash after reservation intentionally
prioritizes avoiding duplicate actuation over guaranteed delivery.

**This is not yet authenticated production authority.** The Python
functions can currently be called by any process running as the same Linux
user that can access the private directory, and process-role strings are
not signed/trusted application identities. The user-facing command permits
only `--inspect`. No live Quickshell or B0 caller integrates with the gate,
so the current running Clock can still tick normally. This component cannot
claim exclusive *system-wide* ownership yet.

Do not infer completion from green synthetic CI. A real BG1-B must add:
- Trusted process identity and exact source-version binding.
- A long-lived broker/IPC interface for Quickshell and the background actor.
- An **atomic transition** in which every Quickshell tick/edit/STOP/SNOOZE
  and every background action enforces the **same** owner epoch.
- Correct handoff on restart, crash, process replacement, clock changes and
  failure to save the alarm document.
- Per-occurrence result/acknowledgement semantics, including the ambiguity
  between reserving a due event and actually producing sound.

The later BG2 may add independent audio and notifications only **after**
mutual enforcement and native tests, with existing DND/BLOCK policy and
popup STOP/SNOOZE routed to the verified owner. A regular user service
does not wake a powered-off or necessarily a suspended machine.

## CI and read-only diagnostics

```sh
python3 -m unittest discover -s tests/time \
  -p 'test_clock_bg1_owner_fencing_contract.py' -v
python3 -I -B services/time/AlarmOwnershipGate.py --inspect \
  --alarm-file /verified/per-shell/dataDir/time-alarms-v2.json \
  --state-dir /verified/per-shell/dataDir/alarm-ownership-v1
```

The second command **reads only** and refuses if the sidecar was not
initialized. It cannot acquire or reserve via CLI. Tests use disposable
directories and two independent test processes, never the user's saved
alarms.

## Continuity / rollback

PATIENT // `The-Post-Apollo-Project`  
ROOM // Clock Background Alarm ownership  
ASSIGNMENT // BG1-A synthetic shared lease and occurrence claim foundation  
STAFF // External Hospital-compatible DOC, not live Hospital registered  
SOURCE // GitHub PR for this milestone, without merge or local activation

No existing Clock, Notification, B0 observer or systemd unit files are changed.
Discarding this unmerged branch returns to the exact existing runtime behavior.
A future local deployment needs separate explicit authorization; no
production service is installed or enabled here.
