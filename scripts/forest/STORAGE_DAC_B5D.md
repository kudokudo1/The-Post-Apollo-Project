# Forest Core B5d // Native disposable storage isolation experiment

PATIENT: The-Post-Apollo-Project  
ROOM: Forest Core original-host storage boundary  
ROLE: Forest backend DOC, external Hospital-compatible  
STATE: CI only; production HOLD.

## IMPLEMENTATION

B5c #2391 verified actual Fedora container installation/removal of the B5b
deny-only host. Independent review of both remains pending at this checkpoint.
B5d tests an independent filesystem boundary, not a new session provider.

A disposable Linux container creates two synthetic B1 databases under
different numeric Linux UIDs/GIDs (61001 and 61002) in a temporary directory.
Each owner has a 0700 directory and uses umask 077 for the 0600 main
database, live SQLite WAL and SHM, and SQLite-generated backup. Two real
unprivileged writer processes hold those databases open. A third UID (61003)
represents a renderer without direct storage access. No accounts are created
on the operator's system. These are test identities, never Forest principals.

The harness tests actual OS file access and read-only SQLite access, cross-owner
and renderer read/write/list refusal, and rename/unlink/create refusal.
It checks the original B1 rows from the owner processes. An intentional
synthetic FD-inheritance control proves that passing an already-open descriptor
to another UID bypasses pathname DAC. This is a reason to enforce launcher
FD custody and isolation, not a protected access mechanism.

## VERIFY

Seven native tests, plus B1 and B5a regressions. CI starts an isolated
container with no network and only the required test files mounted read-only.
No host mounts, live DB, user data, signing credentials or inference.

## WATCH OUT FOR

These are Linux discretionary access-control (DAC) observations, not
authentication, at-rest encryption, SELinux confinement, release enrollment,
backup retention or protected storage custody. Root and code with the storage
UID are not excluded by mode bits. Different UIDs are a candidate isolation
option, not an accepted production account mapping. A single shared service
UID would require further intra-service principal isolation; this experiment
does not establish that. SQLite temporary files, crash/recovery, restore,
key management, antirollback and actual trusted launcher remain separate.
The deny-only B5b/B5c host is deliberately not connected to this storage.
The inherited descriptor test demonstrates an actual limitation.

## NEXT / DECISIONS

Review exact-head native evidence independently. Ask operator and DOC1/2 to
accept or revise runtime identity separation, independently protected owner
mapping, storage/key custody and approved launcher. DOC3 owns independent
list/title/read/generate and egress permissions; do not grant them here.
No native inference, workstation operation, production merge authorization
or UI activation. Forest production HOLD.
