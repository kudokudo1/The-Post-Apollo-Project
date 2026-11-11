# MACHINE // Tab-count recognition pattern, unlinked preview

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / browser window recognition  
**STAFF ROLE:** External Hospital-compatible DOC; live registration not verified  
**STATE:** Repository implementation in draft; no local deployment or automatic browser pairing

## IMPLEMENTATION

The operator requested a compact per-Brave-window tab pattern:
**TABS // 2 // 5 // 6**, using these independent Post-Apollo colors:

- `TABS`: cyan
- `//` separators: white
- each numeric count: orange
- 7 px spacing between tokens

The extension's existing opt-in window inventory already projects each
**normal non-private** Brave window into a temporary window ID and
`tab_count`, using `chrome.windows.getAll` only when the user opens or
refreshes its popup. The new `#tab-pattern` displays its *real* count
sequence in the same order as the extension's window list. **It does not
read tab titles, URLs, cookies, page contents or private windows.**

A reusable `widgets/MachineBraveTabPattern.qml` displays the identical
colors and spacing in TimeW. The MACHINE page includes a short manual
`BRAVE // TAB COUNT PREVIEW` text field: after reading the extension,
the operator can enter `2 // 5 // 6` to preview the signature beside
the existing desktop geometry controls. The parser allows at most
64 numbers, 2048 tabs per window and 8192 tabs total. It refuses any
letters, URLs, HTML, malformed delimiters or excessive counts. Zero-tab
windows are valid.

## HOW TO USE

For a future operator-approved local version of the code:

1. Open the disposable Brave MACHINE extension popup (or choose REFRESH
   WINDOWS). Read the cyan/white/orange `TABS // …` signature. Its order
   follows that browser popup's window list, not Sway's window list.
2. In TIME → MACHINE → SAVE DESKTOP, enter only its count sequence (for
   example `2 // 5 // 6`) into `BRAVE // TAB COUNT PREVIEW`.
   The widget displays colored, spaced tokens.
3. The status remains `BROWSER LIST ORDER // UNLINKED // NOT SAVED`.
   This is deliberately a **manual visual hint**, not saved metadata.
   Clearing the field removes the preview. It is not an input to SAVE,
   MARK, STORED, RESTORE, or any live pairing process.

The operator's normal Brave browser, its tabs and the native-messaging
bridge remain unchanged by repository authoring.

## VERIFY

Dedicated CI checks the real QML input parser, CSS colors, extension
DOM display, count order, private-window refusal, unchanged extension
permissions and zero new TimeW processes. The prior topology privacy
and limits test also runs. Actual Quickshell/Brave visual acceptance
is **not** demonstrated by source checks.

## WATCH OUT FOR

A `2 // 5 // 6` signature is not unique, not stable across browsing,
and cannot distinguish two windows with equal tab counts. Brave
window IDs can change between sessions. This display does **not**
automatically map a Brave window to a Sway desktop window and grants
no right to move windows, capture sensitive tab URLs or restore tabs.

The next independent gate is a trusted one-window-at-a-time browser /
compositor identity association. The current A/B/A focus diagnostic
proves only host continuity, not this binding.

## DECISIONS

Small UI/color enhancement with real browser-side counts and manually
entered, transient TimeW visualization. No automatic capture,
serialization, new browser permissions, extra host process, background
poller, local-machine write or production activation.
