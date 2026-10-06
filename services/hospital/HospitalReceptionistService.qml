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

    property var inbox: []
    property var activityEvents: []
    property var subjectStates: ({})
    property bool activityHydrated: false
    property var pendingActivities: []
    property int maxActivityEvents: 100

    FileView {
        id: activityFile

        path: Quickshell.dataPath("hospital-reception.json")
        atomicWrites: true

        adapter: JsonAdapter {
            id: activityAdapter

            property int schemaVersion: 1
            property var events: []
            property var subjects: ({})
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

    function refreshVisibleInbox() {
        const ordered = activityEvents.slice().sort(function(a, b) {
            return root.eventEpoch(b) - root.eventEpoch(a);
        });

        inbox = ordered.slice(0, 5);
    }

    function hydrateActivity() {
        activityEvents =
            Array.isArray(activityAdapter.events)
            ? activityAdapter.events.slice(-maxActivityEvents)
            : [];
        subjectStates =
            activityAdapter.subjects
            && typeof activityAdapter.subjects === "object"
            ? Object.assign({}, activityAdapter.subjects)
            : ({});
        activityHydrated = true;
        refreshVisibleInbox();

        if (pendingActivities.length > 0) {
            const pending = pendingActivities.slice();
            pendingActivities = [];

            for (let i = 0; i < pending.length; ++i)
                recordActivity(pending[i] || {});
        }
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

        next = next.slice(-maxActivityEvents);
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
