# Window Assembly Tracker

Reusable geometry machinery for Post-Apollo windows that are visually one object
but are actually several independent Sway toplevels.

The tracker replaces one-off "keep these windows glued together" loops with a
single scene model.

## Mental model

A scene owns one canonical rectangle:

```text
SCENE
x / y / width / height
    |
    +-- member A
    +-- member B
    +-- member C
```

Each member is described once as an affine transform of the scene rectangle:

```text
member.x      = scene.x + xRel * scene.width  + xPx
member.y      = scene.y + yRel * scene.height + yPx
member.width  =           wRel * scene.width  + wPx
member.height =           hRel * scene.height + hPx
```

That is enough to describe fixed bezels, proportional bays, side panels,
receiver decks, companion windows, and embedded external apps.

If a member with `canLead: true` is focused and moved/resized in Sway, the
Python bridge inverts its transform, updates the canonical scene, and moves the
followers directly over persistent Sway IPC.

The hot path does not bounce through QML. Pending follower moves are coalesced:
**latest geometry wins**.

## Files

- `WindowAssemblyTracker.qml` — small QML API/controller.
- `WindowAssemblyBridge.py` — persistent Sway IPC observer/mutator.

## QML example

```qml
import "../../services/windowassembly"

WindowAssemblyTracker {
    id: assembly
    intervalMs: 8

    Component.onCompleted: {
        defineScene(
            "example",
            rect(200, 180, 1200, 800),
            [
                member(
                    "screen",
                    { appId: "example-screen" },
                    transform(
                        0, 30,
                        0, 24,
                        1, -250,
                        1, -150
                    ),
                    { canLead: true }
                ),

                member(
                    "controls",
                    { title: "EXAMPLE_CONTROLS" },
                    transform(
                        1, -220,
                        0, 24,
                        0, 220,
                        1, -150
                    ),
                    { canLead: true }
                )
            ],
            {
                minimumWidth: 600,
                minimumHeight: 400,
                watch: true
            }
        );
    }

    onSnapshot: function(payload) {
        // payload.rect is the current canonical scene geometry.
        // payload.leader is the focused member currently driving the group.
    }
}
```

## Post-Apollo TV shape

The unfinished TV can be represented without hard-coding a new tracking loop
for every bezel:

```text
scene
+-- top
+-- left
+-- screen
+-- right controls
+-- bottom
+-- receiver/deck
```

Example relationships once the final dimensions exist:

```text
top:
    xRel=0  xPx=0
    yRel=0  yPx=0
    wRel=1  wPx=0
    hRel=0  hPx=TOP_HEIGHT

left:
    xRel=0  xPx=0
    yRel=0  yPx=TOP_HEIGHT
    wRel=0  wPx=LEFT_WIDTH
    hRel=1  hPx=-(TOP_HEIGHT + BOTTOM_HEIGHT + DECK_HEIGHT)

screen:
    xRel=0  xPx=LEFT_WIDTH
    yRel=0  yPx=TOP_HEIGHT
    wRel=1  wPx=-(LEFT_WIDTH + RIGHT_WIDTH)
    hRel=1  hPx=-(TOP_HEIGHT + BOTTOM_HEIGHT + DECK_HEIGHT)

right:
    xRel=1  xPx=-RIGHT_WIDTH
    yRel=0  yPx=TOP_HEIGHT
    wRel=0  wPx=RIGHT_WIDTH
    hRel=1  hPx=-(TOP_HEIGHT + BOTTOM_HEIGHT + DECK_HEIGHT)

bottom:
    xRel=0  xPx=0
    yRel=1  yPx=-(BOTTOM_HEIGHT + DECK_HEIGHT)
    wRel=1  wPx=0
    hRel=0  hPx=BOTTOM_HEIGHT

deck:
    xRel=0  xPx=0
    yRel=1  yPx=-DECK_HEIGHT
    wRel=1  wPx=0
    hRel=0  hPx=DECK_HEIGHT
```

Those numbers are deliberately not frozen yet. The chassis is still missing its
top, left, and bottom TV frame pieces. Once the physical proportions are final,
the relationships are entered once and the tracker maintains the assembly.

## Current scope

This first pass owns geometry only:

- persistent Sway IPC
- arbitrary named scenes
- arbitrary named members
- focused-member leadership
- bidirectional scene recovery
- direct follower movement
- latest-wins command coalescing
- QML scene updates
- multiple simultaneous scenes

It does **not** own application lifecycle, power states, animation choreography,
or semantic identity. Those remain with the menu/widget using the tracker.
