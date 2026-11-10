# 🏥💜 Connections C3e-U // Actual C4c guest self-observation into DOC diagnostics

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · protected host evidence transfer  
STAFF ROLE // DOC · Original protected Connections development  
ASSIGNMENT // Consume the **existing C4c** running signed-host observation format without promoting its authority  
CONCURRENT OWNER // C4b/C4c signed Silverblue guest and rollback; TASKS C5 authorization  
PREDECESSORS // C3e-T #1643 merged; C4c #1646 merged; C3e-S #1627 merged  
PRODUCTION // HOLD

## IMPLEMENTATION

The original C3e-T goal was read-only measurement of the real C3d signed Python status service during the already-passing, booted Fedora Silverblue guest. C4b's owner independently implemented **C4c PR #1646**, merged into main. Historical [signed offline Silverblue #42638232336](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42638232336) reported overall SUCCESS, **but this is no longer sufficient evidence of C4c's signed running-host measurement**. An independent review on November 10 found that the merged guest script's `<<'C4B_RUNNING_HOST_PROBE' ||` command inserted an indented shell `fail` line into Python's standard input before `import grp`. That malformed Python could fail while the surrounding shell still printed `C4B_PASS // SAME_C3B_SERVICE_SIGNED_RPM_SCRIPT_AND_INTERPRETER_OBSERVED`. The older CI result may still support separately checked boot/rollback controls, but **not successful execution of that embedded verifier**. See [C3e finding #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606#issuecomment-6774220264).

Unlike C3e-T's optional CLI, the C4c guest source defines a same-service observation. **Successful execution of its embedded verifier is still a required live test**, not something C3e-U infers from source inspection or a historical PASS marker. Intended to run *after C3b's systemd/D-Bus/SELinux identity checks* and before service stop, the C4c verifier checks the signed C3d RPM with an isolated disposable RPM signer/keyring; the signed RPM's **three file-header SHA-256 values** for its exact host script/unit/bus policy against immutable root-owned installed bytes; actual kernel service PID/start/4x UID/GID and D-Bus process/user owner; interpreter inode and separate SHA-256; `--read-only` invocation; and real RPM package ownership. On successful execution, C4c is intended to emit `C4B_OBSERVED // {…}` JSON inside its guest.

**C3e-U is the smallest DOC-owned receiving side for this existing real C4c format, not a duplicate guest collector.** It:

1. Accepts *one bounded* `C4B_OBSERVED //` line, with no unbounded guest-log ingestion, unknown or duplicate JSON fields, or lax numeric types.
2. Validates the **exact fields the actual merged C4c guest source returns**. Its tests parse C4c's embedded `observe()` Python AST instead of relying solely on a manually invented sample.
3. Requires externally supplied expected signed RPM SHA-256, installed script SHA-256 and interpreter SHA-256, plus expected service PID/start/UID/GID, from an independently controlled verifier. Never accept the producer's own hashes as sole proof.
4. Refuses mismatched root/signed payloads or process identities, wrong systemd unit/SELinux state, claimed authentication or credentials, trailing lines and extra/duplicate fields.
5. Returns only a **diagnostic compatibility receipt**, always `installedGuestMeasured:false`, `signedGuestOriginAuthenticated:false`, `evidenceCryptographicallyAttested:false`, `hostAuthenticated:false`, `canApprove:false`, `credentialActionsEnabled:false`, `productionAuthority:false`.

The C3e-U CLI reads the bounded line from stdin and prints a single JSON diagnostic/refusal. It never signs the guest claim, issues a C3e-Q challenge, writes a C3e-R durable ledger entry, grants a provider credential or edits a C4b/C4c owned source file.

## HOW TO USE

Source-only GitHub CI runs `.github/workflows/connections-c3eu-c4c-observed-guest-import.yml`. It validates against the *actual C4c source-defined producer schema*, the original 18 adversarial local input cases, and a new exact-byte replay of the first real exported C4d observation; plus C4b/C3b and C3e-Q deny-only regressions.

The C4b owner has now exported a bounded real `C4B_OBSERVED //` line as [CI artifact `c4d-one-guest-observation`, artifact 13800918170, run #42894509754](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42894509754), after original two-boot rollback PASS. C3e DOC inspected that exact ZIP, reconstructed the one line for deterministic regression, and independently computed the signed/running **script** SHA from the exact CI-head tracked source. The other ephemeral RPM/interpreter/process pins still require **independent** signers/witnesses; the copied guest fields must never be used as production evidence. This DOC PR does not alter the guest, C2v, or C4b exporter.

## VERIFY

**2026-11-10 genuine exported-artifact review:** [C4b/C4d exact-head CI #42894509754](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42894509754) **SUCCESS**, head `fe1f1d0c9175c07a73f04c3c5bcdf611e486bea1`. Logs show both actual Fedora Silverblue boots/rollback, the signed C3d process check and `C4D_PASS // SIGNED_SILVERBLUE_TWO_BOOT_AND_ONE_OBSERVATION_GATE`. GitHub uploaded precisely one `C4B_OBSERVED.txt`, containing 18 expected fields and all six production-authority flags false. The new DOC regression reconstructs the exact original 819-byte artifact via its SHA-256 and replays it into the real C3e-U `inspect()` implementation. Only the signed/running **script** SHA is independently derived from tracked CI-head source. This CI test is **diagnostic compatibility**, not an independent proof of the signed RPM/interpreter PID custody.

**2026-11-10 evidence correction:** A corrected heredoc in the C4b-owned draft [#1756](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1756) now executes Python and refuses invalid observations. [Real exact-head Silverblue #42864373807](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42864373807) then failed closed with `SIGNED_RPM_PACKAGE_IDENTITY_REFUSED`; the original full two-boot/rollback gate did not pass and no artifact was exported. C3e-U/Grammar CI on that head passed, but **only as source/contract tests**. Newer owner draft heads may exist; always reacquire their run status instead of treating this historical failure as the latest.

- [x] C3e-U's 18 source-contract/CLI/adversarial tests passed in merged [PR #1653](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1653); these are not genuine guest artifact tests.
- [x] C3e-U's original CI regression suite passed; future C4b source/guest changes still require their own exact-head verification.
- [x] C3e-U exact-head CI and Grammar for this documentation correction passed; signed release checks remain a separate evidence boundary.
- [x] Original C3e-U [PR #1653](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1653) is merged. This documentation correction is a separate draft awaiting review.
- [x] **Real guest output** collected from the C4b owner's full successful CI run and one-line artifact; archive/entry digest and independently sourced script digest checked.
- [ ] Independently authenticated ephemeral RPM/interpreter/guest PID-start and protected transport/custody verified before stronger claims.

## WATCH OUT FOR

Historical #42638232336 exported no standalone real UART record. The **newer successful #42894509754** exported one bounded `C4B_OBSERVED.txt`. Its ZIP SHA-256 `ac083f693ac139058b22ea9dd2b0e37767a04f0c30e17fc45de3fdfce599c7a9` matches GitHub's published artifact digest, and the lone 819-byte line has SHA-256 `e3fa68a28a3160262632785d656855fa62a079dbf8e95c0d4e1e76aa5da44bb9`. The independent *repository source* script SHA-256 is `1bc6cc2030efc08f873bc8f73a9644d869482e3e70c6553a108ade9d97441ce5`, matching the guest's `signed_script_sha256` and `running_script_sha256`. Replaying other values **from the guest itself** exercises the importer format only and is explicitly **not independently pinned RPM/interpreter/PID evidence**. An attacker controlling the guest or controller could still forge plaintext.

Although the guest result is now exported, it remains **guest self-observation**. For protected C3e-Q/R/S use, an independently enrolled signer, challenge origin, trusted report transport, signed actual package reference, durable anti-replay outside the compromised guest, and operator-authorized consent remain separate requirements. Do not sign arbitrary C4c diagnostic JSON under a disposable local key and call it verified attestation. C3e-U deliberately produces **no Q-compatible signed envelope** and no authority escalation.

The C4b/C4c owner delivered the in-guest signed-host verifier, and #42894509754 demonstrated a corrected successful real guest run with the bounded export, signed-service checks and both original boot/rollback gates. C3e-T was not specifically invoked, and duplicating guest-owned measurements in DOC would not independently authenticate an unsigned observation. The remaining trust gap is a **protected, independent RPM/interpreter/PID-start witness and signed challenge/replay custody**, not guest plaintext availability.

## CHECKLIST

- [x] Verify C3e-T #1643 and C4c #1646 merged into current main.
- [x] Reconcile the historical C4c workflow's overall PASS with the later-discovered false-positive embedded Python success marker.
- [x] Verify corrected C4c embedded verifier, real two-boot rollback, and one bounded artifact are reported PASS in the exact-head CI run #42894509754.
- [x] Independently validate exported ZIP/line hashes, exact source-derived script digest and 18-field deny-only schema.
- [ ] Obtain independent authenticated RPM, interpreter, PID/start and anti-replay witnesses for anything above diagnostic compatibility.
- [x] Inspect actual C4c schema and C3e-Q/R/S trust boundary.
- [x] Implement read-only source-checked importer without editing C4b/C4c files.
- [x] Add new adversarial CLI/source contract tests, CI and handoff.
- [x] Original C3e-U source/contract CI passed on merge and remained green after the independent guest failure.
- [ ] Independent review/merge authorization and operator acceptance.
- [x] C4b owner produced a bounded diagnostic real guest artifact; PR #1762 remains subject to owner review/merge decision.
- [ ] Independently enrolled/protected signed report issuer and trust inputs; C3e-U does not implement them.
- [ ] C5 genuine operator consent, production identity authority and first provider transaction.

## NEXT / DECISIONS

**Next technical target:** complete independent review of the exported diagnostic against the existing C3e-U importer and record its exact source/ZIP/line provenance. The *script* pin is independently source-verified, but the ephemeral RPM/interpreter/PID/start pins and remote origin still need an independent signed witness before C3e-Q/R promotion. Do not change C4b-owned code or treat a guest self-report as protected authority. Coordinate exact location/transport with C4b owner through [handoff #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606). Keep C3e-U's diagnostic-only implementation on main; this evidence correction is independently reviewable as a draft, with no secret/provider/system change.

Production HOLD, no local workstation modification, no live Hospital registration or cross-worker ownership transfer.
