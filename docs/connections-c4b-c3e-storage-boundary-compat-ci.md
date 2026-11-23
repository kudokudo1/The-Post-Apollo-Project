# 🏥💜 DOC 2 // C4b denial-to-C3e protected-HOLD compatibility

PATIENT: The-Post-Apollo-Project  
ROOM / STAFF: Universal Connections C4b Silverblue Gateway / DOC 2  
STATE: Source-only, disposable CI. Production HOLD.

## IMPLEMENTATION

The accepted C4b real Fedora Silverblue native baseline is PR #2211. It already exercises the unchanged C3e-AH checker against the actual running service, including signed DENIED receipts, SELinux process measurements, negative tamper cases and two-reboot rollback. This milestone does not change the native runner. The existing PR-path filter automatically triggers a fresh real-KVM regression on this new test file; that run must be assessed separately, and the previous #2211 acceptance remains the independent baseline.

The merged DOC 1 storage-independent semantic interface is PR #2229. Its LOCAL_DEVELOPMENT_ONLY mode uses the disposable SQLite ledger; INDEPENDENT_CUSTODIAN_REQUIRED deliberately has no protected backend and returns INDEPENDENT_CUSTODIAN_UNAVAILABLE_HOLD.

This DOC 2-owned compatibility probe imports both original implementations without modifying them. It first verifies the exact signed BEGIN UNAVAILABLE frame against the supplied CI controller challenge using the existing C4b code. It then constructs DOC 1 TrustBoundary in protected-required mode with no local adapter. It refuses any extra, changed, or authority-positive fields, and exposes only fixture diagnostic digests plus a required HOLD status.

Four additive files: one C4b CI compatibility helper, one 14-case hostile suite, a dedicated workflow and this document. No native gateway, identity service, enrollment root, protected signer, C5 grant, network socket, SQL store, provider credential or workstation setup is introduced.

## VERIFY

The dedicated workflow exercises 14 new compatibility tests, original C4b controller challenge attacks and the original C3e storage-boundary/no-local-fallback suite. Tests cover invalid/stale challenge, substituted public key, altered signed frame, duplicate UART proof, forged grant flags, altered protected HOLD status, fake remote-looking adapter, and assertion that a valid CI denial does not access local SQLite.

Tests use a freshly generated fixture signing key solely within the test suite. These results do NOT establish independent root enrollment, actual installed-host identity, protected nonce spend, current history, human consent or release authorization. Original #2211 real KVM native PASS remains separate. This PR's automatically triggered official KVM regression is also a required verification result, not evidence of new protected authority. All production authority flags remain false.

## HOW TO USE

Use the pull request's GitHub-hosted workflow. Nothing is installed on the operator's machine. Do not package this under the actual Silverblue identity RPM.

## WATCH OUT FOR

This is an explicitly nonauthoritative compatibility check of two existing diagnostics, NOT a frozen network protocol or future production evidence provider. The fact that a guest-local public key can verify a signed denial does not make that key operator-enrolled. The protected custodian has yet to be provisioned, reviewed and approved. No implicit fallback from protected mode to disposable SQLite is allowed.

## NEXT / DECISIONS

Independent Nurse 2 source review and operator merge decision remain separate. DOC 1 and an appointed protected-custody owner must later authorize actual current-state/nonce/host origin semantics before DOC 2 designs a production-grade transport or active-seat enrollment. No Sign-In activation.
