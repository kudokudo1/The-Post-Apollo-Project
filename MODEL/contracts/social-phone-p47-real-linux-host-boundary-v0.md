# Social PHONE P47 // Real Linux status-only host socket

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Role:** External Hospital-compatible PHONE DOC, live Hospital Room/Assignment/Session not verified  
**Base continuity:** P45 [#1957](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1957) and P46 [#1960](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1960) are OPEN and unmerged at this checkpoint. P47 branch is based on P46 but its PR targets **main** to prevent prior stacked-side-branch disappearance. Mainline P44 reconciliation remains in P45. The pending protected-save owner contract is [#1885](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1885).

## IMPLEMENTATION
P47 replaces a fully mocked host entrypoint with a **real, Linux AF_UNIX/SOCK_STREAM transport** for an intentionally narrow, non-sensitive STATUS operation. The module `services/phone/PhonePersonalHostSocketP47.py` has no CLI, automatic launch, systemd unit, QML binding, keyring access or save callback. Its API takes an explicit path to an already created private 0700 directory, an explicit stop signal, and optionally a readiness event. It refuses symlinks, non-canonical directory paths, non-owner/non-0700 ownership and permissions, preexisting socket names and excessively long Unix paths. It creates only a 0600 socket.

For every accepted socket, P47 reads *actual Linux kernel* `SO_PEERCRED` and rejects unexpected UID/malformed credentials. This does **not** establish installed software identity, genuine seat/session status, independent release provenance or human consent. Valid requests must be exactly one canonical, bounded, one-line `{"operation":"STATUS","schema":"post-apollo.phone.personal-host-status.p47.v1"}` frame. Private actions such as SAVE, arbitrary JSON, extra authorization/notes/keys, duplicate/noncanonical frames, oversized messages, missing newline or slow input always receive the same content-free DENIED result. There is one response per accepted connection and no persistent client session.

The STATUS answer confirms only that the socket handler observed an equal-UID kernel peer. **Every authority stays false**, including `installedIdentityVerified`, `independentChallengeVerified`, `c5OneUseConsentVerified`, `keyReadAuthorized`, `productionEnabled`, `personalSaveAuthorized`, `readbackTrusted` and `retryAuthorized`. The socket never imports P35/P36/P41b/P45/P46, never reads a key, contact, note, or vault, never issues a signer/challenge/consent and never replies SAVED. It cleans up its own socket inode on orderly shutdown without deleting another replaced path.

The tests run an **actual Linux socket** on a disposable GitHub runner, not a fake transport. They verify kernel peer observation, permissions, valid canonical STATUS, blocked private actions and authorization injections, slow/multiframe/malformed refusals, cleanup, existing path preservation and absence of secret/production modules.

## HOW TO USE
Nothing is installed or running on the user's Fedora desktop. P47 must be launched by a separately authorized future protected host with a prepared 0700 socket directory; this PR has no public executable entrypoint and no default location. It is not a private data API. The Social editor still displays **HOST UNAVAILABLE / NOT SAVED**, and SAVE remains hard disabled.

## VERIFY
- Dedicated exact-head GitHub CI starts real AF_UNIX sockets inside temporary owned directories with actual kernel `SO_PEERCRED`.
- Test adversarial request sizes, extra keys, bad status, second requests, timeouts, mismatched mock UID, nonowner permissions and preexisting path refusal.
- Recheck P45 mainline completeness and P42/P44 live editor source regressions. These source tests do not establish a native installed service, independent C4b/C3e signer, C5 consent, or cross-UID systemd/SELinux security.

## WATCH OUT FOR
**Same-UID peer credentials do not authenticate Post Apollo or the user gesture.** A same-UID malicious process can connect to, forge or replace user-owned sockets. A 0600 socket is not a robust trust boundary against same-UID attackers; it is only a defensive transport primitive. Do not promote `linuxPeerCredentialsObserved` to `installedIdentityVerified`.

The P45 key lookup and P46 provisioning callback remain unbound and dormant. P47's STATUS cannot authorize reading a key or saving a note. No CREATE, UNLOCK, ROTATE, ERASE, LINK, FAVORITE, NOTE, UNLINK or RESTORE socket operation is exposed. An actual installed PHONE process must eventually verify immutable pinned service identity, release signature, SELinux/cgroup/seat/session, independent external C3e one-use challenge and C5 signed per-action consent, plus host-owned atomic authorization through P35 encrypted CAS/fsync/readback. Do not expose a write IPC simply by adding an operation case to this socket.

C4b Identity PR #1785 is still owner work, and no verified production C5 PHONE signed consent exists at this checkpoint. Issue #1885 stays blocking. Do not merge P47 ahead of mainline reconciliation review for P45/P46.

## CHECKLIST
- [x] Recheck P45/P46 open branch state and PHONE-only ownership.
- [x] Implement real Linux AF_UNIX status-only server using actual SO_PEERCRED.
- [x] Reject save/secret/consent claims and enforce owner-only socket creation.
- [x] Test against a real disposable Linux socket, malformed/slow/oversize and path races.
- [ ] Check exact-head CI and independent review.
- [ ] Operator review/merge P45, P46, then P47, rechecking all three modules on `main`.
- [ ] C4b/Identity installed-source authenticity and C3e independent anti-replay authority.
- [ ] C5 genuine one-use human PHONE consent, protected key lifecycle/rotation and host-only lease through P35 commit.
- [ ] Native Fedora/SELinux/systemd installed-host tests and separately authorized activation.

## NEXT
**Real installed-host authority bridge**, not another test receipt: jointly obtain the owning C4b/C3e/C5 canonical evidence/provenance and installed service identity. Replace P47's untrusted STATUS-only transport with a separately reviewed, signer-authenticated interface that uses a nonforgeable host-held one-action lease and commits each P41b exact edit through P35 encrypted CAS, returning authenticated readback. QML SAVE can become enabled only after that service proves its identity and consent on the actual user session.

## DECISIONS
This is a real OS communication boundary, but **not a production PHONE save service**. No desktop, keyring, user contacts, local machine or upstream-owner code was changed. No service installation, activation, merge, or claim of live Hospital registration. Operator final authority retained.
