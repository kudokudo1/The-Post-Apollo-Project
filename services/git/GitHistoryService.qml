import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repositoryPath: ""
    property bool detailBusy: false
    property string selectedSha: ""
    property string detailText: "SELECT A COMMIT"
    property string lastError: ""

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    readonly property bool available:
        String(repositoryPath || "").trim().length > 0

    function showCommit(sha) {
        const repo = String(repositoryPath || "").trim();
        const target = String(sha || "").trim();

        if (!repo || !target || detailBusy)
            return false;

        detailBusy = true;
        selectedSha = target;
        detailText = "READING COMMIT // " + target.slice(0, 10);
        lastError = "";

        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        detailProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'sha="$2"',
                'if ! git -C "$repo" rev-parse --verify "$sha^{commit}" >/dev/null 2>&1; then',
                '  printf "COMMIT NOT FOUND\\n"',
                '  exit 21',
                'fi',
                'git -C "$repo" show',
                '  --no-ext-diff',
                '  --decorate=short',
                '  --date=local',
                '  --format="commit %H%nAuthor: %an <%ae>%nDate:   %ad%n%n    %s%n%n%b"',
                '  --stat',
                '  --summary',
                '  "$sha"'
            ].join(" \\\n"),
            "git-history-detail",
            repo,
            target
        ]);

        return true;
    }

    function maybeFinish() {
        if (!detailBusy || !exitSeen || !stdoutSeen || !stderrSeen)
            return;

        detailBusy = false;

        const out = String(stdoutText || "").trim();
        const err = String(stderrText || "").trim();

        if (exitCode !== 0) {
            lastError = err || out || ("HISTORY EXIT " + exitCode);
            detailText = "ERROR // " + lastError;
            return;
        }

        lastError = "";
        detailText = out || "NO COMMIT DETAIL";
    }

    Process {
        id: detailProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.stdoutText = this.text;
                root.stdoutSeen = true;
                root.maybeFinish();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.stderrText = this.text;
                root.stderrSeen = true;
                root.maybeFinish();
            }
        }

        onExited: function(code, exitStatus) {
            root.exitCode = Number(code);
            root.exitSeen = true;
            root.maybeFinish();
        }
    }
}
