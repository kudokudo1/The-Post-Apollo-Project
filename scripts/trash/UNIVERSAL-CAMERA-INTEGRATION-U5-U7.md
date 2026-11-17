# 🏥💜 Trash++ // U5–U7 Current-Main Integration Checkpoint

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Trash++ Universal Resource Lifecycle  
ROLE // Hospital-compatible external DOC (live Hospital attachment unverified)  
ASSIGNMENT // Reconcile U5 Gallery, U6 Cleanup queue and U7 Desktop screenshot controls onto current `main`, with safety regression  
BASE // `e3aac84a341d25de30e34c514a972fa5f62cbb16`  
ORIGINAL U5/U6 PR // #1967 at `aec59ac411f649288b0d6d20c21ae26b05b5d943` (open, unmerged when this reconciliation began)  
U7 TESTED SOURCE // `d7cff89d03dd77375f86b9ca79de3b3b8d8d129e`, PR #1974 (merged to the U6 feature branch, not `main`)  
INTEGRATION BRANCH // `feat/trashpp-u5-u7-main-integration-20261117`

## IMPLEMENTATION
This branch begins at latest verified `main` and copies the exact 14 *previously tested U7 head* source/test/runbook file blobs, which carry U5 and U6 as well. The only feature-owned path also changed on `main` since U5's old base is `.github/workflows/trash-bottom-left-launcher.yml`. That file is **not copied wholesale**: its current-main contents, `components/qmldir` trigger, U1/U3/U4 Restore and all other existing test steps are retained. U5, U6 and U7 Node regression steps are added alongside U4.

Existing `main` `components/qmldir` (startup fix PR #1976) remains present, as do `modules/Trash.qml` and `scripts/camera/camera_cli.py` unchanged. No new source operation or global delete power is introduced. All three UI source adapters still hand off to the unchanged, Camera-owned one-use/GIO backend. No protected Archive, Media, Hospital or Clock source files are modified.

- U5: one selected Camera Gallery file, previewed plan and explicit shared TRASH confirmation.
- U6: marked Batch/Grid/Swipe/Hunt queue, scoped revision and explicit final shared TRASH click.
- U7: previewed Desktop screenshot-like files, one-use plan, explicit final shared TRASH click.
- Restore remains separately owned U4; shared BURN in these Camera controls is disabled.

## HOW TO USE
**Review only** until merge approval and authorized workstation sync. After permitted activation, open Camera Gallery for U5 selected file TRASH; Trash++ → CLEANUP → queue for U6; or Trash++ → CLEANUP → DESKTOP → PREVIEW MATCHES → TRASH for U7. The original backend independently authorizes, scopes and performs recoverable GIO moves.

## VERIFY
- Rechecked current `main`, Syntagma `AGENTS.md` and Hospital/permission/working guides before construction.
- Mainline changes since the U5 base affect the integration file set only at Trash CI workflow; original U7 source/test blobs therefore transfer without overwriting another worker's current Camera changes.
- Exact-head CI must run the revised Trash workflow, Camera M1, GitHub Grammar and remaining relevant checks. Test claims are recorded after actual results, not presumed.
- Native all-size Quickshell visuals, host file recoverability and user acceptance remain separate from CI.

## WATCH OUT FOR
- The pre-existing U5 PR #1967 remains independent and would overlap this proposed single integration PR. Select **one** approved mainline route; never merge duplicate feature branches blindly.
- Clock's B2B2–B2B5 signed test jobs on old U5 were failing a mixed-history file-scope comparison; this clean current-main descendant should not bring Clock-only commits into this feature PR. If red checks recur, examine raw logs; do not weaken Clock owner protections.
- Only repository Git objects/branch changed. No local machine modification, real GIO move, file Burn, production authority grant, live Hospital registration, or PR merge.

## CHECKLIST
- [x] Reconfirm main, all U5/U6/U7 PR and Syntagma states
- [x] Compare 75 current-main commits and U5/U6/U7 file scopes
- [x] Preserve exact Camera-reviewed feature/test file content and mainline U4 / qmldir paths
- [x] Combine U4+U5+U6+U7 workflow regression tests
- [ ] Exact-head CI and any test repairs
- [ ] Independent review and operator route/merge decision
- [ ] Post-merge CI, authorized native UI + disposable-file restore verification

## NEXT
Complete exact-head test checks and handoff. Then independently review the clean integration PR against #1967 and request an explicit operator decision before choosing a mainline landing route. U8 Media inventory stays a separate owner-specific step.

## DECISIONS
Create a new scoped draft integration PR rather than overwrite open U5 feature history or merge existing PRs. Preserve main source-owner interfaces; no automatic merge.
