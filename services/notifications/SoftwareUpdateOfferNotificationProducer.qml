import QtQuick
import Quickshell
import Quickshell.Io
import qs.services.notifications

// A read-only, low-frequency update-offer observer. Only a *separate*
// Kitty terminal with typed DOWNLOAD or APPLY can run Flatpak updates.
// Firmware review opens the native GNOME Software page. No QML code performs
// OS/package mutations, handles passwords, or reboots.
Scope {
    id: producer

    property var offers: ({})
    property var sessionSeen: ({})
    property string deferKind: ""
    property string deferToken: ""
    property double lastScanMs: 0
    property var lastReviewAt: ({})

    readonly property string script: Quickshell.shellPath("scripts/updates/update_offers.py")

    function knownKind(kind) {
        return ["silverblue", "oh-my-zsh", "powerlevel10k",
                "flatpak-user", "flatpak-system", "firmware"].indexOf(kind) !== -1;
    }

    function isCurrent(kind, token) {
        const k = String(kind || "");
        const t = String(token || "");
        return producer.knownKind(k) && /^[a-f0-9]{24}$/.test(t)
            && !!producer.offers[k] && producer.offers[k].token === t;
    }

    function refresh() {
        if (!NotificationsService.historyReady || scanProcess.running
                || deferProcess.running || Date.now() - producer.lastScanMs < 60000)
            return;
        producer.lastScanMs = Date.now();
        scanProcess.running = true;
    }

    function acceptScan(raw) {
        let parsed;
        try {
            parsed = JSON.parse(String(raw || ""));
        } catch (error) {
            return;
        }
        if (!parsed || parsed.schema !== 1 || !Array.isArray(parsed.offers))
            return;
        const current = {};
        for (const row of parsed.offers.slice(0, 6)) {
            const kind = String((row || {}).kind || "");
            const token = String((row || {}).token || "");
            if (!producer.knownKind(kind) || !/^[a-f0-9]{24}$/.test(token)
                    || !row.title || !row.message || current[kind])
                continue;
            current[kind] = { token: token, phase: String(row.phase || "") };
            const key = kind + ":" + token;
            if (producer.sessionSeen[key])
                continue;
            const nextSeen = Object.assign({}, producer.sessionSeen);
            nextSeen[key] = true;
            producer.sessionSeen = nextSeen;
            NotificationsService.pushRich({
                "id": "apollo-update-" + kind + "-" + token,
                "source": "UPDATES",
                "sourceId": "apollo-update-monitor",
                "category": "internal",
                "severity": "normal",
                "title": String(row.title).slice(0, 110),
                "message": String(row.message).slice(0, 360)
                           + (kind.startsWith("flatpak-")
                              ? " Open Notifications Hub: DOWNLOAD or NOT NOW."
                              : kind === "firmware"
                              ? " Open Notifications Hub: OPEN UPDATES or NOT NOW."
                              : " Open Notifications Hub: REVIEW or NOT NOW."),
                "tags": ["system", "updates", "operator-confirmation"],
                "context": {
                    "origin": "apollo",
                    "domain": "system",
                    "eventType": "software-update-offer",
                    "updateKind": kind,
                    "updateToken": token,
                    "phase": current[kind].phase
                }
            });
        }
        producer.offers = current;
    }

    function review(kind, token) {
        if (!producer.isCurrent(kind, token))
            return false;
        const now = Date.now();
        if (now - Number(producer.lastReviewAt[kind] || 0) < 45000)
            return false;
        const next = Object.assign({}, producer.lastReviewAt);
        next[kind] = now;
        producer.lastReviewAt = next;
        if (kind === "firmware") {
            // GNOME Software owns fwupd's device warnings, authorization,
            // installation and any reboot. Never run fwupdmgr update here.
            Quickshell.execDetached(["gnome-software", "--mode=updates"]);
            return true;
        }
        // The Python entrypoint rechecks the immutable offer fingerprint.
        // Flatpaks ask for DOWNLOAD (cache only) or APPLY (deploy).
        Quickshell.execDetached([
            "kitty", "--hold", "-e", "/usr/bin/python3",
            producer.script, "review", String(kind), String(token)
        ]);
        return true;
    }

    function defer(kind, token) {
        if (!producer.isCurrent(kind, token) || deferProcess.running)
            return false;
        producer.deferKind = String(kind);
        producer.deferToken = String(token);
        deferProcess.command = ["/usr/bin/python3", producer.script, "defer",
                                producer.deferKind, producer.deferToken];
        deferProcess.running = true;
        return true;
    }

    function acceptDefer(exitCode) {
        if (exitCode === 0 && producer.isCurrent(producer.deferKind, producer.deferToken)) {
            const remaining = Object.assign({}, producer.offers);
            delete remaining[producer.deferKind];
            producer.offers = remaining;
            NotificationsService.updateNotification(
                "apollo-update-" + producer.deferKind + "-" + producer.deferToken, {
                    "title": "UPDATES // OFFER DEFERRED",
                    "message": "Post-Apollo will not offer this unchanged update again "
                               + "for 24 hours. System updaters keep their own settings."
                });
        }
        producer.deferKind = "";
        producer.deferToken = "";
    }

    Process {
        id: scanProcess
        command: ["/usr/bin/python3", producer.script, "scan"]
        stdout: StdioCollector {
            onStreamFinished: producer.acceptScan(text)
        }
    }

    Process {
        id: deferProcess
        stdout: StdioCollector {}
        onExited: function(code, exitStatus) {
            producer.acceptDefer(Number(code));
        }
    }

    Timer {
        interval: 6 * 60 * 60 * 1000
        running: true
        repeat: true
        onTriggered: producer.refresh()
    }
    Connections {
        target: NotificationsService
        function onHistoryReadyChanged() {
            if (NotificationsService.historyReady)
                producer.refresh();
        }
    }
    Component.onCompleted: Qt.callLater(producer.refresh)
}
