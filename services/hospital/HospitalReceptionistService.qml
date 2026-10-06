import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property var transcript: [
        {
            sender: "RECEPTION",
            body: "Front desk online. I can route you to Surgery, Reports, Rounds, Staff, Phone, or Intercom."
        }
    ]

    signal routeRequested(string route)
    signal activityActionRequested(var item)
    signal teamNavigationRequested(string team)

    property var inbox: []
    property var activityEvents: []
    property var subjectStates: ({})
    property bool activityHydrated: false
    property var pendingActivities: []
    property int maxActivityEvents: 100

    property string lastReadAt: ""
    property bool visitActive: false
    property string visitStartedAt: ""
    property bool pendingVisitStart: false
    property int unreadCount: 0
    property int recentCount: 0
    property var pinnedKeys: []
    property int pinnedCount: 0
    property int maxPinnedEvents: 5

    // Session-local conversational reference. This is intentionally not
    // persisted: Reception remembers "that" only inside the live session.
    property string contextEventKey: ""
    property string contextSource: ""
    property string contextTarget: ""
    property bool contextUnreadOnly: false
    property bool contextFavoritesOnly: false
    property bool contextProblemsOnly: false

    FileView {
        id: activityFile

        path: Quickshell.dataPath("hospital-reception.json")
        atomicWrites: true

        adapter: JsonAdapter {
            id: activityAdapter

            property int schemaVersion: 1
            property var events: []
            property var subjects: ({})
            property string lastReadAt: ""
            property var pinnedKeys: []
        }

        onAdapterUpdated: writeAdapter()
        onLoaded: root.hydrateActivity()
        onLoadFailed: root.hydrateActivity()
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
            return "NO NEW ACTIVITY SINCE LAST VISIT.";

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
        append("RECEPTION", briefingBody());
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

    function trimActivityEvents(eventsValue) {
        const source =
            Array.isArray(eventsValue)
            ? eventsValue.slice()
            : [];

        source.sort(function(a, b) {
            return root.eventEpoch(a) - root.eventEpoch(b);
        });

        const pinned = [];
        const unpinned = [];

        for (let i = 0; i < source.length; ++i) {
            if (isPinned(source[i] || {}))
                pinned.push(source[i]);
            else
                unpinned.push(source[i]);
        }

        const unpinnedBudget =
            Math.max(0, maxActivityEvents - pinned.length);
        const kept =
            pinned.concat(
                unpinned.slice(
                    Math.max(0, unpinned.length - unpinnedBudget)
                )
            );

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

        for (let i = 0;
                i < pinnedKeys.length && visible.length < 5;
                ++i) {
            const pinned = byKey[String(pinnedKeys[i] || "")];

            if (pinned)
                visible.push(pinned);
        }

        for (let i = 0;
                i < ordered.length && visible.length < 5;
                ++i) {
            const event = ordered[i] || {};

            if (!isPinned(event))
                visible.push(event);
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
            schemaVersion: 1,
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
            ? reportEvents.slice(-5)
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

    function activityQuerySource(queryValue) {
        const query = String(queryValue || "").toLowerCase();

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
            targetValue) {
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

    function activityListResponse(labelValue, eventsValue) {
        const label = String(labelValue || "RECENT");
        const events =
            Array.isArray(eventsValue)
            ? eventsValue.slice(0, 5)
            : [];

        if (events.length === 0)
            return label + " // NONE RECORDED";

        const lines = [label + " // " + String(events.length)];

        for (let i = 0; i < events.length; ++i)
            lines.push("- " + activityLine(events[i] || {}));

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
    }

    function rememberActivityContext(
            eventValue,
            sourceValue,
            targetValue,
            unreadOnlyValue,
            favoritesOnlyValue,
            problemsOnlyValue) {
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
                contextTarget
            );

        if (contextProblemsOnly) {
            matches = matches.filter(function(event) {
                return root.isProblemActivity(event || {});
            });
        }

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

    function answerContextFollowUp(textValue) {
        const raw = String(textValue || "").trim();

        if (!raw)
            return false;

        const query = raw.toLowerCase();
        const goThere =
            query.indexOf("take me there") >= 0
            || query.indexOf("go there") >= 0
            || query.indexOf("show me there") >= 0
            || query.indexOf("take me to there") >= 0;
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
            );
        const favoriteThat =
            query.indexOf("favorite that") >= 0
            || query.indexOf("favorite it") >= 0
            || query.indexOf("favourite that") >= 0
            || query.indexOf("favourite it") >= 0
            || query.indexOf("pin that") >= 0
            || query.indexOf("pin it") >= 0;
        const unfavoriteThat =
            query.indexOf("unfavorite that") >= 0
            || query.indexOf("unfavorite it") >= 0
            || query.indexOf("unfavourite that") >= 0
            || query.indexOf("unfavourite it") >= 0
            || query.indexOf("unpin that") >= 0
            || query.indexOf("unpin it") >= 0;
        const beforeThat =
            query.indexOf("before that") >= 0
            || query.indexOf("before it") >= 0
            || query.indexOf("previous one") >= 0
            || query.indexOf("previous event") >= 0;
        const newerThanThat =
            query.indexOf("anything newer") >= 0
            || query.indexOf("anything after that") >= 0
            || query.indexOf("anything after it") >= 0
            || query.indexOf("what happened after that") >= 0
            || query.indexOf("what happened after it") >= 0;

        if (!goThere
                && !openThat
                && !favoriteThat
                && !unfavoriteThat
                && !beforeThat
                && !newerThanThat)
            return false;

        append("OPERATOR", raw);

        if (goThere && contextTarget) {
            append(
                "RECEPTION",
                "OPENING ROOM // " + contextTarget
            );
            teamNavigationRequested(contextTarget);
            return true;
        }

        const current = contextEvent();

        if (!current) {
            append(
                "RECEPTION",
                "NO ACTIVE CONTEXT // ASK ME ABOUT AN EVENT, ROOM, OR TEAM FIRST"
            );
            clearActivityContext();
            return true;
        }

        if (goThere) {
            append(
                "RECEPTION",
                "OPENING // " + activityLine(current)
            );
            activityActionRequested(current);
            return true;
        }

        if (openThat) {
            append(
                "RECEPTION",
                "OPENING // " + activityLine(current)
            );
            activityActionRequested(current);
            return true;
        }

        if (favoriteThat || unfavoriteThat) {
            const desired = favoriteThat && !unfavoriteThat;

            setPinned(current, desired);
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
            const olderIndex = index + 1;

            if (olderIndex >= matches.length) {
                append(
                    "RECEPTION",
                    "NOTHING OLDER IN THIS CONTEXT"
                );
                return true;
            }

            const older = matches[olderIndex] || {};

            rememberActivityContext(
                older,
                contextSource,
                contextTarget,
                contextUnreadOnly,
                contextFavoritesOnly,
                contextProblemsOnly
            );
            append(
                "RECEPTION",
                activityListResponse("BEFORE", [older])
            );
            return true;
        }

        if (newerThanThat) {
            if (index <= 0) {
                append(
                    "RECEPTION",
                    "NOTHING NEWER IN THIS CONTEXT"
                );
                return true;
            }

            const newer = matches.slice(0, index);
            const newest = newer[0] || {};

            rememberActivityContext(
                newest,
                contextSource,
                contextTarget,
                contextUnreadOnly,
                contextFavoritesOnly,
                contextProblemsOnly
            );
            append(
                "RECEPTION",
                activityListResponse("NEWER", newer)
            );
            return true;
        }

        return false;
    }

    function actionableMatches(
            sourceValue,
            favoritesOnly,
            targetValue,
            problemsOnly) {
        let matches =
            matchingActivity(
                sourceValue,
                false,
                favoritesOnly,
                targetValue
            );

        if (problemsOnly) {
            matches = matches.filter(function(event) {
                return root.isProblemActivity(event || {});
            });
        }

        return matches;
    }

    function answerActivityAction(textValue) {
        const raw = String(textValue || "").trim();

        if (!raw)
            return false;

        const query = raw.toLowerCase();
        const asksAction =
            query.indexOf("show me") >= 0
            || query.indexOf("take me to") >= 0
            || query.indexOf("go to") >= 0
            || query.indexOf("jump to") >= 0
            || query.indexOf("open the latest") >= 0
            || query.indexOf("open latest") >= 0
            || query.indexOf("open the newest") >= 0
            || query.indexOf("open newest") >= 0
            || query.indexOf("open the recent") >= 0
            || query.indexOf("open recent") >= 0;

        if (!asksAction)
            return false;

        const target = activityTargetFromQuery(raw);
        let source = activityQuerySource(query);
        const favoritesOnly =
            query.indexOf("favorite") >= 0
            || query.indexOf("favourite") >= 0
            || query.indexOf("pinned") >= 0;
        const problemsOnly =
            query.indexOf("problem") >= 0
            || query.indexOf("issue") >= 0
            || query.indexOf("attention") >= 0;
        const asksSpecificHistoricalEvent =
            query.indexOf("latest") >= 0
            || query.indexOf("newest") >= 0
            || query.indexOf("recent") >= 0
            || favoritesOnly
            || problemsOnly;

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
                problemsOnly
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
                    false
                );
        }

        append("OPERATOR", raw);

        if (matches.length === 0) {
            const label = [
                target,
                source ? source.toUpperCase() : "",
                favoritesOnly ? "FAVORITE" : "",
                problemsOnly ? "PROBLEM" : ""
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
            problemsOnly
        );
        append(
            "RECEPTION",
            "OPENING // " + activityLine(selected)
        );
        activityActionRequested(selected);
        return true;
    }

    function answerActivityQuestion(textValue) {
        const raw = String(textValue || "").trim();

        if (!raw)
            return false;

        const query = raw.toLowerCase();
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
            || query.indexOf("kept") >= 0;
        const asksRecent =
            query.indexOf("recent") >= 0
            || query.indexOf("latest") >= 0
            || query.indexOf("what happened") >= 0
            || query.indexOf("what's happened") >= 0
            || query.indexOf("whats happened") >= 0
            || query.indexOf("activity") >= 0
            || query.indexOf("last call") >= 0
            || query.indexOf("last report") >= 0
            || query.indexOf("last round") >= 0
            || query.indexOf("last intercom") >= 0
            || query.indexOf("last message") >= 0
            || query.indexOf("last staff") >= 0;
        const asksWhen =
            query.indexOf("when was") >= 0
            || query.indexOf("when did") >= 0
            || query.indexOf("last activity") >= 0
            || query.indexOf("last thing") >= 0;
        const asksCount =
            query.indexOf("how many") >= 0
            || query.indexOf("count ") >= 0
            || query.indexOf("count?") >= 0;
        const asksHelp =
            query.indexOf("what do you know") >= 0
            || query.indexOf("what can you tell me") >= 0
            || query.indexOf("what can i ask") >= 0;

        if (!asksNew
                && !asksFavorites
                && !asksRecent
                && !asksWhen
                && !asksCount
                && !asksHelp)
            return false;

        append("OPERATOR", raw);

        if (asksHelp) {
            append(
                "RECEPTION",
                "I can report what is new, what you missed, recent activity, favorites, Room or team history, counts, and last activity. I can show a team or open a recorded problem, then follow up with open that, take me there, favorite that, before that, or anything newer."
            );
            return true;
        }

        const source = activityQuerySource(query);
        const target = activityTargetFromQuery(raw);
        const matches =
            matchingActivity(
                source,
                asksNew,
                asksFavorites,
                target
            );
        let label = "";

        if (asksFavorites)
            label = "FAVORITES";
        else if (asksNew)
            label = "NEW SINCE LAST VISIT";
        else
            label = "RECENT";

        if (source)
            label += " // " + source.toUpperCase();

        if (target)
            label += " // " + target;

        if (asksCount) {
            clearActivityContext();
            append(
                "RECEPTION",
                activityCountResponse(label, matches)
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
                    false
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
                false
            );
        } else {
            clearActivityContext();
        }

        append(
            "RECEPTION",
            activityListResponse(label, matches)
        );
        return true;
    }

    function request(route, operatorText) {
        const target = String(route || "").toLowerCase();

        if (operatorText)
            append("OPERATOR", operatorText);

        let response = "";

        if (target === "surgery")
            response = "Routing to Surgery.";
        else if (target === "reports")
            response = "Opening surgical history and evidence.";
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
                "I can route Surgery, Reports, Rounds, Staff, Phone, or Intercom."
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

        const query = raw.toLowerCase();

        if (answerContextFollowUp(raw))
            return true;

        if (answerActivityAction(raw))
            return true;

        if (answerActivityQuestion(raw))
            return true;

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

        if (query.indexOf("round") >= 0
                || query.indexOf("attention") >= 0
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

        append("OPERATOR", raw);
        append(
            "RECEPTION",
            "I don't have authority to improvise that action. Ask for Surgery, Reports, Rounds, Staff, Phone, or Intercom."
        );
        return false;
    }
}
