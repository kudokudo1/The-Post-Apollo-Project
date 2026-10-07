import QtQuick
import Quickshell

QtObject {
    id: root

    required property var registryService
    property var responsibilityService: null

    property string lastDialedId: ""
    property string lastStatus: ""
    property string lastError: ""

    signal callLaunched(var specialist)
    signal persistentCallRequested(string roomTeam, var specialist)

    function detachedCall(record, workingDirectory, contextPrompt) {
        const specialist = record || {};
        const name =
            String(specialist.name || specialist.id || "SPECIALIST").trim();
        const command =
            String(specialist.endpoint || specialist.command || "").trim();
        const cwd = String(workingDirectory || "").trim();
        const prompt = String(contextPrompt || "").trim();

        if (!command) {
            lastStatus = "";
            lastError =
                "PHONE STOPPED // "
                + name
                + " HAS NO COMMAND";
            return false;
        }

        const launchArgs = ["kitty"];

        if (cwd) {
            launchArgs.push("--directory");
            launchArgs.push(cwd);
        }

        launchArgs.push(command);

        if (prompt)
            launchArgs.push(prompt);

        Quickshell.execDetached(launchArgs);
        lastDialedId = String(specialist.id || "");
        lastStatus =
            "FRESH CALL LAUNCHED // "
            + name
            + (prompt ? " // CONTEXT ATTACHED" : "");
        lastError = "";
        callLaunched(specialist);
        return true;
    }

    function callSpecialist(
        record,
        workingDirectory,
        contextPrompt,
        forceFresh
    ) {
        const specialist = record || {};
        const id = String(specialist.id || "").trim();
        const name =
            String(specialist.name || specialist.id || "SPECIALIST").trim();
        const presence =
            String(specialist.presence || "UNKNOWN").toUpperCase();
        const callable = !!specialist.callable;

        lastError = "";

        if (!id || !callable) {
            lastStatus = "";
            lastError = "PHONE STOPPED // SPECIALIST IS NOT CALLABLE";
            return false;
        }

        if (presence !== "READY") {
            lastStatus = "";
            lastError =
                "PHONE STOPPED // "
                + name
                + " IS "
                + presence;
            return false;
        }

        if (!!forceFresh)
            return detachedCall(
                specialist,
                workingDirectory,
                contextPrompt
            );

        const room =
            responsibilityService
            ? responsibilityService.roomForSpecialist(specialist)
            : null;
        const team = room ? String(room.team || "").trim() : "";

        if (!team) {
            lastStatus = "";
            lastError =
                "PHONE STOPPED // NO UNIQUE ROOM OWNER // "
                + "RIGHT CLICK FOR FRESH TERMINAL";
            return false;
        }

        lastDialedId = id;
        lastStatus =
            "CALL ATTACHED // "
            + name
            + " // ROOM "
            + team;
        lastError = "";
        persistentCallRequested(team, specialist);
        callLaunched(specialist);
        return true;
    }
}
