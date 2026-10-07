import QtQuick
import Quickshell
import Quickshell.Io

// Live repository snapshot service for the Universal Operation Journal.
//
// This captures repository evidence before/after a mutation. It does not
// perform Undo. Recovery classification is intentionally conservative until
// content-preserving recovery mechanics exist.
Scope {
    id: root

    property string repositoryPath: ""
    property bool busy: false
    property int serial: 0

    property string pendingRequestId: ""
    property string pendingLabel: ""
    property var pendingContext: null

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal snapshotReady(string requestId, var snapshot)
    signal snapshotFailed(string requestId, string detail)

    function nextRequestId() {
        serial += 1;
        return "snapshot-"
            + String(Date.now().toString(36))
            + "-"
            + String(serial.toString(36));
    }

    function capture(label, context) {
        const repo = String(repositoryPath || "").trim();

        if (!repo || busy)
            return "";

        const requestId = nextRequestId();

        busy = true;
        pendingRequestId = requestId;
        pendingLabel = String(label || "SNAPSHOT");
        pendingContext = context || {};

        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        snapshotProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'gitdir="$(git -C "$repo" rev-parse --git-dir 2>/dev/null || true)"',
                'case "$gitdir" in /*) ;; "") ;; *) gitdir="$repo/$gitdir" ;; esac',
                'branch="$(git -C "$repo" branch --show-current 2>/dev/null || true)"',
                'head="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                'head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                'printf "IDENTITY\\t%s\\t%s\\t%s\\n" "$branch" "$head" "$head_ref"',
                'git -C "$repo" for-each-ref --format="REF%09%(refname)%09%(objectname)%09%(objecttype)" refs/heads refs/tags refs/remotes 2>/dev/null',
                'git -C "$repo" for-each-ref --format="UPSTREAM%09%(refname:short)%09%(upstream:short)" refs/heads 2>/dev/null',
                'index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                'index_path="$(git -C "$repo" rev-parse --git-path index 2>/dev/null || true)"',
                'case "$index_path" in /*) ;; "") ;; *) index_path="$repo/$index_path" ;; esac',
                'index_hash=""',
                'if [ -n "$index_path" ] && [ -f "$index_path" ]; then index_hash="$(git -C "$repo" hash-object "$index_path" 2>/dev/null || true)"; fi',
                'printf "INDEX\\t%s\\t%s\\n" "$index_tree" "$index_hash"',
                'staged="$(git -C "$repo" diff --cached --name-only 2>/dev/null | wc -l | tr -d " ")"',
                'unstaged="$(git -C "$repo" diff --name-only 2>/dev/null | wc -l | tr -d " ")"',
                'untracked="$(git -C "$repo" ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d " ")"',
                'conflicts="$(git -C "$repo" diff --name-only --diff-filter=U 2>/dev/null | wc -l | tr -d " ")"',
                'status64="$(git -C "$repo" status --porcelain=v1 --untracked-files=all 2>/dev/null | base64 -w0 2>/dev/null || true)"',
                'staged_hash="$(git -C "$repo" diff --cached --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                'worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                'untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                'printf "STATUS\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$staged" "$unstaged" "$untracked" "$conflicts" "$status64" "$staged_hash" "$worktree_hash" "$untracked_hash"',
                'state="NONE"',
                'if [ -n "$gitdir" ] && [ -f "$gitdir/MERGE_HEAD" ]; then state="MERGE";',
                'elif [ -n "$gitdir" ] && { [ -d "$gitdir/rebase-merge" ] || [ -d "$gitdir/rebase-apply" ]; }; then state="REBASE";',
                'elif [ -n "$gitdir" ] && [ -f "$gitdir/CHERRY_PICK_HEAD" ]; then state="CHERRY_PICK";',
                'elif [ -n "$gitdir" ] && [ -f "$gitdir/REVERT_HEAD" ]; then state="REVERT";',
                'elif [ -n "$gitdir" ] && [ -f "$gitdir/BISECT_LOG" ]; then state="BISECT"; fi',
                'orig_head="$(git -C "$repo" rev-parse -q --verify ORIG_HEAD 2>/dev/null || true)"',
                'merge_head="$(git -C "$repo" rev-parse -q --verify MERGE_HEAD 2>/dev/null || true)"',
                'cherry_head="$(git -C "$repo" rev-parse -q --verify CHERRY_PICK_HEAD 2>/dev/null || true)"',
                'revert_head="$(git -C "$repo" rev-parse -q --verify REVERT_HEAD 2>/dev/null || true)"',
                'printf "OPSTATE\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$state" "$orig_head" "$merge_head" "$cherry_head" "$revert_head"',
                'git -C "$repo" reflog -1 --format="REFLOG%x09%H%x09%gD%x09%gs" HEAD 2>/dev/null || true',
                'worktrees64="$(git -C "$repo" worktree list --porcelain 2>/dev/null | base64 -w0 2>/dev/null || true)"',
                'printf "WORKTREES64\\t%s\\n" "$worktrees64"',
                'while IFS= read -r wt; do',
                '  [ -n "$wt" ] || continue',
                '  wt_head="$(git -C "$wt" rev-parse HEAD 2>/dev/null || true)"',
                '  wt_branch="$(git -C "$wt" branch --show-current 2>/dev/null || true)"',
                '  wt_dirty="$(git -C "$wt" status --porcelain=v1 --untracked-files=all 2>/dev/null | wc -l | tr -d " ")"',
                '  printf "WORKTREE\\t%s\\t%s\\t%s\\t%s\\n" "$wt" "$wt_head" "$wt_branch" "$wt_dirty"',
                'done < <(git -C "$repo" worktree list --porcelain 2>/dev/null | sed -n "s/^worktree //p")'
            ].join("\n"),
            "git-repository-snapshot",
            repo
        ]);

        return requestId;
    }

    function parseSnapshot(text) {
        const refs = [];
        const branchUpstreams = [];
        const worktrees = [];
        const lines = String(text || "").split("\n");

        let branch = "";
        let head = "";
        let headRef = "";
        let indexTree = "";
        let indexHash = "";

        let stagedCount = 0;
        let unstagedCount = 0;
        let untrackedCount = 0;
        let conflictCount = 0;
        let statusBase64 = "";
        let stagedPatchHash = "";
        let worktreePatchHash = "";
        let untrackedListHash = "";

        let operationState = "NONE";
        let origHead = "";
        let mergeHead = "";
        let cherryPickHead = "";
        let revertHead = "";

        let reflogHead = "";
        let reflogSelector = "";
        let reflogSubject = "";
        let worktreePorcelainBase64 = "";

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");

            if (!line)
                continue;

            if (line.indexOf("IDENTITY\t") === 0) {
                const p = line.split("\t");
                branch = p.length > 1 ? p[1] : "";
                head = p.length > 2 ? p[2] : "";
                headRef = p.length > 3 ? p[3] : "";
                continue;
            }

            if (line.indexOf("REF\t") === 0) {
                const p = line.split("\t");
                refs.push({
                    ref: p.length > 1 ? p[1] : "",
                    sha: p.length > 2 ? p[2] : "",
                    objectType: p.length > 3 ? p[3] : ""
                });
                continue;
            }

            if (line.indexOf("UPSTREAM\t") === 0) {
                const p = line.split("\t");
                branchUpstreams.push({
                    branch: p.length > 1 ? p[1] : "",
                    upstream: p.length > 2 ? p[2] : ""
                });
                continue;
            }

            if (line.indexOf("INDEX\t") === 0) {
                const p = line.split("\t");
                indexTree = p.length > 1 ? p[1] : "";
                indexHash = p.length > 2 ? p[2] : "";
                continue;
            }

            if (line.indexOf("STATUS\t") === 0) {
                const p = line.split("\t");
                stagedCount = Number(p.length > 1 ? p[1] : 0);
                unstagedCount = Number(p.length > 2 ? p[2] : 0);
                untrackedCount = Number(p.length > 3 ? p[3] : 0);
                conflictCount = Number(p.length > 4 ? p[4] : 0);
                statusBase64 = p.length > 5 ? p[5] : "";
                stagedPatchHash = p.length > 6 ? p[6] : "";
                worktreePatchHash = p.length > 7 ? p[7] : "";
                untrackedListHash = p.length > 8 ? p[8] : "";
                continue;
            }

            if (line.indexOf("OPSTATE\t") === 0) {
                const p = line.split("\t");
                operationState = p.length > 1 ? p[1] : "NONE";
                origHead = p.length > 2 ? p[2] : "";
                mergeHead = p.length > 3 ? p[3] : "";
                cherryPickHead = p.length > 4 ? p[4] : "";
                revertHead = p.length > 5 ? p[5] : "";
                continue;
            }

            if (line.indexOf("REFLOG\t") === 0) {
                const p = line.split("\t");
                reflogHead = p.length > 1 ? p[1] : "";
                reflogSelector = p.length > 2 ? p[2] : "";
                reflogSubject =
                    p.length > 3 ? p.slice(3).join("\t") : "";
                continue;
            }

            if (line.indexOf("WORKTREES64\t") === 0) {
                worktreePorcelainBase64 = line.slice(12);
                continue;
            }

            if (line.indexOf("WORKTREE\t") === 0) {
                const p = line.split("\t");
                worktrees.push({
                    path: p.length > 1 ? p[1] : "",
                    head: p.length > 2 ? p[2] : "",
                    branch: p.length > 3 ? p[3] : "",
                    dirtyCount: Number(p.length > 4 ? p[4] : 0)
                });
            }
        }

        const dirty =
            stagedCount > 0
            || unstagedCount > 0
            || untrackedCount > 0
            || conflictCount > 0;

        let anyDirtyWorktree = false;

        for (let i = 0; i < worktrees.length; ++i) {
            if (Number((worktrees[i] || {}).dirtyCount || 0) > 0) {
                anyDirtyWorktree = true;
                break;
            }
        }

        const evidenceOnly =
            dirty
            || anyDirtyWorktree
            || operationState !== "NONE"
            || !head;

        return {
            snapshotVersion: 1,
            requestId: pendingRequestId,
            repository: String(repositoryPath || ""),
            label: pendingLabel,
            capturedAt: new Date().toISOString(),
            context: pendingContext || {},

            branch: branch,
            head: head,
            headRef: headRef,
            refs: refs,
            branchUpstreams: branchUpstreams,

            index: {
                tree: indexTree,
                hash: indexHash
            },

            workingState: {
                stagedCount: stagedCount,
                unstagedCount: unstagedCount,
                untrackedCount: untrackedCount,
                conflictCount: conflictCount,
                statusBase64: statusBase64,
                stagedPatchHash: stagedPatchHash,
                worktreePatchHash: worktreePatchHash,
                untrackedListHash: untrackedListHash
            },

            operationState: {
                state: operationState,
                origHead: origHead,
                mergeHead: mergeHead,
                cherryPickHead: cherryPickHead,
                revertHead: revertHead
            },

            reflog: {
                head: reflogHead,
                selector: reflogSelector,
                subject: reflogSubject
            },

            worktrees: worktrees,
            worktreePorcelainBase64: worktreePorcelainBase64,

            recoveryClass:
                evidenceOnly
                ? "EVIDENCE_ONLY"
                : "REF_RECOVERABLE",
            recoveryReason:
                operationState !== "NONE"
                ? "ACTIVE GIT OPERATION"
                : anyDirtyWorktree || dirty
                ? "DIRTY CONTENT IS EVIDENCE-ONLY UNTIL CONTENT SNAPSHOTS EXIST"
                : !head
                ? "NO HEAD COMMIT"
                : "CLEAN REF STATE CAPTURED"
        };
    }

    function maybeFinish() {
        if (!busy || !exitSeen || !stdoutSeen || !stderrSeen)
            return;

        const requestId = pendingRequestId;
        const out = String(stdoutText || "");
        const err = String(stderrText || "").trim();

        busy = false;

        if (exitCode !== 0 || out.indexOf("ERROR\t") === 0) {
            const detail = String(
                err
                || out
                || ("SNAPSHOT EXIT " + exitCode)
            ).trim();

            pendingRequestId = "";
            pendingLabel = "";
            pendingContext = null;
            snapshotFailed(requestId, detail || "SNAPSHOT FAILED");
            return;
        }

        const snapshot = parseSnapshot(out);

        pendingRequestId = "";
        pendingLabel = "";
        pendingContext = null;
        snapshotReady(requestId, snapshot);
    }

    Process {
        id: snapshotProcess

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
