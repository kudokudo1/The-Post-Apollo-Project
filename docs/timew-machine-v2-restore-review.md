# MACHINE // V2 restore review, deny-only (November 18, 2026)

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // TimeW MACHINE · Desktop & Brave Recovery
STAFF ROLE // External Hospital-compatible DOC; no live Hospital registration verified
ASSIGNMENT // Reconcile saved V1/V2 geometry against a fresh desktop observation without actuation
PHASE // Read-only integration; no merge or production activation authorized

## IMPLEMENTATION

`services/time/MachineRestoreReviewV2.py` is an additive, one-shot V2 review path.

1. Read a selected canonical UUID checkpoint from the existing read-only V1 SQLite loader and the independent V2 geometry reader. Reject cross-record mismatch, corrupt geometry, injected extra fields and positive authority flags.
2. Read the current Sway layout through the existing `stable_geometry()` double-observation function, using only fixed `swaymsg -r -t get_outputs/get_workspaces/get_tree` queries. No command IPC or background polling.
3. Classify every saved window by its checkpoint-local UUID **as a record key only**: missing/changed output, absent/relocated workspace, duplicate app instances, app not running, state/position changes or apparent rectangle agreement.
4. Return only bounded, allowlisted app/output/workspace and reason labels, never raw Sway IDs, titles, PID, URLs, commands or browser contents.

Crucial: `OBSERVED_GEOMETRY_AGREEMENT_UNTRUSTED` is **not restored** or authenticated identity. The duplicate-Brave case remains blocked even if both rectangles appear correct. Every result reports `restore_allowed=false`, `live_window_identity_verified=false`, `exact_geometry_restore_verified=false`, `browser_tabs_restorable=false`, `safe_actions=[]`, `requires_fresh_recheck=true`.

For V1-only checkpoints, the tool reports `legacy_only` without attempting a current Sway observation; its count stays in `needs_attention`.

## HOW TO USE

The existing TimeW one-click SAVE/RESTORE controls are **unchanged** by this source-only stage. There is no new button and no background service.

Developer-only, explicitly invoked **read-only** inspection on an installed, reviewed code copy would use:

```bash
python3 -B -I services/time/MachineRestoreReviewV2.py review <EXISTING-CHECKPOINT-UUID>
```

This reads the operator's existing checkpoint metadata and current compositor. It does not authorize any move, launch or browser access. Do not treat even a matching status as permission to restore. For automated verification use only the synthetic test below.

## VERIFY

CI command: `python3 -B -I tests/timew/test_machine_restore_review_v2.py`.

Uses disposable temporary `XDG_DATA_HOME`, synthetic two-monitor Sway geometry with two Brave windows and one Kitty window, actual V1/V2 atomic SQLite save and read, and injected live geometry. Covers ambiguous multi-instance refusal, different transient UUIDs, changed rectangle/output/workspace, missing output/app, duplicate live instance, fullscreen change, forged positive grants, extra private fields, corrupted cross-record consistency, invalid IDs, V1-only behavior and no accidental live read for legacy records. Runs inherited geometry, save bridge, one-click restore and UI contracts unchanged.

This is not native Fedora/SwayPX acceptance; the source does not run a compositor in CI. Exact-head CI, Nurse 2 security review and operator decisions remain separate.

## WATCH OUT FOR

- The saved V2 `window_key` is generated from ephemeral Sway container IDs or a one-capture namespace. It is **not** a durable Brave-window-to-Sway identity.
- Matching a sole app ID and rectangle is an **untrusted observation**. The planner never returns an executable placement plan.
- A different connected monitor or workspace is a hold; there is no invented fallback monitor choice.
- The existing `MachineRestoreCheckpoint.py` still performs only the prior bounded V1 restore and may report its own narrower completion. This PR **does not** change or silently replace that behavior.
- Brave's encrypted archive/broker remains separately deny-only. No C3e/C5 grants, browser secrets, native host registration, disk migration or real archive restoration are introduced.

## CHECKLIST

- [x] Recover canonical Syntagma and latest MACHINE head / ownership
- [x] Add pure V1/V2/live geometry reconciliation contract
- [x] Add additive read-only CLI and fixture-only negative tests
- [x] Add dedicated GitHub CI and this runbook
- [ ] Exact-head workflow results and raw step verification
- [ ] Independent Nurse 2 review
- [ ] Operator merge decision
- [ ] Separate future UI integration and authenticated multi-window identity
- [ ] Real protected Brave archive authorization and restore
- [ ] Native SwayPX visual acceptance

## NEXT / DECISIONS

Keep as a **DRAFT PR**. After exact-head automated verification, arrange independent review. Only afterward consider wiring a read-only `REVIEW V2 RESTORE` control to TimeW, without touching the existing V1 RESTORE action. Actual V2 move, window creation, browser/tab restoration or live desktop activation requires separately authorized work. No local user machine changes are made here.
