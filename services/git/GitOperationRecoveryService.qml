import QtQuick
import Quickshell
import Quickshell.Io

// First executable recovery layer for the Universal Operation Journal.
//
// Recovery is operation-specific and guarded against the recorded AFTER state.
// Unsupported operations are refused rather than approximated with reset.
Scope {
    id: root

    property string repositoryPath: ""
    property bool busy: false
    property string pendingOperationId: ""
    property var pendingRecord: null

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal recoveryStarted(string operationId)
    signal recoveryFinished(
        string operationId,
        bool success,
        string detail
    )

    function refSha(snapshot, refName) {
        const refs =
            snapshot && Array.isArray(snapshot.refs)
            ? snapshot.refs
            : [];

        for (let i = 0; i < refs.length; ++i) {
            const row = refs[i] || {};

            if (String(row.ref || "") === String(refName || ""))
                return String(row.sha || "");
        }

        return "";
    }

    function argument(record, index) {
        const metadata = (record || {}).metadata || {};
        const args =
            Array.isArray(metadata.arguments)
            ? metadata.arguments
            : [];

        return index >= 0 && index < args.length
            ? String(args[index] || "")
            : "";
    }

    function preview(record) {
        const row = record || {};
        const kind = String(row.kind || "");
        const status = String(row.status || "");
        const recoveryClass = String(row.recoveryClass || "");
        const before = row.before || {};
        const after = row.after || {};

        if (status !== "COMPLETE") {
            return {
                allowed: false,
                strategy: "REFUSE",
                reason: "ONLY COMPLETE OPERATIONS CAN BE UNDONE"
            };
        }

        if (recoveryClass !== "REF_RECOVERABLE"
                || String(before.recoveryClass || "") !== "REF_RECOVERABLE"
                || String(after.recoveryClass || "") !== "REF_RECOVERABLE") {
            return {
                allowed: false,
                strategy: "REFUSE",
                reason: "OPERATION IS NOT CLEAN REF-RECOVERABLE"
            };
        }

        if (kind === "BRANCH_WORKSPACE/CREATE") {
            const name = argument(row, 0);
            const ref = "refs/heads/" + name;
            const beforeSha = refSha(before, ref);
            const afterSha = refSha(after, ref);

            if (!name || beforeSha || !afterSha) {
                return {
                    allowed: false,
                    strategy: "REFUSE",
                    reason: "CREATE REF TRANSITION IS NOT EXACT"
                };
            }

            return {
                allowed: true,
                strategy: "DELETE_CREATED_BRANCH",
                branch: name,
                expectedSha: afterSha,
                summary:
                    "DELETE CREATED BRANCH "
                    + name
                    + " @ "
                    + afterSha.slice(0, 12)
            };
        }

        if (kind === "BRANCH_WORKSPACE/RENAME") {
            const oldName = argument(row, 0);
            const newName = argument(row, 1);
            const oldRef = "refs/heads/" + oldName;
            const newRef = "refs/heads/" + newName;
            const beforeOld = refSha(before, oldRef);
            const beforeNew = refSha(before, newRef);
            const afterOld = refSha(after, oldRef);
            const afterNew = refSha(after, newRef);

            if (!oldName
                    || !newName
                    || !beforeOld
                    || beforeNew
                    || afterOld
                    || afterNew !== beforeOld) {
                return {
                    allowed: false,
                    strategy: "REFUSE",
                    reason: "RENAME REF TRANSITION IS NOT EXACT"
                };
            }

            return {
                allowed: true,
                strategy: "RENAME_BRANCH_BACK",
                oldName: oldName,
                newName: newName,
                expectedSha: afterNew,
                summary:
                    "RENAME "
                    + newName
                    + " BACK TO "
                    + oldName
            };
        }

        return {
            allowed: false,
            strategy: "REFUSE",
            reason:
                "UNDO STRATEGY NOT IMPLEMENTED FOR "
                + (kind || "UNKNOWN OPERATION")
        };
    }

    function execute(operationId, record) {
        if (busy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const plan = preview(record);

        if (!repo) {
            recoveryFinished(
                String(operationId || ""),
                false,
                "NO REPOSITORY"
            );
            return false;
        }

        if (!plan.allowed) {
            recoveryFinished(
                String(operationId || ""),
                false,
                String(plan.reason || "UNDO REFUSED")
            );
            return false;
        }

        busy = true;
        pendingOperationId = String(operationId || "");
        pendingRecord = record || {};

        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        recoveryStarted(pendingOperationId);

        recoveryProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'strategy="$2"',
                'a="$3"',
                'b="$4"',
                'expected="$5"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "REFUSED\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'if [ -n "$(git -C "$repo" status --porcelain=v1 --untracked-files=all 2>/dev/null)" ]; then',
                '  printf "REFUSED\\tWORKTREE DIRTY // UNDO WILL NOT DISCARD CONTENT\\n"',
                '  exit 22',
                'fi',
                'case "$strategy" in',
                '  DELETE_CREATED_BRANCH)',
                '    branch="$a"',
                '    ref="refs/heads/$branch"',
                '    current="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$current" != "$ref" ] || { printf "REFUSED\\tCREATED BRANCH IS CURRENTLY CHECKED OUT\\n"; exit 31; }',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tBRANCH MOVED SINCE RECORDED OPERATION\\n"; exit 32; }',
                '    if git -C "$repo" worktree list --porcelain 2>/dev/null | grep -Fqx "branch $ref"; then',
                '      printf "REFUSED\\tBRANCH IS CHECKED OUT IN A WORKTREE\\n"',
                '      exit 33',
                '    fi',
                '    git -C "$repo" update-ref -d "$ref" "$expected" || { printf "REFUSED\\tGUARDED REF DELETE FAILED\\n"; exit 34; }',
                '    printf "OK\\tDELETED CREATED BRANCH // %s\\n" "$branch"',
                '    ;;',
                '  RENAME_BRANCH_BACK)',
                '    old="$a"',
                '    new="$b"',
                '    oldref="refs/heads/$old"',
                '    newref="refs/heads/$new"',
                '    git -C "$repo" show-ref --verify --quiet "$oldref" && { printf "REFUSED\\tORIGINAL BRANCH NAME NOW EXISTS\\n"; exit 41; }',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$newref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tRENAMED BRANCH MOVED SINCE RECORDED OPERATION\\n"; exit 42; }',
                '    git -C "$repo" branch -m "$new" "$old" >/dev/null 2>&1 || { printf "REFUSED\\tGUARDED RENAME BACK FAILED\\n"; exit 43; }',
                '    printf "OK\\tRENAMED %s BACK TO %s\\n" "$new" "$old"',
                '    ;;',
                '  *)',
                '    printf "REFUSED\\tUNKNOWN RECOVERY STRATEGY\\n"',
                '    exit 90',
                '    ;;',
                'esac'
            ].join("\n"),
            "git-operation-recovery",
            repo,
            String(plan.strategy || ""),
            String(plan.branch || plan.oldName || ""),
            String(plan.newName || ""),
            String(plan.expectedSha || "")
        ]);

        return true;
    }

    function maybeFinish() {
        if (!busy || !exitSeen || !stdoutSeen || !stderrSeen)
            return;

        const operationId = pendingOperationId;
        const out = String(stdoutText || "").trim();
        const err = String(stderrText || "").trim();
        const line = out.split("\n")[0] || "";
        const parts = line.split("\t");
        const kind = parts.length > 0 ? parts[0] : "";
        const detail =
            parts.length > 1
            ? parts.slice(1).join("\t")
            : String(err || out || ("EXIT " + exitCode)).trim();
        const success = exitCode === 0 && kind === "OK";

        busy = false;
        pendingOperationId = "";
        pendingRecord = null;

        recoveryFinished(
            operationId,
            success,
            detail || (success ? "UNDO COMPLETE" : "UNDO REFUSED")
        );
    }

    Process {
        id: recoveryProcess

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
