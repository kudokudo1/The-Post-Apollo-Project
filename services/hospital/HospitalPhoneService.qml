import QtQuick
import Quickshell

QtObject {
    id: root

    required property var registryService

    property string lastDialedId: ""
    property string lastStatus: ""
    property string lastError: ""

    signal callLaunched(var specialist)

    function callSpecialist(record, workingDirectory, contextPrompt) {
        const specialist = record || {};
        const id = String(specialist.id || "").trim();
        const name = String(
            specialist.name
            || specialist.id
            || "SPECIALIST"
        ).trim();
        const presence = String(
            specialist.presence
            || "UNKNOWN"
        ).toUpperCase();
        const callable = !!specialist.callable;
        const command = String(
            specialist.endpoint
            || specialist.command
            || ""
        ).trim();
        const cwd = String(workingDirectory || "").trim();
        const prompt = String(contextPrompt || "").trim();

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

        lastDialedId = id;
        lastStatus =
            "CALL LAUNCHED // "
            + name
            + (prompt ? " // CONTEXT ATTACHED" : "");
        lastError = "";
        callLaunched(specialist);
        return true;
    }
}
