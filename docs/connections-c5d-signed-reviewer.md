# 🏥💜 Connections C5d // Distinct signed reviewer process (CI only)

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // TASKS encrypted recovery ↔ Connections protected consent
STAFF ROLE // External Hospital-compatible DOC; live Hospital staffing/lease unverified
ASSIGNMENT // C5d separately signed reviewer-program identity and sender binding; no human-consent claim
CHECKPOINT // C5c PR #1535 merged at `10ff840fb2c4afb6e67174b6e6c358f27ebe9c36`
AUTHORITY // Operator November 8 "continue", GitHub-only bounded security development. No desktop, Fedora, keyring, permissions activation, real TASKS draft text, saved-source writer, host installation, merge without green checks or production credentials.

## IMPLEMENTATION

C5c established the signed application code identity of a compiled **client** before C5b would bind it. C5b still trusted the reviewer descriptor's original kernel socket-creator identity. A transferred reviewer FD from the original harness was not separately tied to a signed reviewer executable. C5d tests that missing boundary.

- `services/connections/experiments/C5dSignedReviewerHost.py`: CI-only C5c/C5b subclass; requires a separately signed, exact-role **reviewer ELF**, independently bound to host-launch configured PID/UID/GID and kernel start ticks. The host gets actual sender credentials from `SO_PASSCRED` on *every reviewer packet*. It compares the kernel executable bytes to the exact SHA256+size in an independently pre-pinned test root signed reviewer policy and delegated signed manifest. Reviewer's identity is checked on every command, including `bindClient`, `approve`, `revoke` and `shutdown`, and executable bytes are re-read to reject PID-stable binary substitution.
- Minimal C5b seam: original `allowed_reviewer(sender, original)` preserves the existing default C5b kernel-origin behavior. C5d overrides this to authenticate the separate reviewer. The shutdown condition uses the authorized result, not socket creator PID, so a correctly signed distinct reviewer can end its own disposable test host.
- Minimal C5c seam: its offline root/delegate policy check permits an explicit, exact role argument. Existing C5c uses its unchanged default TASKS test-client role; C5d requires the **different** `postapollo.connections.test-reviewer.v1` role.
- `tests/connections/fixtures/C5dSignedReviewerDummy.c`: a second compiled program with only reviewer-side messaging. It accepts test harness JSON instructions, not user interaction. An unauthenticated client cannot send review instructions or access the reviewer-only kernel FD.
- `tests/connections/test_connections_c5d_signed_reviewer.py`: generates temporary GPG root, two delegated signing identities, exact signed compiled client and reviewer manifests, distinct real subprocesses and a separate host. Tests correct scope + one-use, same-user wrong reviewer ELF, forwarded descriptor spoof from an unauthorized process, separately signed role substitution, root/signature/floor refusal, durable revoke and client self-approval denial. The dedicated CI reruns C5c, C5b, C5a and TASKS M15e/M15d/M15c writer/credential gates.

**No human consent is verified.** The test harness feeds instructions over the reviewer's stdin. Both fake reviewer and caller are compiled disposable test executables in the same temporary CI job; the host does not manage credentials, session lock state, real source, operator identity, approval prompts or secrets. All C5a/C5b actual-grant flags remain false.

## HOW TO USE

No workstation action. The only behavior is a GitHub Actions disposable Linux process test. Production TASKS → SYNC → RECOVERY → CAPTURE remains disabled for SAVE ENCRYPTED DRAFT, unlocked preview and clear.

## VERIFY

Required at exact reviewed head:
1. Both OS processes are different compiled ELF programs and independently verified against different signed roles, not a shared shell or claimed PID label.
2. C5d refuses approval, revocation and shutdown from an unsigned same-UID reviewer, wrong/policy-swapped root, forged delegated key, bad role or insufficient release floor.
3. A copied reviewer FD in an **unapproved process** is denied by each packet's SCM_CREDENTIALS; even a signed TASKS client cannot self-approve on its client FD.
4. C5b's durable SQL approval, revocation, expiry, same-host crash refusal and all three exact TASKS scopes remain functioning, no production QML import and sole existing FileView writer preserved.
5. Existing C5c/C5b/C5a, TASKS and CPU++ CI paths green.

## WATCH OUT FOR

This is cryptographic **reviewer executable provenance**, not a trusted human decision. A CI harness can supply any JSON approval and signs its own temporary keys. There is no OS user session, no verified password or FIDO key, no secure in-desktop UI confirmation, no screen locking/liveness evidence, no remote protected authority, no tamper-proof key custody, no runtime dependency attestation, nor proof that a person viewed a particular task preview.

The stronger reviewer check still depends on Linux /proc and the test harness controlled trust pins and PIDs. It does not defend against root, compromised same-UID ptrace, mutable libraries, injected process memory, or a privileged host sending altered requests. A signer authorizes *code identity*, not arbitrary actions by that code. The eventual protected consent channel must bind a human decision to exact operation, target, source revision and a host-generated one-use challenge, with a genuine display/input trust boundary. UI-only checkbox is not permission.

The separate C4b Silverblue signed-confined installation branch remains under another worker's control (latest checked PR #1555). C3e release floors/witnesses also have separate source ownership. Do not promote this unmounted CI prototype to their release/service or host authorizations by inference.

## CHECKLIST

- [x] Confirm merged C5c, current main, Syntagma and current neighboring C4b ownership
- [x] Implement distinct signed reviewer program gate without changing production grants
- [x] Preserve C5b default semantics and C5c client policy compatibility
- [x] Add real Linux subprocess and signed policy adversarial tests, CI and documentation
- [ ] Review exact-head CI and repair actual defects
- [ ] Merge after green review within operator's standing GitHub authority
- [ ] Operator decides and authorizes actual protected human prompt/session requirement
- [ ] Coordinate signed/SELinux-protected host service and identity with C4b/C3e
- [ ] Host-owned real key lifecycle, one-editor capture, encrypted checkpoint, restart/preview/clear
- [ ] Native Fedora verification, user visual acceptance

## NEXT

A future C5e should prove **genuine user-presence authorization** via an independently trusted OS/session mechanism, not the client, a fake reviewer, a script, or UI self-approval. It must establish operator/seat/session identity and purpose-bound, one-time confirmation through an approved mechanism (for example, a properly registered Polkit authority using a separately launched authentication agent), without an unreviewed key release. Before production, this needs a design decision, a native Fedora sandbox, and ownership coordination with C4b/C3e.

## DECISIONS

Keep no real grants, no keyring, no saved source mutation, no Fedora changes, no runtime installation, no automatic replay and no forged "humanAuthenticated" flag. CI-only work is a verified technical mechanism once checks pass, not final user acceptance.
