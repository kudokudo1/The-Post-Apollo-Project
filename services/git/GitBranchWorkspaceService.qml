import QtQuick
import Quickshell
import Quickshell.Io

// Shared low-level branch/worktree mechanism.
//
// Git surfaces can use this directly. Hospital can wrap the same operations
// with stronger Bed/Room/live-certification safety semantics.
Scope {
    id: root

    property string repositoryPath: ""

    property bool refreshing: false
    property bool actionBusy: false
    property string actionName: ""
    property string actionStatus: "READY"
    property string lastError: ""

    property string currentBranch: ""
    property string currentHead: ""
    property var branches: []
    property var worktrees: []

    property bool inspectExitSeen: false
    property bool inspectStdoutSeen: false
    property bool inspectStderrSeen: false
    property int inspectExitCode: -1
    property string inspectStdoutText: ""
    property string inspectStderrText: ""

    property bool actionExitSeen: false
    property bool actionStdoutSeen: false
    property bool actionStderrSeen: false
    property int actionExitCode: -1
    property string actionStdoutText: ""
    property string actionStderrText: ""

    signal refreshed()
    signal actionFinished(string action, bool success, string detail)

    readonly property bool available:
        String(repositoryPath || "").trim().length > 0

    function branchForName(name) {
        const needle = String(name || "");

        for (let i = 0; i < branches.length; ++i) {
            if (String((branches[i] || {}).name || "") === needle)
                return branches[i];
        }

        return null;
    }

    function worktreeForBranch(name) {
        const needle = String(name || "");

        for (let i = 0; i < worktrees.length; ++i) {
            if (String((worktrees[i] || {}).branch || "") === needle)
                return worktrees[i];
        }

        return null;
    }

    function branchIsOccupied(name) {
        return worktreeForBranch(name) !== null;
    }

    function refresh() {
        const repo = String(repositoryPath || "").trim();

        if (refreshing || actionBusy)
            return false;

        if (!repo) {
            currentBranch = "";
            currentHead = "";
            branches = [];
            worktrees = [];
            lastError = "NO REPOSITORY";
            return false;
        }

        refreshing = true;
        lastError = "";

        inspectExitSeen = false;
        inspectStdoutSeen = false;
        inspectStderrSeen = false;
        inspectExitCode = -1;
        inspectStdoutText = "";
        inspectStderrText = "";

        inspectProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "REFUSED\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'current="$(git -C "$repo" branch --show-current 2>/dev/null || true)"',
                'head="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                'printf "CURRENT\\t%s\\t%s\\n" "$current" "$head"',
                'git -C "$repo" for-each-ref --format="BRANCH%09%(refname:short)%09%(objectname)%09%(upstream:short)" refs/heads 2>/dev/null',
                'while IFS= read -r name; do',
                '  [ -n "$name" ] || continue',
                '  branch_ref="refs/heads/$name"',
                '  upstream="$(git -C "$repo" for-each-ref --format="%(upstream:short)" "$branch_ref" 2>/dev/null)"',
                '  target="$upstream"',
                '  [ -n "$target" ] || target="HEAD"',
                '  if git -C "$repo" merge-base --is-ancestor "$branch_ref" "$target" >/dev/null 2>&1; then merged="1"; else merged="0"; fi',
                '  printf "MERGED\t%s\t%s\n" "$name" "$merged"',
                'done < <(git -C "$repo" for-each-ref --format="%(refname:short)" refs/heads 2>/dev/null)',
                'git -C "$repo" worktree list --porcelain 2>/dev/null',
                'while IFS= read -r wt; do',
                '  count="$(git -C "$wt" status --porcelain=v1 2>/dev/null | wc -l | tr -d " ")"',
                '  printf "DIRTY\\t%s\\t%s\\n" "$wt" "$count"',
                'done < <(git -C "$repo" worktree list --porcelain 2>/dev/null | sed -n "s/^worktree //p")'
            ].join("\n"),
            "git-branch-workspace-inspect",
            repo
        ]);

        return true;
    }

    function parseInspection(text) {
        const lines = String(text || "").split("\n");
        const branchRows = [];
        const treeRows = [];
        const dirtyByPath = {};
        const mergedByBranch = {};

        let tree = null;
        let nextCurrentBranch = "";
        let nextCurrentHead = "";

        function finishTree() {
            if (!tree)
                return;

            treeRows.push(tree);
            tree = null;
        }

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");

            if (!line)
                continue;

            if (line.indexOf("CURRENT\t") === 0) {
                const parts = line.split("\t");
                nextCurrentBranch = parts.length > 1 ? parts[1] : "";
                nextCurrentHead = parts.length > 2 ? parts[2] : "";
                continue;
            }

            if (line.indexOf("BRANCH\t") === 0) {
                const parts = line.split("\t");
                branchRows.push({
                    name: parts.length > 1 ? parts[1] : "",
                    head: parts.length > 2 ? parts[2] : "",
                    upstream: parts.length > 3 ? parts[3] : ""
                });
                continue;
            }

            if (line.indexOf("MERGED\t") === 0) {
                const parts = line.split("\t");
                if (parts.length > 2)
                    mergedByBranch[parts[1]] = parts[2] === "1";
                continue;
            }

            if (line.indexOf("worktree ") === 0) {
                finishTree();
                tree = {
                    path: line.slice("worktree ".length),
                    head: "",
                    branch: "",
                    detached: false,
                    locked: false,
                    prunable: false,
                    dirtyCount: 0
                };
                continue;
            }

            if (line.indexOf("DIRTY\t") === 0) {
                const parts = line.split("\t");
                if (parts.length > 2)
                    dirtyByPath[parts[1]] = Number(parts[2] || 0);
                continue;
            }

            if (!tree)
                continue;

            if (line.indexOf("HEAD ") === 0)
                tree.head = line.slice("HEAD ".length);
            else if (line.indexOf("branch refs/heads/") === 0)
                tree.branch = line.slice("branch refs/heads/".length);
            else if (line === "detached")
                tree.detached = true;
            else if (line.indexOf("locked") === 0)
                tree.locked = true;
            else if (line.indexOf("prunable") === 0)
                tree.prunable = true;
        }

        finishTree();

        for (let i = 0; i < treeRows.length; ++i) {
            const row = treeRows[i];
            row.dirtyCount = Number(dirtyByPath[row.path] || 0);
        }

        for (let i = 0; i < branchRows.length; ++i) {
            const row = branchRows[i];
            row.merged = Boolean(mergedByBranch[row.name]);
        }

        currentBranch = nextCurrentBranch;
        currentHead = nextCurrentHead;
        branches = branchRows;
        worktrees = treeRows;
    }

    function maybeFinishInspection() {
        if (!refreshing
                || !inspectExitSeen
                || !inspectStdoutSeen
                || !inspectStderrSeen)
            return;

        refreshing = false;

        if (inspectExitCode !== 0) {
            const detail = String(
                inspectStderrText
                || inspectStdoutText
                || ("INSPECT EXIT " + inspectExitCode)
            ).trim();

            lastError = detail || "BRANCH INSPECTION FAILED";
            return;
        }

        parseInspection(inspectStdoutText);
        lastError = "";
        refreshed();
    }

    function runAction(operation, a, b, c) {
        const repo = String(repositoryPath || "").trim();
        const op = String(operation || "").trim();

        if (actionBusy || refreshing)
            return false;

        if (!repo || !op) {
            lastError = !repo ? "NO REPOSITORY" : "NO OPERATION";
            return false;
        }

        actionBusy = true;
        actionName = op.toUpperCase();
        actionStatus = actionName + " // RUNNING";
        lastError = "";

        actionExitSeen = false;
        actionStdoutSeen = false;
        actionStderrSeen = false;
        actionExitCode = -1;
        actionStdoutText = "";
        actionStderrText = "";

        actionProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'op="$2"',
                'a="$3"',
                'b="$4"',
                'c="$5"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "REFUSED\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'case "$op" in',
                '  switch)',
                '    target="$a"',
                '    remote="$b"',
                '    [ -n "$remote" ] || remote="origin"',
                '    allow_dirty="$c"',
                '    [ -n "$allow_dirty" ] || allow_dirty="0"',
                '    [ -n "$target" ] || { printf "REFUSED\\tNO TARGET BRANCH\\n"; exit 22; }',
                '    if [ "$allow_dirty" != "1" ] && [ -n "$(git -C "$repo" status --porcelain=v1 2>/dev/null)" ]; then',
                '      printf "REFUSED\\tWORKTREE DIRTY // COMMIT OR STASH FIRST\\n"',
                '      exit 23',
                '    fi',
                '    current="$(git -C "$repo" branch --show-current 2>/dev/null || true)"',
                '    if [ "$current" = "$target" ]; then',
                '      printf "OK\\tALREADY ON %s\\n" "$target"',
                '      exit 0',
                '    fi',
                '    if git -C "$repo" worktree list --porcelain 2>/dev/null | grep -Fqx "branch refs/heads/$target"; then',
                '      printf "REFUSED\\tBRANCH ALREADY CHECKED OUT IN ANOTHER WORKTREE\\n"',
                '      exit 24',
                '    fi',
                '    if git -C "$repo" show-ref --verify --quiet "refs/heads/$target"; then',
                '      git -C "$repo" switch "$target" >/dev/null 2>&1 || { printf "REFUSED\\tLOCAL BRANCH SWITCH FAILED\\n"; exit 25; }',
                '    else',
                '      if ! git -C "$repo" show-ref --verify --quiet "refs/remotes/$remote/$target"; then',
                '        git -C "$repo" fetch "$remote" "refs/heads/$target:refs/remotes/$remote/$target" >/dev/null 2>&1 || { printf "REFUSED\\tREMOTE BRANCH NOT FOUND\\n"; exit 26; }',
                '      fi',
                '      git -C "$repo" switch -c "$target" --track "$remote/$target" >/dev/null 2>&1 || { printf "REFUSED\\tTRACKING BRANCH CREATE FAILED\\n"; exit 27; }',
                '    fi',
                '    printf "OK\\tSWITCHED TO %s\\n" "$target"',
                '    ;;',
                '  create)',
                '    name="$a"',
                '    start="$b"',
                '    [ -n "$start" ] || start="HEAD"',
                '    git check-ref-format --branch "$name" >/dev/null 2>&1 || { printf "REFUSED\\tINVALID BRANCH NAME\\n"; exit 31; }',
                '    git -C "$repo" show-ref --verify --quiet "refs/heads/$name" && { printf "REFUSED\\tLOCAL BRANCH ALREADY EXISTS\\n"; exit 32; }',
                '    git -C "$repo" branch "$name" "$start" >/dev/null 2>&1 || { printf "REFUSED\\tBRANCH CREATE FAILED\\n"; exit 33; }',
                '    printf "OK\\tCREATED %s FROM %s\\n" "$name" "$start"',
                '    ;;',
                '  rename)',
                '    old="$a"',
                '    new="$b"',
                '    git check-ref-format --branch "$new" >/dev/null 2>&1 || { printf "REFUSED\\tINVALID NEW BRANCH NAME\\n"; exit 41; }',
                '    git -C "$repo" show-ref --verify --quiet "refs/heads/$old" || { printf "REFUSED\\tSOURCE BRANCH NOT FOUND\\n"; exit 42; }',
                '    git -C "$repo" show-ref --verify --quiet "refs/heads/$new" && { printf "REFUSED\\tDESTINATION BRANCH EXISTS\\n"; exit 43; }',
                '    git -C "$repo" branch -m "$old" "$new" >/dev/null 2>&1 || { printf "REFUSED\\tBRANCH RENAME FAILED\\n"; exit 44; }',
                '    printf "OK\\tRENAMED %s -> %s\\n" "$old" "$new"',
                '    ;;',
                '  delete)',
                '    name="$a"',
                '    force="$b"',
                '    [ -n "$force" ] || force="0"',
                '    current="$(git -C "$repo" branch --show-current 2>/dev/null || true)"',
                '    [ "$current" != "$name" ] || { printf "REFUSED\\tCANNOT DELETE CURRENT BRANCH\\n"; exit 51; }',
                '    if git -C "$repo" worktree list --porcelain 2>/dev/null | grep -Fqx "branch refs/heads/$name"; then',
                '      printf "REFUSED\\tBRANCH IS CHECKED OUT IN A WORKTREE\\n"',
                '      exit 52',
                '    fi',
                '    if [ "$force" = "1" ]; then mode="-D"; else mode="-d"; fi',
                '    git -C "$repo" branch "$mode" "$name" >/dev/null 2>&1 || { printf "REFUSED\\tBRANCH DELETE FAILED // MAY NOT BE MERGED\\n"; exit 53; }',
                '    printf "OK\\tDELETED %s\\n" "$name"',
                '    ;;',
                '  set-upstream)',
                '    branch="$a"',
                '    upstream="$b"',
                '    git -C "$repo" branch --set-upstream-to="$upstream" "$branch" >/dev/null 2>&1 || { printf "REFUSED\\tSET UPSTREAM FAILED\\n"; exit 61; }',
                '    printf "OK\\tUPSTREAM %s -> %s\\n" "$branch" "$upstream"',
                '    ;;',
                '  clear-upstream)',
                '    branch="$a"',
                '    git -C "$repo" branch --unset-upstream "$branch" >/dev/null 2>&1 || { printf "REFUSED\\tCLEAR UPSTREAM FAILED\\n"; exit 62; }',
                '    printf "OK\\tCLEARED UPSTREAM // %s\\n" "$branch"',
                '    ;;',
                '  add-worktree)',
                '    path="$a"',
                '    branch="$b"',
                '    [ -n "$path" ] && [ -n "$branch" ] || { printf "REFUSED\\tWORKTREE PATH + BRANCH REQUIRED\\n"; exit 71; }',
                '    git -C "$repo" worktree add "$path" "$branch" >/dev/null 2>&1 || { printf "REFUSED\\tWORKTREE ADD FAILED\\n"; exit 72; }',
                '    printf "OK\\tWORKTREE %s -> %s\\n" "$branch" "$path"',
                '    ;;',
                '  new-worktree)',
                '    path="$a"',
                '    branch="$b"',
                '    start="$c"',
                '    [ -n "$start" ] || start="HEAD"',
                '    [ -n "$path" ] && [ -n "$branch" ] || { printf "REFUSED\\tWORKTREE PATH + BRANCH REQUIRED\\n"; exit 73; }',
                '    git check-ref-format --branch "$branch" >/dev/null 2>&1 || { printf "REFUSED\\tINVALID BRANCH NAME\\n"; exit 74; }',
                '    git -C "$repo" worktree add -b "$branch" "$path" "$start" >/dev/null 2>&1 || { printf "REFUSED\\tNEW WORKTREE CREATE FAILED\\n"; exit 75; }',
                '    printf "OK\\tNEW WORKTREE %s -> %s\\n" "$branch" "$path"',
                '    ;;',
                '  remove-worktree)',
                '    path="$a"',
                '    force="$b"',
                '    [ -n "$force" ] || force="0"',
                '    [ -n "$path" ] || { printf "REFUSED\\tWORKTREE PATH REQUIRED\\n"; exit 76; }',
                '    if [ "$force" = "1" ]; then',
                '      git -C "$repo" worktree remove --force "$path" >/dev/null 2>&1 || { printf "REFUSED\\tWORKTREE REMOVE FAILED\\n"; exit 77; }',
                '    else',
                '      git -C "$repo" worktree remove "$path" >/dev/null 2>&1 || { printf "REFUSED\\tWORKTREE DIRTY OR LOCKED\\n"; exit 78; }',
                '    fi',
                '    printf "OK\\tREMOVED WORKTREE // %s\\n" "$path"',
                '    ;;',
                '  *)',
                '    printf "REFUSED\\tUNKNOWN OPERATION // %s\\n" "$op"',
                '    exit 90',
                '    ;;',
                'esac'
            ].join("\n"),
            "git-branch-workspace-action",
            repo,
            op,
            String(a || ""),
            String(b || ""),
            String(c || "")
        ]);

        return true;
    }

    function switchBranch(branch, remote, allowDirty) {
        return runAction(
            "switch",
            String(branch || ""),
            String(remote || "origin"),
            allowDirty ? "1" : "0"
        );
    }

    function createBranch(name, startPoint) {
        return runAction("create", name, startPoint || "HEAD", "");
    }

    function renameBranch(oldName, newName) {
        return runAction("rename", oldName, newName, "");
    }

    function deleteBranch(name, force) {
        return runAction("delete", name, force ? "1" : "0", "");
    }

    function setUpstream(branch, upstream) {
        return runAction("set-upstream", branch, upstream, "");
    }

    function clearUpstream(branch) {
        return runAction("clear-upstream", branch, "", "");
    }

    function addWorktree(path, branch) {
        return runAction("add-worktree", path, branch, "");
    }

    function createWorktree(path, branch, startPoint) {
        return runAction("new-worktree", path, branch, startPoint || "HEAD");
    }

    function removeWorktree(path, force) {
        return runAction("remove-worktree", path, force ? "1" : "0", "");
    }

    function maybeFinishAction() {
        if (!actionBusy
                || !actionExitSeen
                || !actionStdoutSeen
                || !actionStderrSeen)
            return;

        actionBusy = false;

        const out = String(actionStdoutText || "").trim();
        const err = String(actionStderrText || "").trim();
        const line = out.split("\n")[0] || "";
        const parts = line.split("\t");
        const kind = parts.length > 0 ? parts[0] : "";
        const detail =
            parts.length > 1
            ? parts.slice(1).join("\t")
            : String(err || out || ("EXIT " + actionExitCode)).trim();

        if (actionExitCode === 0 && kind === "OK") {
            actionStatus = actionName + " // " + (detail || "OK");
            lastError = "";
            actionFinished(actionName, true, detail || "OK");
            refresh();
            return;
        }

        lastError = detail || (actionName + " FAILED");
        actionStatus = actionName + " // REFUSED";
        actionFinished(actionName, false, lastError);
    }

    Process {
        id: inspectProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.inspectStdoutText = this.text;
                root.inspectStdoutSeen = true;
                root.maybeFinishInspection();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.inspectStderrText = this.text;
                root.inspectStderrSeen = true;
                root.maybeFinishInspection();
            }
        }

        onExited: function(code, exitStatus) {
            root.inspectExitCode = Number(code);
            root.inspectExitSeen = true;
            root.maybeFinishInspection();
        }
    }

    Process {
        id: actionProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.actionStdoutText = this.text;
                root.actionStdoutSeen = true;
                root.maybeFinishAction();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.actionStderrText = this.text;
                root.actionStderrSeen = true;
                root.maybeFinishAction();
            }
        }

        onExited: function(code, exitStatus) {
            root.actionExitCode = Number(code);
            root.actionExitSeen = true;
            root.maybeFinishAction();
        }
    }
}
