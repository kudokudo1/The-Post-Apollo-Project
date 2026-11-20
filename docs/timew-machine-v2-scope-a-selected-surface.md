# 🏥💜 TimeW MACHINE // Scope A selected current surface, geometry only

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE · Desktop & Brave Recovery  
**STAFF ROLE:** External Hospital-compatible DOC (live Hospital registration unverified)  
**OWNER DECISION:** Operator accepted **Scope A FIRST, Scope B NEXT**, recorded at [issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067).  
**SOURCE:** [Connections/C3e per-surface proposal PR #2097](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2097), merged but implementation semantics still need SwayPX/C5 owner agreement.  
**STATE:** Source-only pure read-only fixture preflight, not an installed trust or consent provider. **PRODUCTION HOLD.**

## IMPLEMENTATION

### Fundamental mechanism

Scope A addresses one selected live *compositor surface* already present in the current seat/session: its current rectangle is compared against a saved checkpoint's rectangle. This operation does not claim to know *which Brave browser window* the surface corresponds to. Two same-app or same-PID Brave windows remain distinct **only if a future protected SwayPX service genuinely witnesses an operator selecting one exact live surface and revokes on its destruction/reuse**. A caller-provided ID, focus history or title cannot achieve this. Scope A is not tab recovery, restoring a closed window, cross-session Brave identity or automatic monitor remapping.

`services/time/MachineV2SelectedSurfaceReview.py` introduces **only** a new *provisional* structural review format and a pure review operation:
- Proposed `schema=post-apollo.timew.selected-live-surface.review.v1` and `audience=timew-selected-live-surface-geometry-only`, **separate from** `MachineV2PairConsent.py` Brave PAIR v1 and its required `browser_window_ref`.
- Candidate fields: challenge SHA-256, selected checkpoint/window key, live Sway con_id, app/output/workspace, current and saved rectangles, seat/session UUID, selection UUID, putative compositor epoch, putative per-surface lifetime UUID/generation and bounded time. This prototype does **not** authenticate, sign, mint or grant any of them.
- Cross-checks a caller-provided list of observed surfaces with unique con IDs and lifetime tuples, exact selected surface, unchanged epoch/generation and rectangle, and saved/live geometry supplied by the existing `MachineV2FloatingPilot.prepare` read-only double-Sway preflight. The **selected surface** must be floating and non-fullscreen; **unrelated** correctly typed tiled/fullscreen surfaces are permitted so ordinary mixed desktops are not needlessly refused. It still rejects malformed observation state, changed selected app, state, output/workspace, monitor configuration, stale candidate and changed saved target.
- **All** results, including fixture-consistent cases, return `read_only=true`, `restore_allowed=false`, `production_authorized=false`, `source_origin_verified=false`, `compositor_surface_lifetime_verified=false`, `active_seat_verified=false`, `c5_operator_consent_verified=false`, `one_use_grant_spent=false`, and `safe_actions=[]`.
- No compositor IPC implementation, signed grant, trusted callback, signer key, C5 approval, local daemon, command runner, installed process or UI route is added. Existing TimeW geometry and Brave PAIR v1 source remain unchanged.

The 5-second **fixture-only** timing cap is not a proposed production consent lease. SwayPX/C3e/C5 owners must agree on the actual expiration and revocation contracts.

### Scope B remains distinct

Scope B later requires independently authenticated Brave-window instance ↔ Wayland surface binding under protected source provenance. It may then unlock actual window matching, browser restarts and extra tab/session restoration work. No Scope A field may be silently interpreted as browser identity or mapped into Brave PAIR v1 by manufacturing a `browser_window_ref`.

## HOW TO USE

For disposable GitHub Actions fixture review only:

```bash
python3 -m pip install cryptography==46.0.4
python3 -B -I tests/timew/test_machine_v2_selected_surface_review.py
```

The dedicated workflow reruns existing Brave signed-verifier, geometry journal, V2 read-only review, pilot and one-click Restore tests. This PR does not offer a UI control or permit local Sway changes.

## VERIFY

Tests use a saved two-window geometry checkpoint, temporary SQLite storage, a double-read fake Sway, two same-app/same-PID Brave-like floating windows **plus unrelated tiled and fullscreen windows**, and a synthetic selected-current-surface record. It refuses duplicate or swapped con_ids, wrong generation/epoch/lifetime, stale time, wrong session/seat/challenge, changed rectangles, fullscreen/nonfloating state, changed output/workspace, different checkpoint/window selection, unknown fields, inappropriate Brave schema/audience or `browser_window_ref`. Successful *consistency* is still **not independent provenance**.

## WATCH OUT FOR

The proof source is missing. The future SwayPX owner must define an **actual compositor-internal, protected, revocable operator-selection and per-surface lifetime hook** that cannot be spoofed by caller JSON. Connections C3e/C4b must separately enroll the protected native issuer/release/root, and C5 must provide a TimeW-specific per-operation visible human approval, unlocked-seat proof and protected one-use spend. None exists as a verified production integration. A same-session geometry operation must stop if the selected surface is destroyed, reused, moved, or changed before either non-atomic command. UNKNOWN and partial dispatch require manual recovery, never automatic retry.

This review code is intentionally **not** a positive authorization pipeline. It does not call the geometry executor, and its returned data must never be promoted to production trust merely because all fixture checks pass.

## CHECKLIST

- [x] TimeW operator direction: A first, B later
- [x] Read-only provisional Scope A schema/audience distinct from Brave PAIR v1
- [x] Synthetic same-app dual-window, lifetime/seat/session/generation and geometry refusals
- [x] No SwayPX, C3e/C4b, C5, QML or existing signed Brave source mutations
- [ ] Exact-head CI and independent Nurse 2 review
- [ ] SwayPX owner accepts a real protected selection/lifetime source
- [ ] C3e/C4b owner accepts and implements approved enrollment/provenance
- [ ] C5 owner accepts and implements an exact TimeW-only protected grant
- [ ] TimeW approved native consumer integration + separate headless and Fedora/SwayPX acceptance
- [ ] Explicit operator merge and production activation decisions

## NEXT / DECISIONS

This draft begins **TimeW-side review engineering**, not final schema approval. Hand off the exact-head CI result and source to Nurse 2, SwayPX, C3e/C4b and C5 via [issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067). Keep the production HOLD, and do not touch the active CloseButton/TimeW UI migration or the operator workstation.
