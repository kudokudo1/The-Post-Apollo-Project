# Clock BG1-B2B10 // Foreground Native Supervisor Socket

**State:** A runnable Linux AF_UNIX supervisor with strictly deny-only
responses. The native process is genuine. **Its protected Clock authority
is NOT provisioned, so this is not an alarm daemon or a production handoff.**

## Why this is different from another signed-response fixture

B2B9 is the missing installed-source verifier. B2B10 adds an actual
long-running foreground native process and a private Unix socket endpoint
that requests can reach. It does not publish Quickshell IPC or claim
control of its FileView.

Invoked explicitly with:

`python3 services/time/AlarmNativeClockSupervisor.py --foreground`

There is **no installed unit** or auto-start rule, and no operator
instruction to run it as part of the live alarm system. Production
startup requires an existing protected `/run/user/<uid>` user runtime
directory; it creates `post-apollo-clock/clock-supervisor-v1.sock`
mode 0600 within a private mode-0700 directory. It refuses an
existing socket instead of deleting someone else's. This is not
production activation.

## Concrete protocol

Requests are single canonical, strict JSON frames terminated by a
newline, up to 1024 bytes:

`{"action":"INSPECT_ORIGIN","v":1}`

Only the exact actions `INSPECT_ORIGIN`, `REQUEST_PAUSE`,
`RELEASE_WRITER`, `TAKE_OWNERSHIP`, and `RING_ALARM`
are recognized. Unknown fields, duplicate fields, extra frames,
noncanonical encodings, malformed versions and oversized requests
refuse. Every result reports `ok=false`; the server never sends a
release token, owner lease, file path or alarm data.

For inspection, the supervisor first uses kernel `SO_PEERCRED`,
then matches the PID against an independently obtained **supervisor
roster**, verifies the accepted connection via `SO_PEERPIDFD` and
exact start ticks, and delegates to B2B9's pinned Clock root, signed
policy, executable/argv and process verifier. A successful test-origin
inspection says only `originObserved=true` and
`OBSERVED_ONLY_NOT_AUTHORIZED`. Every capability remains false.

**Critical boundary:** The current production server has **no trusted
roster provisioning**. A normal `--foreground` process starts with
an empty roster and refuses all origin admissions, pauses and
actuation. Only a disposable Python CI harness can inject a
`SyntheticSessionPin` through an in-process API guarded by an
explicit synthetic-only runtime marker. There is no command-line,
environment variable or socket payload that enables this in a real
production instance.

All recognized pause, release, takeover and ring actions respond with
`NATIVE_WRITER_HANDOFF_NOT_AUTHORIZED`, including if the peer has
valid signed test-origin evidence.

## Tests

The CI suite starts the **real native Unix-socket listener** and a
separate real signed Python child process. It exercises a pinned
SO_PEERPIDFD process and signed B2B9 fixture, unpinned client, bad
root signature, wrong release fingerprint, changed executable,
mismatched start ticks, unauthorized pause, unknown/duplicate keys,
oversized data, symlink/socket occupation, unsafe directory
permissions and safe socket cleanup. It reruns B2B9, B2B6 and
B2B1. Exactly four new B2B10 Clock-owned files are added to the
separate dependent PR.

## What is still missing before alarm ownership moves

- An approved installed **Clock-specific** signing root, protected
  signer key and independently maintained release floor. Neither
  Connections nor Identity keys may be repurposed.
- A protected supervisor that independently registers the real
  Quickshell old-writer process and authorizes exactly one session.
  B2B10's test roster does not meet that requirement.
- An authenticated QML `QUIESCING` transition that stops new
  accepted edits and timer events while finishing previously queued
  saves. It needs a durable final V2 source revision witness and
  post-release restart denial.
- A single canonical owner, atomic durable STOP/SNOOZE operations,
  safe crash/rollback, and BG2 audio + notification verification.
  The real mounted Clock's barrier is still immutable `ACTIVE`.
- Real Fedora Silverblue native runtime acceptance before production.

## Recovery and boundaries

PATIENT // The-Post-Apollo-Project
ROOM // Clock Reliable Background Alarm Ownership
STAFF ROLE // External Hospital-compatible DOC, not live registered
ASSIGNMENT // BG1-B2B10 real native deny-only supervisor endpoint
DEPENDENCY // B2B9 installed Clock-role trust preflight, PR #2022
SCOPE // 4 new Clock files; no other worker changes
PERMISSIONS // Draft GitHub source/tests only; no merge or local edits
HOW TO USE // CI-only before approved native installation
WATCH OUT FOR // An AF_UNIX listener does not grant writer authority
NEXT // Protected roster/release-floor custody + real Quickshell pause
DECISIONS // No real Clock ownership or ringing granted
