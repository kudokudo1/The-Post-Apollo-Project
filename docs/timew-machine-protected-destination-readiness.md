# MACHINE // Protected destination readiness observation · read-only

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Protected Brave Archive
STAFF ROLE // Hospital-compatible external DOC, not verified live Hospital-registered
ASSIGNMENT // Verify an already-existing service-owned destination before any separately authorized encrypted archive transfer
SCOPE // Read-only source module, privileged disposable Linux tests, independent CI workflow and runbook

## IMPLEMENTATION

MACHINE PR #1898 (read-only source inventory) and #1900 (disposable simulated destination isolation/rollback) were both **OPEN, DRAFT and UNMERGED** when this branch was created. To avoid a concurrent worker's workflow changes, this PR branches from main and has its own `timew-machine-protected-destination-readiness.yml` workflow. It does not depend on or edit either open PR.

The new `services/time/MachineBraveProtectedDestinationReadiness.py` is a **read-only observation library**, not a service, installer, native Brave host, migration utility or operator CLI. Its production-style primitive `inspect_pinned_fd(fd)` accepts only a directory descriptor previously opened and anchored by an external trusted supervisor. The module itself never creates a directory or copies data.

The library enforces the following narrow observations under the *currently running non-root service Unix account*:

- The existing protected root is a real directory, owned by the effective UID of that service process and mode exactly 0700. The inspection refuses root (UID 0).
- All entries are canonical UUID-named `.json` records. Unexpected entries, temp/crash leftovers, symlinks, hardlinks, wrong owner, wrong 0600 file mode, invalid envelope, and oversized or malformed files cause refusal. An empty protected directory is acceptable as **an observation**, not an approval.
- Every encrypted record is read descriptor-relative through the existing vault validation functions and observed twice. Different inventory snapshots fail closed; the root descriptor must still refer to the same inode/device.
- The response contains only record UUID, UTC creation timestamp, encrypted byte size, SHA-256 record digest, total count and a deterministic SHA-256 observation fingerprint. No tab URL, title, ciphertext, passphrase, session content or key leaves the module.
- The output deliberately reports **false** for path ancestry authentication, cross-UID runtime isolation, SELinux policy verification, backup status, authenticated client, operator consent, migration permission and RESTORE. An observation cannot grant access.

The separate `inspect_trusted_path_for_fixture(Path)` helper is only for isolated CI callers: it opens an absolute, final-component no-follow path and confirms the directory's device/inode before and after inspection. A raw client-supplied path must NEVER be accepted as trusted input. An installed service would require a reviewed supervisor to securely open the full directory ancestry and pass a pinned file descriptor to the service.

## HOW TO USE

There is **no new TimeW button, production CLI or local installation**. The module's `__main__` is intentionally non-operational. GitHub CI invokes only:

```bash
sudo -n python3 -B -I tests/timew/test_machine_protected_destination_readiness.py
```

Do not execute this privileged fixture on the workstation. Real target provisioning, backup, file ownership changes, SELinux/LSM policy, approved migration and rollback require separate implementation, external security review and explicit operator authorization.

## VERIFY

On the disposable Ubuntu GitHub runner, root constructs a temporary fixture with three unassigned numeric UIDs: ordinary browser principal, different non-root protected service principal, and unrelated foreign principal. Without creating system users, the test drops into actual service UID to run the inspection code and uses genuine kernel permission decisions to prove that the browser and foreign UID **cannot read, list, append, unlink, chmod or create** files in the service-owned protected directory.

Other synthetic tests cover:
- Existing empty directory and valid sealed records, reproducible metadata-only fingerprints and **no filesystem modifications**.
- Invalid file owner, group/world permissions, hardlink, symlink, unexpected entries, incomplete temp files, invalid schema and missing protected directory.
- Wrong protected root owner, insecure directory permissions, final path symlink, root execution refusal and invalid descriptor.
- Preservation of exact original ciphertext bytes, file inode and mode throughout inspection.
- Regression of existing sealed vault, offline archive manager, exact request binding and cumulative deadline on main.

There is no real service UID, installed systemd unit, actual browser, production archive, private OS filesystem or workstation connection involved.

## WATCH OUT FOR

- **Read-only observation is not a security certificate.** A passing file inspection does not verify the full path ancestry, mount confinement, filesystem ACL/LSM policy, backup custody, active graphical seat, signed client or C5 human consent. The output explicitly declines these claims.
- The old ordinary-account source directory remains readable to programs with that same UID until an operator-authorized transfer and source-retirement plan is completed.
- SHA-256 confirms encrypted bytes during observed reads but not the AES-GCM tag or trusted browser origin. The service never gets the passphrase.
- Files can change between samples. Two consecutive identical readings cannot prevent a malicious concurrent writer or sudden power loss. Actual migration needs stronger transaction and recovery design.
- `SO_PEERCRED`, `SO_PEERPIDFD` and the existing cancellation guards are still deny-only. No positive archive access is connected.
- MACHINE owns this bounded feature. Connections C3e owns live signed process/seat evidence, C5 owns one-use human authorization, and the operator alone authorizes deployment/acceptance.

## CHECKLIST

- [x] Recheck Syntagma AGENTS/OPERATE, current main and open #1898/#1900 ownership
- [x] Develop strict non-root, read-only, pinned-directory inspection
- [x] Return metadata-only observations and explicit all-false trust/permission flags
- [x] Test real Linux browser-versus-service UID access denial and unsafe target refusal
- [x] Add independent workflow without editing #1900's pending seam
- [ ] Exact-head GitHub CI and independent Nurse 2 security review
- [ ] Operator merge/acceptance and separate explicit local installation approval
- [ ] Trusted service identity / target path ancestry and LSM policy validation
- [ ] Independent backup, approved migration/rollback, and real data custody
- [ ] C3e live client/seat witness, C5 one-use consent, protected TimeW UI and restoration

## NEXT / DECISIONS

The next MACHINE implementation can design an operator-reviewed **offline encrypted archive transfer plan and recovery ledger** under a distinct service principal, but must not execute one on real user data without explicit authorization, approved backup and independently verified OS identity. PR #1898 and #1900 remain independent review gates until GitHub reports them merged. No local system, browser profile, process, account or archive modified.
