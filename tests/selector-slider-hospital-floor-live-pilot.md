✦︎✦︎✦︎ Meta Apollo Logos //

# F1 INDEX // REAL HOSPITAL FLOOR PILOT

> **STATE //** operator-runtime verification pending  
> **GIT EVIDENCE //** REMOTE and REPO live pilots operator-accepted (2026-10-15)  
> **SCOPE //** Hospital Surgery FLOOR only; other services and selectors unchanged

## Operator workflow

Open **HOSPITAL > SURGERY** (not Reception). In the `FLOOR // REPOSITORY`
box beside the floor name, a new **LIVE FLOOR // OFF** toggle appears
once floor switching is available. If the Hospital is discovering floors,
refreshing its patient model, or running an operation, the switch stays
disabled until the existing `floorSwitchEnabled` guard permits it.

OFF is the default on each menu session and whenever leaving Surgery.
With OFF, the real FLOOR slider uses its original immediate selection.
With ON, dragging previews a candidate floor, and release requests the
selected floor once through the **existing** `root.selectFloor(index)`
method; that method alone decides whether the request is allowed.

## Live acceptance checks

1. Wait for floor discovery and idle Hospital status. With **LIVE FLOOR // OFF**,
   move the existing FLOOR slider and confirm that selection remains immediate,
   with no flick or changed appearance.
2. Enable **LIVE FLOOR // ON**. Press and drag to a *different* known floor
   without releasing; the active floor, its label and active bed/room context
   should **not** change while previewing.
3. Release. The intended floor should become current **once**, its floor
   name should agree with the handle, and the appropriate patient/audit
   context should refresh without flick or duplicate transitions.
4. Test quick drag, pointer release near the first/last floor, and a click
   on the track. Confirm there is no unexpected top-of-track flick.
5. With ON, try Escape during an unfinished drag: no request should commit.
   If the floor model changes mid-drag, an outdated preview must not commit.
6. Wait for a permitted safe state and use the toggle to return OFF;
   immediate selection should resume.
7. Navigate to another Hospital surface and back to Surgery; LIVE FLOOR
   must be OFF again. Close/reopen Hospital; it must also remain OFF.
8. Check the existing floor PREV/NEXT buttons and active-operation safety
   guards, and verify both Git REPO/REMOTE remain as previously accepted.

## Safety and stop criteria

- This is a **real floor switch**: selecting a floor changes the Hospital
  repository/bed/room context and can request fresh audits. It does not
  start a surgical operation, move a bed, or run a Git push/pull by itself.
- Do not attempt a floor selection during live operation/rehearsal/armed
  work. Existing `floorSwitchEnabled` guards remain authoritative.
- If an unexpected floor is selected, a refresh loops, an active state
  changes during preview, or the handle flicks, turn the toggle OFF,
  document the observation, and do not graduate the pilot.
- The observed Git REPO/REMOTE runtime passes do not certify Hospital:
  operator-specific runtime confirmation is required before permanent
  adoption or removal of the testing switch.
