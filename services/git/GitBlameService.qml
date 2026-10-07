import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repositoryPath: ""
    property string filePath: ""
    property string revision: "WORKTREE"

    property int requestedStartLine: 0
    property int requestedEndLine: 0

    property bool followRenames: true
    property bool busy: false

    property var rows: []
    property var groups: []

    property string status: "READY"
    property string lastError: ""

    property bool blameExitSeen: false
    property bool blameStdoutSeen: false
    property bool blameStderrSeen: false
    property int blameExitCode: -1
    property string blameStdoutText: ""
    property string blameStderrText: ""

    signal loaded()
    signal commitRequested(string sha)
    signal historyRequested(string sha, string path, int line)

    readonly property bool available:
        String(repositoryPath || "").trim().length > 0

    readonly property int lineCount: rows.length
    readonly property int groupCount: groups.length

    function rowAt(index) {
        if (index < 0 || index >= rows.length)
            return null;
        return rows[index];
    }

    function groupAt(index) {
        if (index < 0 || index >= groups.length)
            return null;
        return groups[index];
    }

    function isUncommittedSha(sha) {
        return /^0{40}$/.test(String(sha || ""));
    }

    function clear() {
        filePath = "";
        revision = "WORKTREE";
        requestedStartLine = 0;
        requestedEndLine = 0;
        rows = [];
        groups = [];
        status = "READY";
        lastError = "";
    }

    function normalizedRange(startLine, endLine) {
        const start = Math.max(0, Number(startLine || 0));
        const end = Math.max(0, Number(endLine || 0));

        if (start <= 0)
            return { start: 0, end: 0, argument: "" };

        const finalEnd = end >= start ? end : start;
        return {
            start: start,
            end: finalEnd,
            argument: "-L" + String(start) + "," + String(finalEnd)
        };
    }

    function load(path, startLine, endLine, revisionName) {
        const repo = String(repositoryPath || "").trim();
        const targetPath = String(path || filePath || "").trim();
        const requestedRevision =
            String(
                revisionName === undefined || revisionName === null
                ? revision
                : revisionName
            ).trim();
        const nextRevision =
            !requestedRevision || requestedRevision === "WORKTREE"
            ? "WORKTREE"
            : requestedRevision;
        const range = normalizedRange(startLine, endLine);

        if (!repo || !targetPath || busy)
            return false;

        filePath = targetPath;
        revision = nextRevision;
        requestedStartLine = range.start;
        requestedEndLine = range.end;

        busy = true;
        rows = [];
        groups = [];
        status = "BLAME // READING";
        lastError = "";

        blameExitSeen = false;
        blameStdoutSeen = false;
        blameStderrSeen = false;
        blameExitCode = -1;
        blameStdoutText = "";
        blameStderrText = "";

        blameProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'path="$2"',
                'revision="$3"',
                'range="$4"',
                'follow="$5"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'if [ -z "$path" ]; then',
                '  printf "ERROR\\tFILE REQUIRED\\n"',
                '  exit 22',
                'fi',
                'cmd=(git -C "$repo" blame --line-porcelain --root)',
                'if [ "$follow" = "1" ]; then cmd+=(--follow); fi',
                'if [ -n "$range" ]; then cmd+=("$range"); fi',
                'if [ "$revision" != "WORKTREE" ]; then',
                '  if ! git -C "$repo" rev-parse --verify "$revision^{commit}" >/dev/null 2>&1; then',
                '    printf "ERROR\\tREVISION NOT FOUND // %s\\n" "$revision"',
                '    exit 23',
                '  fi',
                '  cmd+=("$revision")',
                'fi',
                'cmd+=(-- "$path")',
                '"${cmd[@]}"'
            ].join("\n"),
            "git-blame-provenance",
            repo,
            targetPath,
            nextRevision,
            range.argument,
            followRenames ? "1" : "0"
        ]);

        return true;
    }

    function loadFile(path, revisionName) {
        return load(path, 0, 0, revisionName);
    }

    function loadRange(path, startLine, endLine, revisionName) {
        return load(path, startLine, endLine, revisionName);
    }

    function parseHeader(line) {
        const match =
            String(line || "").match(
                /^\^?([0-9a-f]{40})\s+(\d+)\s+(\d+)(?:\s+(\d+))?$/
            );

        if (!match)
            return null;

        return {
            sha: match[1],
            originalLine: Number(match[2] || 0),
            finalLine: Number(match[3] || 0),
            span: Number(match[4] || 1)
        };
    }

    function buildGroups(sourceRows) {
        const out = [];

        for (let i = 0; i < sourceRows.length; ++i) {
            const row = sourceRows[i] || {};
            const previous =
                out.length > 0
                ? out[out.length - 1]
                : null;
            const joinsPrevious =
                previous
                && previous.sha === row.sha
                && previous.sourcePath === row.sourcePath
                && previous.endLine + 1 === row.finalLine
                && previous.originalEndLine + 1 === row.originalLine;

            if (joinsPrevious) {
                previous.endLine = row.finalLine;
                previous.originalEndLine = row.originalLine;
                previous.lineCount += 1;
                continue;
            }

            out.push({
                sha: row.sha,
                shortSha: row.shortSha,
                uncommitted: Boolean(row.uncommitted),
                author: row.author,
                authorMail: row.authorMail,
                authorTime: row.authorTime,
                authorTimezone: row.authorTimezone,
                summary: row.summary,
                sourcePath: row.sourcePath,
                previousSha: row.previousSha,
                previousPath: row.previousPath,
                startLine: row.finalLine,
                endLine: row.finalLine,
                originalStartLine: row.originalLine,
                originalEndLine: row.originalLine,
                lineCount: 1
            });
        }

        return out;
    }

    function parseBlame(text) {
        const out = [];
        const lines = String(text || "").split("\n");
        let current = null;

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            const header = parseHeader(line);

            if (header) {
                current = {
                    sha: header.sha,
                    originalLine: header.originalLine,
                    finalLine: header.finalLine,
                    span: header.span,
                    author: "",
                    authorMail: "",
                    authorTime: 0,
                    authorTimezone: "",
                    summary: "",
                    sourcePath: filePath,
                    previousSha: "",
                    previousPath: ""
                };
                continue;
            }

            if (!current)
                continue;

            if (line.indexOf("author ") === 0) {
                current.author = line.slice(7);
                continue;
            }

            if (line.indexOf("author-mail ") === 0) {
                current.authorMail = line.slice(12);
                continue;
            }

            if (line.indexOf("author-time ") === 0) {
                current.authorTime = Number(line.slice(12) || 0);
                continue;
            }

            if (line.indexOf("author-tz ") === 0) {
                current.authorTimezone = line.slice(10);
                continue;
            }

            if (line.indexOf("summary ") === 0) {
                current.summary = line.slice(8);
                continue;
            }

            if (line.indexOf("previous ") === 0) {
                const previous = line.slice(9);
                const separator = previous.indexOf(" ");

                if (separator > 0) {
                    current.previousSha = previous.slice(0, separator);
                    current.previousPath = previous.slice(separator + 1);
                }
                continue;
            }

            if (line.indexOf("filename ") === 0) {
                current.sourcePath = line.slice(9);
                continue;
            }

            if (line.indexOf("\t") === 0) {
                const sha = String(current.sha || "");
                out.push({
                    sha: sha,
                    shortSha:
                        isUncommittedSha(sha)
                        ? "WORKTREE"
                        : sha.slice(0, 8),
                    uncommitted: isUncommittedSha(sha),
                    originalLine: Number(current.originalLine || 0),
                    finalLine: Number(current.finalLine || 0),
                    author: current.author,
                    authorMail: current.authorMail,
                    authorTime: Number(current.authorTime || 0),
                    authorTimezone: current.authorTimezone,
                    summary: current.summary,
                    sourcePath:
                        current.sourcePath
                        || filePath,
                    previousSha: current.previousSha,
                    previousPath: current.previousPath,
                    content: line.slice(1)
                });
                current = null;
            }
        }

        rows = out;
        groups = buildGroups(out);
    }

    function rowsForRange(startLine, endLine) {
        const range = normalizedRange(startLine, endLine);

        if (range.start <= 0)
            return rows.slice();

        return rows.filter(function(row) {
            const line = Number((row || {}).finalLine || 0);
            return line >= range.start && line <= range.end;
        });
    }

    function groupsForRange(startLine, endLine) {
        const selectedRows = rowsForRange(startLine, endLine);
        return buildGroups(selectedRows);
    }

    function requestCommit(sha) {
        const target = String(sha || "").trim();

        if (!target || isUncommittedSha(target))
            return false;

        commitRequested(target);
        return true;
    }

    function requestHistory(sha, path, line) {
        const target = String(sha || "").trim();

        if (!target || isUncommittedSha(target))
            return false;

        historyRequested(
            target,
            String(path || filePath || ""),
            Math.max(0, Number(line || 0))
        );
        return true;
    }

    function requestHistoryForRow(index) {
        const row = rowAt(index);

        if (!row)
            return false;

        return requestHistory(
            row.sha,
            row.sourcePath || filePath,
            row.finalLine
        );
    }

    function maybeFinishBlame() {
        if (!busy
                || !blameExitSeen
                || !blameStdoutSeen
                || !blameStderrSeen)
            return;

        busy = false;

        if (blameExitCode !== 0) {
            lastError = String(
                blameStderrText
                || blameStdoutText
                || ("BLAME EXIT " + blameExitCode)
            ).trim();

            if (lastError.indexOf("ERROR\t") === 0)
                lastError = lastError.slice(6);

            rows = [];
            groups = [];
            status = "BLAME // REFUSED";
            return;
        }

        parseBlame(blameStdoutText);
        lastError = "";
        status =
            "BLAME // "
            + String(rows.length)
            + " LINES // "
            + String(groups.length)
            + " GROUPS";
        loaded();
    }

    Process {
        id: blameProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.blameStdoutText = this.text;
                root.blameStdoutSeen = true;
                root.maybeFinishBlame();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.blameStderrText = this.text;
                root.blameStderrSeen = true;
                root.maybeFinishBlame();
            }
        }

        onExited: function(code, exitStatus) {
            root.blameExitCode = Number(code);
            root.blameExitSeen = true;
            root.maybeFinishBlame();
        }
    }
}
