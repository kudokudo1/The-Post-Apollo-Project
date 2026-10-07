import QtQuick
import Quickshell
import Quickshell.Io

// Guarded transfer of one selected WORKTREE +/- line between existing
// worktrees of the same repository. Whole-file and hunk transfer remain in
// GitChangeTransferService.
Scope {
    id: root

    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null

    property bool previewBusy: false
    property bool transferBusy: false
    property string status: "LINE TRANSFER // READY"
    property string lastError: ""

    property string destinationPath: ""
    property string transferMode: "move"
    property string filePath: ""
    property int hunkIndex: -1
    property int lineIndex: -1
    property string fingerprint: ""
    property string patchBase64: ""
    property int maxRecoveryPatchBytes: 524288
    property string sourceBranch: ""
    property string destinationBranch: ""
    property string sourceHead: ""
    property string destinationHead: ""
    property int patchBytes: 0
    property int patchLines: 0

    property string processPhase: ""
    property bool processExitSeen: false
    property bool processStdoutSeen: false
    property bool processStderrSeen: false
    property int processExitCode: -1
    property string processStdout: ""
    property string processStderr: ""

    property string pendingDestination: ""
    property string pendingMode: "move"
    property string pendingFile: ""
    property int pendingHunk: -1
    property int pendingLine: -1

    property string pendingJournalId: ""
    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property bool pendingSuccess: false
    property string pendingDetail: ""

    signal previewReady(var preview)
    signal previewFailed(string detail)
    signal transferFinished(bool success, string detail)

    readonly property bool hasPreview:
        fingerprint.length > 0
        && destinationPath.length > 0
        && filePath.length > 0
        && hunkIndex >= 0
        && lineIndex >= 0

    function normalizeMode(mode) {
        return String(mode || "").toLowerCase() === "copy"
            ? "copy"
            : "move";
    }

    function safePath(value) {
        const path = String(value || "").trim();

        if (!path
                || path.charAt(0) === "/"
                || path === ".."
                || path.indexOf("../") === 0
                || path.indexOf("/../") >= 0)
            return "";

        return path;
    }

    function clearPreview() {
        destinationPath = "";
        transferMode = "move";
        filePath = "";
        hunkIndex = -1;
        lineIndex = -1;
        fingerprint = "";
        patchBase64 = "";
        sourceBranch = "";
        destinationBranch = "";
        sourceHead = "";
        destinationHead = "";
        patchBytes = 0;
        patchLines = 0;
    }

    function contentRecoverable() {
        return patchBase64.length > 0
            && patchBytes > 0
            && patchBytes <= maxRecoveryPatchBytes;
    }

    function context() {
        return {
            source: "GitLineTransferService",
            operation: "TRANSFER_LINE",
            scope: "line",
            mode: String(transferMode || "move"),
            sourcePath: String(repositoryPath || ""),
            destinationPath: String(destinationPath || ""),
            file: String(filePath || ""),
            hunkIndex: Number(hunkIndex),
            lineIndex: Number(lineIndex),
            fingerprint: String(fingerprint || ""),
            patchBytes: Number(patchBytes || 0),
            patchBase64:
                contentRecoverable()
                ? String(patchBase64 || "")
                : "",
            sourceBranch: String(sourceBranch || ""),
            destinationBranch: String(destinationBranch || ""),
            sourceHead: String(sourceHead || ""),
            destinationHead: String(destinationHead || ""),
            recoveryClass:
                contentRecoverable()
                ? "CONTENT_RECOVERABLE"
                : "EVIDENCE_ONLY"
        };
    }

    function evidenceSnapshot(snapshot) {
        let out = {};

        try {
            out = JSON.parse(JSON.stringify(snapshot || {}));
        } catch (error) {
            out = {};
        }

        if (contentRecoverable()) {
            out.recoveryClass = "CONTENT_RECOVERABLE";
            out.recoveryReason =
                "EXACT LINE TRANSFER PATCH STORED IN JOURNAL";
        } else {
            out.recoveryClass = "EVIDENCE_ONLY";
            out.recoveryReason =
                patchBytes > maxRecoveryPatchBytes
                ? "LINE TRANSFER PATCH EXCEEDS RECOVERY PAYLOAD LIMIT"
                : "LINE TRANSFER RECOVERY PAYLOAD UNAVAILABLE";
        }
        return out;
    }

    function engineScript() {
        return [
            'import base64, difflib, hashlib, os, re, subprocess, sys',
            'phase, source, destination, mode, path, hi, li, expected, esh, edh = sys.argv[1:11]',
            'hunk_index, line_index = int(hi), int(li)',
            'def run(args, cwd=None, data=None):',
            '    return subprocess.run(args, cwd=cwd, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def git(repo, *args): return run(["git", "-C", repo] + list(args))',
            'def text(p): return p.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg, code=1): print("REFUSED\\t" + msg); sys.exit(code)',
            'source, destination = os.path.realpath(source), os.path.realpath(destination)',
            'if source == destination: refuse("SOURCE AND DESTINATION ARE THE SAME WORKTREE")',
            'for repo, label in ((source, "SOURCE"), (destination, "DESTINATION")):',
            '    if git(repo, "rev-parse", "--is-inside-work-tree").returncode != 0: refuse(label + " IS NOT A GIT WORKTREE")',
            'def common(repo):',
            '    p = git(repo, "rev-parse", "--git-common-dir")',
            '    if p.returncode: refuse("COMMON GIT DIR UNAVAILABLE")',
            '    value = text(p)',
            '    if not os.path.isabs(value): value = os.path.join(repo, value)',
            '    return os.path.realpath(value)',
            'if common(source) != common(destination): refuse("DESTINATION BELONGS TO A DIFFERENT REPOSITORY")',
            'src_branch, dst_branch = text(git(source, "branch", "--show-current")), text(git(destination, "branch", "--show-current"))',
            'src_head, dst_head = text(git(source, "rev-parse", "HEAD")), text(git(destination, "rev-parse", "HEAD"))',
            'if not src_branch: refuse("SOURCE WORKTREE IS DETACHED")',
            'if not dst_branch: refuse("DESTINATION WORKTREE IS DETACHED")',
            'if src_branch == dst_branch: refuse("SOURCE AND DESTINATION USE THE SAME BRANCH")',
            'def active(repo):',
            '    gd = text(git(repo, "rev-parse", "--git-dir"))',
            '    if not os.path.isabs(gd): gd = os.path.join(repo, gd)',
            '    if os.path.isfile(os.path.join(gd, "MERGE_HEAD")): return "MERGE"',
            '    if os.path.isdir(os.path.join(gd, "rebase-merge")) or os.path.isdir(os.path.join(gd, "rebase-apply")): return "REBASE"',
            '    if os.path.isfile(os.path.join(gd, "CHERRY_PICK_HEAD")): return "CHERRY_PICK"',
            '    if os.path.isfile(os.path.join(gd, "REVERT_HEAD")): return "REVERT"',
            '    return "NONE"',
            'if active(source) != "NONE": refuse("SOURCE HAS AN ACTIVE GIT OPERATION")',
            'if active(destination) != "NONE": refuse("DESTINATION HAS AN ACTIVE GIT OPERATION")',
            'if git(destination, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("DESTINATION WORKTREE IS NOT CLEAN")',
            'if git(source, "ls-files", "--error-unmatch", "--", path).returncode: refuse("UNTRACKED OR UNKNOWN SOURCE PATH // " + path)',
            'if git(source, "ls-files", "-u", "--", path).stdout.strip(): refuse("CONFLICTED SOURCE PATH // " + path)',
            'cached = git(source, "diff", "--cached", "--quiet", "--", path).returncode',
            'if cached != 0: refuse("SELECTED PATH HAS STAGED CHANGES" if cached == 1 else "STAGED DIFF CHECK FAILED")',
            'if phase == "execute":',
            '    if src_head != esh: refuse("SOURCE HEAD CHANGED SINCE PREVIEW")',
            '    if dst_head != edh: refuse("DESTINATION HEAD CHANGED SINCE PREVIEW")',
            'diffp = git(source, "diff", "--no-ext-diff", "--", path)',
            'if diffp.returncode: sys.stderr.buffer.write(diffp.stderr); sys.exit(diffp.returncode)',
            'lines = diffp.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
            'hunks, current = [], None',
            'for raw in lines:',
            '    if raw.startswith("@@"):',
            '        if current is not None: hunks.append(current)',
            '        current = [raw]',
            '    elif current is not None: current.append(raw)',
            'if current is not None: hunks.append(current)',
            'if hunk_index < 0 or hunk_index >= len(hunks): refuse("HUNK NOT FOUND")',
            'hunk, body = hunks[hunk_index], hunks[hunk_index][1:]',
            'if line_index < 0 or line_index >= len(body): refuse("LINE NOT FOUND")',
            'selected = body[line_index]',
            'if not selected or selected[0] not in "+-": refuse("LINE IS NOT A CHANGE")',
            'm = re.match(r"^@@ -(\\d+)(?:,(\\d+))? \\+(\\d+)(?:,(\\d+))? @@", hunk[0])',
            'if not m: refuse("HUNK HEADER INVALID")',
            'old_cursor, new_cursor, selected_old = int(m.group(1)), int(m.group(3)), 0',
            'for idx, raw in enumerate(body):',
            '    prefix = raw[:1]',
            '    if idx == line_index: selected_old = old_cursor; break',
            '    if prefix == " ": old_cursor += 1; new_cursor += 1',
            '    elif prefix == "-": old_cursor += 1',
            '    elif prefix == "+": new_cursor += 1',
            'basep = git(source, "show", ":" + path)',
            'if basep.returncode: sys.stderr.buffer.write(basep.stderr); sys.exit(basep.returncode)',
            'base = basep.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
            'target = list(base); pos = max(0, selected_old - 1)',
            'if selected[0] == "+": target.insert(min(pos, len(target)), selected[1:])',
            'else:',
            '    if pos >= len(target): refuse("SOURCE LINE OUT OF RANGE")',
            '    target.pop(pos)',
            'patch = "".join(difflib.unified_diff(base, target, fromfile="a/" + path, tofile="b/" + path, n=3)).encode("utf-8", "surrogateescape")',
            'if not patch: refuse("NO LINE PATCH PRODUCED")',
            'fingerprint = hashlib.sha256(patch).hexdigest()',
            'check = run(["git", "-C", destination, "apply", "--check", "--whitespace=nowarn", "-"], data=patch)',
            'if check.returncode: refuse("LINE DOES NOT APPLY CLEANLY TO DESTINATION")',
            'if mode == "move":',
            '    reverse = run(["git", "-C", source, "apply", "-R", "--check", "--whitespace=nowarn", "-"], data=patch)',
            '    if reverse.returncode: refuse("SOURCE LINE CANNOT BE REMOVED CLEANLY")',
            'if phase == "preview":',
            '    if len(patch) <= 524288: print("PATCH64\\t" + base64.b64encode(patch).decode("ascii"))',
            '    print("PREVIEW\\t{}\\t{}\\t{}\\t{}\\t{}\\t{}\\t{}\\t{}".format(fingerprint, len(patch), patch.count(b"\\n"), src_branch, dst_branch, src_head, dst_head, mode))',
            '    sys.exit(0)',
            'if fingerprint != expected: refuse("SOURCE LINE CHANGED SINCE PREVIEW")',
            'apply = run(["git", "-C", destination, "apply", "--whitespace=nowarn", "-"], data=patch)',
            'if apply.returncode: refuse("DESTINATION LINE APPLY FAILED")',
            'if mode == "move":',
            '    remove = run(["git", "-C", source, "apply", "-R", "--whitespace=nowarn", "-"], data=patch)',
            '    if remove.returncode:',
            '        rollback = run(["git", "-C", destination, "apply", "-R", "--whitespace=nowarn", "-"], data=patch)',
            '        if rollback.returncode: refuse("SOURCE LINE REMOVE FAILED // DESTINATION ROLLBACK FAILED", 9)',
            '        refuse("SOURCE LINE REMOVE FAILED // DESTINATION ROLLED BACK", 8)',
            '    print("OK\\tMOVED LINE // {} // HUNK {} // LINE {}".format(path, hunk_index, line_index))',
            'else: print("OK\\tCOPIED LINE // {} // HUNK {} // LINE {}".format(path, hunk_index, line_index))'
        ].join("\n");
    }

    function startProcess(phase, destination, path, hunk, line, mode) {
        processPhase = phase;
        processExitSeen = false;
        processStdoutSeen = false;
        processStderrSeen = false;
        processExitCode = -1;
        processStdout = "";
        processStderr = "";

        process.exec([
            "python3",
            "-c",
            engineScript(),
            phase,
            String(repositoryPath || ""),
            String(destination || ""),
            normalizeMode(mode),
            String(path || ""),
            String(hunk),
            String(line),
            phase === "execute" ? fingerprint : "",
            phase === "execute" ? sourceHead : "",
            phase === "execute" ? destinationHead : ""
        ]);
    }

    function preview(destination, path, hunk, line, mode) {
        if (previewBusy || transferBusy)
            return false;

        const target = safePath(path);
        const hi = Number(hunk);
        const li = Number(line);

        clearPreview();
        lastError = "";

        if (!String(repositoryPath || "").trim()
                || !String(destination || "").trim()
                || !target
                || !Number.isInteger(hi)
                || hi < 0
                || !Number.isInteger(li)
                || li < 0) {
            lastError = "LINE TRANSFER // INVALID PREVIEW TARGET";
            status = "LINE TRANSFER // REFUSED";
            previewFailed(lastError);
            return false;
        }

        pendingDestination = String(destination);
        pendingMode = normalizeMode(mode);
        pendingFile = target;
        pendingHunk = hi;
        pendingLine = li;

        previewBusy = true;
        status = "LINE TRANSFER // PREVIEWING";
        startProcess("preview", destination, target, hi, li, mode);
        return true;
    }

    function execute() {
        if (previewBusy || transferBusy || !hasPreview)
            return false;

        if ((operationJournal && !snapshotService)
                || (snapshotService && !operationJournal)) {
            lastError = "JOURNAL + SNAPSHOT SERVICES MUST BE PAIRED";
            return false;
        }

        transferBusy = true;
        pendingSuccess = false;
        pendingDetail = "";
        status = "LINE TRANSFER // SNAPSHOT BEFORE";

        if (!operationJournal && !snapshotService) {
            startProcess(
                "execute",
                destinationPath,
                filePath,
                hunkIndex,
                lineIndex,
                transferMode
            );
            return true;
        }

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "CHANGES BEFORE // TRANSFER LINE",
            context()
        );

        if (!pendingSnapshotRequest) {
            failBeforeSnapshot("SNAPSHOT SERVICE BUSY OR UNAVAILABLE");
            return false;
        }

        return true;
    }

    function failBeforeSnapshot(detail) {
        transferBusy = false;
        snapshotPhase = "";
        pendingSnapshotRequest = "";
        lastError =
            "LINE TRANSFER BEFORE SNAPSHOT FAILED // "
            + String(detail || "UNKNOWN ERROR");
        status = "LINE TRANSFER // REFUSED";
        transferFinished(false, lastError);
    }

    function finishProcess() {
        if (!processExitSeen || !processStdoutSeen || !processStderrSeen)
            return;

        const out = String(processStdout || "").trim();
        const err = String(processStderr || "").trim();
        const rows = out.split("\n");
        let control = "";
        let recoveryPayload = "";

        for (let i = 0; i < rows.length; ++i) {
            if (rows[i].indexOf("PATCH64\t") === 0)
                recoveryPayload = rows[i].slice(8);
        }

        for (let i = rows.length - 1; i >= 0; --i) {
            if (rows[i].indexOf("PREVIEW\t") === 0
                    || rows[i].indexOf("OK\t") === 0
                    || rows[i].indexOf("REFUSED\t") === 0) {
                control = rows[i];
                break;
            }
        }

        const fields = control.split("\t");

        if (processPhase === "preview") {
            previewBusy = false;

            if (processExitCode !== 0
                    || fields.length < 9
                    || fields[0] !== "PREVIEW") {
                clearPreview();
                lastError =
                    fields[0] === "REFUSED"
                    ? fields.slice(1).join("\t")
                    : String(err || out || ("PREVIEW EXIT " + processExitCode));
                status = "LINE TRANSFER // REFUSED";
                previewFailed(lastError);
                return;
            }

            fingerprint = fields[1];
            patchBase64 = recoveryPayload;
            patchBytes = Number(fields[2] || 0);
            patchLines = Number(fields[3] || 0);
            sourceBranch = fields[4];
            destinationBranch = fields[5];
            sourceHead = fields[6];
            destinationHead = fields[7];
            transferMode = normalizeMode(fields[8]);
            destinationPath = pendingDestination;
            filePath = pendingFile;
            hunkIndex = pendingHunk;
            lineIndex = pendingLine;
            status = "LINE TRANSFER // PREVIEW READY";
            lastError = "";

            previewReady({
                scope: "line",
                destinationPath: destinationPath,
                file: filePath,
                hunkIndex: hunkIndex,
                lineIndex: lineIndex,
                mode: transferMode,
                fingerprint: fingerprint,
                recoveryClass:
                    contentRecoverable()
                    ? "CONTENT_RECOVERABLE"
                    : "EVIDENCE_ONLY",
                sourceHead: sourceHead,
                destinationHead: destinationHead,
                patchBytes: patchBytes,
                patchLines: patchLines
            });
            return;
        }

        pendingSuccess =
            processExitCode === 0
            && fields.length > 0
            && fields[0] === "OK";
        pendingDetail =
            fields.length > 1
            ? fields.slice(1).join("\t")
            : String(err || out || ("EXECUTE EXIT " + processExitCode));

        if (!operationJournal || !snapshotService) {
            finalizeTransfer(null, "");
            return;
        }

        status = "LINE TRANSFER // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "CHANGES AFTER // TRANSFER LINE",
            context()
        );

        if (!pendingSnapshotRequest)
            finalizeTransfer(null, "AFTER SNAPSHOT COULD NOT START");
    }

    function finalizeTransfer(afterSnapshot, warningText) {
        const warning = String(warningText || "");
        const snapshot =
            afterSnapshot
            ? evidenceSnapshot(afterSnapshot)
            : {
                snapshotVersion: 1,
                repository: String(repositoryPath || ""),
                capturedAt: new Date().toISOString(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason:
                    warning || "LINE TRANSFER AFTER SNAPSHOT UNAVAILABLE"
            };

        if (pendingJournalId && operationJournal) {
            if (pendingSuccess)
                operationJournal.completeOperation(
                    pendingJournalId,
                    snapshot,
                    pendingDetail + (warning ? " // " + warning : "")
                );
            else
                operationJournal.failOperation(
                    pendingJournalId,
                    snapshot,
                    pendingDetail + (warning ? " // " + warning : "")
                );
        }

        const success = pendingSuccess;
        const detail =
            pendingDetail
            + (warning ? " // " + warning : "");

        transferBusy = false;
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";

        if (success) {
            status =
                warning
                ? "LINE TRANSFER // COMPLETE // SNAPSHOT WARNING"
                : "LINE TRANSFER // COMPLETE";
            lastError = warning;
            clearPreview();
        } else {
            status = "LINE TRANSFER // REFUSED";
            lastError = detail || "LINE TRANSFER FAILED";
        }

        transferFinished(success, detail);
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
                    root.operationJournal
                    ? root.operationJournal.beginOperation(
                        "CHANGES/TRANSFER_LINE",
                        root.evidenceSnapshot(snapshot),
                        root.context()
                    )
                    : "";

                if (root.operationJournal
                        && !root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "JOURNAL RECORD COULD NOT START"
                    );
                    return;
                }

                root.status = "LINE TRANSFER // EXECUTING";
                root.startProcess(
                    "execute",
                    root.destinationPath,
                    root.filePath,
                    root.hunkIndex,
                    root.lineIndex,
                    root.transferMode
                );
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeTransfer(snapshot, "");
            }
        }

        function onSnapshotFailed(requestId, detail) {
            if (String(requestId || "")
                    !== String(root.pendingSnapshotRequest || ""))
                return;

            root.pendingSnapshotRequest = "";

            if (root.snapshotPhase === "BEFORE") {
                root.snapshotPhase = "";
                root.failBeforeSnapshot(detail);
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeTransfer(
                    null,
                    "AFTER SNAPSHOT FAILED // "
                        + String(detail || "UNKNOWN ERROR")
                );
            }
        }
    }

    Process {
        id: process

        stdout: StdioCollector {
            onStreamFinished: {
                root.processStdout = this.text;
                root.processStdoutSeen = true;
                root.finishProcess();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.processStderr = this.text;
                root.processStderrSeen = true;
                root.finishProcess();
            }
        }

        onExited: function(code, exitStatus) {
            root.processExitCode = Number(code);
            root.processExitSeen = true;
            root.finishProcess();
        }
    }
}
