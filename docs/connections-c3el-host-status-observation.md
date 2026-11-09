# 🏥💜 C3e-L // Kernel-pinned host status observation, CI only

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · protected-host release trust  
STAFF ROLE // DOC · Protected Connections development  
ASSIGNMENT // Prove reverse host identity and read-only status consumption  
DEPENDENCY // C3e-K draft #1591; C3e-J merged #1585, C3e-I merged #1540  
CONCURRENT OWNERS // C2v/C4b immutable Silverblue lifecycle, TASKS C5 consent  
PROVIDER // OPEN AI // CHATGPT external Hospital-compatible; no live registration verified  
PRODUCTION // HOLD

## IMPLEMENTATION

The C3e-K Linux witness already checks which nonroot process *requests* an observation. C3e-L adds the missing **reverse** check: the nonroot client must authenticate the *responding* root-host process from Linux kernel identity, and must independently check the strict witness response.

A disposable test supervisor pins the expected host PID, UID=0, GID=0, kernel process-start tick, SHA-256 of previously enrolled C3e-F witness identity and minimum policy/release floor. The nonroot C3e-L client verifies:

1. Root-owned `/run/c3ek-ci-*/public/witness.sock` socket and entire directory scope, ownership, group and exact mode. Symlinks, missing files, unexpected paths and writable directories refuse.
2. Connection `SO_PEERCRED` identifies the exact pinned root host PID/UID/GID. Host process-start tick is checked before and after the request; the socket inode cannot change without refusal.
3. Exactly the preexisting C3e-J/K `WITNESS-FLOOR-READ-V1` packet may pass. The response has a bounded byte length, no extra/duplicate JSON fields, exact schema, real integer policy/sequence floors and exact pre-enrolled witness digest. It must deny both authorization and write capability.
4. Parsed observations must not fall below the test supervisor's enrolled floor. The adapter exposes transport-peer evidence and observed floors, **but explicitly returns** `hostAuthenticated: false`, `canApprove: false`, `credentialActionsEnabled: false`, `productionAuthority: false`.

This composes the C3e-F existing witness validator with the C3e-K OS-separated host. It does not touch K's server code, C2v/C4b files, C5 consent, the native QML broker or any stored real credentials. It is a **disposable test-only component, not production authentication**.

## HOW TO USE

PR's GitHub workflow `.github/workflows/connections-c3el-host-status-observation.yml` runs real root-host and nonroot-client subprocesses in a disposable Ubuntu runner. It checks both socket ends, invalid/stale IDs, forwarded-socket precedent, digest/floor substitutions, malformed/untrusted status responses, and existing default-deny production policy.

This is **stacked on C3e-K #1591**, which is still draft and unmerged. It must not be merged into `main` before that dependency is resolved. No operator desktop or Fedora command is necessary.

## VERIFY

- [ ] New actual nonroot client + root host integration and adversarial tests pass on exact head.
- [ ] C3e-K distinct UID and C3e-J same UID regression checks pass.
- [ ] C3e-I/H/G/F signed operator approval, release floor and crash recovery regressions pass.
- [ ] Root-pinned admission, signed fake RPM and Meta Apollo Grammar checks pass.
- [ ] Independent security/source review and final operator acceptance remain separate from CI.

## WATCH OUT FOR

**This does not authenticate a signed installed executable** or a real operator-approved host enrollment. The "trusted" pins come from the disposable CI supervisor, not an externally protected issuer; the Linux root process is a test server and remains outside C4b production systemd/SELinux installation. This provides stronger test transport evidence but does not deliver genuine remote witness rollback protection, a secret vault, operator session/user-presence confirmation, deployed signing key custody, or a production credential operation.

An observed witness-floor response is not a release update, and a successful kernel identity check is not consent. A malicious root actor can impersonate a root process given access to bootstrap pins; a malicious same-host privileged actor can restore all software ledgers. Actual signed executable provenance, externally protected enrollment, native lifecycle and a bounded host-owned consent protocol must be developed and reviewed before enabling production authorization.

## CHECKLIST

- [x] Confirm C3e-K exact-head checks and K source; reconcile C2v/C4b and TASKS C5 parallel owners.
- [x] Add new reverse kernel host observation implementation without changing protected server.
- [x] Add real integration/adversarial tests, CI workflow and handoff.
- [ ] Verify exact-head CI, fix only observed defects.
- [ ] Separate independent review and operator merge disposition.
- [ ] Coordinate signed deployed host identity, durable witness custody and bounded operator consent before any real credential release.

## NEXT / DECISIONS

After the stacked PR passes and owner review is complete, the next development target is **verified signed host executable identity and installation provenance** tied to this bidirectional kernel-authenticated channel. Coordinate that seam with C3b/C4b immutable service owner before linking live CPU++ Connections or TASKS C5. Keep all grants and QML host-authenticated flags false. No production activation or local machine changes.
