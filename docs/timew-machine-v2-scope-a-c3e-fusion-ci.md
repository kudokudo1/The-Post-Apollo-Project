# 🏥💜 TimeW MACHINE // Scope A signed-source + continuity compatibility, CI ONLY

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE · Desktop & Brave Recovery  
**STAFF:** External Hospital-compatible DOC; no live Hospital registration verified  
**ORDER:** A first (selected current floating surface geometry), B later (verified specific Brave-window identity)  
**STATE:** Test-only integration / production HOLD

## IMPLEMENTATION

C3e already supplies a bounded, purpose-bound **test** proof for a selected-surface packet, and TimeW already provides a geometry preflight plus a three-snapshot continuity review. Before this increment, they were tested independently. A swapped checkpoint, changed challenge, mismatched surface identity, wrong signature purpose or stale release floor must not accidentally combine into a convincing TimeW result.

A new **test-only** TimeW consumer, `tests/timew/TimeWScopeAC3eFusionPreflight.py`, requires:
1. The same exact Scope A selected-surface claim and external-looking (but caller-supplied) 32-byte fixture challenge across the C3e test signature, TimeW initial saved/current selected-geometry review and three-phase continuity review.
2. An Ed25519 signature valid for the **TimeW-only** purpose, matching independently caller-pinned test public key fingerprint, host, release floor and expiry; a Hospital-purpose proof or original Brave PAIR v1 audience refuses.
3. Exact checkpoint/window key, one selected live con ID, selected seat/session, saved before/target rectangle, and consistent identity across before-resize, after-resize and after-move snapshots.
4. Explicit denial flags from every underlying result. An upstream result that claims native geometry permission or consent is **refused**, not promoted.
5. A fresh result with `restore_allowed=false`, `production_authorized=false`, `native_timew_geometry_allowed=false`, `safe_actions=[]` and all native issuer/seat/C5 fields FALSE, even if the injected fixtures are internally consistent.

The fixture uses a temporary SQLite checkpoint, a fake read-only Sway process output, two same-app Brave-like windows, unrelated tiled Kitty and fullscreen Obsidian, ephemeral CI Ed25519 keys with **no installed trust root**, plus hostile mismatches and replay tests. Existing production geometry, C3e code, C5, SwayPX, Hospital, TimeW QML and Brave PAIR v1 are unchanged. No network, actual Sway command, signing service, consent grant, live host access or activation exists.

**Trust boundary:** Correct Ed25519 mathematics is not proof of an enrolled signer; a C3e CI packet with real Linux peer credentials is not proof a protected compositor actually selected that window. Nor does a three-stage geometry fixture establish a real surface lifetime. Combining these observations **cannot authorize anything** until separate SwayPX, C3e/C4b and C5 owners accept installed source, challenge, revocation, seat and one-use grant semantics. A replayed consistent fixture remains a replay.

## HOW TO USE

GitHub Actions CI only: `python3 -B -I tests/timew/test_timew_scope_a_c3e_fusion.py` with the existing CI environment and pinned cryptography dependency. This is not an app entrypoint and has no user-facing controls.

## VERIFY

The dedicated Scope A GitHub workflow runs this new test alongside previously merged source-only selected-surface continuity, separate signed Brave pairing, journal and original one-click Restore/UI regressions.

Hostile tests refuse altered signed purposes, proof hash or signature, signer-key substitution and revocation, host and release-floor mismatch, selected current window substitution, changed checkpoint/window key, challenge/seat/session mismatch, altered before/after rectangles, compositor lifecycle and generation changes, overwritten unrelated window inventory, and unsolicited upstream positive authority.

## WATCH OUT FOR

The proof verifier lives under Connections' **CI test tree**, not a stable production API. This TimeW test deliberately uses that existing implementation for source-only compatibility checks rather than importing it into the production TimeW service. Owner-controlled native APIs are not defined by these fixtures. C5's real exact-action approval and protected spend remain missing; the current signed fixture grant is not one.

## CHECKLIST

- [x] TimeW-only CI consumer, no production API
- [x] Scope A and Scope B signatures/audiences kept distinct
- [x] Fail-closed mismatch tests and permanent authority denial
- [ ] Exact-head GitHub CI and Nurse 2 independent review
- [ ] SwayPX protected selected-surface issuer, C3e/C4b installed source trust and C5 consent contract
- [ ] Native Fedora/SwayPX acceptance and separate operator production release

## NEXT / DECISIONS

Present evidence on canonical [issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067), review in a draft PR and preserve the explicit owner boundaries. Do not merge or enable production Restore without independent review and operator acceptance. Scope A first; Scope B after native Scope A is accepted.
