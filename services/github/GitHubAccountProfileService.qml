import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property bool loading: false
    property bool saving: false
    readonly property bool busy: loading || saving

    property string login: ""
    property string displayName: ""
    property string bio: ""
    property string email: ""
    property string primaryEmail: ""
    property bool primaryEmailAvailable: false
    property string primaryEmailMessage: "PRIMARY EMAIL // NOT LOADED"
    property string profileUrl: ""

    property string stateText: "ACCOUNT PROFILE // READY"
    property string lastError: ""

    property string readStdout: ""
    property string readStderr: ""
    property bool readStdoutSeen: false
    property bool readStderrSeen: false
    property bool readExitSeen: false
    property int readExitCode: -1

    property string saveStdout: ""
    property string saveStderr: ""
    property bool saveStdoutSeen: false
    property bool saveStderrSeen: false
    property bool saveExitSeen: false
    property int saveExitCode: -1

    signal profileLoaded()
    signal profileSaved(bool success)

    function applyProfileObject(value) {
        const profile = value || {};

        login = String(profile.login || "");
        displayName = String(profile.name || "");
        bio = String(profile.bio || "");
        email = String(profile.email || "");
        profileUrl = String(profile.html_url || "");

        if (profile.primaryEmail !== undefined) {
            primaryEmail = String(profile.primaryEmail || "");
            primaryEmailAvailable = !!profile.primaryEmailAvailable;
            primaryEmailMessage = String(
                profile.primaryEmailMessage
                || (
                    primaryEmailAvailable
                    ? "PRIMARY EMAIL // READY"
                    : "PRIMARY EMAIL // UNAVAILABLE"
                  )
            );
        }
    }

    function refreshProfile() {
        if (busy)
            return false;

        loading = true;
        lastError = "";
        stateText = "ACCOUNT PROFILE // READING";
        readStdout = "";
        readStderr = "";
        readStdoutSeen = false;
        readStderrSeen = false;
        readExitSeen = false;
        readExitCode = -1;

        readProcess.exec([
            "bash",
            "-lc",
            [
                'profile="$(gh api user --jq "{login,name,bio,email,html_url}")" || exit $?',
                'primary_email=""',
                'primary_available=false',
                'primary_message="PRIMARY EMAIL // user:email scope required"',
                'if emails="$(gh api user/emails 2>/dev/null)"; then',
                '  primary_email="$(printf "%s" "$emails" | jq -r "map(select(.primary == true))[0].email // empty")"',
                '  primary_available=true',
                '  primary_message="PRIMARY EMAIL // READY"',
                'fi',
                "jq -nc --argjson profile \"$profile\" --arg primaryEmail \"$primary_email\" --argjson primaryEmailAvailable \"$primary_available\" --arg primaryEmailMessage \"$primary_message\" '$profile + {primaryEmail:$primaryEmail,primaryEmailAvailable:$primaryEmailAvailable,primaryEmailMessage:$primaryEmailMessage}'"
            ].join("\n")
        ]);
        watchdog.restart();
        return true;
    }

    function saveProfile(name, nextBio, nextEmail) {
        if (busy)
            return false;

        saving = true;
        lastError = "";
        stateText = "ACCOUNT PROFILE // SAVING";
        saveStdout = "";
        saveStderr = "";
        saveStdoutSeen = false;
        saveStderrSeen = false;
        saveExitSeen = false;
        saveExitCode = -1;

        saveProcess.exec([
            "bash",
            "-lc",
            [
                'exec gh api --method PATCH user',
                '  -f "name=$1"',
                '  -f "bio=$2"',
                '  -f "email=$3"',
                '  --jq "{login,name,bio,email,html_url}"'
            ].join(" \\\n"),
            "pa-account-profile",
            String(name || ""),
            String(nextBio || ""),
            String(nextEmail || "").trim()
        ]);
        watchdog.restart();
        return true;
    }

    function maybeFinishRead() {
        if (!loading
                || !readStdoutSeen
                || !readStderrSeen
                || !readExitSeen)
            return;

        loading = false;
        watchdog.stop();

        const output = String(readStdout || "").trim();
        const error = String(readStderr || "").trim();

        if (readExitCode !== 0) {
            lastError = error || output || "ACCOUNT PROFILE READ FAILED";
            stateText = "ERROR // " + lastError;
            profileLoaded();
            return;
        }

        try {
            applyProfileObject(JSON.parse(output || "{}"));
            stateText = "ACCOUNT PROFILE // READY";
            lastError = "";
        } catch (parseError) {
            lastError = "ACCOUNT PROFILE PARSE // " + String(parseError);
            stateText = "ERROR // " + lastError;
        }

        profileLoaded();
    }

    function maybeFinishSave() {
        if (!saving
                || !saveStdoutSeen
                || !saveStderrSeen
                || !saveExitSeen)
            return;

        saving = false;
        watchdog.stop();

        const output = String(saveStdout || "").trim();
        const error = String(saveStderr || "").trim();

        if (saveExitCode !== 0) {
            lastError = error || output || "ACCOUNT PROFILE SAVE FAILED";
            stateText = "ERROR // " + lastError;
            profileSaved(false);
            return;
        }

        try {
            applyProfileObject(JSON.parse(output || "{}"));
            stateText = "ACCOUNT PROFILE // SAVED";
            lastError = "";
            profileSaved(true);
        } catch (parseError) {
            lastError = "ACCOUNT PROFILE SAVE PARSE // " + String(parseError);
            stateText = "ERROR // " + lastError;
            profileSaved(false);
        }
    }

    Process {
        id: readProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.readStdout = this.text;
                root.readStdoutSeen = true;
                root.maybeFinishRead();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.readStderr = this.text;
                root.readStderrSeen = true;
                root.maybeFinishRead();
            }
        }

        onExited: function(exitCode, exitStatus) {
            root.readExitCode = Number(exitCode);
            root.readExitSeen = true;
            root.maybeFinishRead();
        }
    }

    Process {
        id: saveProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.saveStdout = this.text;
                root.saveStdoutSeen = true;
                root.maybeFinishSave();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.saveStderr = this.text;
                root.saveStderrSeen = true;
                root.maybeFinishSave();
            }
        }

        onExited: function(exitCode, exitStatus) {
            root.saveExitCode = Number(exitCode);
            root.saveExitSeen = true;
            root.maybeFinishSave();
        }
    }

    Timer {
        id: watchdog
        interval: 120000
        repeat: false

        onTriggered: {
            const wasSaving = root.saving;

            root.loading = false;
            root.saving = false;
            root.lastError = "ACCOUNT PROFILE REQUEST TIMEOUT";
            root.stateText = "ERROR // " + root.lastError;

            if (readProcess.running)
                readProcess.running = false;

            if (saveProcess.running)
                saveProcess.running = false;

            if (wasSaving)
                root.profileSaved(false);
            else
                root.profileLoaded();
        }
    }
}
