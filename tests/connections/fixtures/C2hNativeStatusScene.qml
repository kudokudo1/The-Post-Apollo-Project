import QtQuick
import Quickshell
import Quickshell.Io
import qs.services.connections
import "widgets/cpuplus"
import "services/connections/ConnectionsRequestDisplayPolicy.js" as DisplayPolicy

// C2h: disposable CI native QML status ingestion; NOT a production bridge.
// This scene starts a fixed FAKE-ONLY C2f host under a private test HOME.
// It never sends approval, stores credentials, or marks the host authenticated.
ShellRoot {
    id: test
    property bool finished: false
    property bool started: false
    property bool exited: false
    property int seen: 0
    property var expected: ["PENDING", "APPROVED", "COMPLETED",
                            "PENDING", "DENIED", "PENDING", "CANCELLED",
                            "PENDING", "EXPIRED", "PENDING", "APPROVED", "FAILED"]
    readonly property bool privateMarker:
        String(Quickshell.env("GITHUB_ACTIONS") || "") === "true"
        && String(Quickshell.env("POST_APOLLO_C2C_FAKE_ONLY") || "") === "1"

    FloatingWindow {
        id: window
        visible: true
        title: "C2H-STATUS-PRIVATE-TEST"
        implicitWidth: 620
        implicitHeight: 900
        Rectangle {
            anchors.fill: parent
            color: "#1B0623"
            CpuPlusSettingsConnectionsDetailsPane {
                id: details
                anchors.fill: parent
                anchors.margins: 15
                selectedId: "nasa-firms"
                requestStatusOpen: true
            }
        }
    }

    function finish(ok) {
        if (finished) return;
        finished = true;
        if (ok)
            console.warn("C2H_NATIVE_STREAM_PASS // REAL_QML_FAKE_HOST_NO_GRANT");
        else
            console.warn("C2H_NATIVE_STREAM_REFUSED");
        Qt.quit();
    }

    function accept(raw) {
        if (finished || !started || exited || seen >= expected.length
                || typeof raw !== "string" || raw.length > 1024) {
            finish(false);
            return;
        }
        var record;
        try { record = JSON.parse(raw); }
        catch(error) { finish(false); return; }
        var view = DisplayPolicy.project(record, "nasa-firms");
        var wanted = expected[seen];
        if (!view.known || view.state !== wanted
                || view.title !== "SIMULATED // " + wanted
                || view.grantActive || view.live || view.canApprove
                || view.requestId !== ""
                || ConnectionsBroker.credentialActionsEnabled
                || ConnectionsRequestStatus.hostConnected
                || ConnectionsRequestStatus.hostAuthenticated
                || ConnectionsRequestStatus.canApprove) {
            finish(false);
            return;
        }
        // Test-only, local property on the REAL CPU++ details pane.
        // Product singleton stays disconnected and cannot be overwritten.
        details.syntheticStatusPreview = record;
        if (details.requestStatusView.state !== wanted
                || details.requestStatusView.grantActive
                || details.requestStatusView.canApprove
                || details.requestStatusView.live) {
            finish(false);
            return;
        }
        seen++;
        // Intentionally do not log requestId, raw record, or synthetic key.
    }

    function afterExit(code) {
        exited = true;
        if (code !== 0 || seen !== expected.length) {
            finish(false);
            return;
        }
        details.syntheticStatusPreview = null;
        if (details.requestStatusView.state !== "OFFLINE"
                || details.requestStatusView.title !== "HOST NOT CONNECTED"
                || ConnectionsRequestStatus.hostConnected
                || ConnectionsBroker.credentialActionsEnabled
                || ConnectionsBroker.authorize({
                    provider:"nasa-firms",consumer:"weather-earth",
                    operation:"fires.hotspots.read"
                }).allowed) {
            finish(false);
            return;
        }
        finish(true);
    }

    Process {
        id: producer
        running: false
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: function(line) { test.accept(line); }
        }
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) { test.afterExit(code); }
    }

    Timer {
        interval: 100
        running: true
        repeat: false
        onTriggered: {
            if (test.finished) return;
            if (!test.privateMarker
                    || details.requestStatusView.state !== "OFFLINE"
                    || ConnectionsRequestStatus.hostConnected) {
                test.finish(false);
                return;
            }
            test.started = true;
            producer.exec([
                "python3", "-B",
                Quickshell.shellPath(
                    "tests/connections/fixtures/C2hStatusProducer.py"),
                "--c2h-fake-stream"
            ]);
        }
    }

    Timer {
        interval: 18000
        running: !test.finished
        repeat: false
        onTriggered: test.finish(false)
    }
}
