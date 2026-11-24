# Forest Core B5f // Split UID installed-host integration experiment

PATIENT: The-Post-Apollo-Project
ROOM: Forest Core launcher, native host and storage boundary
ROLE: Forest backend DOC, external Hospital-compatible
STATE: Disposable CI only; production HOLD.

## IMPLEMENTATION

B5e #2400 merged 7c76728c with 53/53 focused tests and 6/6 workflows.
B5b through B5e independent reviews remain outstanding at preparation.
DOC2 accepted development mechanics, not production identity or storage.

B5f connects the installed B5c deny-only host to a real requester process
with a DIFFERENT Linux UID while B5d synthetic databases remain present.
A disposable root CI controller creates an unnamed SEQPACKET pair and
starts the exact RPM-installed B5b script as one of two fixture owners.
It starts a separate renderer UID with only the corresponding socket,
closes its endpoint copies and bounds process completion. It uses the
B5e close_fds/pass_fds discipline, not B5e's same-UID launcher function.
This test-only controller is not an accepted privileged broker.

B5d's existing writer code creates two live synthetic B1 databases, WAL,
SHM and backups under separate owner identities. The renderer first tests
actual denial of direct read/write/list and SQLite access. A deliberately
inheritable DB descriptor in the controller is excluded from the
renderer, which checks EBADF itself. It then submits one test token.
The actual installed host can emit only the fixed public HOLD packet.
It has no private database opener, model transport, issuer or positive
authority path. The test also verifies host UID, both fixture owners,
ancillary rights refusal, STOP and before/after fixture file bytes,
inodes, modes and ownership. Owner readback remains possible.

## HOW TO USE / VERIFY

Disposable Fedora CI only. Reuse the unchanged B5c RPM builder and verify
installed bytes/mode/roster, run seven integration tests, then erase package.
B5b, B5a and B1 regressions run separately. No workstation installation.

### Corrective fixture isolation

The original merged #2402 native CI ran 4/6 tests successfully. Two tests
failed at their pre-exchange file-roster assertions after the owner
readback case caused SQLite to create backup.db-wal and backup.db-shm.
The readback and exchange cases previously shared class-scoped fixtures.
Each case now constructs fresh temporary databases and starts fresh writer
processes, then stops those processes and removes its own fixture directory.
The readback case validates any legitimate backup sidecars for owner, mode
and regular-file type. The exchange baseline still requires the original
exact roster and compares all bytes/metadata; an added negative regression
proves unexpected backup sidecars remain a refusal. No host, launcher, B1,
B5d or Connections source changes.

## WATCH OUT FOR

The root test controller can bypass DAC and controls both fixture UIDs.
This experiment is neither independent root custody nor an authentication
boundary. It does not demonstrate that the host cannot read files belonging
to its own UID, that no reads occurred, that the FD recipient is enrolled,
or that matching before/after bytes prove no intervening mutation.
It demonstrates observed post-exchange fixture integrity and denial-only
socket behavior. No private query, user DB, encrypted storage, authority
keys, C5 permit, real seat, per-message identity or protected revoke fence.
No claims of production launcher approval or Silverblue reboot evidence.

## NEXT / DECISIONS

Independent Forest Nurse 2 review of B5b-B5f. Operator and DOC1/2 must
accept the installed original-source, separate runtime identity/launcher,
protected storage/key custody and independent release/recipient evidence.
DOC3 retains list/title/stream/commit permission and revocation ownership.
Do not connect private storage or release titles until those gates exist.
No auto-merge, native inference or production activation.
