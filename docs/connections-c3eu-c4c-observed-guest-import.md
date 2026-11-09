# 🏥💜 Connections C3e-U // Actual C4c guest self-observation into DOC diagnostics

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · protected host evidence transfer  
STAFF ROLE // DOC · Original protected Connections development  
ASSIGNMENT // Consume the **existing C4c** running signed-host observation format without promoting its authority  
CONCURRENT OWNER // C4b/C4c signed Silverblue guest and rollback; TASKS C5 authorization  
PREDECESSORS // C3e-T #1643 merged; C4c #1646 merged; C3e-S #1627 merged  
PRODUCTION // HOLD

## IMPLEMENTATION

The original C3e-T goal was read-only measurement of the real C3d signed Python status service during the already-passing, booted Fedora Silverblue guest. C4b's owner independently implemented **C4c PR #1646**, merged into main. Its exact-head real [signed offline Silverblue #42638232336](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42638232336) passed both real boots and the fail-closed C4b runtime/source tests.

Unlike C3e-T's optional CLI, C4c now performs the actual guest observation itself. While the same service remains running, *after C3b verified systemd/D-Bus/SELinux identity* and before service stop, the C4c guest checks the signed C3d RPM with an isolated disposable RPM signer/keyring; the signed RPM's **three file-header SHA-256 values** for its exact host script/unit/bus policy against immutable root-owned installed bytes; actual kernel service PID/start/4x UID/GID and D-Bus process/user owner; interpreter inode and separate SHA-256; `--read-only` invocation; and real RPM package ownership. C4c emits `C4B_OBSERVED // {…}` JSON inside its guest.

**C3e-U is the smallest DOC-owned receiving side for this existing real C4c format, not a duplicate guest collector.** It:

1. Accepts *one bounded* `C4B_OBSERVED //` line, with no unbounded guest-log ingestion, unknown or duplicate JSON fields, or lax numeric types.
2. Validates the **exact fields the actual merged C4c guest source returns**. Its tests parse C4c's embedded `observe()` Python AST instead of relying solely on a manually invented sample.
3. Requires externally supplied expected signed RPM SHA-256, installed script SHA-256 and interpreter SHA-256, plus expected service PID/start/UID/GID, from an independently controlled verifier. Never accept the producer's own hashes as sole proof.
4. Refuses mismatched root/signed payloads or process identities, wrong systemd unit/SELinux state, claimed authentication or credentials, trailing lines and extra/duplicate fields.
5. Returns only a **diagnostic compatibility receipt**, always `installedGuestMeasured:false`, `signedGuestOriginAuthenticated:false`, `evidenceCryptographicallyAttested:false`, `hostAuthenticated:false`, `canApprove:false`, `credentialActionsEnabled:false`, `productionAuthority:false`.

The C3e-U CLI reads the bounded line from stdin and prints a single JSON diagnostic/refusal. It never signs the guest claim, issues a C3e-Q challenge, writes a C3e-R durable ledger entry, grants a provider credential or edits a C4b/C4c owned source file.

## HOW TO USE

Source-only GitHub CI runs `.github/workflows/connections-c3eu-c4c-observed-guest-import.yml`. It validates against the *actual C4c source-defined producer schema* and 18 adversarial local input cases, plus C4b/C3b and C3e-Q deny-only regressions.

A future owner-controlled real evidence handoff would extract one validated `C4B_OBSERVED //` line from C4b's signed guest test results and supply **independently verified** hashes and process identity. That requires the C4b owner to decide how to export the bounded report as a reviewable guest artifact while preserving the current two-boot rollback and cleanup. This PR itself does not alter the guest, its CI log collection, or the C4b owner workflow.

## VERIFY

- [ ] 18 new cases, including producer AST schema compatibility, strict pin/refusal checks and CLI, pass on exact PR head.
- [ ] C4b signed service source policy, C3b installed origin and C3e-Q detached signature tests remain green.
- [ ] Meta Apollo Grammar and root-pinned/signed RPM release checks remain green.
- [ ] Independent security/owner review and operator merge disposition.
- [ ] **Real guest output** collected from the C4b owner, with independent package verification and protected transport, before stronger claims.

## WATCH OUT FOR

The **actual real guest UART JSON is not exported** as a standalone artifact in the successful #42638232336 workflow. The positive C3e-U local unit-test report therefore uses *synthetic values matching the exact real C4c source schema*. It is source-contract compatibility, **not authenticated C4c guest evidence**. Repeating the exact schema, passing independent *caller-supplied* pins, or seeing real host-process checks in a separate CI step does not prove that a hostile guest or controller has not fabricated the plaintext report.

Even if the guest result is later exported, it is still only **guest self-observation**. For protected C3e-Q/R/S use, an independently enrolled signer, challenge origin, trusted report transport, signed actual package reference, durable anti-replay outside the compromised guest, and operator-authorized consent remain separate requirements. Do not sign arbitrary C4c diagnostic JSON under a disposable local key and call it verified attestation. C3e-U deliberately produces **no Q-compatible signed envelope** and no authority escalation.

The C4b/C4c owner has delivered the actual signed-host in-guest measurement; C3e-T was not specifically invoked, and duplicating it would not strengthen the signed package checks C4c already performs. The remaining problem is exporting authentic evidence into DOC and ultimately binding it to an independently protected witness.

## CHECKLIST

- [x] Verify C3e-T #1643 and C4c #1646 merged into current main.
- [x] Verify corrected exact-head C4c real offline signed Silverblue workflow passed.
- [x] Inspect actual C4c schema and C3e-Q/R/S trust boundary.
- [x] Implement read-only source-checked importer without editing C4b/C4c files.
- [x] Add new adversarial CLI/source contract tests, CI and handoff.
- [ ] Repair any observed C3e-U CI failure within DOC lane.
- [ ] Independent review/merge authorization and operator acceptance.
- [ ] C4b owner's bounded real guest report export and signed independent report issuer.
- [ ] C5 genuine operator consent, production identity authority and first provider transaction.

## NEXT / DECISIONS

**Next technical target:** capture a bounded C4c `C4B_OBSERVED` record as durable CI evidence from the **real running guest**, without modifying existing security requirements or falsely upgrading it to remote attestation. Coordinate exact location/transport with C4b owner through [handoff #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606). Keep C3e-U draft and additive, on direct main, without any secret/provider/system change.

Production HOLD, no local workstation modification, no live Hospital registration or cross-worker ownership transfer.
