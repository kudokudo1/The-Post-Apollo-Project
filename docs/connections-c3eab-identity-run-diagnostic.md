# 🏥💜 Connections C3e-AB // C4b real Silverblue full-run diagnostic boundary

PATIENT // The-Post-Apollo-Project
ROOM // Universal Connections · protected C3e actual host evidence intake
STAFF ROLE // DOC · original protected Connections developer
CONCURRENT OWNER // C4b Silverblue worker, PR #1785
ASSIGNMENT // Distinguish genuine partial guest observations from claimed full two-boot rollback before protected release/host trust admission
STATE // CI-only diagnostic. This is not independently authenticated host evidence.
PRODUCTION // HOLD

## IMPLEMENTATION
Original C3e-AB comprises a DOC-owned read-only marker parser, its adversarial tests, a lightweight CI workflow and this document. The C3e-AC follow-up tightens these same four protected-DOC-owned files. No C4b, Identity DOC, C5, runtime broker, workstation or production files edited.

At the November 16 checkpoint, C4b owner's PR #1785 at `ec9c7c0069821865714291912947fce512df047a` passed all four workflows, including real official Silverblue run #43431743641. Its bounded `c4b-identity-silverblue-guest-markers` artifact was uploaded with one-day retention and has expired. The C3e-AC source contract is based on C4b's reviewed `sanitize_guest_marker_artifact.py`, which strips QEMU/UART prefixes and emits ASCII-only marker lines. Its VM job checks *both* an enforcing custom SELinux domain, signed four-command denials and independent AF_INET refusal **and** a second reboot with complete OSTree rollback, keyring and test policy removal. Missing any stage returns a nonzero runner exit.

C3e-AB/AC treats the artifact as **untrusted diagnostic data**, never an attestation. It accepts at most 65,536 bytes and 200 bounded ASCII marker lines. C3e-AC requires every line to start with `C4B_ID_`, to have canonical marker framing (`C4B_ID_KIND // printable value`), and to contain no prefix, trailing whitespace or control bytes. It refuses `UNVERIFIED REPORT: C4B_ID_PASS // ...` and raw UART serial prefixes rather than treating embedded tokens as stage evidence. It searches ordered, exact stage markers from the C4b script, not arbitrary mentions in journal/details. It distinguishes ordinary duplication of heartbeat/console lines, including nested guest FAIL/BLOCKED tokens inside journal detail, and enforces exactly one final numeric VM exit marker, expected enforcing SELinux context, four individual UNAVAILABLE actions, separate kernel network denial, service teardown, and the final rollback stage.

A stage-complete CI result requires all required markers *in order*, zero VM exit, caller-reported completed SUCCESS workflow, and no C4b FAIL/BLOCKED markers. A log showing SELinux and teardown but lacking `rollback_pending`, `REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED`, `TEST_KEYRING_REMOVED_AND_PRODUCTION_DISABLED`, and the final complete two-boot marker is explicitly **incomplete**. Missing/contradictory/malformed input refuses at the strict gate.

Even a complete matching marker sequence is only `COMPLETE_MARKER_SEQUENCE_ONLY_NO_HOST_ATTESTATION`. All origin/key/rollback-external/host/C5/credential/sign-in/production flags remain FALSE. The requested workflow status is also caller-supplied. No file signature, independently trusted GitHub OIDC source, independent release root, signed kernel witness, logind seat, external issuer or rollback-resistant challenge is enrolled by the parser.

## HOW TO USE
Read `tests/connections/c3e_release_trust/C3eABIdentityRunDiagnostic.py` and its tests. The dedicated GitHub `connections-c3eab-identity-run-diagnostic.yml` workflow runs entirely against disposable, synthetic marker fixtures and no actual user system. The module may later be used offline to classify already available CI markers, but it cannot certify real installed-host identity or justify production authentication. The current GitHub PR does not download another worker's artifact, does not require it to persist, and does not edit their workflow.

## VERIFY
- [ ] Twenty-five C3e-AB/AC negative and complete-marker tests, exact-head CI.
- [ ] Grammar and any triggered existing regressions PASS.
- [ ] Independent Nurse 2 exact-head audit before a protected DOC merge.
- [ ] C4b worker separately proves full official VM run SUCCESS with actual two-boot rollback, then independent signed host-provenance/enrollment and replay issuer review.

## WATCH OUT FOR
**Historical partial C4b evidence:** Real run #43144030036 was previously inspected. Its logs show official installed signed guest, enforcing `postapollo_identity_ci_t`, nonroot four signed UNAVAILABLE denials with kernel checks, independent AF_INET refusal, and test SELinux module/service cleanup. However the workflow failed with code 2; its recorded output does not show the required final service-probe-finished stage, rollback_pending stage, RPM layer removal, test keyring removal or host-side two-boot PASS marker. This is technical progress, not proof of the complete rollback requirement. The later C4b full-run repair and successful #43431743641 supersede that earlier failed VM outcome for C4b implementation status; the short-lived sanitized artifact still needs regeneration for a fresh independent C3e intake.

A console line is not a signed kernel measurement. An attacker can forge a complete log or the caller-reported workflow conclusion; C3e-AB would then report only internal consistency, and **all authorization flags remain false**. Distinct keys in one CI environment are not independently enrolled authorities. Signed C3e-X/Y/Z records remain synthetic until C4b delivers an authenticated witness producer, separately enrolled roots and an externally protected challenge issuer.

This gate targets the exact currently defined C4b marker vocabulary. If that worker changes its script and stages, the DOC owner must inspect and review the new boundary rather than inventing PASS markers or silently loosening required checks. This gate is intentionally not the older C3e-U/V/W guest-status importer, which belongs to the different Connections status service.

## CHECKLIST
- [x] Reacquire Syntagma/Hospital rules, DOC scope, merged C3e-AA and active C4b latest source/head.
- [x] Inspect real C4b #43144030036 job logs and source marker contracts.
- [x] Add read-only stage-completeness diagnostic and C3e-AC strict marker-only regression cases (25 total).
- [ ] Exact-head CI and independent NRS-2 audit.
- [ ] C4b full rollback authenticated CI result and independently observed actual process-origin witness, not just self-reported log.
- [ ] Separate C3e external rollback-resistant challenge authority, C5 user-consent and operator final production approval.

## NEXT
Verify the C3e-AC 25-case CI on the exact branch head, request independent Nurse 2 audit, and ask the C4b owner for a newly retained/sanitized artifact from a fresh successful run. Independently establish GitHub source/run/artifact provenance before classifying real evidence. Next integration requires separately protected external signing/issuer custody and actual host-origin/seat evidence. Do not merge or activate production without appropriate approval.

## DECISIONS
C3e-AC tightens diagnostic input framing only and remains CI-only; no host permissions, keys, credential actions, native adapter changes, C4b code writes, user workstation modifications or live Hospital registration. Operator retains final acceptance.