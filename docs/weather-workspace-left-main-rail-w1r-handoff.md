# Weather Station W1r // Restore classic-style main rail

PATIENT // The-Post-Apollo-Project
ROOM // Weather Station / W1r main navigation placement
CONNECTION // External, Hospital-compatible ChatGPT; not live Hospital registered
ASSIGNMENT // Seven main family buttons left; top INDEX opens detailed navigator
PHASE // GitHub implementation and CI
SOURCE // W1 merge #1096 and the operator's subsequent navigation placement request

## IMPLEMENTATION

This is a bounded revision to W1 layout. It changes no collector, data
source, active history watcher, rotating relevance policy, storage schema,
Magick calculation, radio controller or compositor actor.

- Main families HOME/WEATHER/COSMOS/EARTH/MEDIA/MAGICK/TOOLS now sit in
  a dedicated StationWorkspaceFamilyRail inside the original 160px
  Station left modeRail. It reuses ModeButton with the original classic
  rail button height, no border and the active-mode highlight.
- The duplicate horizontal TOP family strip is removed from
  StationWorkspaceSurface. The content area begins directly below
  the Station's canonical 62px header. The bottom per-family
  submenu row remains in place.
- The old header launcher control already displayed INDEX while
  SUBJECTS was open, but previously disabled itself. It now opens
  the existing MORE detailed route tree, retaining the visible
  label INDEX. Clicking INDEX again returns to the prior workspace.
  In CLASSIC, the same control still launches the original context
  terminal or Star Map according to its existing label.
- The CLASSIC return button remains at the base of the left rail.
  The INDEX tree retains its previous dedicated subject rail.
  The full 160px original modeRail width now applies to CLASSIC,
  SUBJECTS workspace and INDEX, preserving the existing Kitty/Sway
  terminal cutout geometry.
- HOME stays the same single mounted original StationHome component
  with its watch ranking, source age, 60s reevaluation, history and
  graph snapshots. No rotation/favorites changes in W1r.
- Tests cover label and handler identity, layout placement, legacy
  transition and source/terminal contract preservation.

## HOW TO USE

After separate local activation: Weather Station > SUBJECTS.
The left rail selects HOME, WEATHER, COSMOS, EARTH, MEDIA, MAGICK or
TOOLS. The bottom row changes the active subject's working submode.
Press INDEX in the upper-right header to enter the detailed subject
tree; press INDEX again to return. Press CLASSIC at the lower left
to restore the original eight-mode interface. In CLASSIC the header
button still owns its prior context terminal behavior.

## VERIFY

GitHub W1r and existing W1/subject/Main Mode/Weather teardown tests
must be green before merging. This PR is not equivalent to live
Fedora Quickshell display or Kitty geometry testing.

## WATCH OUT FOR

No new source polling is introduced. The modeRail now occupies
160px within the 1000px Station window, reducing workspace width
from the previous full-width design; bottom mode labels and content
must receive a visual fit check on the real desktop. W2 favorites
and smart deck and W3 graph cards remain separate upcoming work.

## CHECKLIST

- [x] Current GitHub source/PR ownership preflight
- [x] Seven primary mode buttons left
- [x] INDEX header reuses MORE behavior
- [x] Bottom submode row and CLASSIC retained
- [x] Original Kitty/terminal and HOME lifetime unchanged
- [x] Focused tests and workflow
- [ ] Final CI green
- [ ] GitHub merge (operator standing authorization)
- [ ] Fedora/Quickshell visual acceptance

## NEXT

After tests: merge W1r if safe, report merge SHA.
Then continue W2 pinning/relevance rotation with no new writers until
the original favorites store ownership is audited.

## DECISIONS

Main family navigation is on the left; INDEX belongs in the canonical
header; bottom submode buttons remain horizontal; CLASSIC is always
available. No local runtime mutation performed.
