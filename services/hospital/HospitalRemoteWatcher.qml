import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: watcher

    property string repoPath: ""
    property string floorKey: ""
    property bool active: false

    // This is intentionally a quiet probe interval. The Hospital UI does not
    // refresh on the timer; it refreshes only if the remote fingerprint changes.
    property int remoteProbeInterval: 120000
    // Reopening Hospital does not probe every time. If Quickshell has stayed
    // alive, an open only triggers an immediate probe after this much quiet time.
    // A Quickshell restart resets this state, so the first open always probes.
    property int openProbeStaleInterval: 600000
    property double lastProbeAtMs: 0

    property bool probing: false
    property bool fetching: false
    property bool initialized: false
    property string fingerprint: ""
    property string pendingFingerprint: ""
    property string lastError: ""

    property bool probeExitSeen: false
    property bool probeStdoutSeen: false
    property bool probeStderrSeen: false
    property int probeExitCode: -1
    property string probeStdoutText: ""
    property string probeStderrText: ""

    property bool fetchExitSeen: false
    property bool fetchStdoutSeen: false
    property bool fetchStderrSeen: false
    property int fetchExitCode: -1
    property string fetchStdoutText: ""
    property string fetchStderrText: ""

    signal remoteSnapshotReady(bool changed)
    signal remoteCheckCompleted(bool refsChanged)

    function resetBaseline() {
        initialized = false;
        fingerprint = "";
        pendingFingerprint = "";
        lastProbeAtMs = 0;
        lastError = "";
    }

    function shouldProbeOnOpen() {
        if (!initialized || lastProbeAtMs <= 0)
            return true;

        return Date.now() - lastProbeAtMs >= openProbeStaleInterval;
    }

    function probeNow() {
        if (!active || probing || fetching)
            return;

        const path = String(repoPath || "").trim();

        if (!path)
            return;

        probing = true;
        lastError = "";
        probeExitSeen = false;
        probeStdoutSeen = false;
        probeStderrSeen = false;
        probeExitCode = -1;
        probeStdoutText = "";
        probeStderrText = "";

        probeProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "NO_REPO\\n"',
                '  exit 20',
                'fi',
                'if ! git -C "$repo" remote get-url origin >/dev/null 2>&1; then',
                '  printf "NO_ORIGIN\\n"',
                '  exit 21',
                'fi',
                'git -C "$repo" ls-remote --symref origin HEAD "refs/heads/*" 2>/dev/null',
                '  | LC_ALL=C sort',
                '  | sha256sum',
                '  | awk "{print \\$1}"'
            ].join("\n"),
            "hospital-remote-probe",
            path
        ]);

        probeWatchdog.restart();
    }

    function maybeFinishProbe() {
        if (!probing
                || !probeExitSeen
                || !probeStdoutSeen
                || !probeStderrSeen)
            return;

        probing = false;
        probeWatchdog.stop();

        if (probeExitCode !== 0) {
            lastError = String(
                probeStderrText
                || probeStdoutText
                || ("REMOTE PROBE EXIT " + probeExitCode)
            ).trim();
            return;
        }

        const next = String(probeStdoutText || "").trim();

        if (!next)
            return;

        // A successful comparison counts as fresh even when nothing changed.
        // This is what prevents close/open/close/open from probing repeatedly.
        lastProbeAtMs = Date.now();

        if (initialized && next === fingerprint) {
            remoteCheckCompleted(false);
            return;
        }

        pendingFingerprint = next;
        fetchRemote(initialized);
    }

    function fetchRemote(wasInitialized) {
        if (fetching)
            return;

        const path = String(repoPath || "").trim();

        if (!path)
            return;

        fetching = true;
        fetchExitSeen = false;
        fetchStdoutSeen = false;
        fetchStderrSeen = false;
        fetchExitCode = -1;
        fetchStdoutText = "";
        fetchStderrText = "";

        // Fetch updates only remote-tracking refs. It never checks out a branch,
        // changes the Bed's working files, merges, or pulls.
        fetchProcess.wasInitialized = wasInitialized;
        fetchProcess.exec([
            "bash",
            "-lc",
            'git -C "$1" fetch --prune origin',
            "hospital-remote-fetch",
            path
        ]);

        fetchWatchdog.restart();
    }

    function maybeFinishFetch() {
        if (!fetching
                || !fetchExitSeen
                || !fetchStdoutSeen
                || !fetchStderrSeen)
            return;

        fetching = false;
        fetchWatchdog.stop();

        if (fetchExitCode !== 0) {
            lastError = String(
                fetchStderrText
                || fetchStdoutText
                || ("REMOTE FETCH EXIT " + fetchExitCode)
            ).trim();
            return;
        }

        const changed = fetchProcess.wasInitialized;
        fingerprint = pendingFingerprint;
        pendingFingerprint = "";
        initialized = true;
        lastError = "";
        remoteSnapshotReady(changed);
        remoteCheckCompleted(changed);
    }

    onFloorKeyChanged: {
        resetBaseline();

        if (active)
            immediateProbe.restart();
    }

    onRepoPathChanged: {
        if (active && !initialized)
            immediateProbe.restart();
    }

    onActiveChanged: {
        if (active && shouldProbeOnOpen())
            immediateProbe.restart();
    }

    Timer {
        id: immediateProbe
        interval: 250
        repeat: false
        onTriggered: watcher.probeNow()
    }

    Timer {
        interval: watcher.remoteProbeInterval
        repeat: true
        running: watcher.active
        onTriggered: watcher.probeNow()
    }

    Process {
        id: probeProcess

        stdout: StdioCollector {
            onStreamFinished: {
                watcher.probeStdoutText = this.text;
                watcher.probeStdoutSeen = true;
                watcher.maybeFinishProbe();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                watcher.probeStderrText = this.text;
                watcher.probeStderrSeen = true;
                watcher.maybeFinishProbe();
            }
        }

        onExited: function(code, exitStatus) {
            watcher.probeExitCode = Number(code);
            watcher.probeExitSeen = true;
            watcher.maybeFinishProbe();
        }
    }

    Process {
        id: fetchProcess
        property bool wasInitialized: false

        stdout: StdioCollector {
            onStreamFinished: {
                watcher.fetchStdoutText = this.text;
                watcher.fetchStdoutSeen = true;
                watcher.maybeFinishFetch();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                watcher.fetchStderrText = this.text;
                watcher.fetchStderrSeen = true;
                watcher.maybeFinishFetch();
            }
        }

        onExited: function(code, exitStatus) {
            watcher.fetchExitCode = Number(code);
            watcher.fetchExitSeen = true;
            watcher.maybeFinishFetch();
        }
    }

    Timer {
        id: probeWatchdog
        interval: 15000
        repeat: false

        onTriggered: {
            if (!watcher.probing)
                return;

            watcher.probing = false;
            watcher.lastError = "REMOTE PROBE TIMEOUT";

            if (probeProcess.running)
                probeProcess.running = false;
        }
    }

    Timer {
        id: fetchWatchdog
        interval: 20000
        repeat: false

        onTriggered: {
            if (!watcher.fetching)
                return;

            watcher.fetching = false;
            watcher.lastError = "REMOTE FETCH TIMEOUT";

            if (fetchProcess.running)
                fetchProcess.running = false;
        }
    }
}
