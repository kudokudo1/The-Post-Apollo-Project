import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property var transcript: [
        {
            sender: "RECEPTION",
            body: "Front desk online. I can route you to Surgery, Attention, Merge Queue, Archive, Reports, Rounds, Staff, Phone, or Intercom."
        }
    ]

    signal routeRequested(string route)
    signal activityActionRequested(var item)
    signal teamNavigationRequested(string team)
    signal specialistHandoffRequested(string mode, string operatorText)
    signal interpretationRequested(string operatorText)

    property bool aiInterpretationEnabled: false
    property var inbox: []
    property var activityEvents: []
    property var subjectStates: ({})
    property bool activityHydrated: false
    property var pendingActivities: []
    // activityEvents is Reception's persistent searchable archive. The desk
    // still projects only five recent/favorite items into inbox.
    property int maxActivityEvents: 2000
    property int guaranteedRecentEvents: 250
    property int reportArchiveBackfillLimit: 250
    property int passiveDuplicateWindowMs: 120000
    // Session-local guard for destructive archive pruning. Selective cleanup
    // is previewed first and requires an explicit confirmation.
    property var pendingArchiveCleanupSpec: null

    readonly property int archiveCount:
        activityEvents.length
    readonly property string archiveOldestAt:
        activityEvents.length > 0
        ? String((activityEvents[0] || {}).recordedAt || "")
        : ""
    readonly property string archiveNewestAt:
        activityEvents.length > 0
        ? String(
            (activityEvents[activityEvents.length - 1] || {}).recordedAt
            || ""
          )
        : ""

    property string lastReadAt: ""
    property bool visitActive: false
    property string visitStartedAt: ""
    property bool pendingVisitStart: false
    property int unreadCount: 0
    property int recentCount: 0
    property var pinnedKeys: []
    property int pinnedCount: 0
    property int maxPinnedEvents: 5
    property string lastArchiveExportStatus: ""
    readonly property string archiveExportPath:
        Quickshell.dataPath("hospital-reception-export.json")

    // Session-local conversational reference. This is intentionally not
    // persisted: Reception remembers "that" only inside the live session.
    property string contextEventKey: ""
    property string contextSource: ""
    property string contextTarget: ""
    property bool contextUnreadOnly: false
    property bool contextFavoritesOnly: false
    property bool contextProblemsOnly: false
    property double contextStartEpoch: 0
    property double contextEndEpoch: 0
    property string contextTimeLabel: ""
    property string contextAttentionMode: ""

    readonly property bool contextActive:
        contextEventKey.length > 0
        || contextTarget.length > 0
    readonly property var contextItem: contextEvent()
    readonly property bool contextHasEvent:
        contextItem !== null
    readonly property bool contextIsFavorite:
        contextHasEvent
        && isPinned(contextItem)
    readonly property bool contextCanBefore:
        contextNeighbor(-1) !== null
    readonly property bool contextCanNewer:
        contextNeighbor(1) !== null
    readonly property bool contextCanThere:
        contextTarget.length > 0
    readonly property string contextLabel: {
        const parts = [];

        if (contextTarget)
            parts.push(contextTarget);

        if (contextSource)
            parts.push(contextSource.toUpperCase());

        if (contextTimeLabel)
            parts.push(contextTimeLabel);

        if (contextAttentionMode)
            parts.push(
                attentionModeLabel(contextAttentionMode)
            );

        if (contextHasEvent)
            parts.push("EVENT");
        else if (contextTarget)
            parts.push("ROOM");

        if (parts.length > 0)
            return parts.join(" // ");

        const item = contextItem || {};
        return String(
            item.title
            || item.source
            || "ACTIVITY"
        );
    }

    FileView {
        id: archiveExportFile

        path: root.archiveExportPath
        blockWrites: true
        atomicWrites: true
        printErrors: false
    }

    FileView {
        id: activityFile

        path: Quickshell.dataPath("hospital-reception.json")
        atomicWrites: true

        adapter: JsonAdapter {
            id: activityAdapter

            property int schemaVersion: 2
            property var events: []
            property var subjects: ({})
            property string lastReadAt: ""
            property var pinnedKeys: []
        }

        onAdapterUpdated: writeAdapter()
        onLoaded: root.hydrateActivity()
        onLoadFailed: root.hydrateActivity()
    }

    function exportArchive(eventsValue, labelValue) {
        const rows =
            Array.isArray(eventsValue)
            ? eventsValue.slice()
            : activityEvents.slice();
        const label =
            String(labelValue || "HOSPITAL RECEPTION ARCHIVE");

        try {
            archiveExportFile.setText(
                JSON.stringify({
                    schemaVersion: 1,
                    exportedAt: nowIso(),
                    label: label,
                    count: rows.length,
                    events: rows
                }, null, 2)
            );
            lastArchiveExportStatus =
                "EXPORTED "
                + String(rows.length)
                + " EVENTS // "
                + archiveExportPath;
            return true;
        } catch (error) {
            lastArchiveExportStatus =
                "EXPORT FAILED // " + String(error);
            return false;
        }
    }

    function nowIso() {
        return new Date().toISOString();
    }

    function nowLabel() {
        return new Date().toLocaleTimeString();
    }

    function timeLabelFor(recordedAtValue) {
        const raw = String(recordedAtValue || "");
        const date = raw ? new Date(raw) : new Date();

        if (Number.isNaN(date.getTime()))
            return nowLabel();

        return date.toLocaleTimeString();
    }

    function eventEpoch(event) {
        const parsed = Date.parse(String((event || {}).recordedAt || ""));
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function timestampEpoch(value) {
        const parsed = Date.parse(String(value || ""));
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function localDayStart(dateValue) {
        const date = dateValue instanceof Date
            ? dateValue
            : new Date(dateValue);

        return new Date(
            date.getFullYear(),
            date.getMonth(),
            date.getDate()
        ).getTime();
    }

    function numberWordValue(value) {
        const token = String(value || "").toLowerCase();
        const words = {
            one: 1,
            two: 2,
            three: 3,
            four: 4,
            five: 5,
            six: 6,
            seven: 7,
            eight: 8,
            nine: 9,
            ten: 10,
            twelve: 12,
            twenty: 20,
            thirty: 30
        };

        if (Object.prototype.hasOwnProperty.call(words, token))
            return Number(words[token] || 0);

        const parsed = Number(token);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function isoDayRange(value) {
        const raw = String(value || "").trim();
        const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);

        if (!match)
            return null;

        const year = Number(match[1]);
        const month = Number(match[2]) - 1;
        const day = Number(match[3]);
        const start = new Date(year, month, day);

        if (start.getFullYear() !== year
                || start.getMonth() !== month
                || start.getDate() !== day)
            return null;

        return {
            label: raw,
            startEpoch: start.getTime(),
            endEpoch:
                new Date(year, month, day + 1).getTime()
        };
    }

    function activityTimeWindow(queryValue) {
        const query = looseQuery(queryValue);
        const now = new Date();
        const nowEpoch = now.getTime();
        const todayStart = localDayStart(now);
        const oneHour = 60 * 60 * 1000;
        const oneDay = 24 * oneHour;
        const oneWeek = 7 * oneDay;

        function result(label, start, end) {
            return {
                active: true,
                label: String(label || ""),
                startEpoch: Number(start || 0),
                endEpoch: Number(end || 0)
            };
        }

        const dateRangeMatch =
            query.match(
                /\b(?:from|between)\s+(\d{4}-\d{2}-\d{2})\s+(?:to|and)\s+(\d{4}-\d{2}-\d{2})\b/
            );

        if (dateRangeMatch && dateRangeMatch.length > 2) {
            const first = isoDayRange(dateRangeMatch[1]);
            const second = isoDayRange(dateRangeMatch[2]);

            if (first && second) {
                return result(
                    "FROM " + dateRangeMatch[1]
                    + " TO " + dateRangeMatch[2],
                    Math.min(first.startEpoch, second.startEpoch),
                    Math.max(first.endEpoch, second.endEpoch)
                );
            }
        }

        const onDateMatch =
            query.match(/\b(?:on|for)\s+(\d{4}-\d{2}-\d{2})\b/);

        if (onDateMatch && onDateMatch.length > 1) {
            const dayRange = isoDayRange(onDateMatch[1]);

            if (dayRange)
                return result(
                    "ON " + onDateMatch[1],
                    dayRange.startEpoch,
                    dayRange.endEpoch
                );
        }

        const sinceDateMatch =
            query.match(/\bsince\s+(\d{4}-\d{2}-\d{2})\b/);

        if (sinceDateMatch && sinceDateMatch.length > 1) {
            const dayRange = isoDayRange(sinceDateMatch[1]);

            if (dayRange)
                return result(
                    "SINCE " + sinceDateMatch[1],
                    dayRange.startEpoch,
                    nowEpoch + 1
                );
        }

        const beforeDateMatch =
            query.match(/\bbefore\s+(\d{4}-\d{2}-\d{2})\b/);

        if (beforeDateMatch && beforeDateMatch.length > 1) {
            const dayRange = isoDayRange(beforeDateMatch[1]);

            if (dayRange)
                return result(
                    "BEFORE " + beforeDateMatch[1],
                    0,
                    dayRange.startEpoch
                );
        }

        if (query.indexOf("last week") >= 0) {
            const day = now.getDay();
            const daysSinceMonday = day === 0 ? 6 : day - 1;
            const thisWeekStart =
                todayStart - (daysSinceMonday * oneDay);

            return result(
                "LAST WEEK",
                thisWeekStart - oneWeek,
                thisWeekStart
            );
        }

        if (query.indexOf("this month") >= 0) {
            return result(
                "THIS MONTH",
                new Date(
                    now.getFullYear(),
                    now.getMonth(),
                    1
                ).getTime(),
                nowEpoch + 1
            );
        }

        if (query.indexOf("last month") >= 0) {
            return result(
                "LAST MONTH",
                new Date(
                    now.getFullYear(),
                    now.getMonth() - 1,
                    1
                ).getTime(),
                new Date(
                    now.getFullYear(),
                    now.getMonth(),
                    1
                ).getTime()
            );
        }

        if (query.indexOf("yesterday") >= 0) {
            return result(
                "YESTERDAY",
                todayStart - oneDay,
                todayStart
            );
        }

        if (query.indexOf("this morning") >= 0
                || query.indexOf("today morning") >= 0) {
            const noon =
                new Date(
                    now.getFullYear(),
                    now.getMonth(),
                    now.getDate(),
                    12, 0, 0, 0
                ).getTime();

            return result(
                "THIS MORNING",
                todayStart,
                Math.min(nowEpoch + 1, noon)
            );
        }

        if (query.indexOf("this afternoon") >= 0
                || query.indexOf("today afternoon") >= 0) {
            const noon =
                new Date(
                    now.getFullYear(),
                    now.getMonth(),
                    now.getDate(),
                    12, 0, 0, 0
                ).getTime();
            const evening =
                new Date(
                    now.getFullYear(),
                    now.getMonth(),
                    now.getDate(),
                    17, 0, 0, 0
                ).getTime();

            return result(
                "THIS AFTERNOON",
                noon,
                Math.min(nowEpoch + 1, evening)
            );
        }

        if (query.indexOf("this evening") >= 0
                || query.indexOf("tonight") >= 0
                || query.indexOf("today evening") >= 0) {
            const evening =
                new Date(
                    now.getFullYear(),
                    now.getMonth(),
                    now.getDate(),
                    17, 0, 0, 0
                ).getTime();

            return result(
                "THIS EVENING",
                evening,
                nowEpoch + 1
            );
        }

        if (query.indexOf("today") >= 0) {
            return result(
                "TODAY",
                todayStart,
                nowEpoch + 1
            );
        }

        if (query.indexOf("this week") >= 0) {
            const day = now.getDay();
            const daysSinceMonday = day === 0 ? 6 : day - 1;

            return result(
                "THIS WEEK",
                todayStart - (daysSinceMonday * oneDay),
                nowEpoch + 1
            );
        }

        const weekdayMatch =
            query.match(
                /\bsince\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/
            );

        if (weekdayMatch && weekdayMatch.length > 1) {
            const weekdays = {
                sunday: 0,
                monday: 1,
                tuesday: 2,
                wednesday: 3,
                thursday: 4,
                friday: 5,
                saturday: 6
            };
            const name = String(weekdayMatch[1] || "").toLowerCase();
            const targetDay = Number(weekdays[name]);
            let delta = now.getDay() - targetDay;

            if (delta < 0)
                delta += 7;

            return result(
                "SINCE " + name.toUpperCase(),
                todayStart - (delta * oneDay),
                nowEpoch + 1
            );
        }

        const relativeMatch =
            query.match(
                /\b(?:last|past)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty|thirty)\s+(hour|hours|day|days|week|weeks)\b/
            );

        if (relativeMatch && relativeMatch.length > 2) {
            const amount = numberWordValue(relativeMatch[1]);
            const unit = String(relativeMatch[2] || "").toLowerCase();
            const scale =
                unit.indexOf("hour") === 0
                ? oneHour
                : unit.indexOf("week") === 0
                ? oneWeek
                : oneDay;

            if (amount > 0) {
                const unitLabel =
                    unit.indexOf("hour") === 0
                    ? amount === 1 ? "HOUR" : "HOURS"
                    : unit.indexOf("week") === 0
                    ? amount === 1 ? "WEEK" : "WEEKS"
                    : amount === 1 ? "DAY" : "DAYS";

                return result(
                    "LAST "
                    + String(amount)
                    + " "
                    + unitLabel,
                    nowEpoch - (amount * scale),
                    nowEpoch + 1
                );
            }
        }

        if (query.indexOf("last hour") >= 0
                || query.indexOf("past hour") >= 0) {
            return result(
                "LAST HOUR",
                nowEpoch - oneHour,
                nowEpoch + 1
            );
        }

        return {
            active: false,
            label: "",
            startEpoch: 0,
            endEpoch: 0
        };
    }

    function eventInTimeWindow(
            eventValue,
            startEpochValue,
            endEpochValue) {
        const epoch = eventEpoch(eventValue || {});
        const start = Number(startEpochValue || 0);
        const end = Number(endEpochValue || 0);

        if (start > 0 && epoch < start)
            return false;

        if (end > 0 && epoch >= end)
            return false;

        return true;
    }

    function readBaselineAt() {
        if (lastReadAt)
            return lastReadAt;

        if (visitActive && visitStartedAt)
            return visitStartedAt;

        return "";
    }

    function isUnread(event) {
        const baseline = readBaselineAt();

        if (!baseline)
            return false;

        return eventEpoch(event) > timestampEpoch(baseline);
    }

    function rebuildReadMetrics() {
        recentCount = Math.min(5, activityEvents.length);

        const baseline = readBaselineAt();

        if (!baseline) {
            unreadCount = 0;
            return;
        }

        let count = 0;

        for (let i = 0; i < activityEvents.length; ++i) {
            if (eventEpoch(activityEvents[i] || {})
                    > timestampEpoch(baseline))
                count += 1;
        }

        unreadCount = count;
    }

    function unreadSourceCounts() {
        const result = {
            rounds: 0,
            reports: 0,
            intercom: 0,
            phone: 0,
            staff: 0,
            other: 0
        };
        const baseline = readBaselineAt();

        if (!baseline)
            return result;

        const cutoff = timestampEpoch(baseline);

        for (let i = 0; i < activityEvents.length; ++i) {
            const event = activityEvents[i] || {};

            if (eventEpoch(event) <= cutoff)
                continue;

            const source =
                String(event.source || "").toLowerCase();

            if (Object.prototype.hasOwnProperty.call(result, source))
                result[source] += 1;
            else
                result.other += 1;
        }

        return result;
    }

    function briefingBody() {
        if (!lastReadAt) {
            return recentCount > 0
                ? (
                    "FIRST DESK VISIT // "
                    + String(recentCount)
                    + " RECENT ITEM"
                    + (recentCount === 1 ? "" : "S")
                    + " AVAILABLE"
                  )
                : "FIRST DESK VISIT // NO RECENT ACTIVITY";
        }

        if (unreadCount <= 0)
            return "";

        const counts = unreadSourceCounts();
        const order = [
            ["rounds", "ROUNDS"],
            ["reports", "REPORTS"],
            ["intercom", "INTERCOM"],
            ["phone", "PHONE"],
            ["staff", "STAFF"],
            ["other", "OTHER"]
        ];
        const parts = [
            String(unreadCount)
            + " NEW SINCE LAST VISIT"
        ];

        for (let i = 0; i < order.length; ++i) {
            const key = order[i][0];
            const label = order[i][1];
            const count = Number(counts[key] || 0);

            if (count > 0)
                parts.push(label + " " + String(count));
        }

        return parts.join(" // ");
    }

    function beginVisit() {
        if (!activityHydrated) {
            pendingVisitStart = true;
            return false;
        }

        if (visitActive)
            return false;

        pendingVisitStart = false;
        visitActive = true;
        visitStartedAt = nowIso();
        rebuildReadMetrics();

        const briefing = briefingBody();

        if (briefing)
            append("RECEPTION", briefing);

        return true;
    }

    function endVisit() {
        pendingVisitStart = false;

        if (!activityHydrated || !visitActive)
            return false;

        visitActive = false;
        visitStartedAt = "";
        lastReadAt = nowIso();
        activityAdapter.lastReadAt = lastReadAt;
        rebuildReadMetrics();
        return true;
    }

    function eventKey(event) {
        return String((event || {}).key || "");
    }

    function isPinned(event) {
        const key = eventKey(event);

        return !!key && pinnedKeys.indexOf(key) >= 0;
    }

    function archiveProtected(eventValue) {
        const event = eventValue || {};
        const source =
            String(event.source || "").toLowerCase();

        if (isPinned(event))
            return true;

        if (source === "reports"
                || source === "phone"
                || source === "intercom")
            return true;

        return isProblemActivity(event);
    }

    function passiveArchiveFingerprint(eventValue) {
        const event = eventValue || {};
        const source =
            String(event.source || "").toLowerCase();

        if (source !== "rounds" && source !== "staff")
            return "";

        if (archiveProtected(event))
            return "";

        const context = event.context || {};
        const room = context.room || {};
        const specialist =
            String(context.specialistId || "");
        const team =
            String(
                context.team
                || room.team
                || room.branch
                || ""
            ).toUpperCase();

        return [
            source,
            String(event.kind || ""),
            String(event.title || ""),
            String(event.detail || ""),
            team,
            specialist
        ].join("::");
    }

    function archiveEventIsMalformed(eventValue) {
        const event = eventValue || {};

        if (archiveProtected(event))
            return false;

        return !eventKey(event)
            || eventEpoch(event) <= 0
            || !String(event.source || "").trim()
            || !String(event.title || "").trim();
    }

    function archiveStats(eventsValue) {
        const events =
            Array.isArray(eventsValue)
            ? eventsValue
            : activityEvents;
        const stats = {
            total: events.length,
            favorites: 0,
            reports: 0,
            important: 0,
            communications: 0,
            passive: 0
        };

        for (let i = 0; i < events.length; ++i) {
            const event = events[i] || {};
            const source =
                String(event.source || "").toLowerCase();

            if (isPinned(event))
                stats.favorites += 1;
            if (source === "reports")
                stats.reports += 1;
            if (isProblemActivity(event))
                stats.important += 1;
            if (source === "phone" || source === "intercom")
                stats.communications += 1;
            if (source === "rounds" || source === "staff")
                stats.passive += 1;
        }

        return stats;
    }

    function archiveDateLabel(recordedAtValue) {
        const date = new Date(String(recordedAtValue || ""));

        if (Number.isNaN(date.getTime()))
            return "UNKNOWN";

        return date.toLocaleString();
    }

    function archiveStatsResponse(eventsValue, labelValue) {
        const events =
            Array.isArray(eventsValue)
            ? eventsValue
            : activityEvents;
        const stats = archiveStats(events);
        const label = String(labelValue || "ARCHIVE");
        const parts = [
            label,
            String(stats.total) + " / " + String(maxActivityEvents),
            "FAVORITES " + String(stats.favorites),
            "REPORTS " + String(stats.reports),
            "IMPORTANT " + String(stats.important),
            "COMMS " + String(stats.communications)
        ];

        if (events.length > 0) {
            const ordered = events.slice().sort(function(a, b) {
                return root.eventEpoch(a) - root.eventEpoch(b);
            });
            const oldest = ordered[0] || {};
            const newest = ordered[ordered.length - 1] || {};

            parts.push(
                "OLDEST "
                + archiveDateLabel(oldest.recordedAt)
            );
            parts.push(
                "NEWEST "
                + archiveDateLabel(newest.recordedAt)
            );
        }

        return parts.join(" // ");
    }

    function hasRecentPassiveDuplicate(eventValue) {
        const event = eventValue || {};
        const fingerprint =
            passiveArchiveFingerprint(event);

        if (!fingerprint)
            return false;

        const epoch = eventEpoch(event);

        if (epoch <= 0)
            return false;

        for (let i = activityEvents.length - 1; i >= 0; --i) {
            const existing = activityEvents[i] || {};
            const existingEpoch = eventEpoch(existing);

            if (existingEpoch <= 0)
                continue;

            if (epoch - existingEpoch > passiveDuplicateWindowMs)
                break;

            if (passiveArchiveFingerprint(existing) === fingerprint)
                return true;
        }

        return false;
    }

    function cleanArchive() {
        const source =
            Array.isArray(activityEvents)
            ? activityEvents.slice()
            : [];
        const kept = [];
        const fingerprintIndex = {};
        let malformedRemoved = 0;
        let duplicateRemoved = 0;

        source.sort(function(a, b) {
            return root.eventEpoch(a) - root.eventEpoch(b);
        });

        for (let i = 0; i < source.length; ++i) {
            const event = source[i] || {};

            if (archiveEventIsMalformed(event)) {
                malformedRemoved += 1;
                continue;
            }

            const fingerprint =
                passiveArchiveFingerprint(event);

            if (fingerprint) {
                const previousIndex =
                    Object.prototype.hasOwnProperty.call(
                        fingerprintIndex,
                        fingerprint
                    )
                    ? Number(fingerprintIndex[fingerprint])
                    : -1;

                if (previousIndex >= 0) {
                    const previous =
                        kept[previousIndex] || {};
                    const delta =
                        eventEpoch(event) - eventEpoch(previous);

                    if (delta >= 0
                            && delta <= passiveDuplicateWindowMs) {
                        // Keep the newest copy of harmless repeated READY /
                        // CLEAR-style passive state noise.
                        kept[previousIndex] = event;
                        duplicateRemoved += 1;
                        continue;
                    }
                }

                fingerprintIndex[fingerprint] = kept.length;
            }

            kept.push(event);
        }

        const compacted = trimActivityEvents(kept);
        const capacityRemoved =
            Math.max(0, kept.length - compacted.length);
        const removed =
            malformedRemoved
            + duplicateRemoved
            + capacityRemoved;

        activityEvents = compacted;
        activityAdapter.events = compacted.slice();
        cleanPinnedKeys();
        refreshVisibleInbox();

        if (contextEventKey && !contextEvent())
            clearActivityContext();

        return {
            before: source.length,
            after: compacted.length,
            removed: removed,
            malformed: malformedRemoved,
            duplicates: duplicateRemoved,
            capacity: capacityRemoved
        };
    }

    function archiveCleanupResponse(resultValue) {
        const result = resultValue || {};

        return [
            "ARCHIVE CLEAN",
            "BEFORE " + String(result.before || 0),
            "AFTER " + String(result.after || 0),
            "REMOVED " + String(result.removed || 0),
            "DUPLICATES " + String(result.duplicates || 0),
            "MALFORMED " + String(result.malformed || 0),
            "CAPACITY " + String(result.capacity || 0)
        ].join(" // ");
    }

    function archiveCleanupWindow(queryValue) {
        const query = looseQuery(queryValue);
        const nowEpoch = Date.now();
        const oneHour = 60 * 60 * 1000;
        const oneDay = 24 * oneHour;
        const oneWeek = 7 * oneDay;
        const olderMatch =
            query.match(
                /\bolder\s+than\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty|thirty)\s+(hour|hours|day|days|week|weeks)\b/
            );

        if (olderMatch && olderMatch.length > 2) {
            const amount = numberWordValue(olderMatch[1]);
            const unit = String(olderMatch[2] || "").toLowerCase();
            const scale =
                unit.indexOf("hour") === 0
                ? oneHour
                : unit.indexOf("week") === 0
                ? oneWeek
                : oneDay;

            if (amount > 0) {
                return {
                    active: true,
                    label:
                        "OLDER THAN "
                        + String(amount)
                        + " "
                        + (
                            unit.indexOf("hour") === 0
                            ? amount === 1 ? "HOUR" : "HOURS"
                            : unit.indexOf("week") === 0
                            ? amount === 1 ? "WEEK" : "WEEKS"
                            : amount === 1 ? "DAY" : "DAYS"
                          ),
                    startEpoch: 0,
                    endEpoch: nowEpoch - (amount * scale)
                };
            }
        }

        return activityTimeWindow(query);
    }

    function archiveCleanupSpec(textValue) {
        const query = looseQuery(textValue);
        const source = activityQuerySource(query);
        const target = activityTargetFromQuery(query);
        const window = archiveCleanupWindow(query);
        const attention = activityAttentionQuery(query);

        return {
            active:
                source.length > 0
                || target.length > 0
                || window.active
                || attention.active,
            source: source,
            target: target,
            startEpoch: Number(window.startEpoch || 0),
            endEpoch: Number(window.endEpoch || 0),
            timeLabel: String(window.label || ""),
            attentionMode:
                String(attention.mode || "").toLowerCase()
        };
    }

    function archiveCleanupSpecLabel(specValue) {
        const spec = specValue || {};
        const parts = [];

        if (spec.source)
            parts.push(String(spec.source).toUpperCase());
        if (spec.target)
            parts.push(String(spec.target).toUpperCase());
        if (spec.timeLabel)
            parts.push(String(spec.timeLabel));
        if (spec.attentionMode)
            parts.push(attentionModeLabel(spec.attentionMode));

        return parts.length > 0
            ? parts.join(" // ")
            : "ALL SAFE PASSIVE NOISE";
    }

    function archiveEventMatchesCleanupSpec(eventValue, specValue) {
        const event = eventValue || {};
        const spec = specValue || {};

        if (spec.source
                && String(event.source || "").toLowerCase()
                   !== String(spec.source).toLowerCase())
            return false;

        if (spec.target
                && !eventMatchesTarget(event, spec.target))
            return false;

        if (!eventInTimeWindow(
                event,
                spec.startEpoch,
                spec.endEpoch))
            return false;

        if (spec.attentionMode
                && !eventMatchesAttentionMode(
                    event,
                    spec.attentionMode))
            return false;

        return true;
    }

    function previewArchiveSelectionCleanup(specValue) {
        const spec = specValue || {};
        let removable = 0;
        let protectedCount = 0;

        for (let i = 0; i < activityEvents.length; ++i) {
            const event = activityEvents[i] || {};

            if (!archiveEventMatchesCleanupSpec(event, spec))
                continue;

            if (archiveProtected(event))
                protectedCount += 1;
            else
                removable += 1;
        }

        return {
            before: activityEvents.length,
            removable: removable,
            protectedCount: protectedCount
        };
    }

    function applyArchiveSelectionCleanup(specValue) {
        const spec = specValue || {};
        const before = activityEvents.length;
        const next = [];
        let removed = 0;
        let protectedCount = 0;

        for (let i = 0; i < activityEvents.length; ++i) {
            const event = activityEvents[i] || {};

            if (!archiveEventMatchesCleanupSpec(event, spec)) {
                next.push(event);
                continue;
            }

            if (archiveProtected(event)) {
                protectedCount += 1;
                next.push(event);
                continue;
            }

            removed += 1;
        }

        activityEvents = next;
        activityAdapter.events = next.slice();
        cleanPinnedKeys();
        refreshVisibleInbox();

        if (contextEventKey && !contextEvent())
            clearActivityContext();

        return {
            before: before,
            after: next.length,
            removed: removed,
            protectedCount: protectedCount
        };
    }

    function archiveSelectionPreviewResponse(specValue) {
        const spec = specValue || {};
        const preview = previewArchiveSelectionCleanup(spec);

        return [
            "ARCHIVE CLEANUP PREVIEW",
            archiveCleanupSpecLabel(spec),
            "REMOVE " + String(preview.removable || 0),
            "PROTECTED " + String(preview.protectedCount || 0),
            "CONFIRM WITH: CONFIRM ARCHIVE CLEANUP"
        ].join(" // ");
    }

    function archiveSelectionCleanupResponse(specValue, resultValue) {
        const result = resultValue || {};

        return [
            "ARCHIVE CLEANUP",
            archiveCleanupSpecLabel(specValue),
            "BEFORE " + String(result.before || 0),
            "AFTER " + String(result.after || 0),
            "REMOVED " + String(result.removed || 0),
            "PROTECTED " + String(result.protectedCount || 0)
        ].join(" // ");
    }

    function answerArchiveMaintenance(textValue) {
        const raw = String(textValue || "").trim();

        if (!raw)
            return false;

        // Maintenance language should be forgiving in the same way as
        // ordinary Reception speech. Strip punctuation/filler before testing
        // intent so "Can you clean up the archive?" does not fall through to
        // the generic archive-history reader.
        const query = socialQuery(raw);
        const mentionsArchive =
            query.indexOf("archive") >= 0;
        const hasCleanupVerb =
            query.indexOf("clean") >= 0
            || query.indexOf("cleanup") >= 0
            || query.indexOf("prune") >= 0
            || query.indexOf("compact") >= 0;
        const asksCleanup =
            mentionsArchive && hasCleanupVerb;
        const asksConfirm =
            mentionsArchive
            && query.indexOf("confirm") >= 0
            && hasCleanupVerb;
        const asksCancel =
            mentionsArchive
            && query.indexOf("cancel") >= 0
            && hasCleanupVerb;
        const asksStats =
            mentionsArchive
            && (
                query.indexOf("status") >= 0
                || query.indexOf("stats") >= 0
                || query.indexOf("size") >= 0
                || query.indexOf("depth") >= 0
                || query.indexOf("capacity") >= 0
                || query.indexOf("health") >= 0
                || query.indexOf("how big") >= 0
                || query.indexOf("how full") >= 0
            );

        if (!asksCleanup && !asksStats)
            return false;

        append("OPERATOR", raw);

        if (asksCancel) {
            pendingArchiveCleanupSpec = null;
            append(
                "RECEPTION",
                "ARCHIVE CLEANUP // CANCELLED"
            );
            return true;
        }

        if (asksConfirm) {
            const pending = pendingArchiveCleanupSpec;

            if (!pending) {
                append(
                    "RECEPTION",
                    "ARCHIVE CLEANUP // NOTHING ARMED"
                );
                return true;
            }

            pendingArchiveCleanupSpec = null;
            append(
                "RECEPTION",
                archiveSelectionCleanupResponse(
                    pending,
                    applyArchiveSelectionCleanup(pending)
                )
            );
            return true;
        }

        if (asksCleanup) {
            const spec = archiveCleanupSpec(query);

            if (spec.active) {
                pendingArchiveCleanupSpec = spec;
                append(
                    "RECEPTION",
                    archiveSelectionPreviewResponse(spec)
                );
                return true;
            }

            pendingArchiveCleanupSpec = null;
            append(
                "RECEPTION",
                archiveCleanupResponse(cleanArchive())
            );
            return true;
        }

        const source = activityQuerySource(query);
        const target = activityTargetFromQuery(query);
        const window = activityTimeWindow(query);
        const attention = activityAttentionQuery(query);
        let matches =
            matchingActivity(
                source,
                false,
                false,
                target,
                window.startEpoch,
                window.endEpoch
            );

        matches =
            filterActivityByAttention(
                matches,
                attention.mode
            );

        const labels = ["ARCHIVE"];

        if (source)
            labels.push(source.toUpperCase());
        if (target)
            labels.push(target);
        if (window.active)
            labels.push(window.label);
        if (attention.active)
            labels.push(attention.label);

        append(
            "RECEPTION",
            archiveStatsResponse(
                matches,
                labels.join(" // ")
            )
        );
        return true;
    }

    function archivePriority(eventValue) {
        const event = eventValue || {};
        const source =
            String(event.source || "").toLowerCase();

        if (isPinned(event))
            return 1000;

        // Reports are evidence-bearing Hospital history. Keep them deep even
        // though Reports remains the authoritative evidence surface.
        if (source === "reports")
            return 700;

        if (isProblemActivity(event))
            return 600;

        // Human communication is generally more meaningful than old passive
        // status snapshots when archive space eventually gets tight.
        if (source === "phone" || source === "intercom")
            return 400;

        return 100;
    }

    function trimActivityEvents(eventsValue) {
        const source =
            Array.isArray(eventsValue)
            ? eventsValue.slice()
            : [];

        source.sort(function(a, b) {
            return root.eventEpoch(a) - root.eventEpoch(b);
        });

        if (source.length <= maxActivityEvents)
            return source;

        const recentCount =
            Math.min(
                guaranteedRecentEvents,
                maxActivityEvents,
                source.length
            );
        const recentStart = source.length - recentCount;
        const recent = source.slice(recentStart);
        const older = source.slice(0, recentStart);
        const olderBudget =
            Math.max(0, maxActivityEvents - recent.length);

        older.sort(function(a, b) {
            const priorityDelta =
                root.archivePriority(b)
                - root.archivePriority(a);

            if (priorityDelta !== 0)
                return priorityDelta;

            return root.eventEpoch(b) - root.eventEpoch(a);
        });

        const kept =
            older.slice(0, olderBudget).concat(recent);

        kept.sort(function(a, b) {
            return root.eventEpoch(a) - root.eventEpoch(b);
        });

        return kept;
    }

    function cleanPinnedKeys() {
        const existing = {};

        for (let i = 0; i < activityEvents.length; ++i) {
            const key = eventKey(activityEvents[i] || {});

            if (key)
                existing[key] = true;
        }

        const next = [];

        for (let i = 0; i < pinnedKeys.length; ++i) {
            const key = String(pinnedKeys[i] || "");

            if (key && existing[key] && next.indexOf(key) < 0)
                next.push(key);
        }

        pinnedKeys = next.slice(0, maxPinnedEvents);
        pinnedCount = pinnedKeys.length;
        activityAdapter.pinnedKeys = pinnedKeys.slice();
    }

    function setPinned(event, pinnedValue) {
        if (!activityHydrated)
            return false;

        const key = eventKey(event);

        if (!key)
            return false;

        const desired = Boolean(pinnedValue);
        const existing = pinnedKeys.indexOf(key);

        if (desired && existing >= 0)
            return true;

        if (!desired && existing < 0)
            return true;

        let next = pinnedKeys.slice();

        if (desired) {
            next = [key].concat(
                next.filter(function(value) {
                    return String(value || "") !== key;
                })
            ).slice(0, maxPinnedEvents);
        } else {
            next.splice(existing, 1);
        }

        pinnedKeys = next;
        pinnedCount = pinnedKeys.length;
        activityEvents = trimActivityEvents(activityEvents);
        activityAdapter.events = activityEvents.slice();
        activityAdapter.pinnedKeys = pinnedKeys.slice();
        refreshVisibleInbox();
        return true;
    }

    function togglePinned(event) {
        return setPinned(event, !isPinned(event));
    }

    function refreshVisibleInbox() {
        const ordered = activityEvents.slice().sort(function(a, b) {
            return root.eventEpoch(b) - root.eventEpoch(a);
        });
        const byKey = {};

        for (let i = 0; i < activityEvents.length; ++i) {
            const event = activityEvents[i] || {};
            const key = eventKey(event);

            if (key)
                byKey[key] = event;
        }

        const visible = [];
        const visibleKeys = {};

        function appendVisible(eventValue) {
            const event = eventValue || {};
            const key = root.eventKey(event);

            if (!key || visibleKeys[key] || visible.length >= 5)
                return false;

            visibleKeys[key] = true;
            visible.push(event);
            return true;
        }

        // Favorites retain their explicit operator-selected order.
        for (let i = 0;
                i < pinnedKeys.length && visible.length < 5;
                ++i) {
            const pinned =
                byKey[String(pinnedKeys[i] || "")];

            if (pinned)
                appendVisible(pinned);
        }

        // Unread operator-attention items outrank ordinary recency, but only
        // while they are genuinely new. Once read they return to normal
        // recency unless the operator explicitly favorited them.
        const priorityUnread =
            ordered.filter(function(event) {
                const row = event || {};

                return !root.isPinned(row)
                    && root.isUnread(row)
                    && root.activityAttentionScore(row) >= 60;
            });

        priorityUnread.sort(function(a, b) {
            const scoreDelta =
                root.activityAttentionScore(b)
                - root.activityAttentionScore(a);

            if (scoreDelta !== 0)
                return scoreDelta;

            return root.eventEpoch(b) - root.eventEpoch(a);
        });

        for (let i = 0;
                i < priorityUnread.length && visible.length < 5;
                ++i)
            appendVisible(priorityUnread[i]);

        // Fill remaining desk slots with ordinary newest-first activity so
        // NOTICE/ROUTINE events remain visible instead of being suppressed.
        for (let i = 0;
                i < ordered.length && visible.length < 5;
                ++i) {
            const event = ordered[i] || {};

            if (!isPinned(event))
                appendVisible(event);
        }

        inbox = visible;
        pinnedCount = Math.min(maxPinnedEvents, pinnedKeys.length);
        rebuildReadMetrics();
    }

    function hydrateActivity() {
        pinnedKeys =
            Array.isArray(activityAdapter.pinnedKeys)
            ? activityAdapter.pinnedKeys.slice(0, maxPinnedEvents)
            : [];
        activityEvents = trimActivityEvents(
            Array.isArray(activityAdapter.events)
            ? activityAdapter.events
            : []
        );
        subjectStates =
            activityAdapter.subjects
            && typeof activityAdapter.subjects === "object"
            ? Object.assign({}, activityAdapter.subjects)
            : ({});
        lastReadAt = String(activityAdapter.lastReadAt || "");
        activityHydrated = true;
        cleanPinnedKeys();
        refreshVisibleInbox();

        if (pendingActivities.length > 0) {
            const pending = pendingActivities.slice();
            pendingActivities = [];

            for (let i = 0; i < pending.length; ++i)
                recordActivity(pending[i] || {});
        }

        if (pendingVisitStart)
            beginVisit();
    }

    function activityKeyExists(keyValue) {
        const key = String(keyValue || "");

        if (!key)
            return false;

        for (let i = 0; i < activityEvents.length; ++i) {
            if (String((activityEvents[i] || {}).key || "") === key)
                return true;
        }

        return false;
    }

    function persistSubjects(nextSubjects) {
        subjectStates = Object.assign({}, nextSubjects || {});
        activityAdapter.subjects = Object.assign({}, subjectStates);
    }

    function recordActivity(spec) {
        const item = spec || {};

        if (!activityHydrated) {
            pendingActivities = pendingActivities.concat([item]);
            return true;
        }

        const recordedAt = String(item.recordedAt || nowIso());
        const source = String(item.source || "").toLowerCase();
        const kind = String(item.kind || source || "activity");
        const title = String(item.title || "HOSPITAL ACTIVITY");
        const detail = String(item.detail || "");
        const route = String(item.route || "");
        const key = String(
            item.key
            || (
                source
                + "::"
                + recordedAt
                + "::"
                + title
            )
        );

        if (activityKeyExists(key))
            return false;

        const event = {
            schemaVersion: 2,
            key: key,
            recordedAt: recordedAt,
            timeLabel:
                String(
                    item.timeLabel
                    || timeLabelFor(recordedAt)
                ),
            source: source,
            kind: kind,
            title: title,
            detail: detail,
            route: route,
            context: item.context || {}
        };

        if (hasRecentPassiveDuplicate(event))
            return false;

        let next = activityEvents.concat([event]);

        next.sort(function(a, b) {
            return root.eventEpoch(a) - root.eventEpoch(b);
        });

        next = trimActivityEvents(next);
        activityEvents = next;
        activityAdapter.events = next.slice();
        refreshVisibleInbox();
        return true;
    }

    function observeSubject(
            subjectValue,
            fingerprintValue,
            recordInitial,
            spec) {
        if (!activityHydrated)
            return false;

        const subject = String(subjectValue || "");
        const fingerprint = String(fingerprintValue || "");

        if (!subject || !fingerprint)
            return false;

        const previous =
            String(subjectStates[subject] || "");

        if (previous === fingerprint)
            return false;

        const nextSubjects = Object.assign({}, subjectStates);
        nextSubjects[subject] = fingerprint;
        persistSubjects(nextSubjects);

        if (!previous && !recordInitial)
            return false;

        return recordActivity(spec || {});
    }

    function syncRounds(roundsRooms) {
        if (!activityHydrated)
            return false;

        const rooms =
            Array.isArray(roundsRooms)
            ? roundsRooms
            : [];
        let initialAttentionBudget = 5;

        for (let i = 0; i < rooms.length; ++i) {
            const room = rooms[i] || {};
            const team = String(room.team || room.branch || "ROOM");
            const repository = String(room.repository || "");
            const state = String(room.state || "UNKNOWN").toUpperCase();
            const ahead = Number(room.ahead || 0);
            const behind = Number(room.behind || 0);
            const rank = Number(room.attentionRank || 0);
            const subject =
                "rounds::"
                + repository
                + "::"
                + team;
            const fingerprint =
                [
                    state,
                    String(ahead),
                    String(behind)
                ].join("|");
            const detailParts = [
                String(room.floorLabel || "FLOOR"),
                state
            ];

            if (ahead > 0)
                detailParts.push("AHEAD " + String(ahead));
            if (behind > 0)
                detailParts.push("BEHIND " + String(behind));

            const previous =
                String(subjectStates[subject] || "");
            const recordInitial =
                !previous
                && rank > 0
                && initialAttentionBudget > 0;

            if (recordInitial)
                initialAttentionBudget -= 1;

            observeSubject(
                subject,
                fingerprint,
                recordInitial,
                {
                    source: "rounds",
                    kind: "room",
                    title:
                        (
                            rank > 0
                            ? String(room.attentionLabel || "ATTENTION")
                            : "CLEAR"
                        )
                        + " // "
                        + team,
                    detail: detailParts.join(" // "),
                    route: "surgery",
                    context: {
                        room: room
                    }
                }
            );
        }

        return true;
    }

    function syncStaff(specialists) {
        if (!activityHydrated)
            return false;

        const staff =
            Array.isArray(specialists)
            ? specialists
            : [];

        for (let i = 0; i < staff.length; ++i) {
            const specialist = staff[i] || {};
            const id = String(specialist.id || "");
            const name = String(
                specialist.name
                || specialist.id
                || "SPECIALIST"
            );
            const presence =
                String(specialist.presence || "UNKNOWN").toUpperCase();

            if (!id)
                continue;

            observeSubject(
                "staff::" + id,
                presence,
                presence === "OFFLINE",
                {
                    source: "staff",
                    kind: "staff",
                    title: presence + " // " + name,
                    detail:
                        String(specialist.role || "SPECIALIST")
                        + " // "
                        + String(specialist.provider || "PROVIDER"),
                    route: "staff",
                    context: {
                        specialistId: id
                    }
                }
            );
        }

        return true;
    }

    function recordPhoneCall(specialistValue) {
        const specialist = specialistValue || {};
        const id = String(specialist.id || "");
        const name = String(
            specialist.name
            || specialist.id
            || "SPECIALIST"
        );

        return recordActivity({
            source: "phone",
            kind: "phone",
            title: "CALL // " + name,
            detail:
                String(specialist.role || "SPECIALIST")
                + " // "
                + String(specialist.provider || "PROVIDER"),
            route: "phone",
            context: {
                specialistId: id
            }
        });
    }

    function recordIntercomMessage(entryValue) {
        const entry = entryValue || {};
        const name = String(
            entry.specialistName
            || entry.specialistId
            || "SPECIALIST"
        );
        const channelType =
            String(entry.channelType || "HOSPITAL").toUpperCase();
        const channelLabel =
            String(entry.channelLabel || "GENERAL");
        const body = String(entry.body || "").trim();
        let detail =
            channelType
            + " // "
            + channelLabel;

        if (body)
            detail += " // " + body;

        return recordActivity({
            source: "intercom",
            kind: "intercom",
            title: "INTERCOM // " + name,
            detail: detail,
            route: "intercom",
            context: {
                specialistId: String(entry.specialistId || ""),
                channelType: channelType,
                channelLabel: channelLabel
            }
        });
    }

    function recordReportEvent(eventValue) {
        const event = eventValue || {};
        const details = event.details || {};
        const team = String(event.team || "ROOM");
        const eventType = String(event.eventType || "REPORT");
        const state = String(event.state || "");
        const branch = String(details.branch || "");
        const recordedAt = String(event.recordedAt || nowIso());
        const titleType =
            eventType.replace(/_/g, " ");

        return recordActivity({
            key:
                "reports::"
                + recordedAt
                + "::"
                + eventType
                + "::"
                + team,
            recordedAt: recordedAt,
            timeLabel: "",
            source: "reports",
            kind: "report",
            title: titleType + " // " + team,
            detail:
                state
                + (
                    branch
                    ? " // " + branch
                    : ""
                  ),
            route: "reports",
            context: {
                team: team,
                eventType: eventType,
                state: state
            }
        });
    }

    function syncReports(reportEvents) {
        if (!activityHydrated)
            return false;

        const events =
            Array.isArray(reportEvents)
            ? reportEvents.slice(-reportArchiveBackfillLimit)
            : [];

        for (let i = 0; i < events.length; ++i)
            recordReportEvent(events[i] || {});

        return true;
    }

    function append(sender, body) {
        const next = transcript.concat([{
            sender: String(sender || ""),
            body: String(body || "")
        }]);

        transcript = next.length > 40
            ? next.slice(next.length - 40)
            : next;
    }

    readonly property var fuzzyVocabulary: [
        "what", "where", "when", "which",
        "problem", "problems", "issue", "issues",
        "wrong", "broken", "broke", "failed", "failure",
        "trouble", "holdup", "holding", "blocking",
        "happening", "happened", "changed", "doing",
        "going", "important", "attention", "recent",
        "latest", "newest", "newer", "older", "before",
        "previous", "activity", "history", "evidence",
        "report", "reports", "round", "rounds",
        "staff", "specialist", "specialists",
        "intercom", "message", "messages",
        "phone", "call", "calls", "favorite", "favorites",
        "favourite", "favourites", "pinned", "starred",
        "saved", "open", "show", "take", "bring",
        "send", "find", "locate", "there", "this",
        "that", "anything", "something", "update",
        "hello", "hey", "thanks", "thank", "morning",
        "afternoon", "evening", "good", "going",
        "today", "yesterday", "tonight", "week", "since",
        "hour", "hours", "day", "days", "past",
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
        "archive", "archives", "earliest", "oldest", "first",
        "clean", "cleanup", "prune", "compact", "size", "depth",
        "capacity", "health", "duplicate", "duplicates",
        "critical", "urgent", "serious", "action", "notice", "notices",
        "routine", "background", "priority", "priorities", "prioritize",
        "focus", "ignore", "wait", "later", "top"
    ]

    function editDistanceOneOrLess(leftValue, rightValue) {
        const left = String(leftValue || "").toLowerCase();
        const right = String(rightValue || "").toLowerCase();

        if (left === right)
            return 0;

        const delta = left.length - right.length;

        if (Math.abs(delta) > 1)
            return 2;

        if (delta === 0) {
            let mismatches = 0;

            for (let i = 0; i < left.length; ++i) {
                if (left[i] !== right[i]) {
                    mismatches += 1;

                    if (mismatches > 1)
                        return 2;
                }
            }

            return mismatches;
        }

        const shorter = delta < 0 ? left : right;
        const longer = delta < 0 ? right : left;
        let shortIndex = 0;
        let longIndex = 0;
        let skipped = false;

        while (shortIndex < shorter.length
                && longIndex < longer.length) {
            if (shorter[shortIndex] === longer[longIndex]) {
                shortIndex += 1;
                longIndex += 1;
                continue;
            }

            if (skipped)
                return 2;

            skipped = true;
            longIndex += 1;
        }

        return 1;
    }

    function fuzzyWord(wordValue) {
        const word = String(wordValue || "").toLowerCase();

        if (!word)
            return word;

        if (/^t\d+(?:-[a-z0-9]+)?$/i.test(word))
            return word;

        let best = word;
        let bestDistance = 2;
        let bestCount = 0;

        for (let i = 0; i < fuzzyVocabulary.length; ++i) {
            const candidate =
                String(fuzzyVocabulary[i] || "").toLowerCase();

            if (!candidate)
                continue;

            if (word === candidate)
                return word;

            // Keep tiny ordinary words exact except for WHAT, which is a
            // deliberate convenience case ("wht", "hat", etc.).
            if (word.length < 4
                    && candidate !== "what")
                continue;

            const distance =
                editDistanceOneOrLess(word, candidate);

            if (distance < bestDistance) {
                best = candidate;
                bestDistance = distance;
                bestCount = 1;
            } else if (distance === bestDistance
                    && distance <= 1) {
                bestCount += 1;
            }
        }

        // Do not guess when a typo is equally close to two commands.
        return bestDistance <= 1 && bestCount === 1
            ? best
            : word;
    }

    function looseQuery(textValue) {
        return String(textValue || "")
            .toLowerCase()
            .replace(/[a-z]+/g, function(word) {
                return root.fuzzyWord(word);
            });
    }

    function socialQuery(textValue) {
        return looseQuery(textValue)
            .replace(/[!?.,;:]+/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function answerSocial(textValue) {
        const raw = String(textValue || "").trim();

        if (!raw)
            return false;

        const query = socialQuery(raw);
        let response = "";

        if (query === "hi"
                || query === "hey"
                || query === "hello"
                || query === "hi there"
                || query === "hey there"
                || query === "hello there"
                || query === "hi reception"
                || query === "hey reception"
                || query === "hello reception") {
            response = "Hey. Front desk's up.";
        } else if (query === "what's up"
                || query === "whats up"
                || query === "what is up"
                || query === "sup") {
            response = "Front desk's up. Hospital's still moving.";
        } else if (query === "how's it going"
                || query === "hows it going"
                || query === "how is it going"
                || query === "how are you"
                || query === "you good"
                || query === "are you good") {
            response = "Doing fine. Desk is online.";
        } else if (query === "good morning") {
            response = "Morning. Front desk's online.";
        } else if (query === "good afternoon") {
            response = "Afternoon. Front desk's online.";
        } else if (query === "good evening") {
            response = "Evening. Front desk's online.";
        } else if (query === "thanks"
                || query === "thank you"
                || query === "thank you reception"
                || query === "thanks reception"
                || query === "appreciate it") {
            response = "Any time.";
        }

        if (!response)
            return false;

        append("OPERATOR", raw);
        append("RECEPTION", response);
        return true;
    }

    function activityQuerySource(queryValue) {
        const query = looseQuery(queryValue);

        if (query.indexOf("report") >= 0
                || query.indexOf("history") >= 0
                || query.indexOf("evidence") >= 0)
            return "reports";

        if (query.indexOf("round") >= 0
                || query.indexOf("attention") >= 0)
            return "rounds";

        if (query.indexOf("intercom") >= 0
                || query.indexOf("message") >= 0)
            return "intercom";

        if (query.indexOf("phone") >= 0
                || query.indexOf("call") >= 0)
            return "phone";

        if (query.indexOf("staff") >= 0
                || query.indexOf("specialist") >= 0)
            return "staff";

        return "";
    }

    function activityTargetFromQuery(queryValue) {
        const query = String(queryValue || "");
        const direct =
            query.match(/\bT\d+(?:-[A-Z0-9]+)?\b/i);

        if (direct && direct.length > 0)
            return String(direct[0] || "").toUpperCase();

        const teamNumber =
            query.match(/\bteam\s+(\d+)\b/i);

        if (teamNumber && teamNumber.length > 1)
            return "T" + String(teamNumber[1] || "");

        return "";
    }

    function eventMatchesTarget(eventValue, targetValue) {
        const event = eventValue || {};
        const target =
            String(targetValue || "").trim().toUpperCase();

        if (!target)
            return true;

        const context = event.context || {};
        const room = context.room || {};
        const values = [
            String(context.team || ""),
            String(room.team || ""),
            String(event.title || ""),
            String(event.detail || "")
        ];

        for (let i = 0; i < values.length; ++i) {
            const value = values[i].toUpperCase();

            if (value.indexOf(target) >= 0)
                return true;
        }

        return false;
    }

    function matchingActivity(
            sourceValue,
            unreadOnly,
            favoritesOnly,
            targetValue,
            startEpochValue,
            endEpochValue) {
        const source = String(sourceValue || "").toLowerCase();
        const target = String(targetValue || "");
        const matches = [];

        for (let i = 0; i < activityEvents.length; ++i) {
            const event = activityEvents[i] || {};

            if (source
                    && String(event.source || "").toLowerCase()
                       !== source)
                continue;

            if (!eventMatchesTarget(event, target))
                continue;

            if (unreadOnly && !isUnread(event))
                continue;

            if (favoritesOnly && !isPinned(event))
                continue;

            if (!eventInTimeWindow(
                    event,
                    startEpochValue,
                    endEpochValue))
                continue;

            matches.push(event);
        }

        matches.sort(function(a, b) {
            return root.eventEpoch(b) - root.eventEpoch(a);
        });

        return matches;
    }

    function activityLine(eventValue) {
        const event = eventValue || {};
        const time = String(event.timeLabel || "");
        const source =
            String(event.source || "activity").toUpperCase();
        const title = String(event.title || "HOSPITAL ACTIVITY");
        const detail = String(event.detail || "");

        return [
            time,
            source,
            title,
            detail
        ].filter(function(value) {
            return String(value || "").length > 0;
        }).join(" // ");
    }

    function activityListResponse(
            labelValue,
            eventsValue,
            showAttention,
            limitValue) {
        const label = String(labelValue || "RECENT");
        const requestedLimit =
            Number(limitValue || 0);
        const limit =
            requestedLimit > 0
            ? Math.max(1, Math.min(5, requestedLimit))
            : 5;
        const events =
            Array.isArray(eventsValue)
            ? eventsValue.slice(0, limit)
            : [];

        if (events.length === 0)
            return label + " // NONE RECORDED";

        const lines = [label + " // " + String(events.length)];

        for (let i = 0; i < events.length; ++i) {
            lines.push(
                "- "
                + (
                    showAttention
                    ? attentionActivityLine(events[i] || {})
                    : activityLine(events[i] || {})
                  )
            );
        }

        return lines.join("\n");
    }

    function activityCountResponse(labelValue, eventsValue) {
        const label = String(labelValue || "ACTIVITY");
        const events =
            Array.isArray(eventsValue)
            ? eventsValue
            : [];
        const counts = {
            rounds: 0,
            reports: 0,
            intercom: 0,
            phone: 0,
            staff: 0,
            other: 0
        };

        for (let i = 0; i < events.length; ++i) {
            const source =
                String((events[i] || {}).source || "").toLowerCase();

            if (Object.prototype.hasOwnProperty.call(counts, source))
                counts[source] += 1;
            else
                counts.other += 1;
        }

        const parts = [
            label + " // " + String(events.length)
        ];
        const order = [
            ["rounds", "ROUNDS"],
            ["reports", "REPORTS"],
            ["intercom", "INTERCOM"],
            ["phone", "PHONE"],
            ["staff", "STAFF"],
            ["other", "OTHER"]
        ];

        for (let i = 0; i < order.length; ++i) {
            const count = Number(counts[order[i][0]] || 0);

            if (count > 0)
                parts.push(order[i][1] + " " + String(count));
        }

        return parts.join(" // ");
    }

    function activityAttentionScore(eventValue) {
        const event = eventValue || {};
        const source =
            String(event.source || "").toLowerCase();
        const context = event.context || {};
        const room = context.room || {};
        const state =
            String(
                context.state
                || room.state
                || ""
            ).toUpperCase();
        const title =
            String(event.title || "").toUpperCase();
        const detail =
            String(event.detail || "").toUpperCase();
        const text =
            [state, title, detail].join(" ");
        let score = 20;

        if (source === "rounds") {
            const rank =
                Number(room.attentionRank || 0);

            if (rank >= 90)
                score = Math.max(score, 95);
            else if (rank >= 60)
                score = Math.max(score, 75);
            else if (rank > 0)
                score = Math.max(score, 45);
            else
                score = Math.max(score, 10);
        } else if (source === "reports") {
            if (state === "BLOCKED")
                score = Math.max(score, 100);
            else if (state === "REOPENED")
                score = Math.max(score, 90);
            else if (state === "INTEGRATING")
                score = Math.max(score, 75);
            else if (state === "ARMED")
                score = Math.max(score, 65);
            else if (state === "CANDIDATE")
                score = Math.max(score, 45);
            else if (state === "VERIFIED"
                    || state === "CERTIFIED"
                    || state === "POST_OP")
                score = Math.max(score, 35);
            else if (state === "IN_MAIN")
                score = Math.max(score, 15);
            else
                score = Math.max(score, 30);
        } else if (source === "staff") {
            if (title.indexOf("OFFLINE //") === 0)
                score = Math.max(score, 75);
            else if (title.indexOf("UNKNOWN //") === 0)
                score = Math.max(score, 40);
            else
                score = Math.max(score, 10);
        } else if (source === "phone"
                || source === "intercom") {
            score = Math.max(score, 35);
        }

        if (text.indexOf("BLOCKED") >= 0
                || text.indexOf("DIVERGED") >= 0
                || text.indexOf("MISSING") >= 0
                || text.indexOf("FAILED") >= 0
                || text.indexOf("FAILURE") >= 0
                || text.indexOf("ERROR") >= 0)
            score = Math.max(score, 95);

        if (text.indexOf("REOPENED") >= 0)
            score = Math.max(score, 90);

        if (text.indexOf("OFFLINE") >= 0
                || text.indexOf("AHEAD") >= 0
                || text.indexOf("BEHIND") >= 0
                || text.indexOf("STALE") >= 0)
            score = Math.max(score, 70);

        if (text.indexOf("ATTENTION") >= 0
                || text.indexOf("WARNING") >= 0
                || text.indexOf("CHECK") >= 0)
            score = Math.max(score, 45);

        return Math.max(0, Math.min(100, score));
    }

    function activityAttentionLabel(eventValue) {
        const score = activityAttentionScore(eventValue);

        if (score >= 90)
            return "CRITICAL";
        if (score >= 60)
            return "ACTION";
        if (score >= 30)
            return "NOTICE";

        return "ROUTINE";
    }

    function attentionModeLabel(modeValue) {
        const mode =
            String(modeValue || "").toLowerCase();

        if (mode === "critical")
            return "CRITICAL";
        if (mode === "action")
            return "ACTION+";
        if (mode === "notice")
            return "NOTICE";
        if (mode === "routine")
            return "ROUTINE";

        return "";
    }

    function rankActivityByAttention(eventsValue) {
        const events =
            Array.isArray(eventsValue)
            ? eventsValue.slice()
            : [];

        events.sort(function(a, b) {
            const scoreDelta =
                root.activityAttentionScore(b)
                - root.activityAttentionScore(a);

            if (scoreDelta !== 0)
                return scoreDelta;

            return root.eventEpoch(b) - root.eventEpoch(a);
        });

        return events;
    }

    function attentionRankingQuery(queryValue) {
        const query = socialQuery(queryValue);
        let active = false;
        let limit = 3;

        if (query.indexOf("top ") >= 0
                || query === "top"
                || query.indexOf("prioritize") >= 0
                || query.indexOf("priority order") >= 0
                || query.indexOf("what comes first") >= 0
                || query.indexOf("where should i start") >= 0
                || query.indexOf("what should i do first") >= 0
                || query.indexOf("what should i look at first") >= 0
                || query.indexOf("what should i check first") >= 0
                || query.indexOf("what should i focus on") >= 0
                || query.indexOf("most important") >= 0) {
            active = true;
        }

        if (!active)
            return {
                active: false,
                limit: 0
            };

        if (query.indexOf(" first") >= 0
                || query.indexOf("most important") >= 0)
            limit = 1;

        const topMatch =
            query.match(
                /\btop\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b/
            );

        if (topMatch && topMatch[1]) {
            const requested =
                numberWordValue(topMatch[1]);

            if (requested > 0)
                limit = requested;
        }

        return {
            active: true,
            limit: Math.max(1, Math.min(5, limit))
        };
    }

    function activityAttentionQuery(queryValue) {
        const query = looseQuery(queryValue);
        let mode = "";

        if (query.indexOf("critical") >= 0
                || query.indexOf("urgent") >= 0
                || query.indexOf("serious") >= 0)
            mode = "critical";
        else if (query.indexOf("routine") >= 0
                || query.indexOf("background") >= 0
                || query.indexOf("low priority") >= 0
                || query.indexOf("can i ignore") >= 0
                || query.indexOf("can ignore") >= 0
                || query.indexOf("what can wait") >= 0
                || query.indexOf("can wait") >= 0
                || query.indexOf("leave for later") >= 0
                || query.indexOf("not urgent") >= 0)
            mode = "routine";
        else if (query.indexOf("notice") >= 0
                || query.indexOf("notices") >= 0
                || query.indexOf("fyi") >= 0)
            mode = "notice";
        else if (query.indexOf("action") >= 0
                || query.indexOf("what needs me") >= 0
                || query.indexOf("needs me") >= 0
                || query.indexOf("needs attention") >= 0
                || query.indexOf("what should i check") >= 0
                || query.indexOf("what should i look at") >= 0
                || query.indexOf("what should i focus on") >= 0
                || query.indexOf("what should i prioritize") >= 0
                || query.indexOf("where should i start") >= 0
                || query.indexOf("important") >= 0
                || query.indexOf("high priority") >= 0)
            mode = "action";

        return {
            active: mode.length > 0,
            mode: mode,
            label: attentionModeLabel(mode)
        };
    }

    function eventMatchesAttentionMode(eventValue, modeValue) {
        const mode =
            String(modeValue || "").toLowerCase();
        const score =
            activityAttentionScore(eventValue);

        if (!mode)
            return true;
        if (mode === "critical")
            return score >= 90;
        if (mode === "action")
            return score >= 60;
        if (mode === "notice")
            return score >= 30 && score < 60;
        if (mode === "routine")
            return score < 30;

        return true;
    }

    function filterActivityByAttention(
            eventsValue,
            modeValue) {
        const events =
            Array.isArray(eventsValue)
            ? eventsValue.slice()
            : [];
        const mode =
            String(modeValue || "").toLowerCase();

        if (!mode)
            return events;

        const filtered =
            events.filter(function(event) {
                return root.eventMatchesAttentionMode(
                    event || {},
                    mode
                );
            });

        filtered.sort(function(a, b) {
            const scoreDelta =
                root.activityAttentionScore(b)
                - root.activityAttentionScore(a);

            if (scoreDelta !== 0)
                return scoreDelta;

            return root.eventEpoch(b) - root.eventEpoch(a);
        });

        return filtered;
    }

    function attentionActivityLine(eventValue) {
        return activityAttentionLabel(eventValue)
            + " // "
            + activityLine(eventValue);
    }

    function isProblemActivity(eventValue) {
        const event = eventValue || {};
        const source =
            String(event.source || "").toLowerCase();
        const context = event.context || {};
        const room = context.room || {};
        const title =
            String(event.title || "").toUpperCase();
        const state =
            String(context.state || "").toUpperCase();

        if (source === "rounds")
            return Number(room.attentionRank || 0) > 0
                || title.indexOf("CLEAR //") !== 0;

        if (source === "staff")
            return title.indexOf("OFFLINE //") === 0;

        if (source === "reports")
            return state === "BLOCKED"
                || state === "REOPENED";

        return false;
    }

    function clearActivityContext() {
        contextEventKey = "";
        contextSource = "";
        contextTarget = "";
        contextUnreadOnly = false;
        contextFavoritesOnly = false;
        contextProblemsOnly = false;
        contextStartEpoch = 0;
        contextEndEpoch = 0;
        contextTimeLabel = "";
        contextAttentionMode = "";
    }

    function rememberActivityContext(
            eventValue,
            sourceValue,
            targetValue,
            unreadOnlyValue,
            favoritesOnlyValue,
            problemsOnlyValue,
            startEpochValue,
            endEpochValue,
            timeLabelValue,
            attentionModeValue) {
        const event = eventValue || {};
        const key = eventKey(event);

        if (!key) {
            clearActivityContext();
            return false;
        }

        contextEventKey = key;
        contextSource = String(sourceValue || "").toLowerCase();
        contextTarget = String(targetValue || "").toUpperCase();
        contextUnreadOnly = Boolean(unreadOnlyValue);
        contextFavoritesOnly = Boolean(favoritesOnlyValue);
        contextProblemsOnly = Boolean(problemsOnlyValue);
        contextStartEpoch = Number(startEpochValue || 0);
        contextEndEpoch = Number(endEpochValue || 0);
        contextTimeLabel = String(timeLabelValue || "");
        contextAttentionMode =
            String(attentionModeValue || "").toLowerCase();
        return true;
    }

    function contextEvent() {
        const key = String(contextEventKey || "");

        if (!key)
            return null;

        for (let i = 0; i < activityEvents.length; ++i) {
            const event = activityEvents[i] || {};

            if (eventKey(event) === key)
                return event;
        }

        return null;
    }

    function contextMatches() {
        let matches =
            matchingActivity(
                contextSource,
                contextUnreadOnly,
                contextFavoritesOnly,
                contextTarget,
                contextStartEpoch,
                contextEndEpoch
            );

        if (contextProblemsOnly) {
            matches = matches.filter(function(event) {
                return root.isProblemActivity(event || {});
            });
        }

        matches =
            filterActivityByAttention(
                matches,
                contextAttentionMode
            );

        return matches;
    }

    function contextIndex(matchesValue) {
        const matches =
            Array.isArray(matchesValue)
            ? matchesValue
            : [];
        const key = String(contextEventKey || "");

        for (let i = 0; i < matches.length; ++i) {
            if (eventKey(matches[i] || {}) === key)
                return i;
        }

        return -1;
    }

    function contextNeighbor(directionValue) {
        const current = contextEvent();

        if (!current)
            return null;

        const matches = contextMatches();
        const index = contextIndex(matches);

        if (index < 0)
            return null;

        const direction = Number(directionValue || 0);
        const nextIndex =
            direction < 0
            ? index + 1
            : direction > 0
            ? index - 1
            : index;

        if (nextIndex < 0 || nextIndex >= matches.length)
            return null;

        return matches[nextIndex] || null;
    }

    function openCurrentContext() {
        const current = contextEvent();

        if (current) {
            activityActionRequested(current);
            return true;
        }

        if (contextTarget) {
            teamNavigationRequested(contextTarget);
            return true;
        }

        return false;
    }

    function openContextPlace() {
        if (contextTarget) {
            teamNavigationRequested(contextTarget);
            return true;
        }

        const current = contextEvent();

        if (!current)
            return false;

        activityActionRequested(current);
        return true;
    }

    function setCurrentContextFavorite(pinnedValue) {
        const current = contextEvent();

        if (!current)
            return false;

        return setPinned(current, Boolean(pinnedValue));
    }

    function moveContextBefore() {
        const older = contextNeighbor(-1);

        if (!older)
            return false;

        rememberActivityContext(
            older,
            contextSource,
            contextTarget,
            contextUnreadOnly,
            contextFavoritesOnly,
            contextProblemsOnly,
            contextStartEpoch,
            contextEndEpoch,
            contextTimeLabel,
            contextAttentionMode
        );
        return true;
    }

    function moveContextNewer() {
        const newer = contextNeighbor(1);

        if (!newer)
            return false;

        rememberActivityContext(
            newer,
            contextSource,
            contextTarget,
            contextUnreadOnly,
            contextFavoritesOnly,
            contextProblemsOnly,
            contextStartEpoch,
            contextEndEpoch,
            contextTimeLabel,
            contextAttentionMode
        );
        return true;
    }

    function contextAction(actionValue) {
        const action =
            String(actionValue || "").trim().toLowerCase();

        if (action === "open") {
            const current = contextEvent();

            if (!openCurrentContext())
                return false;

            append(
                "RECEPTION",
                current
                ? "OPENING // " + activityLine(current)
                : contextTarget
                ? "OPENING ROOM // " + contextTarget
                : "OPENING CONTEXT"
            );
            return true;
        }

        if (action === "there") {
            if (!openContextPlace())
                return false;

            append(
                "RECEPTION",
                contextTarget
                ? "OPENING ROOM // " + contextTarget
                : "OPENING CONTEXT"
            );
            return true;
        }

        if (action === "favorite") {
            const current = contextEvent();

            if (!current)
                return false;

            const desired = !isPinned(current);

            setCurrentContextFavorite(desired);
            append(
                "RECEPTION",
                (
                    desired
                    ? "FAVORITED // "
                    : "UNFAVORITED // "
                )
                + activityLine(current)
            );
            return true;
        }

        if (action === "before") {
            if (!moveContextBefore()) {
                append(
                    "RECEPTION",
                    "NOTHING OLDER IN THIS CONTEXT"
                );
                return false;
            }

            append(
                "RECEPTION",
                activityListResponse(
                    "BEFORE",
                    [contextEvent()]
                )
            );
            return true;
        }

        if (action === "newer") {
            if (!moveContextNewer()) {
                append(
                    "RECEPTION",
                    "NOTHING NEWER IN THIS CONTEXT"
                );
                return false;
            }

            append(
                "RECEPTION",
                activityListResponse(
                    "NEWER",
                    [contextEvent()]
                )
            );
            return true;
        }

        return false;
    }

    function answerContextFollowUp(textValue) {
        const raw = String(textValue || "").trim();

        if (!raw)
            return false;

        const query = looseQuery(raw);
        const explicitContextTime = activityTimeWindow(query);
        const asksContextStatus =
            query === "what's going on"
            || query === "whats going on"
            || query === "what is going on"
            || query === "what's happening"
            || query === "whats happening"
            || query === "what is happening"
            || query === "what's happening here"
            || query === "whats happening here"
            || query === "what is happening here"
            || query.indexOf("tell me what's happening") >= 0
            || query.indexOf("tell me what is happening") >= 0
            || query.indexOf("can you tell me what's happening") >= 0
            || query.indexOf("can you tell me what is happening") >= 0;
        const asksContextProblem =
            query.indexOf("what's the holdup") >= 0
            || query.indexOf("whats the holdup") >= 0
            || query.indexOf("what is the holdup") >= 0
            || query.indexOf("what's holding us up") >= 0
            || query.indexOf("whats holding us up") >= 0
            || query.indexOf("what is holding us up") >= 0
            || query.indexOf("what's holding things up") >= 0
            || query.indexOf("what is holding things up") >= 0
            || query.indexOf("what's the problem here") >= 0
            || query.indexOf("whats the problem here") >= 0
            || query.indexOf("what is the problem here") >= 0
            || query === "what's the problem"
            || query === "whats the problem"
            || query === "what is the problem"
            || query.indexOf("what's blocking us") >= 0
            || query.indexOf("what is blocking us") >= 0;
        const asksContextDoing =
            query === "what are they doing"
            || query === "what're they doing"
            || query === "whatre they doing"
            || query === "what are they up to"
            || query === "what're they up to"
            || query === "whatre they up to";
        const goThere =
            query.indexOf("take me there") >= 0
            || query.indexOf("go there") >= 0
            || query.indexOf("show me there") >= 0
            || query.indexOf("take me to there") >= 0
            || query.indexOf("bring me there") >= 0
            || query.indexOf("send me there") >= 0
            || query.indexOf("head there") >= 0;
        const openThat =
            (
                query.indexOf("open that") >= 0
                || query.indexOf("open it") >= 0
                || query.indexOf("show me that") >= 0
                || query.indexOf("show me it") >= 0
                || query.indexOf("take me to that") >= 0
                || query.indexOf("take me to it") >= 0
                || query.indexOf("go to that") >= 0
                || query.indexOf("go to it") >= 0
                || query.indexOf("open this") >= 0
                || query.indexOf("show me this") >= 0
                || query.indexOf("take me to this") >= 0
                || query.indexOf("go to this") >= 0
            );
        const favoriteThat =
            query.indexOf("favorite that") >= 0
            || query.indexOf("favorite it") >= 0
            || query.indexOf("favourite that") >= 0
            || query.indexOf("favourite it") >= 0
            || query.indexOf("pin that") >= 0
            || query.indexOf("pin it") >= 0
            || query.indexOf("favorite this") >= 0
            || query.indexOf("favourite this") >= 0
            || query.indexOf("pin this") >= 0;
        const unfavoriteThat =
            query.indexOf("unfavorite that") >= 0
            || query.indexOf("unfavorite it") >= 0
            || query.indexOf("unfavourite that") >= 0
            || query.indexOf("unfavourite it") >= 0
            || query.indexOf("unpin that") >= 0
            || query.indexOf("unpin it") >= 0
            || query.indexOf("unfavorite this") >= 0
            || query.indexOf("unfavourite this") >= 0
            || query.indexOf("unpin this") >= 0;
        const beforeThat =
            query.indexOf("before that") >= 0
            || query.indexOf("before it") >= 0
            || query.indexOf("previous one") >= 0
            || query.indexOf("previous event") >= 0
            || query === "take me back"
            || query === "go back"
            || query === "back"
            || query.indexOf("back one") >= 0
            || query.indexOf("older one") >= 0
            || query.indexOf("older event") >= 0;
        const newerThanThat =
            query.indexOf("anything newer") >= 0
            || query.indexOf("anything after that") >= 0
            || query.indexOf("anything after it") >= 0
            || query.indexOf("what happened after that") >= 0
            || query.indexOf("what happened after it") >= 0
            || query.indexOf("next one") >= 0
            || query.indexOf("next event") >= 0
            || query.indexOf("newer one") >= 0;

        if (!asksContextStatus
                && !asksContextProblem
                && !asksContextDoing
                && !goThere
                && !openThat
                && !favoriteThat
                && !unfavoriteThat
                && !beforeThat
                && !newerThanThat)
            return false;

        if ((asksContextStatus || asksContextProblem)
                && !contextTarget)
            return false;

        append("OPERATOR", raw);

        if (asksContextStatus || asksContextProblem) {
            const startEpoch =
                explicitContextTime.active
                ? explicitContextTime.startEpoch
                : contextStartEpoch;
            const endEpoch =
                explicitContextTime.active
                ? explicitContextTime.endEpoch
                : contextEndEpoch;
            const timeLabel =
                explicitContextTime.active
                ? explicitContextTime.label
                : contextTimeLabel;
            let matches =
                matchingActivity(
                    "",
                    false,
                    false,
                    contextTarget,
                    startEpoch,
                    endEpoch
                );

            if (asksContextProblem) {
                matches = matches.filter(function(event) {
                    return root.isProblemActivity(event || {});
                });
            }

            if (matches.length > 0) {
                rememberActivityContext(
                    matches[0],
                    "",
                    contextTarget,
                    false,
                    false,
                    asksContextProblem,
                    startEpoch,
                    endEpoch,
                    timeLabel
                );
            }

            append(
                "RECEPTION",
                activityListResponse(
                    (
                        asksContextProblem
                        ? "IMPORTANT // "
                        : "RECENT // "
                    )
                    + contextTarget
                    + (
                        timeLabel
                        ? " // " + timeLabel
                        : ""
                      ),
                    matches
                )
            );
            return true;
        }

        if (asksContextDoing) {
            if (!contextTarget) {
                append(
                    "RECEPTION",
                    "NO ACTIVE TEAM CONTEXT // ASK ME ABOUT A ROOM OR TEAM FIRST"
                );
                return true;
            }

            const matches =
                matchingActivity(
                    "",
                    false,
                    false,
                    contextTarget,
                    contextStartEpoch,
                    contextEndEpoch
                );

            if (matches.length > 0) {
                rememberActivityContext(
                    matches[0],
                    "",
                    contextTarget,
                    false,
                    false,
                    false,
                    contextStartEpoch,
                    contextEndEpoch,
                    contextTimeLabel
                );
            }

            append(
                "RECEPTION",
                activityListResponse(
                    "RECENT // "
                    + contextTarget
                    + (
                        contextTimeLabel
                        ? " // " + contextTimeLabel
                        : ""
                      ),
                    matches
                )
            );
            return true;
        }

        if (goThere && contextTarget)
            return contextAction("there");

        const current = contextEvent();

        if (!current) {
            append(
                "RECEPTION",
                "NO ACTIVE CONTEXT // ASK ME ABOUT AN EVENT, ROOM, OR TEAM FIRST"
            );
            clearActivityContext();
            return true;
        }

        if (goThere)
            return contextAction("there");

        if (openThat)
            return contextAction("open");

        if (favoriteThat || unfavoriteThat) {
            const desired = favoriteThat && !unfavoriteThat;

            setCurrentContextFavorite(desired);
            append(
                "RECEPTION",
                (
                    desired
                    ? "FAVORITED // "
                    : "UNFAVORITED // "
                )
                + activityLine(current)
            );
            return true;
        }

        const matches = contextMatches();
        const index = contextIndex(matches);

        if (index < 0) {
            append(
                "RECEPTION",
                "CONTEXT EXPIRED // THAT EVENT IS NO LONGER IN RETAINED HISTORY"
            );
            clearActivityContext();
            return true;
        }

        if (beforeThat) {
            contextAction("before");
            return true;
        }

        if (newerThanThat) {
            contextAction("newer");
            return true;
        }

        return false;
    }

    function actionableMatches(
            sourceValue,
            favoritesOnly,
            targetValue,
            problemsOnly,
            startEpochValue,
            endEpochValue,
            attentionModeValue) {
        let matches =
            matchingActivity(
                sourceValue,
                false,
                favoritesOnly,
                targetValue,
                startEpochValue,
                endEpochValue
            );

        if (problemsOnly) {
            matches = matches.filter(function(event) {
                return root.isProblemActivity(event || {});
            });
        }

        matches =
            filterActivityByAttention(
                matches,
                attentionModeValue
            );

        return matches;
    }

    function answerActivityAction(textValue) {
        const raw = String(textValue || "").trim();

        if (!raw)
            return false;

        const query = looseQuery(raw);
        const asksLocation =
            query.indexOf("where is") >= 0
            || query.indexOf("where's") >= 0
            || query.indexOf("wheres") >= 0
            || query.indexOf("find ") >= 0
            || query.indexOf("locate ") >= 0;
        const asksAction =
            query.indexOf("show me") >= 0
            || query.indexOf("take me to") >= 0
            || query.indexOf("go to") >= 0
            || query.indexOf("jump to") >= 0
            || query.indexOf("bring me to") >= 0
            || query.indexOf("send me to") >= 0
            || query.indexOf("head to") >= 0
            || query.indexOf("open the latest") >= 0
            || query.indexOf("open latest") >= 0
            || query.indexOf("open the newest") >= 0
            || query.indexOf("open newest") >= 0
            || query.indexOf("open the recent") >= 0
            || query.indexOf("open recent") >= 0
            || asksLocation;

        if (!asksAction)
            return false;

        const target = activityTargetFromQuery(raw);
        const timeWindow = activityTimeWindow(query);
        const attention = activityAttentionQuery(query);
        let source = activityQuerySource(query);
        const favoritesOnly =
            query.indexOf("favorite") >= 0
            || query.indexOf("favourite") >= 0
            || query.indexOf("pinned") >= 0;
        const problemsOnly =
            query.indexOf("problem") >= 0
            || query.indexOf("issue") >= 0
            || query.indexOf("attention") >= 0
            || query.indexOf("wrong") >= 0
            || query.indexOf("broke") >= 0
            || query.indexOf("broken") >= 0
            || query.indexOf("failed") >= 0
            || query.indexOf("failure") >= 0
            || query.indexOf("trouble") >= 0;
        const asksSpecificHistoricalEvent =
            query.indexOf("latest") >= 0
            || query.indexOf("newest") >= 0
            || query.indexOf("recent") >= 0
            || favoritesOnly
            || problemsOnly
            || attention.active
            || timeWindow.active;

        if (target
                && !source
                && !asksSpecificHistoricalEvent) {
            append("OPERATOR", raw);
            contextEventKey = "";
            contextSource = "";
            contextTarget = target;
            contextUnreadOnly = false;
            contextFavoritesOnly = false;
            contextProblemsOnly = false;
            contextStartEpoch = 0;
            contextEndEpoch = 0;
            contextTimeLabel = "";
            contextAttentionMode = "";
            append(
                "RECEPTION",
                "OPENING ROOM // " + target
            );
            teamNavigationRequested(target);
            return true;
        }

        // Historical event actions can still prefer a retained Rounds event.
        if (target && !source && !favoritesOnly)
            source = "rounds";

        let matches =
            actionableMatches(
                source,
                favoritesOnly,
                target,
                problemsOnly,
                timeWindow.startEpoch,
                timeWindow.endEpoch,
                attention.mode
            );

        // A team may not have a retained Rounds event. Fall back to any
        // retained event for that team rather than pretending it does.
        if (matches.length === 0
                && target
                && source === "rounds"
                && !problemsOnly) {
            matches =
                actionableMatches(
                    "",
                    favoritesOnly,
                    target,
                    false,
                    timeWindow.startEpoch,
                    timeWindow.endEpoch,
                    attention.mode
                );
        }

        append("OPERATOR", raw);

        if (matches.length === 0) {
            const label = [
                target,
                source ? source.toUpperCase() : "",
                favoritesOnly ? "FAVORITE" : "",
                problemsOnly ? "PROBLEM" : "",
                attention.active ? attention.label : "",
                timeWindow.active ? timeWindow.label : ""
            ].filter(function(value) {
                return String(value || "").length > 0;
            }).join(" // ");

            append(
                "RECEPTION",
                (label || "ACTIVITY")
                + " // NOTHING RECORDED TO OPEN"
            );
            return true;
        }

        const selected = matches[0] || {};

        rememberActivityContext(
            selected,
            source,
            target,
            false,
            favoritesOnly,
            problemsOnly,
            timeWindow.startEpoch,
            timeWindow.endEpoch,
            timeWindow.label,
            attention.mode
        );
        append(
            "RECEPTION",
            "OPENING // "
            + (
                attention.active
                ? activityAttentionLabel(selected) + " // "
                : ""
              )
            + activityLine(selected)
        );
        activityActionRequested(selected);
        return true;
    }

    function answerActivityQuestion(textValue) {
        const raw = String(textValue || "").trim();

        if (!raw)
            return false;

        const query = looseQuery(raw);
        const targetHint = activityTargetFromQuery(raw);
        const timeWindow = activityTimeWindow(query);
        const attention = activityAttentionQuery(query);
        const ranking = attentionRankingQuery(query);
        const asksDoing =
            !!targetHint
            && (
                query.indexOf(" doing") >= 0
                || query.indexOf(" up to") >= 0
            );
        const asksNew =
            query.indexOf("what's new") >= 0
            || query.indexOf("whats new") >= 0
            || query.indexOf("what is new") >= 0
            || query.indexOf("anything new") >= 0
            || query.indexOf("what did i miss") >= 0
            || query.indexOf("did i miss") >= 0
            || query.indexOf("since last") >= 0
            || query.indexOf("while i was gone") >= 0;
        const asksFavorites =
            query.indexOf("favorite") >= 0
            || query.indexOf("favourite") >= 0
            || query.indexOf("pinned") >= 0
            || query.indexOf("kept") >= 0
            || query.indexOf("starred") >= 0
            || query.indexOf("saved") >= 0;
        const asksRecent =
            asksDoing
            || query.indexOf("recent") >= 0
            || query.indexOf("latest") >= 0
            || query.indexOf("what happened") >= 0
            || query.indexOf("what's happened") >= 0
            || query.indexOf("whats happened") >= 0
            || query.indexOf("what changed") >= 0
            || query.indexOf("what's changed") >= 0
            || query.indexOf("whats changed") >= 0
            || query.indexOf("what is going on") >= 0
            || query.indexOf("what's going on") >= 0
            || query.indexOf("whats going on") >= 0
            || query.indexOf("what is happening") >= 0
            || query.indexOf("what's happening") >= 0
            || query.indexOf("whats happening") >= 0
            || query.indexOf("tell me what's happening") >= 0
            || query.indexOf("tell me what is happening") >= 0
            || query.indexOf("can you tell me what's happening") >= 0
            || query.indexOf("can you tell me what is happening") >= 0
            || query.indexOf("catch me up") >= 0
            || query.indexOf("update me") >= 0
            || query.indexOf("give me an update") >= 0
            || query.indexOf("anything happen") >= 0
            || query.indexOf("did anything happen") >= 0
            || query.indexOf("activity") >= 0
            || query.indexOf("last call") >= 0
            || query.indexOf("last report") >= 0
            || query.indexOf("last round") >= 0
            || query.indexOf("last intercom") >= 0
            || query.indexOf("last message") >= 0
            || query.indexOf("last staff") >= 0;
        const asksProblems =
            query.indexOf("what went wrong") >= 0
            || query.indexOf("what's wrong") >= 0
            || query.indexOf("whats wrong") >= 0
            || query.indexOf("anything wrong") >= 0
            || query.indexOf("anything important") >= 0
            || query.indexOf("what broke") >= 0
            || query.indexOf("what failed") >= 0
            || query.indexOf("holdup") >= 0
            || query.indexOf("hold up") >= 0
            || query.indexOf("holding us up") >= 0
            || query.indexOf("holding things up") >= 0
            || query.indexOf("what's the problem") >= 0
            || query.indexOf("whats the problem") >= 0
            || query.indexOf("what is the problem") >= 0
            || query.indexOf("blocking us") >= 0
            || query.indexOf("blocking things") >= 0
            || query.indexOf("problem") >= 0
            || query.indexOf("issue") >= 0
            || query.indexOf("trouble") >= 0;
        const asksWhen =
            query.indexOf("when was") >= 0
            || query.indexOf("when did") >= 0
            || query.indexOf("last activity") >= 0
            || query.indexOf("last thing") >= 0;
        const asksCount =
            query.indexOf("how many") >= 0
            || query.indexOf("count ") >= 0
            || query.indexOf("count?") >= 0;
        const asksArchive =
            query.indexOf("archive") >= 0
            || query.indexOf("deep history") >= 0
            || query.indexOf("older history") >= 0;
        const asksOldest =
            query.indexOf("oldest") >= 0
            || query.indexOf("earliest") >= 0
            || query.indexOf("first activity") >= 0
            || query.indexOf("first thing") >= 0;
        const asksHelp =
            query.indexOf("what do you know") >= 0
            || query.indexOf("what can you tell me") >= 0
            || query.indexOf("what can i ask") >= 0;

        if (!asksNew
                && !asksFavorites
                && !asksRecent
                && !asksProblems
                && !asksWhen
                && !asksCount
                && !asksArchive
                && !asksOldest
                && !asksHelp
                && !attention.active
                && !ranking.active
                && !timeWindow.active)
            return false;

        append("OPERATOR", raw);

        if (asksHelp) {
            append(
                "RECEPTION",
                "I understand recent activity, archive history, archive status and cleanup, oldest or earliest activity, critical/action/notice/routine attention levels, ranked priorities like top three or what should I look at first, what changed, what went wrong, what needs attention, favorites, Room or team history, counts, and time windows like today, yesterday, this morning, this week, last week, this month, last month, the last 3 hours, the last 2 weeks, since 2026-10-01, on 2026-10-01, or from 2026-10-01 to 2026-10-05. Selective archive cleanup is previewed first; say confirm archive cleanup to execute it or cancel archive cleanup to abort. I can also find or show a team, then follow up with open this, take me there, favorite this, go back, or next one. When a live context is selected, you can say call Codex about this, message Hermes about this, or name another registered specialist. AI interpretation can be enabled from the front desk; it only suggests a validated route or specialist handoff and requires review before execution."
            );
            return true;
        }

        let source = activityQuerySource(query);

        if (asksArchive
                && source === "reports"
                && query.indexOf("report") < 0
                && query.indexOf("evidence") < 0)
            source = "";

        const target = targetHint;
        let matches =
            matchingActivity(
                source,
                asksNew,
                asksFavorites,
                target,
                timeWindow.startEpoch,
                timeWindow.endEpoch
            );

        if (asksProblems) {
            matches = matches.filter(function(event) {
                return root.isProblemActivity(event || {});
            });
        }

        matches =
            filterActivityByAttention(
                matches,
                attention.mode
            );

        if (ranking.active)
            matches = rankActivityByAttention(matches);

        let label = "";

        if (asksFavorites)
            label = "FAVORITES";
        else if (ranking.active)
            label =
                attention.active
                ? attention.label
                : "PRIORITY";
        else if (attention.active)
            label = attention.label;
        else if (asksProblems)
            label = "IMPORTANT";
        else if (asksNew)
            label = "NEW SINCE LAST VISIT";
        else if (asksArchive || asksOldest)
            label = "ARCHIVE";
        else
            label = "RECENT";

        if (source)
            label += " // " + source.toUpperCase();

        if (target)
            label += " // " + target;

        if (timeWindow.active)
            label += " // " + timeWindow.label;

        if (ranking.active)
            label += " // TOP " + String(ranking.limit);

        if (asksCount) {
            clearActivityContext();
            append(
                "RECEPTION",
                activityCountResponse(label, matches)
            );
            return true;
        }

        if (asksOldest) {
            const oldest =
                matches.length > 0
                ? matches[matches.length - 1]
                : null;

            if (oldest) {
                rememberActivityContext(
                    oldest,
                    source,
                    target,
                    asksNew,
                    asksFavorites,
                    asksProblems,
                    timeWindow.startEpoch,
                    timeWindow.endEpoch,
                    timeWindow.label,
                    attention.mode
                );
            } else {
                clearActivityContext();
            }

            append(
                "RECEPTION",
                oldest
                ? activityListResponse(
                    label + " // OLDEST",
                    [oldest]
                  )
                : label + " // NONE RECORDED"
            );
            return true;
        }

        if (asksWhen) {
            if (matches.length > 0) {
                rememberActivityContext(
                    matches[0],
                    source,
                    target,
                    asksNew,
                    asksFavorites,
                    asksProblems,
                    timeWindow.startEpoch,
                    timeWindow.endEpoch,
                    timeWindow.label,
                    attention.mode
                );
            } else {
                clearActivityContext();
            }

            append(
                "RECEPTION",
                matches.length > 0
                ? activityListResponse(
                    "LAST // "
                    + (
                        target
                        ? target
                        : source
                        ? source.toUpperCase()
                        : "ACTIVITY"
                      )
                    + (
                        timeWindow.active
                        ? " // " + timeWindow.label
                        : ""
                      ),
                    [matches[0]]
                  )
                : label + " // NONE RECORDED"
            );
            return true;
        }

        if (matches.length > 0) {
            rememberActivityContext(
                matches[0],
                source,
                target,
                asksNew,
                asksFavorites,
                asksProblems,
                timeWindow.startEpoch,
                timeWindow.endEpoch,
                timeWindow.label,
                attention.mode
            );
        } else {
            clearActivityContext();
        }

        append(
            "RECEPTION",
            activityListResponse(
                label,
                matches,
                attention.active || ranking.active,
                ranking.active ? ranking.limit : 0
            )
        );
        return true;
    }

    function specialistHandoffIntent(textValue) {
        const query = looseQuery(textValue);
        const refersToContext =
            query.indexOf("about this") >= 0
            || query.indexOf("about that") >= 0
            || query.indexOf("about it") >= 0
            || query.indexOf("regarding this") >= 0
            || query.indexOf("regarding that") >= 0
            || query.indexOf("with this context") >= 0
            || query.indexOf("send this to") >= 0
            || query.indexOf("send that to") >= 0;

        if (!refersToContext)
            return "";

        if (query.indexOf("call") >= 0
                || query.indexOf("dial") >= 0
                || query.indexOf("phone") >= 0)
            return "phone";

        if (query.indexOf("intercom") >= 0
                || query.indexOf("message") >= 0
                || query.indexOf("send this to") >= 0
                || query.indexOf("send that to") >= 0
                || query.indexOf("talk to") >= 0
                || query.indexOf("tell ") >= 0
                || query.indexOf("ask ") >= 0)
            return "intercom";

        return "";
    }

    function request(route, operatorText) {
        const target = String(route || "").toLowerCase();

        if (operatorText)
            append("OPERATOR", operatorText);

        let response = "";

        if (target === "surgery")
            response = "Routing to Surgery.";
        else if (target === "archive")
            response = "Opening Reception archive.";
        else if (target === "reports")
            response = "Opening surgical history and evidence.";
        else if (target === "attention")
            response = "Opening GitHub Attention triage.";
        else if (target === "merge_queue")
            response = "Opening the current repository merge queue.";
        else if (target === "rounds")
            response = "Opening Hospital-wide rounds.";
        else if (target === "staff")
            response = "Opening the specialist registry.";
        else if (target === "phone")
            response = "Opening Phone.";
        else if (target === "intercom")
            response = "Opening Intercom.";
        else {
            append(
                "RECEPTION",
                "I can route Surgery, Attention, Merge Queue, Archive, Reports, Rounds, Staff, Phone, or Intercom."
            );
            return false;
        }

        append("RECEPTION", response);
        routeRequested(target);
        return true;
    }

    function submit(text) {
        const raw = String(text || "").trim();

        if (!raw)
            return false;

        const query = looseQuery(raw);

        if (pendingArchiveCleanupSpec) {
            const maintenanceQuery = socialQuery(raw);
            const keepsCleanupArm =
                maintenanceQuery.indexOf("archive") >= 0
                && maintenanceQuery.indexOf("cleanup") >= 0
                && (
                    maintenanceQuery.indexOf("confirm") >= 0
                    || maintenanceQuery.indexOf("cancel") >= 0
                   );

            if (!keepsCleanupArm)
                pendingArchiveCleanupSpec = null;
        }

        if (answerSocial(raw))
            return true;

        if (answerContextFollowUp(raw))
            return true;

        if (answerActivityAction(raw))
            return true;

        if (query.indexOf("open archive") >= 0
                || query.indexOf("show archive browser") >= 0
                || query.indexOf("browse archive") >= 0
                || query.indexOf("go to archive") >= 0)
            return request("archive", raw);

        if (answerArchiveMaintenance(raw))
            return true;

        if (answerActivityQuestion(raw))
            return true;

        const handoffMode =
            specialistHandoffIntent(raw);

        if (handoffMode) {
            append("OPERATOR", raw);
            specialistHandoffRequested(
                handoffMode,
                raw
            );
            return true;
        }

        if (query.indexOf("intercom") >= 0
                || query.indexOf("message") >= 0
                || query.indexOf("talk to") >= 0)
            return request("intercom", raw);

        if (query.indexOf("phone") >= 0
                || query.indexOf("call") >= 0
                || query.indexOf("dial") >= 0)
            return request("phone", raw);

        if (query.indexOf("report") >= 0
                || query.indexOf("history") >= 0
                || query.indexOf("evidence") >= 0
                || query.indexOf("clipboard") >= 0)
            return request("reports", raw);

        if (query.indexOf("merge queue") >= 0
                || query.indexOf("mergequeue") >= 0)
            return request("merge_queue", raw);

        if (query.indexOf("attention") >= 0
                || query.indexOf("triage") >= 0
                || query.indexOf("pull request") >= 0
                || query.indexOf("github") >= 0)
            return request("attention", raw);

        if (query.indexOf("round") >= 0
                || query.indexOf("bell") >= 0
                || query.indexOf("hospital wide") >= 0)
            return request("rounds", raw);

        if (query.indexOf("staff") >= 0
                || query.indexOf("specialist") >= 0
                || query.indexOf("codex") >= 0
                || query.indexOf("hermes") >= 0)
            return request("staff", raw);

        if (query.indexOf("surgery") >= 0
                || query.indexOf("room") >= 0
                || query.indexOf("patient") >= 0)
            return request("surgery", raw);

        if (aiInterpretationEnabled) {
            append("OPERATOR", raw);
            append(
                "RECEPTION",
                "AI INTERPRETATION // REQUESTED // REVIEW REQUIRED"
            );
            interpretationRequested(raw);
            return true;
        }

        append("OPERATOR", raw);
        append(
            "RECEPTION",
            "I don't have authority to improvise that action. Ask for Surgery, Attention, Merge Queue, Archive, Reports, Rounds, Staff, Phone, or Intercom."
        );
        return false;
    }
}
