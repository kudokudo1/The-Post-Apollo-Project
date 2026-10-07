import QtQuick
import Quickshell
import Quickshell.Io

// Text-only three-way conflict editor.
//
// Loads Git's unmerged index stages:
//   :1:path = BASE, :2:path = OURS, :3:path = THEIRS
// and the worktree file as RESULT. Conflict-marker blocks may be resolved
// individually in memory, manually edited, saved as a draft, or written and
// staged once every marker is gone.
//
// Every write re-verifies the exact stage blob identities captured at load.
// This service never continues/aborts the enclosing Git operation.
Scope {
    id: root

    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null
    property int maxResultCharacters: 131072

    property bool loading: false
    property bool busy: false
    property bool loaded: false
    property bool staged: false
    property string state: "READY"
    property string lastError: ""

    property string path: ""
    property string operationState: "NONE"
    property string baseSha: ""
    property string oursSha: ""
    property string theirsSha: ""
    property string baseText: ""
    property string oursText: ""
    property string theirsText: ""
    property string resultText: ""
    property var blocks: []
    property int selectedBlockIndex: -1

    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property bool pendingStage: false
    property string pendingPayloadJson: ""
    property string pendingJournalId: ""
    property bool pendingSuccess: false
    property string pendingDetail: ""

    property bool loadExitSeen: false
    property bool loadStdoutSeen: false
    property bool loadStderrSeen: false
    property int loadExitCode: -1
    property string loadStdout: ""
    property string loadStderr: ""

    property bool writeExitSeen: false
    property bool writeStdoutSeen: false
    property bool writeStderrSeen: false
    property int writeExitCode: -1
    property string writeStdout: ""
    property string writeStderr: ""

    signal loadedConflict(string path)
    signal resultSaved(string path, bool staged, bool success, string detail)

    readonly property int unresolvedCount: blocks.length
    readonly property bool hasMarkers: containsConflictMarkers(resultText)
    readonly property bool canStage:
        loaded
        && !busy
        && unresolvedCount === 0
        && !hasMarkers
        && resultText.length <= maxResultCharacters

    function cloneValue(value) {
        if (value === null || typeof value === "undefined")
            return null;

        try {
            return JSON.parse(JSON.stringify(value));
        } catch (error) {
            return null;
        }
    }

    function clear() {
        if (loading || busy)
            return false;

        loaded = false;
        staged = false;
        path = "";
        operationState = "NONE";
        baseSha = "";
        oursSha = "";
        theirsSha = "";
        baseText = "";
        oursText = "";
        theirsText = "";
        resultText = "";
        blocks = [];
        selectedBlockIndex = -1;
        state = "READY";
        lastError = "";
        return true;
    }

    function containsConflictMarkers(value) {
        const rows = String(value || "").split("\n");

        for (let i = 0; i < rows.length; ++i) {
            const line = String(rows[i] || "");

            if (line.indexOf("<<<<<<<") === 0
                    || line.indexOf("|||||||") === 0
                    || line === "======="
                    || line.indexOf(">>>>>>>") === 0)
                return true;
        }

        return false;
    }

    function parseConflictBlocks(value) {
        const rows = String(value || "").split("\n");
        const out = [];
        let i = 0;

        while (i < rows.length) {
            if (String(rows[i] || "").indexOf("<<<<<<<") !== 0) {
                i += 1;
                continue;
            }

            const start = i;
            i += 1;

            const ours = [];
            const base = [];
            const theirs = [];
            let section = "ours";
            let complete = false;

            while (i < rows.length) {
                const line = String(rows[i] || "");

                if (line.indexOf("|||||||") === 0) {
                    section = "base";
                    i += 1;
                    continue;
                }

                if (line === "=======") {
                    section = "theirs";
                    i += 1;
                    continue;
                }

                if (line.indexOf(">>>>>>>") === 0) {
                    complete = true;
                    break;
                }

                if (section === "ours")
                    ours.push(line);
                else if (section === "base")
                    base.push(line);
                else
                    theirs.push(line);

                i += 1;
            }

            if (!complete) {
                i = start + 1;
                continue;
            }

            out.push({
                index: out.length,
                startLine: start,
                endLine: i,
                oursLines: ours,
                baseLines: base,
                theirsLines: theirs,
                oursText: ours.join("\n"),
                baseText: base.join("\n"),
                theirsText: theirs.join("\n")
            });
            i += 1;
        }

        return out;
    }

    function updateParsedResult() {
        blocks = parseConflictBlocks(resultText);

        if (blocks.length <= 0)
            selectedBlockIndex = -1;
        else if (selectedBlockIndex < 0
                || selectedBlockIndex >= blocks.length)
            selectedBlockIndex = 0;
    }

    function setResultText(value) {
        if (!loaded || busy)
            return false;

        const text = String(value || "");

        if (text.length > maxResultCharacters) {
            lastError =
                "RESULT EXCEEDS "
                + String(maxResultCharacters)
                + " CHARACTER EDITOR LIMIT";
            return false;
        }

        resultText = text;
        staged = false;
        lastError = "";
        updateParsedResult();
        state =
            blocks.length > 0
            ? "CONFLICT // " + String(blocks.length) + " BLOCKS"
            : "RESULT // MARKERS CLEARED";
        return true;
    }

    function selectBlock(index) {
        const value = Number(index);

        if (value < 0 || value >= blocks.length)
            return false;

        selectedBlockIndex = value;
        return true;
    }

    function applyBlock(index, mode) {
        if (!loaded || busy)
            return false;

        const rowIndex = Number(index);
        const token = String(mode || "").toLowerCase();

        if (rowIndex < 0 || rowIndex >= blocks.length)
            return false;

        if (["ours", "theirs", "both", "base"].indexOf(token) < 0)
            return false;

        const block = blocks[rowIndex] || {};
        const rows = String(resultText || "").split("\n");
        let replacement = [];

        if (token === "ours")
            replacement = cloneValue(block.oursLines || []) || [];
        else if (token === "theirs")
            replacement = cloneValue(block.theirsLines || []) || [];
        else if (token === "base")
            replacement = cloneValue(block.baseLines || []) || [];
        else
            replacement =
                (cloneValue(block.oursLines || []) || [])
                .concat(cloneValue(block.theirsLines || []) || []);

        rows.splice(
            Number(block.startLine || 0),
            Number(block.endLine || 0)
                - Number(block.startLine || 0)
                + 1,
            ...replacement
        );

        resultText = rows.join("\n");
        updateParsedResult();

        if (blocks.length > 0)
            selectedBlockIndex =
                Math.min(rowIndex, blocks.length - 1);

        staged = false;
        state =
            blocks.length > 0
            ? "CONFLICT // " + String(blocks.length) + " BLOCKS"
            : "RESULT // MARKERS CLEARED";
        lastError = "";
        return true;
    }

    function takeOurs(index) {
        return applyBlock(index, "ours");
    }

    function takeTheirs(index) {
        return applyBlock(index, "theirs");
    }

    function takeBoth(index) {
        return applyBlock(index, "both");
    }

    function takeBase(index) {
        return applyBlock(index, "base");
    }

    function load(targetPath) {
        if (loading || busy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const filePath = String(targetPath || "").trim();

        if (!repo || !filePath) {
            state = "REFUSED";
            lastError =
                !repo
                ? "NO REPOSITORY"
                : "CONFLICT PATH REQUIRED";
            return false;
        }

        loading = true;
        loaded = false;
        staged = false;
        state = "LOADING THREE-WAY STAGES";
        lastError = "";

        loadExitSeen = false;
        loadStdoutSeen = false;
        loadStderrSeen = false;
        loadExitCode = -1;
        loadStdout = "";
        loadStderr = "";

        loadProcess.exec([
            "python3",
            "-c",
            loadScript(),
            repo,
            filePath,
            String(maxResultCharacters)
        ]);

        return true;
    }

    function loadScript() {
        return [
            'import json, os, subprocess, sys',
            'repo, path, limit_text = sys.argv[1:4]',
            'limit = int(limit_text)',
            'def run(*args): return subprocess.run(["git", "-C", repo] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg): print("REFUSED\\t" + msg); sys.exit(1)',
            'if run("rev-parse", "--is-inside-work-tree").returncode: refuse("NOT A GIT WORKTREE")',
            'gd = text(run("rev-parse", "--git-dir"))',
            'if not os.path.isabs(gd): gd = os.path.join(repo, gd)',
            'state = "NONE"',
            'if os.path.isfile(os.path.join(gd, "MERGE_HEAD")): state = "MERGE"',
            'elif os.path.isdir(os.path.join(gd, "rebase-merge")) or os.path.isdir(os.path.join(gd, "rebase-apply")): state = "REBASE"',
            'elif os.path.isfile(os.path.join(gd, "CHERRY_PICK_HEAD")): state = "CHERRY_PICK"',
            'elif os.path.isfile(os.path.join(gd, "REVERT_HEAD")): state = "REVERT"',
            'raw = run("ls-files", "-u", "--", path)',
            'if raw.returncode: refuse("UNMERGED INDEX CANNOT BE READ")',
            'entries = {}',
            'for line in raw.stdout.decode("utf-8", "surrogateescape").splitlines():',
            '    left, sep, entry_path = line.partition("\\t")',
            '    fields = left.split()',
            '    if not sep or len(fields) < 3: continue',
            '    entries[int(fields[2])] = fields[1]',
            'if 2 not in entries and 3 not in entries: refuse("PATH IS NOT AN UNMERGED TEXT CONFLICT")',
            'def stage_bytes(stage):',
            '    if stage not in entries: return b""',
            '    proc = run("show", ":" + str(stage) + ":" + path)',
            '    if proc.returncode: refuse("CONFLICT STAGE " + str(stage) + " CANNOT BE READ")',
            '    return proc.stdout',
            'payload = {}',
            'for key, stage in (("base", 1), ("ours", 2), ("theirs", 3)):',
            '    data = stage_bytes(stage)',
            '    if b"\\x00" in data: refuse("RICH CONFLICT EDITOR DOES NOT SUPPORT BINARY CONTENT")',
            '    try: value = data.decode("utf-8")',
            '    except UnicodeDecodeError: refuse("RICH CONFLICT EDITOR REQUIRES UTF-8 TEXT")',
            '    if len(value) > limit: refuse("CONFLICT STAGE EXCEEDS EDITOR LIMIT")',
            '    payload[key] = value',
            'target = os.path.join(repo, path)',
            'try:',
            '    data = open(target, "rb").read() if os.path.isfile(target) else b""',
            'except OSError as exc: refuse("WORKTREE RESULT CANNOT BE READ // " + str(exc))',
            'if b"\\x00" in data: refuse("RICH CONFLICT EDITOR DOES NOT SUPPORT BINARY RESULT")',
            'try: result = data.decode("utf-8")',
            'except UnicodeDecodeError: refuse("RICH CONFLICT EDITOR REQUIRES UTF-8 RESULT")',
            'if len(result) > limit: refuse("WORKTREE RESULT EXCEEDS EDITOR LIMIT")',
            'payload.update({"path": path, "operationState": state, "stage1": entries.get(1, ""), "stage2": entries.get(2, ""), "stage3": entries.get(3, ""), "result": result})',
            'print("JSON\\t" + json.dumps(payload, separators=(",", ":")))'
        ].join("\n");
    }

    function maybeFinishLoad() {
        if (!loading
                || !loadExitSeen
                || !loadStdoutSeen
                || !loadStderrSeen)
            return;

        loading = false;

        const out = String(loadStdout || "").trim();
        const err = String(loadStderr || "").trim();
        const rows = out.split("\n");
        let payload = null;
        let refused = "";

        for (let i = 0; i < rows.length; ++i) {
            const line = String(rows[i] || "");

            if (line.indexOf("JSON\t") === 0) {
                try {
                    payload = JSON.parse(line.slice(5));
                } catch (error) {
                    payload = null;
                }
            } else if (line.indexOf("REFUSED\t") === 0) {
                refused = line.slice(8);
            }
        }

        if (loadExitCode !== 0 || !payload) {
            loaded = false;
            state = "REFUSED";
            lastError =
                refused
                || err
                || out
                || ("CONFLICT LOAD EXIT " + loadExitCode);
            return;
        }

        path = String(payload.path || "");
        operationState = String(payload.operationState || "NONE");
        baseSha = String(payload.stage1 || "");
        oursSha = String(payload.stage2 || "");
        theirsSha = String(payload.stage3 || "");
        baseText = String(payload.base || "");
        oursText = String(payload.ours || "");
        theirsText = String(payload.theirs || "");
        resultText = String(payload.result || "");
        loaded = true;
        staged = false;
        selectedBlockIndex = -1;
        updateParsedResult();
        state =
            blocks.length > 0
            ? "CONFLICT // "
                + String(blocks.length)
                + " BLOCK"
                + (blocks.length === 1 ? "" : "S")
            : "RESULT // NO MARKER BLOCKS";
        lastError = "";
        loadedConflict(path);
    }

    function journalContext(stageResult) {
        return {
            source: "GitConflictEditorService",
            operation:
                stageResult
                ? "CONFLICT_RESOLVE"
                : "CONFLICT_DRAFT",
            path: path,
            operationState: operationState,
            stage1: baseSha,
            stage2: oursSha,
            stage3: theirsSha,
            stageResolved: Boolean(stageResult),
            unresolvedBefore: unresolvedCount
        };
    }

    function saveResult(stageResult) {
        if (!loaded || loading || busy)
            return false;

        if (!operationJournal || !snapshotService) {
            state = "REFUSED";
            lastError =
                "CONFLICT EDITOR REQUIRES JOURNAL + SNAPSHOT SERVICES";
            return false;
        }

        if (resultText.length > maxResultCharacters) {
            state = "REFUSED";
            lastError = "RESULT EXCEEDS EDITOR LIMIT";
            return false;
        }

        if (stageResult
                && (
                    unresolvedCount > 0
                    || containsConflictMarkers(resultText)
                )) {
            state = "REFUSED";
            lastError =
                "CANNOT STAGE RESULT WHILE CONFLICT MARKERS REMAIN";
            return false;
        }

        pendingStage = Boolean(stageResult);
        pendingPayloadJson = JSON.stringify({
            result: resultText,
            stage1: baseSha,
            stage2: oursSha,
            stage3: theirsSha,
            stage: Boolean(stageResult)
        });
        pendingJournalId = "";
        pendingSuccess = false;
        pendingDetail = "";

        busy = true;
        state =
            pendingStage
            ? "SNAPSHOT BEFORE // STAGE RESOLUTION"
            : "SNAPSHOT BEFORE // SAVE DRAFT";
        lastError = "";
        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            pendingStage
            ? "CHANGES BEFORE // CONFLICT RESOLVE"
            : "CHANGES BEFORE // CONFLICT DRAFT",
            journalContext(pendingStage)
        );

        if (!pendingSnapshotRequest) {
            busy = false;
            snapshotPhase = "";
            state = "REFUSED";
            lastError = "BEFORE SNAPSHOT COULD NOT START";
            return false;
        }

        return true;
    }

    function saveDraft() {
        return saveResult(false);
    }

    function stageResolved() {
        return saveResult(true);
    }

    function startWrite() {
        writeExitSeen = false;
        writeStdoutSeen = false;
        writeStderrSeen = false;
        writeExitCode = -1;
        writeStdout = "";
        writeStderr = "";
        state =
            pendingStage
            ? "WRITING + STAGING RESULT"
            : "WRITING RESULT DRAFT";

        writeProcess.exec([
            "python3",
            "-c",
            writeScript(),
            String(repositoryPath || ""),
            path,
            pendingPayloadJson
        ]);
    }

    function writeScript() {
        return [
            'import json, os, re, subprocess, sys',
            'repo, path, payload_json = sys.argv[1:4]',
            'def run(*args): return subprocess.run(["git", "-C", repo] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def refuse(msg): print("REFUSED\\t" + msg); sys.exit(1)',
            'try: payload = json.loads(payload_json)',
            'except Exception: refuse("RESULT PAYLOAD JSON INVALID")',
            'expected = {1: str(payload.get("stage1", "")), 2: str(payload.get("stage2", "")), 3: str(payload.get("stage3", ""))}',
            'raw = run("ls-files", "-u", "--", path)',
            'if raw.returncode: refuse("UNMERGED INDEX CANNOT BE READ")',
            'actual = {}',
            'for line in raw.stdout.decode("utf-8", "surrogateescape").splitlines():',
            '    left, sep, entry_path = line.partition("\\t"); fields = left.split()',
            '    if sep and len(fields) >= 3: actual[int(fields[2])] = fields[1]',
            'for stage in (1, 2, 3):',
            '    if actual.get(stage, "") != expected.get(stage, ""): refuse("CONFLICT STAGES CHANGED SINCE EDITOR LOAD")',
            'result = str(payload.get("result", "")); stage_result = bool(payload.get("stage", False))',
            'if stage_result and re.search(r"(?m)^(<<<<<<<|\\|\\|\\|\\|\\|\\||=======|>>>>>>>)", result): refuse("CONFLICT MARKERS REMAIN IN RESULT")',
            'target = os.path.join(repo, path)',
            'parent = os.path.dirname(target)',
            'if parent: os.makedirs(parent, exist_ok=True)',
            'try:',
            '    with open(target, "w", encoding="utf-8", newline="") as handle: handle.write(result)',
            'except OSError as exc: refuse("RESULT WRITE FAILED // " + str(exc))',
            'if stage_result:',
            '    added = run("add", "--", path)',
            '    if added.returncode: refuse("RESULT STAGE FAILED // " + added.stderr.decode("utf-8", "replace").strip())',
            '    remaining = run("ls-files", "-u", "--", path)',
            '    if remaining.returncode or remaining.stdout.strip(): refuse("PATH REMAINS UNMERGED AFTER STAGE")',
            '    print("OK\\tSTAGED RESOLVED RESULT // " + path)',
            'else:',
            '    print("OK\\tSAVED RESULT DRAFT // " + path)'
        ].join("\n");
    }

    function maybeFinishWrite() {
        if (!busy
                || !writeExitSeen
                || !writeStdoutSeen
                || !writeStderrSeen)
            return;

        const out = String(writeStdout || "").trim();
        const err = String(writeStderr || "").trim();
        const rows = out.split("\n");
        let control = "";

        for (let i = rows.length - 1; i >= 0; --i) {
            const line = String(rows[i] || "");

            if (line.indexOf("OK\t") === 0
                    || line.indexOf("REFUSED\t") === 0) {
                control = line;
                break;
            }
        }

        const fields = control.split("\t");
        pendingSuccess =
            writeExitCode === 0
            && fields[0] === "OK";
        pendingDetail =
            fields.length > 1
            ? fields.slice(1).join("\t")
            : String(
                err
                || out
                || ("CONFLICT WRITE EXIT " + writeExitCode)
              ).trim();

        state = "SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            pendingStage
            ? "CHANGES AFTER // CONFLICT RESOLVE"
            : "CHANGES AFTER // CONFLICT DRAFT",
            journalContext(pendingStage)
        );

        if (!pendingSnapshotRequest)
            finalizeWrite(null, "AFTER SNAPSHOT COULD NOT START");
    }

    function finalizeWrite(afterSnapshot, warningText) {
        const warning = String(warningText || "");
        const snapshot =
            afterSnapshot
            || {
                snapshotVersion: 1,
                repository: String(repositoryPath || ""),
                capturedAt: new Date().toISOString(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason:
                    warning || "CONFLICT EDITOR AFTER SNAPSHOT UNAVAILABLE"
            };
        const detail =
            String(pendingDetail || "")
            + (warning ? " // " + warning : "");

        if (pendingJournalId && operationJournal) {
            if (pendingSuccess)
                operationJournal.completeOperation(
                    pendingJournalId,
                    snapshot,
                    detail
                );
            else
                operationJournal.failOperation(
                    pendingJournalId,
                    snapshot,
                    detail
                );
        }

        const success = pendingSuccess;
        const didStage = pendingStage;

        busy = false;
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        pendingJournalId = "";
        pendingPayloadJson = "";
        pendingSuccess = false;
        pendingDetail = "";

        if (success) {
            staged = didStage;
            state =
                didStage
                ? "RESOLVED // STAGED"
                : (
                    blocks.length > 0
                    ? "DRAFT SAVED // CONFLICTS REMAIN"
                    : "DRAFT SAVED // MARKERS CLEARED"
                  );
            lastError = warning;
        } else {
            state = "REFUSED";
            lastError = detail || "CONFLICT RESULT WRITE FAILED";
        }

        resultSaved(path, didStage, success, detail);
    }

    Connections {
        target: root.snapshotService
        enabled: root.snapshotService !== null
        ignoreUnknownSignals: true

        function onSnapshotReady(requestId, snapshot) {
            if (String(requestId || "")
                    !== String(root.pendingSnapshotRequest || ""))
                return;

            root.pendingSnapshotRequest = "";

            if (root.snapshotPhase === "BEFORE") {
                root.snapshotPhase = "";
                root.pendingJournalId =
                    root.operationJournal.beginOperation(
                        root.pendingStage
                        ? "CHANGES/CONFLICT_RESOLVE"
                        : "CHANGES/CONFLICT_DRAFT",
                        snapshot,
                        root.journalContext(root.pendingStage)
                    );

                if (!root.pendingJournalId) {
                    root.busy = false;
                    root.state = "REFUSED";
                    root.lastError =
                        "CONFLICT EDITOR JOURNAL RECORD COULD NOT START";
                    return;
                }

                root.startWrite();
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeWrite(snapshot, "");
            }
        }

        function onSnapshotFailed(requestId, detail) {
            if (String(requestId || "")
                    !== String(root.pendingSnapshotRequest || ""))
                return;

            root.pendingSnapshotRequest = "";

            if (root.snapshotPhase === "BEFORE") {
                root.snapshotPhase = "";
                root.busy = false;
                root.state = "REFUSED";
                root.lastError =
                    "CONFLICT EDITOR BEFORE SNAPSHOT FAILED // "
                    + String(detail || "UNKNOWN ERROR");
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeWrite(
                    null,
                    "AFTER SNAPSHOT FAILED // "
                        + String(detail || "UNKNOWN ERROR")
                );
            }
        }
    }

    Process {
        id: loadProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.loadStdout = this.text;
                root.loadStdoutSeen = true;
                root.maybeFinishLoad();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.loadStderr = this.text;
                root.loadStderrSeen = true;
                root.maybeFinishLoad();
            }
        }

        onExited: function(code, exitStatus) {
            root.loadExitCode = Number(code);
            root.loadExitSeen = true;
            root.maybeFinishLoad();
        }
    }

    Process {
        id: writeProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.writeStdout = this.text;
                root.writeStdoutSeen = true;
                root.maybeFinishWrite();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.writeStderr = this.text;
                root.writeStderrSeen = true;
                root.maybeFinishWrite();
            }
        }

        onExited: function(code, exitStatus) {
            root.writeExitCode = Number(code);
            root.writeExitSeen = true;
            root.maybeFinishWrite();
        }
    }
}
