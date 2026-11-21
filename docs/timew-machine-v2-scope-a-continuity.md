# 🏥💜 TimeW MACHINE // Scope A per-command continuity, deny-only

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE · Desktop & Brave Recovery  
**STAFF:** External Hospital-compatible DOC, live Hospital session unverified  
**ORDER:** Scope A (selected current surface geometry) first; Scope B (specific Brave identity) later  
**STATUS:** Read-only synthetic fixture, no installed trust or production movement

## IMPLEMENTATION

Scope A compares an existing selected floating window to a saved rectangle. Geometry execution, however, is two non-atomic operations: **resize**, then **move**. The compositor may destroy, recycle, resize, reparent or move a window between them. A prior Sway container ID or signed packet is insufficient to prove the same live object still exists.

The new pure review module, services/time/MachineV2SurfaceContinuityReview.py, inspects exactly three **injected, untrusted test snapshots**:

1. **Before resize**: selected current surface still has its original rectangle.
2. **After resize**: same surface lifetime, compositor epoch, generation, container, app, output/workspace, and its expected new width/height with original x/y.
3. **After move**: same surface lifetime and final target rectangle.

All sample timestamps must remain monotonic and inside the fixture lease. Duplicate container IDs, duplicate lifetime tokens, compositor-epoch drift, changes to the selected surface or unexpected changes in unrelated observed surfaces refuse. Unrelated tiled and fullscreen windows are allowed when stable. Two Brave-like windows with the same app and PID are not treated as interchangeable.

**Every snapshot, session/seat assertion and clock is caller supplied.** Even a fixture that passes every check returns production_authorized=false, restore_allowed=false, safe_actions=[] and false native-provenance and consent fields. It does not sign, dispatch, spend a grant, talk to SwayPX, install a native issuer, or change the UI.

This structural test does **not** prove a native Wayland resize must preserve original x/y. A future independently verified SwayPX implementation must define real geometry and per-command revocation behavior, accounting for compositor constraints.

## HOW TO USE

Disposable CI only: run `python3 -B -I tests/timew/test_machine_v2_surface_continuity_review.py`. The existing Scope A GitHub Actions workflow will run the new test together with original signed Brave, journal, floating pilot and one-click Restore regressions.

## VERIFY

Hostile fixtures test same-app windows, selected surface reuse, changed compositor generation/epoch, wrong session, output and workspace, malformed state, duplicate lifetime/con IDs, changed unrelated tiled/fullscreen windows, incomplete resize, early move, expired/reversed clocks, wrong phase order, and Brave PAIR schema confusion.

Replaying a consistent synthetic fixture is **not** replay protection: protected one-use spending has not been implemented for Scope A. Unknown or uncertain partial dispatch requires **manual review**, not automatic success/retry.

## WATCH OUT FOR

- **SwayPX:** must own the protected, revocable compositor-internal operator selection and real lifetime evidence, not focus or ordinary GET_TREE JSON.
- **C3e/C4b:** must own independently enrolled installed issuer/release/process/seat provenance, not merely sign caller-provided fields. Connections draft #2107 is still synthetic and stateless.
- **C5:** must provide independent visible exact-operation approval, active unlocked seat and protected one-use spending. Hospital signers are not TimeW signers.
- **TimeW:** keep this mode separate from the signed Brave PAIR v1. No production Restore activation from this result.
- **Nurse 2:** independently review no-authorization output, command-gap races, window reuse, wrong seat, partial completion, and replay.
- **Operator:** retains merge, native installation and final production acceptance.

## CHECKLIST

- [x] Pure three-phase inter-command review with permanent authorization refusal
- [x] Hostile selected/other surface, expiry and identity tests
- [x] Preserve original Brave PAIR, geometry journal, existing UI and owner boundaries
- [ ] Exact-head GitHub CI and independent Nurse 2 review
- [ ] Real protected compositor witness and C5 consent
- [ ] Native acceptance and separate production approval

## NEXT / DECISIONS

Post checkpoint to issue #2067. **Scope A first, Scope B later; production HOLD.**
