# ApolloHubW Phase 3 // TimeW CALC and WORLD owner-seam audit

**STATUS:** source-backed integration audit; **BLOCKED for functional Hub CALC/WORLD integration pending owner-approved seam**. This is not a new canonical rule, a runtime acceptance record, or permission to change TimeW, shell, or OS processes.  
**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / assignment:** external Hospital-compatible ApolloHubW Phase 3 / TimeW integration  
**Source baseline:** `main` `2f3aac06066aa1b5c144cf043a039611c30ab451`, inspected 2026-10-26 (America/New_York). Re-check HEAD before implementation.  
**Authority:** [Syntagma AGENTS](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/AGENTS.md), [Hospital Agent Protocol](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/OPERATE/HOSPITAL-AGENT-PROTOCOL.md), and [Post-Apollo Working Guide](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/OPERATE/POST-APOLLO-WORKING-GUIDE.md).  
**Ownership:** TimeW parent `widgets/TimeW.qml` and its process-backed calculator/zone catalog remain owner tissue; this audit does not claim Hospital registration, transfer, or owner permission.

## Verified current wiring

| Capability | Owner / implementation | Hub-facing contract at baseline | Consequence |
| --- | --- | --- | --- |
| Local clock and 12/24 formatting | `services/hub/ApolloHubTimePolicy.js`; `widgets/hub/ApolloHubTile.qml` has one 1-second timer | `ApolloHubTimeMini.qml` receives `timeSnapshot`, `use24Hour` | Already supported; no new clock timer. |
| Stopwatch | `TimeW.qml` exposes `hubStopwatchSnapshot`, `hubStopwatchAction`, `hubRefreshStopwatch` | `shell.qml` forwards through `ApolloHubW.qml` and tile | Shared owner lifetime, no duplicate stopwatch. |
| Countdown | `TimeW.qml` exposes `hubCountdownSnapshot` and `hubCountdownRequest` | `shell.qml` forwards through `ApolloHubW.qml` and tile | Shared owner lifetime, stable countdown IDs. |
| 12/24 civil-time input/output formatting | Pure `services/time/TimeConverterFormat.js`: `parseInput`, `convertInput`, `displayInput`, `formatResult` | No CALC-specific Hub UI | Safe pure formatting only; not an actual time-zone conversion or duration calculation. |
| Time-zone conversion | `TimeW.qml` owns `runTimeConverter()` and its private `converterProcess` calling `TimeZoneConverter.py` | **No `hubConverter*` snapshot/request API** | Hub cannot reuse the current action without a new, owner-approved bridge. |
| Elapsed arithmetic and time difference | `TimeW.qml` owns `runTimeArithmetic()` / `runTimeDifference()`, private `arithmeticProcess` / `differenceProcess` | **No Hub calculator snapshot/request API** | No safe shared request/result seam. |
| IANA zone catalog and country search | `TimeW.qml` uses `timedatectl list-timezones`, fixed `iso3166.tab` and `zone.tab` reads, then pure `WorldZoneSearch.js` | No owner-published catalog or search result to Hub | Do not spawn a second catalog lookup or claim fixed UTC offsets are IANA zones. |
| World-clock offset | `TimeW.qml` performs owner-owned `date +%z` lookup with allowlisted TZ and projects via `WorldClockPolicy.js` | No Hub world-zone snapshot or selection API | UTC offset depends on the selected zone and instant; the local clock offset is not a zone ID. |
| Time Machine | Separate TimeW machine workflows | Deliberately excluded from Phase 3 first wave | No capture, restore, revive, or window mutation. |

**Evidence anchors:** `TimeW.qml` contains `hubCountdown*` and `hubStopwatch*` methods/properties, but no `hubConverter` or `hubWorld` methods/properties. `shell.qml` routes only countdown/stopwatch actions into the Hub Time tile. `ApolloHubTimeMini.qml` offers CLOCK, STOPWATCH and COUNTDOWN. `TimeW.qml` gates converter and catalog operations on `menuOpen` and `selectedMode`; directly calling its private methods from the Hub would not preserve their current owner preconditions.

## Blocker and minimal owner decision

A functional Hub CALC/WORLD page needs a **TimeW-owner-published, read-only snapshot and explicit request seam**, or a separately approved owner-side refactor. A Hub-only implementation that launches `TimeZoneConverter.py`, `TimeArithmetic.py`, `TimeDifference.py`, `timedatectl`, or `date +%z` would duplicate the owner's process path. A Hub-only JS time-zone calculation would silently lose IANA/DST ambiguity handling. Neither is authorized.

**Proposed contract for owner review, not approved or implemented:**

1. Owner exposes a bounded immutable `hubTimeCalcSnapshot` with source, capability/version, selected input IDs, normalized result, `unavailable / idle / requested / pending / applied / failed` phase, and a monotonically increasing request generation. Never infer success from an accepted request alone.
2. Owner exposes an explicit `hubTimeCalcRequest(kind, payload)` for `convert`, `arithmetic`, `difference`, and a read-only `hubWorldZoneSnapshot` / selection path. Validate IANA catalog membership, input dates/times, and generation in the owner; retain DST fold/gap alternatives and errors.
3. Existing TimeW menu remains independent. Requests from Hub must not depend on opening TimeW or switching its visible mode. A shared owner process/result lifecycle must not overwrite a standalone CALC draft or allow a stale response to overwrite newer inputs.
4. Hub consumes these snapshots through the already established `shell.qml → ApolloHubW.qml → ApolloHubTile.qml` pattern, with no new process, polling timer, file reader, or database. H:1 stays compact; H:2/H:3 may add CALC/WORLD only after the owner seam is approved.
5. Define keyboard-focus handoff, input draft preservation across H/W resizing and tab switches, failure/retry, and live owner-vs-Hub parity before implementation.

**Required coordination:** TimeW owner and the serialized `shell.qml` bridge owner. Existing TimeW CALC process methods and shell wiring are outside the current Hub-only write authorization. If they cannot publish the seam, park this capability; do not add a cosmetic nonfunctional CALC tab.

## Acceptance and recovery

- **Verified here:** current GitHub source paths, action and data flow, absence of a Hub CALC/WORLD owner seam, and active PR list at baseline.
- **Not verified:** local Fedora/Quickshell runtime, real timezone conversion from Hub, performance, focus, draft continuity, or operator acceptance.
- **No changes made:** `TimeW.qml`, `shell.qml`, `services/time/*`, Hub QML, live computer, production state, or other workers' branches.
- **NEXT:** owner/host approval for the typed snapshot/request contract, then a separate narrow implementation and CI test. If no owner seam is available, pause Phase 3 unattended work at this checkpoint. TASKS TODAY/PLANNER/PROJECTS remain source-complete but await desktop acceptance.
