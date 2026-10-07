import QtQuick
import Quickshell
import Quickshell.Io

// Absorb staged tracked changes into an earlier commit.
//
// First slice is deliberately strict: staged tracked changes only, no
// unstaged/untracked/conflicted content, target must be an earlier non-merge
// commit on the current linear history, exact patch <= 512 KiB.
Scope {
    id: root

    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null
    property int maxRecoveryPatchBytes: 524288

    property bool previewBusy: false
    property bool executionBusy: false
    property string state: "READY"
    property string lastError: ""

    property string branchName: ""
    property string headSha: ""
    property string baseSha: ""
    property string targetSha: ""
    property string targetSubject: ""
    property var files: []
    property string patchBase64: ""
    property string fingerprint: ""
    property int patchBytes: 0

    property bool armed: false
    property string armedPlanJson: ""

    property string pendingJournalId: ""
    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property bool pendingExecutionSuccess: false
    property string pendingExecutionDetail: ""
    property string pendingNewHead: ""

    property bool previewExitSeen: false
    property bool previewStdoutSeen: false
    property bool previewStderrSeen: false
    property int previewExitCode: -1
    property string previewStdout: ""
    property string previewStderr: ""

    property bool executeExitSeen: false
    property bool executeStdoutSeen: false
    property bool executeStderrSeen: false
    property int executeExitCode: -1
    property string executeStdout: ""
    property string executeStderr: ""

    signal previewReady()
    signal executionFinished(bool success, string detail, string newHead)

    function cloneValue(value) {
        try {
            return JSON.parse(JSON.stringify(value || []));
        } catch (error) {
            return [];
        }
    }

    function clear() {
        if (previewBusy || executionBusy)
            return false;

        branchName = "";
        headSha = "";
        baseSha = "";
        targetSha = "";
        targetSubject = "";
        files = [];
        patchBase64 = "";
        fingerprint = "";
        patchBytes = 0;
        armed = false;
        armedPlanJson = "";
        state = "READY";
        lastError = "";
        return true;
    }

    function disarm(reason) {
        armed = false;
        armedPlanJson = "";
        if (reason)
            state = "ABSORB // " + String(reason);
    }

    function preview(target) {
        if (previewBusy || executionBusy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const targetInput = String(target || "").trim();

        if (!repo || !targetInput) {
            state = "ABSORB // REFUSED";
            lastError = !repo ? "NO REPOSITORY" : "TARGET COMMIT REQUIRED";
            return false;
        }

        previewBusy = true;
        armed = false;
        armedPlanJson = "";
        state = "ABSORB // READING STAGED PATCH";
        lastError = "";

        previewExitSeen = false;
        previewStdoutSeen = false;
        previewStderrSeen = false;
        previewExitCode = -1;
        previewStdout = "";
        previewStderr = "";

        previewProcess.exec([
            "python3",
            "-c",
            previewScript(),
            repo,
            targetInput,
            String(maxRecoveryPatchBytes)
        ]);
        return true;
    }

    function previewScript() {
        return [
            'import base64, hashlib, json, os, subprocess, sys',
            'repo, target_input, limit_text = sys.argv[1:4]',
            'limit = int(limit_text)',
            'def run(*args, data=None): return subprocess.run(["git", "-C", repo] + list(args), input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg): print("REFUSED\\t" + msg); sys.exit(1)',
            'if run("rev-parse", "--is-inside-work-tree").returncode: refuse("NOT A GIT WORKTREE")',
            'branch = text(run("branch", "--show-current"))',
            'if not branch: refuse("DETACHED HEAD")',
            'head = text(run("rev-parse", "HEAD"))',
            'target = text(run("rev-parse", target_input + "^{commit}"))',
            'if not target: refuse("TARGET COMMIT CANNOT BE RESOLVED")',
            'if target == head: refuse("TARGET MUST BE EARLIER THAN HEAD")',
            'if run("merge-base", "--is-ancestor", target, head).returncode: refuse("TARGET IS NOT AN ANCESTOR OF HEAD")',
            'parents = text(run("rev-list", "--parents", "-n", "1", target)).split()',
            'if len(parents) != 2: refuse("ABSORB TARGET MUST HAVE EXACTLY ONE PARENT")',
            'base = parents[1]',
            'if run("rev-list", "--merges", base + ".." + head).stdout.strip(): refuse("REWRITE RANGE CONTAINS MERGE COMMITS")',
            'gd = text(run("rev-parse", "--git-dir"))',
            'if not os.path.isabs(gd): gd = os.path.join(repo, gd)',
            'if os.path.isfile(os.path.join(gd, "MERGE_HEAD")) or os.path.isdir(os.path.join(gd, "rebase-merge")) or os.path.isdir(os.path.join(gd, "rebase-apply")) or os.path.isfile(os.path.join(gd, "CHERRY_PICK_HEAD")) or os.path.isfile(os.path.join(gd, "REVERT_HEAD")): refuse("ACTIVE GIT OPERATION")',
            'if run("ls-files", "-u").stdout.strip(): refuse("CONFLICTED INDEX")',
            'if run("diff", "--quiet").returncode != 0: refuse("UNSTAGED CHANGES PRESENT")',
            'if run("ls-files", "--others", "--exclude-standard").stdout.strip(): refuse("UNTRACKED FILES PRESENT")',
            'patch = run("diff", "--cached", "--binary", "--full-index").stdout',
            'if not patch: refuse("NO STAGED CHANGES TO ABSORB")',
            'if len(patch) > limit: refuse("STAGED PATCH EXCEEDS RECOVERY PAYLOAD LIMIT")',
            'paths = [p for p in text(run("diff", "--cached", "--name-only")).splitlines() if p]',
            'payload = {"branch": branch, "head": head, "target": target, "base": base, "subject": text(run("show", "-s", "--format=%s", target)), "files": paths, "patchBase64": base64.b64encode(patch).decode("ascii"), "fingerprint": hashlib.sha256(patch).hexdigest(), "patchBytes": len(patch)}',
            'print("JSON\\t" + json.dumps(payload, separators=(",", ":")))'
        ].join("\n");
    }

    function maybeFinishPreview() {
        if (!previewBusy
                || !previewExitSeen
                || !previewStdoutSeen
                || !previewStderrSeen)
            return;

        previewBusy = false;
        const out = String(previewStdout || "").trim();
        const err = String(previewStderr || "").trim();
        const lines = out.split("\n");
        let payload = null;
        let refused = "";

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
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

        if (previewExitCode !== 0 || !payload) {
            state = "ABSORB // REFUSED";
            lastError =
                refused
                || err
                || out
                || ("ABSORB PREVIEW EXIT " + previewExitCode);
            return;
        }

        branchName = String(payload.branch || "");
        headSha = String(payload.head || "");
        targetSha = String(payload.target || "");
        baseSha = String(payload.base || "");
        targetSubject = String(payload.subject || "");
        files = cloneValue(payload.files || []);
        patchBase64 = String(payload.patchBase64 || "");
        fingerprint = String(payload.fingerprint || "");
        patchBytes = Number(payload.patchBytes || 0);
        state =
            "ABSORB // PLAN READY // "
            + String(files.length)
            + " FILE"
            + (files.length === 1 ? "" : "S");
        lastError = "";
        previewReady();
    }

    function planObject() {
        return {
            branch: branchName,
            head: headSha,
            target: targetSha,
            base: baseSha,
            targetSubject: targetSubject,
            files: cloneValue(files),
            patchBase64: patchBase64,
            fingerprint: fingerprint,
            patchBytes: patchBytes
        };
    }

    function arm() {
        if (previewBusy || executionBusy)
            return false;

        const plan = planObject();
        if (!plan.branch
                || !plan.head
                || !plan.target
                || !plan.base
                || !plan.patchBase64
                || !plan.fingerprint
                || plan.patchBytes <= 0
                || plan.patchBytes > maxRecoveryPatchBytes) {
            state = "ABSORB // REFUSED";
            lastError = "ABSORB PLAN IS INCOMPLETE";
            return false;
        }

        armedPlanJson = JSON.stringify(plan);
        armed = true;
        state = "ABSORB // ARMED";
        lastError = "";
        return true;
    }

    function planStillArmed() {
        return armed
            && armedPlanJson === JSON.stringify(planObject());
    }

    function context() {
        const plan = planObject();
        return {
            source: "GitHistoryAbsorbService",
            operation: "ABSORB_STAGED",
            branch: plan.branch,
            head: plan.head,
            targetSha: plan.target,
            baseSha: plan.base,
            files: cloneValue(plan.files),
            patchBase64: plan.patchBase64,
            fingerprint: plan.fingerprint,
            patchBytes: plan.patchBytes,
            recoveryClass: "CONTENT_RECOVERABLE"
        };
    }

    function evidenceSnapshot(snapshot) {
        let out = {};
        try {
            out = JSON.parse(JSON.stringify(snapshot || {}));
        } catch (error) {
            out = {};
        }
        out.recoveryClass = "CONTENT_RECOVERABLE";
        out.recoveryReason =
            "EXACT PRE-ABSORB STAGED PATCH STORED IN JOURNAL";
        return out;
    }

    function executeArmed() {
        if (previewBusy || executionBusy || !planStillArmed())
            return false;

        if (!operationJournal || !snapshotService) {
            state = "ABSORB // REFUSED";
            lastError = "ABSORB REQUIRES JOURNAL + SNAPSHOT SERVICES";
            return false;
        }

        executionBusy = true;
        state = "ABSORB // SNAPSHOT BEFORE";
        lastError = "";
        pendingExecutionSuccess = false;
        pendingExecutionDetail = "";
        pendingNewHead = "";

        executeExitSeen = false;
        executeStdoutSeen = false;
        executeStderrSeen = false;
        executeExitCode = -1;
        executeStdout = "";
        executeStderr = "";

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY BEFORE // ABSORB STAGED",
            context()
        );

        if (!pendingSnapshotRequest) {
            failBeforeSnapshot("SNAPSHOT SERVICE BUSY OR UNAVAILABLE");
            return false;
        }
        return true;
    }

    function failBeforeSnapshot(detail) {
        executionBusy = false;
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        state = "ABSORB // REFUSED";
        lastError =
            "ABSORB BEFORE SNAPSHOT FAILED // "
            + String(detail || "UNKNOWN ERROR");
        executionFinished(false, lastError, "");
    }

    function executionScript() {
        return [
            'import base64, hashlib, json, os, shutil, subprocess, sys, tempfile',
            'repo = sys.argv[1]',
            'plan = json.loads(sys.argv[2])',
            'branch, expected_head, target, base = plan["branch"], plan["head"], plan["target"], plan["base"]',
            'patch = base64.b64decode(plan["patchBase64"], validate=True)',
            'fingerprint = plan["fingerprint"]',
            'def run(repo_path, *args, data=None, env=None): return subprocess.run(["git", "-C", repo_path] + list(args), input=data, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg, code=1): print("REFUSED\\t" + msg); sys.exit(code)',
            'if hashlib.sha256(patch).hexdigest() != fingerprint: refuse("STORED STAGED PATCH FINGERPRINT MISMATCH")',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED SINCE ARM")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED SINCE ARM")',
            'if run(repo, "diff", "--quiet").returncode != 0: refuse("UNSTAGED CHANGES APPEARED SINCE ARM")',
            'if run(repo, "ls-files", "--others", "--exclude-standard").stdout.strip(): refuse("UNTRACKED FILES APPEARED SINCE ARM")',
            'if run(repo, "ls-files", "-u").stdout.strip(): refuse("CONFLICTED INDEX SINCE ARM")',
            'current_patch = run(repo, "diff", "--cached", "--binary", "--full-index").stdout',
            'if hashlib.sha256(current_patch).hexdigest() != fingerprint: refuse("STAGED PATCH CHANGED SINCE ARM")',
            'if run(repo, "rev-list", "--merges", base + ".." + expected_head).stdout.strip(): refuse("REWRITE RANGE NOW CONTAINS MERGE COMMITS")',
            'tmp = tempfile.mkdtemp(prefix="pa-absorb-")',
            'wt = os.path.join(tmp, "worktree")',
            'try:',
            '    add = run(repo, "worktree", "add", "--detach", wt, expected_head)',
            '    if add.returncode: refuse("ABSORB REHEARSAL WORKTREE CREATE FAILED // " + add.stderr.decode("utf-8", "replace").strip())',
            '    applied = run(wt, "apply", "--index", "--binary", "--whitespace=nowarn", "-", data=patch)',
            '    if applied.returncode: refuse("STAGED PATCH DOES NOT APPLY IN REHEARSAL // " + applied.stderr.decode("utf-8", "replace").strip())',
            '    fixup = run(wt, "-c", "commit.gpgSign=false", "commit", "--no-verify", "--fixup=" + target)',
            '    if fixup.returncode: refuse("FIXUP COMMIT REHEARSAL FAILED // " + fixup.stderr.decode("utf-8", "replace").strip())',
            '    env = dict(os.environ); env["GIT_SEQUENCE_EDITOR"] = ":"; env["GIT_EDITOR"] = ":"',
            '    rebased = run(wt, "-c", "commit.gpgSign=false", "rebase", "-i", "--autosquash", "--empty=keep", "--reapply-cherry-picks", base, env=env)',
            '    if rebased.returncode:',
            '        run(wt, "rebase", "--abort")',
            '        detail = rebased.stderr.decode("utf-8", "replace").strip() or rebased.stdout.decode("utf-8", "replace").strip()',
            '        refuse("ABSORB REHEARSAL CONFLICT OR FAILURE // " + detail)',
            '    new_head = text(run(wt, "rev-parse", "HEAD"))',
            '    if not new_head: refuse("ABSORB REHEARSAL PRODUCED NO HEAD")',
            'finally:',
            '    run(repo, "worktree", "remove", "--force", wt)',
            '    shutil.rmtree(tmp, ignore_errors=True)',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED AFTER REHEARSAL")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED AFTER REHEARSAL")',
            'if run(repo, "diff", "--quiet").returncode != 0 or run(repo, "ls-files", "--others", "--exclude-standard").stdout.strip() or run(repo, "ls-files", "-u").stdout.strip(): refuse("WORKTREE CHANGED AFTER REHEARSAL")',
            'current_patch = run(repo, "diff", "--cached", "--binary", "--full-index").stdout',
            'if hashlib.sha256(current_patch).hexdigest() != fingerprint: refuse("STAGED PATCH CHANGED AFTER REHEARSAL")',
            'ref = "refs/heads/" + branch',
            'run(repo, "update-ref", "ORIG_HEAD", expected_head)',
            'move = run(repo, "update-ref", ref, new_head, expected_head)',
            'if move.returncode: refuse("GUARDED ABSORB BRANCH UPDATE FAILED")',
            'align = run(repo, "reset", "--hard", new_head)',
            'if align.returncode:',
            '    rollback = run(repo, "update-ref", ref, expected_head, new_head)',
            '    run(repo, "reset", "--hard", expected_head)',
            '    restored = run(repo, "apply", "--index", "--binary", "--whitespace=nowarn", "-", data=patch)',
            '    if rollback.returncode or restored.returncode: refuse("ABSORB REALIGN FAILED // ROLLBACK INCOMPLETE", 91)',
            '    refuse("ABSORB REALIGN FAILED // HISTORY + STAGED PATCH ROLLED BACK", 90)',
            'print("OK\\t{}\\t{}\\t{}".format(expected_head, new_head, target))'
        ].join("\n");
    }

    function startExecutionProcess() {
        state = "ABSORB // REHEARSING";
        executeProcess.exec([
            "python3",
            "-c",
            executionScript(),
            String(repositoryPath || ""),
            armedPlanJson
        ]);
    }

    function maybeFinishExecution() {
        if (!executionBusy
                || !executeExitSeen
                || !executeStdoutSeen
                || !executeStderrSeen)
            return;

        const out = String(executeStdout || "").trim();
        const err = String(executeStderr || "").trim();
        const lines = out.split("\n");
        let control = "";
        for (let i = lines.length - 1; i >= 0; --i) {
            const line = String(lines[i] || "");
            if (line.indexOf("OK\t") === 0
                    || line.indexOf("REFUSED\t") === 0) {
                control = line;
                break;
            }
        }

        const fields = control.split("\t");
        pendingExecutionSuccess =
            executeExitCode === 0
            && fields.length >= 4
            && fields[0] === "OK";
        pendingExecutionDetail =
            fields.length > 1
            ? fields.slice(1).join("\t")
            : String(err || out || ("ABSORB EXIT " + executeExitCode)).trim();
        pendingNewHead =
            pendingExecutionSuccess
            ? String(fields[2] || "")
            : "";

        state = "ABSORB // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY AFTER // ABSORB STAGED",
            context()
        );

        if (!pendingSnapshotRequest)
            finalizeExecution(null, "AFTER SNAPSHOT COULD NOT START");
    }

    function finalizeExecution(afterSnapshot, warningText) {
        const warning = String(warningText || "");
        const success = pendingExecutionSuccess;
        const detail =
            String(pendingExecutionDetail || "")
            + (warning ? " // " + warning : "");
        const snapshot =
            afterSnapshot
            ? evidenceSnapshot(afterSnapshot)
            : {
                snapshotVersion: 1,
                repository: String(repositoryPath || ""),
                capturedAt: new Date().toISOString(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason: warning || "ABSORB AFTER SNAPSHOT UNAVAILABLE"
            };

        if (pendingJournalId && operationJournal) {
            if (success)
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

        executionBusy = false;
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        armed = false;
        armedPlanJson = "";

        if (success) {
            state = warning
                ? "ABSORB // COMPLETE // SNAPSHOT WARNING"
                : "ABSORB // COMPLETE";
            lastError = warning;
            headSha = pendingNewHead;
        } else {
            state = "ABSORB // REFUSED";
            lastError = detail || "ABSORB FAILED";
        }

        const newHead = pendingNewHead;
        pendingNewHead = "";
        executionFinished(success, detail, newHead);
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
                        "HISTORY/ABSORB_STAGED",
                        root.evidenceSnapshot(snapshot),
                        root.context()
                    );

                if (!root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "ABSORB JOURNAL RECORD COULD NOT START"
                    );
                    return;
                }

                root.startExecutionProcess();
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeExecution(snapshot, "");
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
                root.finalizeExecution(
                    null,
                    "AFTER SNAPSHOT FAILED // "
                        + String(detail || "UNKNOWN ERROR")
                );
            }
        }
    }

    Process {
        id: previewProcess
        stdout: StdioCollector {
            onStreamFinished: {
                root.previewStdout = this.text;
                root.previewStdoutSeen = true;
                root.maybeFinishPreview();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                root.previewStderr = this.text;
                root.previewStderrSeen = true;
                root.maybeFinishPreview();
            }
        }
        onExited: function(code, exitStatus) {
            root.previewExitCode = Number(code);
            root.previewExitSeen = true;
            root.maybeFinishPreview();
        }
    }

    Process {
        id: executeProcess
        stdout: StdioCollector {
            onStreamFinished: {
                root.executeStdout = this.text;
                root.executeStdoutSeen = true;
                root.maybeFinishExecution();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                root.executeStderr = this.text;
                root.executeStderrSeen = true;
                root.maybeFinishExecution();
            }
        }
        onExited: function(code, exitStatus) {
            root.executeExitCode = Number(code);
            root.executeExitSeen = true;
            root.maybeFinishExecution();
        }
    }
}
