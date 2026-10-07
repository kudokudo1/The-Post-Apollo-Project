import QtQuick

QtObject {
    id: root

    // Deliberately session-local. This packet is the live referent shared by
    // Hospital surfaces; it is not persisted across Quickshell restarts so
    // stale "this/that" references cannot silently regain authority.
    property string source: ""
    property string kind: ""
    property string title: ""
    property string detail: ""
    property string route: ""
    property string team: ""
    property string specialistId: ""
    property string channelType: ""
    property string channelLabel: ""
    property string recordedAt: ""
    property string operatorQuestion: ""
    property var room: ({})
    property var report: ({})
    property var specialist: ({})
    property string updatedAt: ""

    readonly property bool active:
        source.length > 0
        || team.length > 0
        || specialistId.length > 0
        || title.length > 0

    readonly property string label: {
        const parts = [];

        if (team)
            parts.push(team);
        if (source)
            parts.push(source.toUpperCase());
        if (title)
            parts.push(title);

        return parts.length > 0
            ? parts.join(" // ")
            : "NO LIVE CONTEXT";
    }

    function stamp() {
        updatedAt = new Date().toISOString();
    }

    function clear() {
        source = "";
        kind = "";
        title = "";
        detail = "";
        route = "";
        team = "";
        specialistId = "";
        channelType = "";
        channelLabel = "";
        recordedAt = "";
        operatorQuestion = "";
        room = ({});
        report = ({});
        specialist = ({});
        updatedAt = "";
    }

    function captureActivity(itemValue, questionValue) {
        const item = itemValue || {};
        const context = item.context || {};
        const roomValue = context.room || {};

        source = String(item.source || "reception").toLowerCase();
        kind = String(item.kind || "");
        title = String(item.title || "");
        detail = String(item.detail || "");
        route = String(item.route || "");
        team = String(
            context.team
            || roomValue.team
            || roomValue.branch
            || ""
        ).trim().toUpperCase();
        specialistId = String(context.specialistId || "").trim();
        channelType =
            String(context.channelType || "").trim().toUpperCase();
        channelLabel = String(context.channelLabel || "").trim();
        recordedAt = String(
            context.recordedAt
            || item.recordedAt
            || ""
        );
        operatorQuestion = String(questionValue || "").trim();
        room = Object.assign({}, roomValue);
        report =
            source === "reports"
            ? {
                team: team,
                eventType: String(context.eventType || ""),
                state: String(context.state || ""),
                recordedAt: recordedAt
            }
            : ({});
        specialist = ({});
        stamp();
        return true;
    }

    function captureRoom(roomValue) {
        const row = roomValue || {};

        source = "rounds";
        kind = "room";
        title =
            String(
                row.team
                || row.branch
                || "ROOM"
            ).trim().toUpperCase();
        detail =
            String(
                row.state
                || row.integrationState
                || ""
            ).trim();
        route = "rounds";
        team = String(row.team || row.branch || "").trim().toUpperCase();
        specialistId = "";
        channelType = "";
        channelLabel = "";
        recordedAt = "";
        operatorQuestion = "";
        room = Object.assign({}, row);
        report = ({});
        specialist = ({});
        stamp();
        return true;
    }

    function captureTeam(teamValue) {
        const value =
            String(teamValue || "").trim().toUpperCase();

        if (!value)
            return false;

        source = "room";
        kind = "room";
        title = value;
        detail = "";
        route = "surgery";
        team = value;
        specialistId = "";
        channelType = "";
        channelLabel = "";
        recordedAt = "";
        operatorQuestion = "";
        room = ({ team: value });
        report = ({});
        specialist = ({});
        stamp();
        return true;
    }

    function captureReport(eventValue) {
        const event = eventValue || {};
        const details = event.details || {};

        source = "reports";
        kind = "report";
        team = String(event.team || "").trim().toUpperCase();
        title =
            String(event.eventType || "REPORT")
                .replace(/_/g, " ");
        detail = String(
            event.reason
            || details.reason
            || event.state
            || ""
        );
        route = "reports";
        specialistId = "";
        channelType = "";
        channelLabel = "";
        recordedAt = String(event.recordedAt || "");
        operatorQuestion = "";
        room = ({ team: team });
        report = {
            team: team,
            eventType: String(event.eventType || ""),
            state: String(event.state || ""),
            recordedAt: recordedAt,
            details: Object.assign({}, details)
        };
        specialist = ({});
        stamp();
        return true;
    }

    function captureSpecialist(specialistValue) {
        const row = specialistValue || {};
        const id = String(row.id || "").trim();

        if (!id)
            return false;

        source = "staff";
        kind = "staff";
        title = String(row.name || id);
        detail =
            String(row.role || "SPECIALIST")
            + " // "
            + String(row.presence || "UNKNOWN");
        route = "staff";
        team = "";
        specialistId = id;
        channelType = "";
        channelLabel = "";
        recordedAt = "";
        operatorQuestion = "";
        room = ({});
        report = ({});
        specialist = Object.assign({}, row);
        stamp();
        return true;
    }

    function setOperatorQuestion(value) {
        operatorQuestion = String(value || "").trim();
        stamp();
    }

    function packet() {
        return {
            source: source,
            kind: kind,
            title: title,
            detail: detail,
            route: route,
            team: team,
            specialistId: specialistId,
            channelType: channelType,
            channelLabel: channelLabel,
            recordedAt: recordedAt,
            operatorQuestion: operatorQuestion,
            room: Object.assign({}, room || {}),
            report: Object.assign({}, report || {}),
            specialist: Object.assign({}, specialist || {}),
            updatedAt: updatedAt
        };
    }

    function handoffBody(requestValue) {
        const request =
            String(requestValue || operatorQuestion || "").trim();
        const lines = [
            "POST-APOLLO HOSPITAL CONTEXT",
            "SOURCE: " + (source ? source.toUpperCase() : "HOSPITAL")
        ];

        if (team)
            lines.push("ROOM: " + team);
        if (title)
            lines.push("SUBJECT: " + title);
        if (detail)
            lines.push("DETAIL: " + detail);
        if (recordedAt)
            lines.push("RECORDED: " + recordedAt);
        if (channelType)
            lines.push(
                "CHANNEL: "
                + channelType
                + (
                    channelLabel
                    ? " // " + channelLabel
                    : ""
                  )
            );
        if (request)
            lines.push("OPERATOR REQUEST: " + request);

        return lines.join("\n");
    }
}
