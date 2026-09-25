# New Intern Update — Hospital Status

**Project:** Taskbars // Post-Apollo  
**Date:** 2026-09-25  
**Authority:** T3 Overhead / Team 0 records  
**Certified patient:** `943d273`

This is the minimum current-state briefing for new interns. It does **not** authorize surgery.

## Traffic law

### Parallel-safe

- services
- providers
- probes
- tests
- docs
- reconnaissance

### Serialized through T3 Overhead

- `AppControlW.qml`
- donor-block removal
- shared navigation/detail/result wiring
- shared selectors
- service lifetime integration

**Rule:** nobody except the currently released host slot touches serialized tissue.

## Current floor

```text
T1   28075def   Process/System        SAFE
T2   77dcc84b   Favorites             ACTIVE HOST SLOT
T3-F 110f6e4    FILES                 FROZEN HOST PATCH
T3-R —          REMOTE                HOLD
T4   —          CPU++                 RECIPIENT STANDBY
T5   a801e195   Tabs/Surfaces         SAFE
T6   d13194a    Application Audio     SAFE
T7   1ad589f7   Desktop Identity      SAFE / RECON
T8   838f0dfe   APPS Core             SAFE
T0   943d273    Recon/Management      SAFE
```

## Current serialized queue

```text
1. T2 Favorites persistence
      ↓ PASS / integrate / certify

2. T3-F FILES
      ↓ re-anchor to exact new certified HEAD
      ↓ reconcile frozen 110f6e4 host patch
      ↓ PASS / integrate / certify

3. T3-R REMOTE
      ↓ reread exact post-FILES certified HEAD
      ↓ operate

4. Later integrations
   T1 / T5 / T6 / T7 / T8
```

## Team notes

**T1 — Process/System**  
Continue isolated shared Process/Resource/System organs. Build contracts that can later serve APPS, WINDOWS, TABS, and RUN. No host wiring yet.

**T2 — Favorites**  
Owns the active serialized host slot. Scope is persistence transplant only. Preserve old JSON, restart persistence, toggles, watches/preferred actions, and HUNTER protected-favorite behavior. Do not expand into FILES reconstruction/COMBI yet.

**T3-F — FILES**  
Frozen at `110f6e4`. Do not modify or merge the host patch until T2 lands and T3 certifies a new patient. Then re-anchor and reconcile.

**T3-R — REMOTE**  
Hold. Its real patient will be the exact certified post-FILES HEAD.

**T4 — CPU++**  
Recipient/validation only. No donor surgery. Consume released shared organs when they are certified.

**T5 — Tabs/Surfaces**  
Continue provider/probe/validator work. Temporary provider keys are acceptable. Do not define canonical application identity.

**T6 — Application Audio**  
Continue isolated shared APP/WINDOW/TAB audio work. Identity assumptions must coordinate with Team 7. No host wiring.

**T7 — Desktop Identity**  
Define the minimal shared identity contract for DesktopEntry ↔ application ↔ Sway window ↔ PID ↔ tab. Feed that contract to T5/T6/T8 and Team 2 adapters. No broad donor surgery.

**T8 — APPS Core**  
Continue standalone provider preparation. Keep APPS-specific catalog/launch behavior separate from Team 1 process control, Team 5 tabs, Team 6 audio, and Team 7 identity. No mass APPS extraction.

**T0 — Recon/Management**  
No surgery. Watch collisions, future targets, and especially contracts forming between T1/T5/T6/T7/T8.

## Intern safety rules

1. **Certified baseline is not the same thing as every team HEAD.**
2. **A service branch may be ahead without being integrated.**
3. **Local PASS is not integration PASS.**
4. **Do not merge a frozen host patch forward independently.**
5. **Do not infer ownership from menu names.**
6. **Do not invent a new canonical identity model; Team 7 owns semantic identity.**
7. **Do not treat a moved file as a liberated organ if it still reaches back into AppControl.**
8. **If work reaches `AppControlW.qml` or shared host routing, stop and route through T3.**

## Report format for interns

When reporting on a room, include:

```text
team:
branch:
base SHA:
current HEAD:
territory:
files changed:
AppControlW touched: YES / NO
shared vessels:
tests:
local pass:
donor pass:
integration status:
blockers:
```

## One-line mental model

```text
Parallel rooms build organs.
T3 controls the shared patient.
Team 0 watches the hospital.
Team 4 proves liberated organs are truly reusable.
```

For the larger architecture, see `docs/ARCHITECTURE.md` on the Team 0 documentation branch.
