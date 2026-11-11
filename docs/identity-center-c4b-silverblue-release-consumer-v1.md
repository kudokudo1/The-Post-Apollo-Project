# 🏥💜 Identity DOC // C4b Silverblue release candidate consumer V1

## IMPLEMENTATION
The Identity-owned `services/identity/silverblue_release_candidate_v1.py` is a
**CI-only, deny-only reader** for C4b's *proposed* [Identity signed RPM/release
contract #1785](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1785).
This implements the **source-envelope compatibility seam**, not a Silverblue
installed-host witness. The format is pinned to C4b's Phase 1 head
`0f18f3f2be394e4930787c5ffaf621e1e92df570`, as inspected November 10.

The consumer checks exact C4b `postapollo.identity.c4b.silverblue.synthetic-release.ci-v1`
schema, purpose-bound signature domain, deny-only role, package, disabled test
unit, complete nine-file roster, strict canonical JSON, Ed25519 release-root
signature, monotonic minimum epoch/sequence, separate pinned receipt public key,
and **independently measured** RPM SHA-256 and nine file digests. Rejects wrong
root, signer, RPM, modules, unit, role, replay floor, duplicate or extra fields.
The independently supplied values are caller responsibilities: **never derive
them from the candidate signed manifest, gateway socket, QML or guest UART.**

On valid synthetic input it returns only `SilverblueReleaseCandidateV1`
metadata, with `installed_guest_measured`, `host_authenticated`,
`production_authority`, `can_begin_sign_in` and
`credential_actions_enabled` all **false**. No native command or installed
process is contacted and there is no consumer path to grant credentials.

## HOW TO USE
Run the dedicated Identity C4b release-candidate CI workflow; inspect adversarial
tests in `tests/identity/test_silverblue_release_candidate_v1.py`.
CPU++ Sign In/Cancel/Retry stays disabled. Do not install/execute on Fedora.

## VERIFY
- [ ] Exact-head Identity CI and Meta Apollo Grammar checks.
- [x] Identity-owned candidate only; no modifications to C4b's worktree.
- [x] Source contract copied from C4b's **proposed draft** with test-only purpose and separate receipt/public release-root identities.
- [ ] Independent C3e review of alignment and trust provenance.

## WATCH OUT FOR
This does **not** certify an RPM's installed ownership, a genuine rpm-ostree
deployment, systemd MainPID/start, SELinux confinement, logind seat, two-boot
rollback, protected release-root custody, or C5 human consent. It is deliberately
not wired into existing `InstalledIdentityCommandAdapterV1` because that
adapter's `InstalledGatewayWitness` is dpkg-specific. A signature on a synthetic
manifest is not equivalent to an installed process or operator permission.

## CHECKLIST
- [x] Strict test-only envelope parser and independent pin comparison
- [x] No production-authorization interface; all authority stays false
- [ ] C4b actual signed Silverblue installed-host/rollback evidence and a
      separately reviewed native witness API
- [ ] C5 independent human one-use authorization, expiry and seat/lock binding
- [ ] C3e contract review, then Identity installed-native bridge and final acceptance

## NEXT
**C4b:** supply and test the actual installed Silverblue Identity gateway
independent witness, including exact policy/keys, package, process/cgroup,
SELinux/seat/rollback, release floor and failure semantics.
**C3e:** independently review this **synthetic read-only interface** against
#1785, especially source digest provenance, root custody and trust-promotion
prohibition. **Identity DOC:** adapt only to the *accepted* installed-host
witness when available; do not use CI result as production evidence.
**C5:** separately supply the one-use real operator consent contract.

## DECISIONS
GitHub Identity-only code/docs/CI branch and draft PR; no local workstation
writes, CI key promotion, real IdP/provider action, C4b/C3e/C5 source edit,
production admission, automatic merge or live Hospital registration. User retains
final authority.
