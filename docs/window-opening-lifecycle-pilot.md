# Syntagma // widget opening lifecycle: trial outcome and compatibility boundary

**State: Stage 1 A/B trial closed — FAIL for visibility-controlled Git and
Hospital.** **Operator runtime report:** October 13, 2026. **Scope:**
window presentation/mapping, not keyboard ownership or Qt navigation.

## Observed result

The operator exercised independently opt-in, visibility-controlled reopening
of **Git** and **Hospital**. Both **crashed after several openings or rapid
repeated clicks**. The operator remembers the same class of problem from
earlier development. Exact crash logs, compositor stack, and crash cause
were **not** collected, so this establishes the failed lifecycle behavior
but not a proven root cause in Qt, Quickshell, SwayFX, or shader cleanup.

| Widget | Tested alternate lifecycle | Outcome | Current safe source policy |
| --- | --- | --- | --- |
| Git | Unmap on close via `visible: menuOpen` | **FAIL** — crash after repeated openings/spam clicks | Permanently mapped; zero-sized input mask on close |
| Hospital | Same independent unmap/remap experiment | **FAIL** — crash after repeated openings/spam clicks | Permanently mapped; zero-sized input mask on close |
| Notifications Hub | Unmap/remap **not** tested in this pilot | Earlier native Qt/Quickshell second-open crash documented in source | Permanently mapped, zero-sized input mask on close |

The two experimental flags
`POST_APOLLO_GIT_VISIBILITY_PILOT` and
`POST_APOLLO_HOSPITAL_VISIBILITY_PILOT` have now been **removed from the
application source** to prevent accidental reuse of a reproducibly
crashing mode. The existing persistent-mapping behavior is explicitly
preserved; other widget implementations were not migrated.

### Why the result matters

This is now operator-level runtime evidence **against** making
visibility-controlled unmapping the unconditional default for *all*
complex layer-shell menus. It is not evidence that visibility-based
opening is inherently invalid:

- **AppControl** and **CPU++** still use `visible: menuOpen`; their
  own operation and stability must be assessed on their own merits.
- Native surfaces, popups, and passive panels have different lifecycle
  needs. A standardized **opening protocol** need not imply an identical
  **native mapping strategy**.
- The precise underlying crash mechanism remains **unverified**. If the
  runtime problem is repaired later, a new controlled experiment may be
  authorized with crash logging, without silently re-enabling this pilot.

## Existing opening strategies // cross-widget inventory

| Widget | Presentation lifecycle | Known evidence / reason | Normalization status |
| --- | --- | --- | --- |
| Git | Always-mapped layer-shell panel; zero-size input mask when closed | **FAIL** on unmap/remap in October 13 runtime trial | Retain persistent mapping |
| Hospital | Same always-mapped / closed masked panel | **FAIL** on unmap/remap in October 13 runtime trial | Retain persistent mapping |
| Notifications Hub | Always mapped, masked closed | Historical native second-open crash recorded directly in widget source | Retain persistent mapping |
| AppControl | `visible: menuOpen` | Visibility lifecycle, retained QML state and startup input behavior | Leave unchanged |
| CPU++ | `visible: menuOpen` | Starts monitor refreshes/animations with menu lifecycle | Leave unchanged |
| Weather | Always visible; zero dimensions when closed; terminal bay excluded from input mask | Specialized terminal pass-through is a real behavior; reason for zero-size mapping not proven | Separate future study |
| Power | Persistent surface contains the launch button **and** menu | Closed launcher needs to remain available within that composition | Leave unchanged |
| Social | Permanent nonfocusable masked controller + separately visible native `FloatingWindow` | Explicit choice for Sway move/resize, Discord native-focus handoff | Native-window adapter |
| Media Deck | `visible: menuOpen`, `WlrKeyboardFocus.None` | Pointer-driven playback deck | Leave unchanged |
| Incoming notification toast | Appears with active notifications | Passive event surface, not the Notifications history/control hub | Out of focusable-menu opening comparison |

## Restoration and safety

The prior pilot command was **relative to the Quickshell repository**, not
to the unrelated `post-apollo-dev-runtime` directory. It did not operate
from that unrelated working directory.

If running a local Quickshell configuration containing the old opt-in code,
restart **without either pilot environment variable**. The safe restart
script forcibly restarts Quickshell instead of using an in-process hot reload,
because Qt sampled glow teardown has historically crashed during hot reload.
Do not repeatedly exercise the failed variant merely to confirm it again.
Preserve unsaved widget state before restarting.

```bash
qsdir="$(readlink -f "${XDG_CONFIG_HOME:-$HOME/.config}/quickshell")"
test -f "$qsdir/scripts/restart_quickshell_safe.sh" || {
  echo "Safe restart script not found in $qsdir"; exit 1;
}
env -u POST_APOLLO_GIT_VISIBILITY_PILOT \
    -u POST_APOLLO_HOSPITAL_VISIBILITY_PILOT \
    bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

The revised GitHub source ignores both removed environment flags entirely,
but this alone does not update the user's local installation. Do not use
`git reset --hard` or overwrite local Quickshell changes as part of recovery.

## What we can standardize now

The **behavioral** opening protocol remains a candidate:
**open request → present surface → request focus when appropriate →
activate the Qt input target → refresh information independently**.

The **presentation mechanism** must remain an explicit, justified adapter.
For these tested complex menus, always-mapped + closed input mask is the
safety baseline. Social's native window and Power's in-panel launcher have
different functional requirements. We should eliminate duplicated requests
and unnecessary delays only in separate, scoped experiments where
responsibility, crash safety, and focus recovery can be tested independently.

**Decision:** no global migration to `visible: menuOpen`. Preserve the
established opening mechanisms; continue cross-widget standardization at
the shared behavioral contract rather than forcing one surface lifecycle.

**Evidence grade:** user-observed runtime crash on both tested alternatives;
source-level regression checks; cause and broader portability unresolved.
