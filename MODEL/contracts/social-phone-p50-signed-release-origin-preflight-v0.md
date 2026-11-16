# PHONE P50 // Signed source-origin preflight for real Linux STATUS service

**PATIENT** `kudokudo1/The-Post-Apollo-Project`  
**ROOM / ASSIGNMENT** Social PHONE protected Favorites/Notes, established external DOC continuation. Live Hospital Room/Assignment/Session not technically verified.  
**BASE** P49 draft PR [#1977](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1977) remains OPEN, 2/2 exact-head green; branch P50 based on P49's head but PR **targets main**. P45–P48 are merged and source-verified on main.  
**PROTECTED OWNERS** C4b/Identity [#1785](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1785) (open; real Silverblue CI full two-boot result), C3e [#1978](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1978) (new sanitized marker-only deny reviewer; no trusted identity) and separate C5 genuine human-consent issuer. PHONE coordination [#1885](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1885) remains OPEN/BLOCKING.

## IMPLEMENTATION

1. `services/phone/PhonePersonalInstalledReleaseP50.py` implements a **real Ed25519 signature verifier** using canonical, bounded, unique-key JSON with explicit PHONE `status-only` domain, role, audience, purpose, monotonic epoch/sequence test floors and exact four-file Python source + systemd unit SHA-256 inventory. Verifies true detached signature bytes under a separately supplied Ed25519 public key. Opens all source files with `O_NOFOLLOW`, checks regular, one-link, non-writable-by-group/world, owned by root or test user, bounded bytes, hashes each file and compares the exact fixed roster. Rejects Identity C4b's release role/schema/unit, extra/missing fields/modules, modified source/unit, wrong root, bad signatures, invalid floors, symlinks, hardlinks or writable paths.
2. Adds an **optional CI-only** `--ci-signed-manifest <path> --ci-signed-signature <path> --ci-release-root <path>` preflight to P49's actual Linux process entrypoint. When supplied, all three inputs are mandatory together, restricted to absolute paths, bounded regular non-symlink files with safe modes. P49 verifies before and after its source/own-/proc checks, **before opening its P47 STATUS socket**. Valid signed test evidence allows the ordinary STATUS-only process to launch; tampered/revoked/invalid evidence refuses with code 78 and no socket. P49's existing test-only launch without this optional mechanism remains available to preserve P49 tests and proposed inert unit. P49's self-hash roster is updated to include P50.
3. Native CI actually spawns P49 as a separate Python isolated-mode child with a freshly minted ephemeral test Ed25519 root and signed real source bytes; checks true AF_UNIX STATUS, all authorization flags false, signed refusal and quiet SIGTERM cleanup. Adversarial fixtures cover source tampering, Identity-cross-role substitution, rollback epoch/sequence, duplicate/noncanonical JSON, altered systemd unit and file symlinks/writable/hardlinked material. P49/P47/P48 Linux tests and P45/P44 locked editor regressions remain in CI.

## HOW TO USE

Nothing is installed on Fedora. No operator action is required. These are source files and CI subprocesses. The P50 public key is provided by the *test caller* and is not independently pinned or provisioned by C4b/C3e. The test manifest, root key and signature are not published as production credentials. There is no real user keyring access and no Favorites/Notes save operation.

## VERIFY

Dedicated P50 exact-head CI plus Meta Apollo Grammar. Verify that a real P49 process starts **only when optional supplied CI release bytes match**, that all results still return `HOST_UNTRUSTED_STATUS_ONLY`, that source/package role swaps and tampering refuse, and that P49's existing no-signer STATUS path remains test-only and non-authorizing. Recheck P49 merge status and exact `main` after review.

## WATCH OUT FOR

**A caller-selected Ed25519 root is not a trusted release root.** An attacker who can supply source bytes, key and manifest can make P50 pass; the parser only proves consistency. **Do not use P50 for installed-host approval, production service admission, Secret Service release, real C5 human consent, or authorization of P35 edits**. No C4b/Identity test receipt, C3e marker log or CI runner can be silently promoted to a PHONE trusted origin. Even when the optional check passes, P47 STATUS reports `installedIdentityVerified:false`, `independentChallengeVerified:false`, `c5OneUseConsentVerified:false`, `personalSaveAuthorized:false` and `keyReadAuthorized:false`.

**Import-order limitation:** Python loads P47/P48/P50 modules before P49's optional CI check executes. Therefore this preflight does not prevent malicious import-time code execution and must never be treated as a secure launcher or production package verification. A future trusted loader/OS package verification must occur *before* module execution.

A real independent PHONE signer root must be enrolled outside the host/checkout and protected against rollback. The installed package must be bound to the exact active systemd MainPID, root-owned installed modules, RPM/OSTree deployment, SELinux policy, cgroup and logind seat, with signer custody and a separately verified complete rollback. P49's status-only service has neither an installed signer nor any C5 PHONE-specific one-action consent. No production UI SAVE.

## CHECKLIST

- [x] Reinspect live GitHub P49/C4b/C3e state and Syntagma authority.
- [x] PHONE exact signed source role/manifest + crypto verifier, no production grant.
- [x] Actual P49 Linux signed optional preflight and source roster protection.
- [x] Adversarial signature/role/source/permissions/rollback and native child tests.
- [ ] Exact-head CI and independent security review.
- [ ] Operator merge P49 first; recheck P50 diff against main and review/merge P50 without side-branch loss.
- [ ] Actual independently enrolled signed PHONE release/host witness, C3e one-use challenge/consumption/revoke floor, C5 one-use signed PHONE action receipt, keyring lock/rotation/erase and P35 host-held CAS/ack lease.
- [ ] Native Silverblue installed PHONE service/SELinux/logind/rollback tests, separate operator deployment and final acceptance.

## NEXT

**Use owner-supplied independent signed installed-origin evidence**, not the CI test root, to bind P49/P50 to a protected PHONE service identity and actual seat/session. In parallel obtain C3e's externally issued/consumed one-use challenge and C5's signed phone-action user consent tied to P41b `editHmac`. Only after these owners deliver can PHONE create the nonforgeable authorization lease that spans protected Secret Service key retrieval, encrypted P35 CAS/fsync and truthful readback. That lease, not the status socket, will be the real SAVE entrypoint.

## DECISIONS

P50 is an additive PHONE-owned review branch, not a new installed service or approved production trust scheme. No local Fedora write, Quickshell reload, actual keyring operation, contact modification, iPhone write, cross-owner file change, merge or production activation. Operator acceptance is separate from green tests.
