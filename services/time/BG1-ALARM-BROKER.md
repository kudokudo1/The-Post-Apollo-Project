# CLOCK // BG1-B1 Synthetic owner broker

**State:** pre-actuation software prototype. **No production service, no alarm
sounds, no notification delivery, no Quickshell integration.**

## What actually runs

`AlarmOwnershipBroker.py` is an ordinary Python process listening on one
Linux `AF_UNIX` socket. Its directory must exist, belong to the current user
and be private (`0700`); the socket is created `0600`. It refuses to
overwrite a previous socket path.

A synthetic test client connects to that socket and sends one bounded JSON
object per line. The kernel supplies the real peer PID, UID and GID through
`SO_PEERCRED`. The broker cross-checks the peer executable and the
`/proc/<pid>/stat` start ticks, then attaches the connection to a named
synthetic role (`quickshell` or `background`). A role name is **not**
authenticated application authority. Any same-UID process running that
expected Python executable can impersonate these test roles.

The broker itself holds the BG1-A ownership token. Clients never receive that
secret. On `acquire`, one connection obtains the synthetic current owner
role/epoch; the other is refused. Every subsequent `renew`, `release` or
`reserve` requires that same live connection. An owner disconnect causes
the broker to try releasing its lease. Unexpected broker death invalidates
the lease by process identity, while the durable claims remain.

## Exact source evidence

`snapshot` opens the caller-supplied absolute
`time-alarms-v2.json` with `O_NOFOLLOW`, checks the local UID, size, V2
shape, and computes a SHA-256 hash of the **exact bytes read**. It returns
that snapshot digest and non-private diagnostic phases, **not** alarm titles,
notes, sound IDs or filesystem paths.

`reserve` accepts an alarm ID, expected due timestamp and the previously
observed snapshot digest. It rejects changed file bytes, missing alarms,
expired or disabled occurrences, and any due time that does not match the
observer's computed candidate. The broker computes the schedule digest
itself from saved schedule fields rather than trusting a client-supplied
hash. A change to an unrelated note or volume is not allowed to generate
another reservation for the same occurrence.

The BG1-A ledger records `RESERVED_ONLY`, one per schedule/due
occurrence. The broker rechecks the source hash after reservation. If it
changed during the operation, it reports a refusal while retaining the
reservation; it **never** tries to roll it back into a second ring.

## Synthetic-only usage

The command has **only** `--serve-synthetic`, no production/actuation
mode. It is intended for disposable CI fixtures, not the user's live
Quickshell storage:

```sh
python3 -I -B services/time/AlarmOwnershipBroker.py \
  --serve-synthetic \
  --alarm-file /fixture/quickshell-id/time-alarms-v2.json \
  --state-dir /fixture/quickshell-id/alarm-ownership-v1 \
  --socket /private-fixture/bg1-synthetic.sock \
  --synthetic-now-ms 1794408000000
```

Socket requests are `hello`, `snapshot`, `acquire`, `renew`,
`reserve`, and `release`. Every response states
`actuationEnabled: false` and `ownsAlarmFile: false`. There is no
`ring`, `play`, `notify`, `stop` or `snooze` command. No changes
to the user's existing alarms are possible through this broker.

## What is still missing before real background alarms

- **Trusted identity:** `SO_PEERCRED` establishes which Linux process
  connected, not whether that process was approved to act as Clock.
  Synthetic same-UID role names are **not authenticated** and cannot be
  promoted into production authority.
- **Mandatory mutual enforcement:** Quickshell and the observer currently
  do not connect to this broker. Quickshell still writes the saved alarm
  document without locking against it, so this broker is not the unique
  real scheduler.
- **Transactional commit:** The saved alarm file and the separate claim
  ledger are not updated together in one transaction. A file revision
  witness limits stale claims but does not eliminate a race between a
  native Quickshell save and the broker. BG1-B2 needs a single writer/
  authenticated broker contract covering edits, tick, STOP and SNOOZE.
- **Audible delivery / acknowledgement:** A reservation is not evidence
  that a tone sounded or a notification appeared. Crash after claim may
  lose a ring by design; a reliable delivery protocol must address that
  explicitly before BG2.
- **True uptime/suspend:** A Linux user process will not necessarily run
  during suspend and does not wake a powered-off machine.

## Hospital / recovery

PATIENT // `The-Post-Apollo-Project`  
ROOM // Clock Background Alarm BG1 ownership  
STAFF ROLE // External Hospital-compatible DOC, not live registered  
ASSIGNMENT // BG1-B1 synthetic socket peer protocol and source witnesses

Branch is stacked on BG1-A PR #1890. Review/merge BG1-A first, then
retarget this branch to `main` if appropriate after rechecking the diff.
This slice adds new broker, docs, tests and CI only; no production
Quickshell file, B0 observer, systemd unit or live desktop is modified.
Discarding the unmerged branch leaves current Clock behavior unchanged.
