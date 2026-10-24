# 🏥💜 ApolloHubW // B10 local Time policy contract

**Status:** B10 backend policy implemented on GitHub `main`; source-level timezone regression tests tracked by `.github/workflows/apollo-hub-time.yml`. The Hub Time tile already displays a working local time via its own one-second QML timer. Integrating the **new formatting policy** into that UI, and desktop acceptance, remain UI-owned work.

## Mechanism and ownership

`services/hub/ApolloHubTimePolicy.js` is a small, pure JavaScript formatter taking a caller-supplied millisecond timestamp. It creates **no timer**, `SystemClock`, subprocess, network request, persisted preference, time-zone database, or clock mutation.

This is intentionally **not** attached to `ApolloHubLiveBridge.observationNowMs`: that existing bridge clock advances on media/weather/system freshness schedules, often every 5 or 60 seconds. Treating it as a second-resolution live clock would make Time lag or stall. The existing `widgets/hub/ApolloHubTile.qml` already has:

```qml
property date now: new Date()
Timer {
    interval: 1000
    repeat: true
    running: tile.visible && (tile.moduleId === "time" || tile.moduleId === "calendar")
    onTriggered: tile.now = new Date()
}
```

The UI owner should **reuse** `tile.now` and not add another observer. The current Clock dock and TimeW each own their existing clocks independently. B10 does not merge or modify those owners.

**Later integration clarification (October 24, 2026):** TimeW now imports the
same pure `ApolloHubTimePolicy.js` formatter as a reusable utility. Its input
comes from TimeW's existing `localClock.date.getTime()` `SystemClock` and
its own `use24Hour` presentation preference. This does **not** make the Hub
responsible for TimeW ticks and does **not** create a shared ticker or new
background polling. The B10 source contract verifies that TimeW preserves
its own one `SystemClock` while using the pure formatter, rather than
forbidding any import of that file.


## Consumer API

From `widgets/hub/ApolloHubTile.qml`, a UI worker can import:

```qml
import "../../services/hub/ApolloHubTimePolicy.js" as TimePolicy
```

The resulting pure snapshot (illustrative binding in the existing tile) is:

```qml
readonly property var timeSnapshot:
    TimePolicy.snapshot(tile.now.getTime(), true)
```

The second argument is an explicit boolean `use24Hour`; `true` means 24-hour clock. The UI owner may later use a user-selected 12/24 preference but must coordinate its persistence and UI controls separately. Calling this policy does not write any setting.

The `snapshot` object has:
- `state: ready|unavailable` and an `error` reason for missing/bad inputs.
- `source: "local-clock"`, `is24Hour`.
- `hour24` (0–23), `hour12` (1–12), `minute` (0–59), `second` (0–59), `meridiem` (`AM`/`PM`).
- `time24` (`13:04:05`), `time12` (`01:04:05 PM`), and `displayTime` selected by `is24Hour`.
- `localDate` (`YYYY-MM-DD`), `dateLabel` (`Thu, 22 Oct 2026`), `weekday`, `month` (1–12), `day`, `year`.
- `utcOffsetMinutes`: signed **minutes east of UTC** for this particular instant. For example, `-240` in New York daylight time or `+345` in Nepal.
- `utcOffsetLabel`: `UTC-04:00`, `UTC+05:45`, etc. This is an *offset*, not an IANA time-zone identifier or a geographical location.

Unavailable snapshots use explicit placeholders (`--:--:--`, empty date, `-1` components, `null` UTC offset), never an invented current time.

## Limits and verification

The policy supports local civil years 1900–2100 and accepts valid Unix epoch timestamps including zero and pre-1970 negatives. It rejects null, strings, NaN, infinity, and invalid 12/24 selections. Date/time comes from JavaScript's local `Date` getters, reflecting the current Quickshell process timezone and system settings, without overriding them.

The CI workflow runs tests across:
- `TZ=America/New_York`: daylight-saving spring forward, fall back, and winter/summer offsets.
- `TZ=UTC`: zero offset canonicalized to numeric 0, rendered `UTC+00:00`.
- `TZ=Asia/Kathmandu`: non-hour `UTC+05:45` offset.
- `TZ=Pacific/Chatham`: quarter-hour daylight offset.
- A Python contract test verifying the policy has no clock ownership or side effects and the Hub already owns its one-second timer.

**Not in B10:** Stopwatch, timers, alarms, countdowns, world-clock zone database, time calculator, persistence, notifications, Media timecodes, and desktop checkpoint “Time Machine.” These belong to TimeW's separately authorized design or later user decisions.

**Desktop acceptance pending:** Confirm the formatted seconds advance with the existing tile, local date flips across midnight, 12/24 presentation works if selected, and reopening the Hub does not display frozen old time.

**No local files, live Quickshell sessions, TimeW, Clock dock, Hub UI or shell files were altered in B10.**
