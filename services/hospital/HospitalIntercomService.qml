import QtQuick
import Quickshell

QtObject {
    id: root

    required property var registryService
    property var responsibilityService: null
    property var dispatchService: null

    property var messages: []
    property string lastStatus: ""
    property string lastError: ""
    property int nextMessageId: 1

    signal messageLaunched(var entry)

    function channelKey(channelType, channelLabel, specialistId) {
        return [
            String(channelType || "HOSPITAL").toUpperCase(),
            String(channelLabel || "").trim(),
            String(specialistId || "").trim()
        ].join("::");
    }

    function messagesFor(channelType, channelLabel, specialistId) {
        const key = channelKey(channelType, channelLabel, specialistId);

        return messages.filter(function(entry) {
            return String((entry || {}).channelKey || "") === key;
        });
    }

    function buildPrompt(channelType, channelLabel, body) {
        const type = String(channelType || "HOSPITAL").toUpperCase();
        const label = String(channelLabel || "GENERAL").trim();
        const message = String(body || "").trim();

        return [
            "HOSPITAL INTERCOM // " + type,
            "CHANNEL: " + label,
            "FROM: OPERATOR",
            "",
            message
        ].join("\n");
    }

    function appendEntry(
        specialist,
        channelType,
        channelLabel,
        body,
        transport,
        roomTeam
    ) {
        const id = String((specialist || {}).id || "");
        const name =
            String(
                (specialist || {}).name
                || (specialist || {}).id
                || "SPECIALIST"
            );

        const entry = {
            id: nextMessageId++,
            channelKey: channelKey(channelType, channelLabel, id),
            channelType:
                String(channelType || "HOSPITAL").toUpperCase(),
            channelLabel:
                String(channelLabel || "GENERAL").trim(),
            specialistId: id,
            specialistName: name,
            sender: "OPERATOR",
            body: String(body || ""),
            transport: String(transport || "PERSISTENT"),
            roomTeam: String(roomTeam || ""),
            launchedAt: new Date().toLocaleTimeString()
        };

        const next = messages.concat([entry]);
        messages = next.length > 80
            ? next.slice(next.length - 80)
            : next;
        messageLaunched(entry);
        return entry;
    }

    function detachedMessage(
        specialist,
        channelType,
        channelLabel,
        body,
        workingDirectory
    ) {
        const command =
            String(
                specialist.endpoint
                || specialist.command
                || ""
            ).trim();
        const extraArgs =
            Array.isArray(specialist.intercomArgs)
            ? specialist.intercomArgs.map(function(value) {
                  return String(value || "");
              }).filter(function(value) {
                  return value.length > 0;
              })
            : [];
        const cwd = String(workingDirectory || "").trim();

        if (!command) {
            lastError =
                "INTERCOM STOPPED // "
                + String(specialist.name || specialist.id || "SPECIALIST")
                + " HAS NO COMMAND";
            return false;
        }

        const prompt = buildPrompt(
            channelType,
            channelLabel,
            body
        );
        const launchArgs = ["kitty"];

        if (cwd) {
            launchArgs.push("--directory");
            launchArgs.push(cwd);
        }

        launchArgs.push(command);

        for (let i = 0; i < extraArgs.length; ++i)
            launchArgs.push(extraArgs[i]);

        launchArgs.push(prompt);
        Quickshell.execDetached(launchArgs);

        appendEntry(
            specialist,
            channelType,
            channelLabel,
            body,
            "DETACHED",
            ""
        );
        lastStatus =
            "INTERCOM FRESH TERMINAL // "
            + String(specialist.name || specialist.id || "SPECIALIST");
        lastError = "";
        return true;
    }

    function sendMessage(
        record,
        channelType,
        channelLabel,
        body,
        workingDirectory,
        forceFresh
    ) {
        const specialist = record || {};
        const id = String(specialist.id || "").trim();
        const name =
            String(specialist.name || specialist.id || "SPECIALIST").trim();
        const presence =
            String(specialist.presence || "UNKNOWN").toUpperCase();
        const callable = !!specialist.callable;
        const message = String(body || "").trim();

        lastError = "";

        if (!message) {
            lastStatus = "";
            lastError = "INTERCOM STOPPED // MESSAGE EMPTY";
            return false;
        }

        if (!id || !callable) {
            lastStatus = "";
            lastError = "INTERCOM STOPPED // SPECIALIST IS NOT CALLABLE";
            return false;
        }

        if (presence !== "READY") {
            lastStatus = "";
            lastError =
                "INTERCOM STOPPED // "
                + name
                + " IS "
                + presence;
            return false;
        }

        if (!!forceFresh) {
            return detachedMessage(
                specialist,
                channelType,
                channelLabel,
                message,
                workingDirectory
            );
        }

        const room =
            responsibilityService
            ? responsibilityService.roomForSpecialist(specialist)
            : null;
        const team = room ? String(room.team || "").trim() : "";

        if (!team) {
            lastStatus = "";
            lastError =
                "INTERCOM STOPPED // NO UNIQUE ROOM OWNER // "
                + "RIGHT CLICK SEND FOR FRESH TERMINAL";
            return false;
        }

        if (!dispatchService) {
            lastStatus = "";
            lastError =
                "INTERCOM STOPPED // PERSISTENT DISPATCH UNAVAILABLE";
            return false;
        }

        const prompt = buildPrompt(
            channelType,
            channelLabel,
            message
        );

        if (!dispatchService.dispatchToRoom(
                team,
                prompt,
                specialist,
                workingDirectory,
                "INTERCOM")) {
            lastStatus = "";
            lastError =
                dispatchService.lastError
                || "INTERCOM STOPPED // DOCTOR DISPATCH BUSY";
            return false;
        }

        appendEntry(
            specialist,
            channelType,
            channelLabel,
            message,
            "PERSISTENT",
            team
        );
        lastStatus =
            "INTERCOM ROUTED // "
            + name
            + " // ROOM "
            + team;
        lastError = "";
        return true;
    }
}
