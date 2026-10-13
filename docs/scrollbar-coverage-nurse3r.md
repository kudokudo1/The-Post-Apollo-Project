# Nurse 3r // Scrollbar coverage and glow retrofit

**Status:** implementation candidate, draft PR #252. Operator authorized adding position indicators to scrollable widgets/menus and restoring existing glow grammar. **Git and Hospital default to stars.** Keep intentional specialized geometry, colors, layered effects, and semantic decorations intact.

## 2026-10-13 source survey

- Surveyed all 68 `widgets/` QML files and the Git/Hospital module roots for `Flickable`, `ListView`, `GridView`, `ScrollView`, `TableView`, `NeonScrollBar`, and native `ScrollBar` declarations.
- The original seven migrated consumer files and earlier star-handle consumers already used the reusable `NeonScrollBar`; they retain their own geometry and color props unless this branch explicitly adjusts glow.
- Added missing shared bars to previously unmarked list/detail panes across Git/GitHub, Hospital, CPU++, Repository Profile, Workflow Library, Run Inspector, Contacts, and Notifications. Ordinary non-Git/Hospital additions keep the **bar** handle rather than switching to stars.
- Existing shared Git/Hospital scrollbars without an explicit style have been assigned `handleStyle: "star"`. Existing star styles remain unchanged.
- Where a previously non-glowing `NeonScrollBar` was meant as a display-only marker, restored a **restrained magenta handle glow** while keeping its dedicated opacity, source palette, dark unlit rail where deliberate, and `interactive: false` policy where established.
- New scrollbar instances use the canonical `NeonScrollBar` glow defaults; no new global recoloring token is introduced.

## Intentional exceptions / follow-up

| Surface | Existing treatment | Why not indiscriminately replace |
| --- | --- | --- |
| `widgets/GitW.qml` — `ScrollingStatusValue` | 2px horizontal progress thumb; magenta glow restored | Tiny status glyph region, very different from a menu list; coordinate a compact star treatment rather than overlay a full-size 16px handle |
| `widgets/GitW.qml` — `localTargetScrollRail` | Interactive 7px cyan rail, orange activity markers and magenta thumb; thumb glow restored | Contains semantic event markers; preserve marker layout/hit regions during any future star migration |
| `widgets/GitBranchesView.qml` — `branchStripRail` | Interactive horizontal rail with drag/click controls | Replacing it requires retaining horizontal wheel routing, the compact 6px band, and branch navigation; don't stack a second independent rail |
| `widgets/GitHubWorkItemsView.qml` | Display-only dark rail, magenta star | Glow restored to the magenta star handle, dark rail stays deliberately dark |
| `widgets/WorkflowLibraryView.qml`, `widgets/RepositoryProfileView.qml` | Layer-specific inactive opacity | Existing 06 visual-review decision remains open; restore glow without adding another root-level fade |

**Verification limitations:** Static matching of scroll surface counts is not a visual proof that all runtime-overflowing panes show a scrollbar, particularly if a custom component owns its own scrolling or a dynamic menu creates its scroller elsewhere. Host layout clearance, pointer interaction, star-size geometry, and actual glow rendering need Quickshell visual tests. Offscreen isolated `NeonScrollBar` Qt smoke is useful but does not instantiate all 43 changed host files. Keep this PR draft until relevant tests and visual review are complete.

**Operator's approval boundary:** This branch changes neither `main` nor the operator's running Quickshell. Do not merge without completing the declared verification gate.
