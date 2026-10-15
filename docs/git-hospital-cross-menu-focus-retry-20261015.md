# 🏥 Nurse 3a // Git / Hospital multi-menu keyboard handoff

**Date:** October 15, 2026. **Stage:** scoped draft, source validation only.

## Operator evidence

With Git **closed**, Hospital's Tab/Main Mode navigation moves normally.
With Git **open**, Hospital's navigation **does not move**, even when the
operator deliberately clicked the visible far-left Hospital menu region.
Git and Hospital have open layer-shell windows that overlap horizontally
by about 178 screen pixels, based on live numeric geometry:
Hospital `(-8,0,772,1346)`, Git `(586,0,1148,816)`.

An earlier opt-in trace from both menus showed Qt navigation-anchor
`activeFocus` frequently **true while `Window.active` false** and failed
end-to-end Tab navigation. This does **not** by itself prove seat ownership
or explain every non-keyboard command. The overlap and panel input masks
are separate, still-unverified pointer-interception possibilities.

## Scoped change

Notifications already contains a **48ms, single-frame, one-shot focus
acquisition retry** when the Qt window is still inactive after an
owner transfer. Git/Hospital have the same permanent-mapped PanelWindow
and shared KeyboardOwnershipCoordinator, but had no matching retry.

Mirror that existing mechanism only in those two windows:

- Queue one 48ms retry after becoming keyboard-active, or opening while
  keyboard-active, and cancel on losing ownership or closing.
- Recheck menu-open, selected keyboard ownership, and actual Qt
  `Window.active` before the retry. If already active, **do nothing**.
- Do not steal from Git's text editor/dial or Hospital's intercom/
  receptionist typing.
- Invoke the **existing** keyboardOwnershipRequested signal to issue the
  same bounded acquisition pulse; restore the existing Qt navigation anchor
  only for the still-selected, non-typing menu.

**Unchanged:** SwayFX mode/bindings, Koinoikos coordinates, Qt Main Mode
Tab shortcuts, `WlrLayershell.keyboardFocus` policy,
KeyboardOwnershipCoordinator's 120ms short Exclusive pulse, widget window
mapping/visibility, input masks, and native Brave focus behavior.

## Controlled live acceptance, before concluding anything

1. Restart Quickshell **using the existing safe full-process script**,
   not hot-reload (historical Qt/QML glow-teardown crashes). Do not
   restart or edit SwayFX.
2. Close Git, open Hospital alone; Tab and harmless buttons still work.
3. Open Git while leaving Hospital visible. Move the pointer into
   Hospital's **uncovered far-left frame** (X below ~586 on the captured
   output). Test Tab Main Mode and a harmless panel button. Reverse
   selection into Git without closing Hospital and test its Tab.
4. Repeat using held Super + grave + Left/Right. On release, watch for
   unexpected rollback to previous owner, which is a known separate
   logical-owner concern. Do not infer this retry fixes that behavior.
5. Click **Brave** underneath and type a harmless non-submitted phrase
   into its address bar, then clear it. Native click-to-type must still
   work, even with both overlays open.
6. Optional: use existing `qs ipc call relationshipFocus diagnose` and
   default-off `focusKeyTrace` to compare intended owner vs. Qt window
   activation and actual Tab. The trace must be stopped after testing.

**Result remains unverified on the operator's compositor** until those
steps pass. If Hospital Tab is still blocked with Git open, inspect
diagnostic `logicalKeyboardOwner`, `focusBoostOwner`,
`windows[*].qtWindowActive`, and actual key delivery; also examine
overlay input-mask overlap and pointer ownership before adding another
focus policy.
