# 🏥💜 ApolloHubW // B9 local Calendar contract

**Status:** Source foundation implemented on GitHub `main`. Calendar UI integration and live desktop acceptance remain separate. This release is a **civil-date grid**, not an appointment/event/calendar-account service.

**Ownership boundary:** The existing Clock/TimeW and Hub UI own visual presentation and local time. B9 borrows the **already-updating** `ApolloHubLiveBridge.observationNowMs`; no second `SystemClock`, polling timer, `Date.now()` loop, network request, JSON store, or calendar-account connection is introduced. The central live bridge still owns the existing Weather, CPU++, Network, Media, Apps, and Uptime snapshots.

## Why this backend is intentionally limited

The current `widgets/hub/ApolloHubTile.qml` Calendar tile displays only `Qt.formatDate(tile.now, "ddd, d MMM yyyy")`, and it already refreshes `tile.now` on its existing Time/Calendar timer. Neither `modules/Clock.qml` nor `widgets/TimeW.qml` exposes appointments. GitHub `main` contained no calendar event provider when B9 was scoped.

Therefore `eventCount` is **-1 (unknown)** and `eventsState` is always `"not-connected"`. Do **not** display `0 events`, `no upcoming appointments`, or invent reminders. Event storage, Google Calendar connection, recurring schedules, calendar permissions and synchronization are separate operator design/authorization decisions.

## B9 backend

`services/hub/ApolloHubCalendarPolicy.js` is a pure JS month-grid policy. `services/hub/ApolloHubLiveBridge.qml` imports it and exposes:

```qml
property int calendarMonthOffset: 0
property int calendarWeekStartsOn: 0
readonly property var calendarSnapshot: CalendarPolicy.snapshot(
    observationNowMs, calendarMonthOffset, calendarWeekStartsOn)
```

The UI already receives `hub.liveBridge`, so the Calendar mini-widget can consume `hub.liveBridge.calendarSnapshot`. No `shell.qml` edits or second bridge instance are needed.

`calendarMonthOffset`: integer in [-120, 120], interpreted **relative to the current local month**; 0 means today’s month. An explicit UI Previous/Next action may adjust this value, and a Today action can reset it to 0. This never changes the computer clock. `calendarWeekStartsOn`: 0 for Sunday, 1 for Monday.

`calendarSnapshot` contains:
- `state`: `ready` or `unavailable`; `error` is a machine-readable reason on invalid input/unsupported year.
- `source: "local-clock"`; `today`: local date key `YYYY-MM-DD`.
- `month`: selected month key `YYYY-MM`; `year`, `monthNumber` (1–12), `monthLabel` (e.g. `October 2026`).
- `weekStartsOn`, `weekdayLabels` (7 ordered abbreviations), `weeks` (4–6), `daysInMonth` (28–31).
- `cells`: four to six full seven-day rows, including trailing/leading adjacent-month dates. Each cell contains `date`, `year`, `month`, `day`, `weekday` (0=Sunday), `row`, `column`, `inMonth`, `isToday`.
- `eventsState: "not-connected"`, `eventCount: -1` as explicit *absence of a configured source*, not proof of an empty calendar.

The policy derives **today from the local wall-clock** and performs **grid arithmetic using UTC day boundaries**. This avoids losing/duplicating calendar dates when local DST changes. No UTC timezone conversion is used to decide which civil date is today. Month navigation uses calendar months, not an assumed 30-day offset.

Supported input civil years: 1900–2100; unusual/out-of-range dates yield `unavailable`, not bogus cells.

## UI owner handoff

The UI may replace the calendar placeholder with the generated month grid, preserving existing Hub size/color/button rules. It should not instantiate another clock or calendar service, and should not change `shell.qml`.

- Bind to `calendarSnapshot` and render `weekdayLabels` and `cells` in a compact 7-column grid.
- Mark `isToday`, distinguish `inMonth:false`, and use `weeks` to size the grid. A 4-week February is valid.
- Previous, Next, Today, and Sunday/Monday preferences are optional UI affordances that operate only the two bridge input properties.
- Treat any event information as **not connected**. Do not imply a calendar account is authenticated or a schedule has been checked.
- If the Calendar tile becomes interactive, coordinate user input and focus with the UI worker; the backend does not own keyboard shortcuts, button semantics, calendar selection, navigation, or appearance.

The pure backend tests are in `tests/hub/test_apollo_hub_calendar_policy.cjs` and `tests/hub/test_apollo_hub_calendar_bridge.py`, run through `.github/workflows/apollo-hub-calendar.yml`. They cover leap years, month/year boundaries, month offsets, four/five/six-row grids, DST transitions, invalid inputs, one shared clock, and the absence of event-source claims.

**Runtime acceptance pending:** Confirm the user's installed Quickshell evaluates the projection, `isToday` updates across local midnight, and optional month navigation does not reset the real clock or disturb other Hub tiles.

**No local files, desktop processes, or actual calendar records were changed.**
