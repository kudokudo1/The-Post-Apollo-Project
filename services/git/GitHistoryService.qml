import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repositoryPath: ""

    property bool refreshing: false
    property bool detailBusy: false
    property bool diffBusy: false
    property bool actionBusy: false

    property var rows: []
    property var branchRefs: []
    property var tagRefs: []

    property string selectedRef: "ALL"
    property string selectedMode: "all"
    property string selectedSha: ""
    property string detailText: "SELECT A COMMIT"
    property var selectedParents: []
    property var selectedChildren: []
    property var changedFiles: []

    property string compareA: ""
    property string compareB: ""
    property string compareText: "SELECT A + B TO COMPARE"
    property string fileDiffText: "SELECT A FILE"
    property string selectedFile: ""

    property string actionName: ""
    property string actionStatus: "READY"
    property string lastError: ""

    property bool queryBusy: false
    property var queryRows: []
    property string queryStatus: "READY"
    property string queryPath: ""
    property string queryAuthor: ""
    property string querySince: ""
    property string queryUntil: ""
    property string queryRange: ""
    property string queryMessage: ""

    property bool reflogBusy: false
    property var reflogRows: []
    property string reflogStatus: "READY"
    property string reflogHeadSha: ""
    property string reflogBranch: ""

    readonly property int reflogRecoveryCount:
        reflogRows.filter(function(row) {
            const item = row || {};
            return !Boolean(item.reachable)
                && !Boolean(item.isHead);
        }).length

    property var activeLanes: []

    property bool inspectExitSeen: false
    property bool inspectStdoutSeen: false
    property bool inspectStderrSeen: false
    property int inspectExitCode: -1
    property string inspectStdoutText: ""
    property string inspectStderrText: ""

    property bool detailExitSeen: false
    property bool detailStdoutSeen: false
    property bool detailStderrSeen: false
    property int detailExitCode: -1
    property string detailStdoutText: ""
    property string detailStderrText: ""

    property bool diffExitSeen: false
    property bool diffStdoutSeen: false
    property bool diffStderrSeen: false
    property int diffExitCode: -1
    property string diffStdoutText: ""
    property string diffStderrText: ""
    property string diffKind: "compare"

    property bool actionExitSeen: false
    property bool actionStdoutSeen: false
    property bool actionStderrSeen: false
    property int actionExitCode: -1
    property string actionStdoutText: ""
    property string actionStderrText: ""

    property bool queryExitSeen: false
    property bool queryStdoutSeen: false
    property bool queryStderrSeen: false
    property int queryExitCode: -1
    property string queryStdoutText: ""
    property string queryStderrText: ""

    property bool reflogExitSeen: false
    property bool reflogStdoutSeen: false
    property bool reflogStderrSeen: false
    property int reflogExitCode: -1
    property string reflogStdoutText: ""
    property string reflogStderrText: ""

    signal refreshed()
    signal actionFinished(string action, bool success, string detail)

    readonly property bool available:
        String(repositoryPath || "").trim().length > 0

    function rowAt(index) {
        if (index < 0 || index >= rows.length)
            return null;
        return rows[index];
    }

    function resetLanes() {
        activeLanes = [];
    }

    function allocateLane(sha, parents) {
        let lanes = activeLanes.slice();
        let lane = lanes.indexOf(sha);

        if (lane < 0) {
            lane = lanes.length;
            lanes.push(sha);
        }

        const primary = parents.length > 0 ? parents[0] : "";

        if (!primary) {
            lanes.splice(lane, 1);
        } else {
            const existing = lanes.indexOf(primary);

            if (existing >= 0 && existing !== lane)
                lanes.splice(lane, 1);
            else
                lanes[lane] = primary;

            let insertAt = Math.min(lane + 1, lanes.length);

            for (let i = 1; i < parents.length; ++i) {
                const parent = parents[i];
                if (!parent || lanes.indexOf(parent) >= 0)
                    continue;
                lanes.splice(insertAt, 0, parent);
                insertAt += 1;
            }
        }

        activeLanes = lanes;
        return lane;
    }

    function cleanRefs(raw) {
        const pieces = String(raw || "").split(",");
        const out = [];

        for (let i = 0; i < pieces.length; ++i) {
            let value = pieces[i].trim();
            if (!value || value === "origin/HEAD")
                continue;
            value = value.replace(/^HEAD -> /, "");
            value = value.replace(/^tag: /, "TAG ");
            out.push(value);
        }

        return out.slice(0, 6).join(" • ");
    }

    function refresh(refName, modeName) {
        const repo = String(repositoryPath || "").trim();
        const ref = String(refName || selectedRef || "ALL").trim();
        const requestedMode = String(
            modeName || selectedMode || "all"
        ).trim();

        if (!repo || refreshing || actionBusy)
            return false;

        selectedRef = ref || "ALL";
        selectedMode =
            requestedMode === "first-parent"
            || requestedMode === "merges"
            || requestedMode === "no-merges"
            ? requestedMode
            : "all";
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
                'scope="$2"',
                'mode="$3"',
                'case "$mode" in',
                '  first-parent) mode_args="--first-parent" ;;',
                '  merges) mode_args="--merges" ;;',
                '  no-merges) mode_args="--no-merges" ;;',
                '  *) mode_args="" ;;',
                'esac',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'git -C "$repo" for-each-ref --sort=-committerdate --format="BRANCH%x09%(refname:short)" refs/heads 2>/dev/null',
                'git -C "$repo" for-each-ref --sort=-creatordate --format="TAG%x09%(refname:short)" refs/tags 2>/dev/null',
                'if [ -z "$scope" ] || [ "$scope" = "ALL" ]; then',
                '  git -C "$repo" log --all --topo-order --date-order $mode_args -n 150 --pretty=format:"ROW%x09%H%x09%P%x09%D%x09%ct%x09%an%x09%s"',
                'else',
                '  if ! git -C "$repo" rev-parse --verify "$scope^{commit}" >/dev/null 2>&1; then',
                '    printf "\\nERROR\\tREF NOT FOUND // %s\\n" "$scope"',
                '    exit 22',
                '  fi',
                '  git -C "$repo" log "$scope" --topo-order --date-order $mode_args -n 150 --pretty=format:"ROW%x09%H%x09%P%x09%D%x09%ct%x09%an%x09%s"',
                'fi',
                'printf "\\nDONE\\n"'
            ].join("\n"),
            "git-history-scan",
            repo,
            selectedRef,
            selectedMode
        ]);

        return true;
    }

    function parseInspection(text) {
        const history = [];
        const branches = [];
        const tags = [];

        resetLanes();

        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            if (!line)
                continue;

            const p = line.split("\t");
            const kind = p.length > 0 ? p[0] : "";

            if (kind === "BRANCH") {
                if (p.length > 1)
                    branches.push(p[1]);
                continue;
            }

            if (kind === "TAG") {
                if (p.length > 1)
                    tags.push(p[1]);
                continue;
            }

            if (kind === "ERROR") {
                lastError = p.length > 1
                    ? p.slice(1).join("\t")
                    : "HISTORY ERROR";
                continue;
            }

            if (kind !== "ROW")
                continue;

            const sha = p.length > 1 ? p[1] : "";
            const parentText = p.length > 2 ? p[2] : "";
            const parents = parentText.trim()
                ? parentText.trim().split(/\s+/)
                : [];
            const refs = p.length > 3 ? p[3] : "";
            const lane = allocateLane(sha, parents);

            history.push({
                sha: sha,
                shortSha: sha.slice(0, 8),
                parents: parents,
                refsText: cleanRefs(refs),
                epoch: p.length > 4 ? Number(p[4] || 0) : 0,
                author: p.length > 5 ? p[5] : "",
                subject: p.length > 6 ? p.slice(6).join("\t") : "",
                lane: lane,
                isHead: refs.indexOf("HEAD ->") >= 0
            });
        }

        rows = history;
        branchRefs = branches;
        tagRefs = tags;
    }

    function maybeFinishInspection() {
        if (!refreshing
                || !inspectExitSeen
                || !inspectStdoutSeen
                || !inspectStderrSeen)
            return;

        refreshing = false;

        if (inspectExitCode !== 0 && !lastError) {
            lastError = String(
                inspectStderrText
                || inspectStdoutText
                || ("HISTORY EXIT " + inspectExitCode)
            ).trim();
        }

        parseInspection(inspectStdoutText);

        if (inspectExitCode === 0)
            lastError = "";

        refreshed();
    }

    function runQuery(path, author, sinceText, untilText, rangeText, messageText) {
        const repo = String(repositoryPath || "").trim();

        if (!repo || queryBusy)
            return false;

        queryPath = String(path || "").trim();
        queryAuthor = String(author || "").trim();
        querySince = String(sinceText || "").trim();
        queryUntil = String(untilText || "").trim();
        queryRange = String(rangeText || "").trim();
        queryMessage = String(messageText || "").trim();

        queryBusy = true;
        queryRows = [];
        queryStatus = "QUERY // RUNNING";
        lastError = "";

        queryExitSeen = false;
        queryStdoutSeen = false;
        queryStderrSeen = false;
        queryExitCode = -1;
        queryStdoutText = "";
        queryStderrText = "";

        queryProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'path="$2"',
                'author="$3"',
                'since_text="$4"',
                'until_text="$5"',
                'range_text="$6"',
                'message_text="$7"',
                'python3 - "$repo" "$path" "$author" "$since_text" "$until_text" "$range_text" "$message_text" <<\'PY\'',
                'import subprocess, sys',
                'repo, path, author, since_text, until_text, range_text, message_text = sys.argv[1:8]',
                'if author == "@me":',
                '    email = subprocess.run(["git", "-C", repo, "config", "user.email"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip()',
                '    name = subprocess.run(["git", "-C", repo, "config", "user.name"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip()',
                '    author = email or name',
                '    if not author:',
                '        print("QUERY IDENTITY NOT CONFIGURED", file=sys.stderr)',
                '        sys.exit(23)',
                'cmd = [',
                '    "git", "-C", repo, "log",',
                '    "--date-order", "-n", "200",',
                '    "--pretty=format:QROW%x09%H%x09%P%x09%D%x09%ct%x09%an%x09%ae%x09%s"',
                ']',
                'if range_text:',
                '    cmd.append(range_text)',
                'else:',
                '    cmd.append("--all")',
                'if author:',
                '    cmd.append("--author=" + author)',
                'if message_text:',
                '    cmd.append("--grep=" + message_text)',
                '    cmd.append("--regexp-ignore-case")',
                'if since_text:',
                '    cmd.append("--since=" + since_text)',
                'if until_text:',
                '    cmd.append("--until=" + until_text)',
                'if path:',
                '    cmd += ["--", path]',
                'proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
                'sys.stdout.buffer.write(proc.stdout)',
                'sys.stderr.buffer.write(proc.stderr)',
                'sys.exit(proc.returncode)',
                'PY'
            ].join("\n"),
            "git-history-query",
            repo,
            queryPath,
            queryAuthor,
            querySince,
            queryUntil,
            queryRange,
            queryMessage
        ]);

        return true;
    }

    function parseQuery(text) {
        const out = [];
        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            if (!line || line.indexOf("QROW\t") !== 0)
                continue;

            const p = line.split("\t");
            const refs = p.length > 3 ? p[3] : "";

            out.push({
                sha: p.length > 1 ? p[1] : "",
                shortSha:
                    p.length > 1
                    ? p[1].slice(0, 8)
                    : "",
                parents:
                    p.length > 2 && p[2].trim()
                    ? p[2].trim().split(/\s+/)
                    : [],
                refsText: cleanRefs(refs),
                epoch:
                    p.length > 4
                    ? Number(p[4] || 0)
                    : 0,
                author: p.length > 5 ? p[5] : "",
                email: p.length > 6 ? p[6] : "",
                subject:
                    p.length > 7
                    ? p.slice(7).join("\t")
                    : ""
            });
        }

        queryRows = out;
    }

    function maybeFinishQuery() {
        if (!queryBusy
                || !queryExitSeen
                || !queryStdoutSeen
                || !queryStderrSeen)
            return;

        queryBusy = false;

        if (queryExitCode !== 0) {
            lastError = String(
                queryStderrText
                || queryStdoutText
                || ("QUERY EXIT " + queryExitCode)
            ).trim();
            queryStatus = "QUERY // REFUSED";
            queryRows = [];
            return;
        }

        parseQuery(queryStdoutText);
        lastError = "";
        queryStatus =
            "QUERY // "
            + String(queryRows.length)
            + " MATCHES";
    }

    function clearQuery() {
        queryPath = "";
        queryAuthor = "";
        querySince = "";
        queryUntil = "";
        queryRange = "";
        queryMessage = "";
        queryRows = [];
        queryStatus = "READY";
    }

    function loadReflog() {
        const repo = String(repositoryPath || "").trim();

        if (!repo || reflogBusy)
            return false;

        reflogBusy = true;
        reflogRows = [];
        reflogStatus = "REFLOG // READING";
        lastError = "";

        reflogExitSeen = false;
        reflogStdoutSeen = false;
        reflogStderrSeen = false;
        reflogExitCode = -1;
        reflogStdoutText = "";
        reflogStderrText = "";

        reflogProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'reachable="$(mktemp)"',
                'trap \'rm -f "$reachable"\' EXIT',
                'git -C "$repo" rev-list --all > "$reachable" 2>/dev/null || true',
                'head_sha="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                'branch="$(git -C "$repo" branch --show-current 2>/dev/null || true)"',
                'printf "RHEAD\\t%s\\t%s\\n" "$head_sha" "$branch"',
                'git -C "$repo" reflog --all -n 200 --date=iso --format="%H%x09%gD%x09%gs" | while IFS="$(printf "\\t")" read -r sha selector subject; do',
                '  reachable_now=0',
                '  is_head=0',
                '  [ -n "$sha" ] && grep -Fxq "$sha" "$reachable" && reachable_now=1',
                '  [ -n "$sha" ] && [ "$sha" = "$head_sha" ] && is_head=1',
                '  printf "RROW\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$sha" "$selector" "$reachable_now" "$is_head" "$subject"',
                'done'
            ].join("\n"),
            "git-history-reflog",
            repo
        ]);

        return true;
    }

    function parseReflog(text) {
        const out = [];
        let nextHeadSha = "";
        let nextBranch = "";
        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            if (!line)
                continue;

            const p = line.split("\t");
            const kind = p.length > 0 ? p[0] : "";

            if (kind === "RHEAD") {
                nextHeadSha = p.length > 1 ? p[1] : "";
                nextBranch = p.length > 2 ? p.slice(2).join("\t") : "";
                continue;
            }

            if (kind !== "RROW")
                continue;

            const sha = p.length > 1 ? p[1] : "";

            out.push({
                sha: sha,
                shortSha: sha.slice(0, 8),
                selector: p.length > 2 ? p[2] : "",
                reachable:
                    p.length > 3
                    ? p[3] === "1"
                    : false,
                isHead:
                    p.length > 4
                    ? p[4] === "1"
                    : false,
                subject:
                    p.length > 5
                    ? p.slice(5).join("\t")
                    : ""
            });
        }

        reflogRows = out;
        reflogHeadSha = nextHeadSha;
        reflogBranch = nextBranch;
    }

    function maybeFinishReflog() {
        if (!reflogBusy
                || !reflogExitSeen
                || !reflogStdoutSeen
                || !reflogStderrSeen)
            return;

        reflogBusy = false;

        if (reflogExitCode !== 0) {
            lastError = String(
                reflogStderrText
                || reflogStdoutText
                || ("REFLOG EXIT " + reflogExitCode)
            ).trim();
            reflogStatus = "REFLOG // REFUSED";
            reflogRows = [];
            return;
        }

        parseReflog(reflogStdoutText);
        lastError = "";
        reflogStatus =
            "REFLOG // "
            + String(reflogRows.length)
            + " ENTRIES // "
            + String(reflogRecoveryCount)
            + " RECOVERY";
    }

    function showCommit(sha) {
        const repo = String(repositoryPath || "").trim();
        const target = String(sha || "").trim();

        if (!repo || !target || detailBusy)
            return false;

        detailBusy = true;
        selectedSha = target;
        detailText = "READING COMMIT // " + target.slice(0, 10);
        selectedParents = [];
        selectedChildren = [];
        changedFiles = [];
        selectedFile = "";
        fileDiffText = "SELECT A FILE";
        lastError = "";

        detailExitSeen = false;
        detailStdoutSeen = false;
        detailStderrSeen = false;
        detailExitCode = -1;
        detailStdoutText = "";
        detailStderrText = "";

        detailProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'sha="$2"',
                'if ! git -C "$repo" rev-parse --verify "$sha^{commit}" >/dev/null 2>&1; then',
                '  printf "ERROR\\tCOMMIT NOT FOUND\\n"',
                '  exit 21',
                'fi',
                'parents="$(git -C "$repo" show -s --format=%P "$sha")"',
                'printf "PARENTS\\t%s\\n" "$parents"',
                'git -C "$repo" rev-list --all --children | awk -v s="$sha" \'$1==s { for (i=2;i<=NF;i++) print "CHILD\\t"$i }\'',
                'git -C "$repo" diff-tree --root --no-commit-id --name-status -r "$sha" | while IFS="$(printf "\\t")" read -r status a b; do',
                '  path="$a"; [ -n "$b" ] && path="$b"',
                '  printf "FILE\\t%s\\t%s\\n" "$status" "$path"',
                'done',
                'printf "TEXT_BEGIN\\n"',
                'git -C "$repo" show --no-ext-diff --decorate=short --date=local --format="commit %H%nAuthor: %an <%ae>%nDate:   %ad%nParents: %P%nRefs:    %D%n%n    %s%n%n%b" --stat --summary "$sha"'
            ].join("\n"),
            "git-history-detail",
            repo,
            target
        ]);

        return true;
    }

    function parseDetail(text) {
        const parents = [];
        const children = [];
        const files = [];
        const body = [];
        let readingBody = false;

        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");

            if (line === "TEXT_BEGIN") {
                readingBody = true;
                continue;
            }

            if (readingBody) {
                body.push(line);
                continue;
            }

            if (line.indexOf("PARENTS\t") === 0) {
                const raw = line.slice(8).trim();
                if (raw) {
                    const values = raw.split(/\s+/);
                    for (let j = 0; j < values.length; ++j)
                        parents.push(values[j]);
                }
            } else if (line.indexOf("CHILD\t") === 0) {
                children.push(line.slice(6).trim());
            } else if (line.indexOf("FILE\t") === 0) {
                const p = line.split("\t");
                files.push({
                    status: p.length > 1 ? p[1] : "",
                    path: p.length > 2 ? p.slice(2).join("\t") : ""
                });
            } else if (line.indexOf("ERROR\t") === 0) {
                lastError = line.slice(6);
            }
        }

        selectedParents = parents;
        selectedChildren = children;
        changedFiles = files;
        detailText = body.join("\n").trim() || "NO COMMIT DETAIL";
    }

    function maybeFinishDetail() {
        if (!detailBusy
                || !detailExitSeen
                || !detailStdoutSeen
                || !detailStderrSeen)
            return;

        detailBusy = false;

        if (detailExitCode !== 0) {
            lastError = String(
                detailStderrText
                || detailStdoutText
                || ("DETAIL EXIT " + detailExitCode)
            ).trim();
            detailText = "ERROR // " + lastError;
            return;
        }

        parseDetail(detailStdoutText);
    }

    function compareCommits(a, b) {
        const repo = String(repositoryPath || "").trim();
        const left = String(a || compareA || "").trim();
        const right = String(b || compareB || "").trim();

        if (!repo || !left || !right || diffBusy)
            return false;

        compareA = left;
        compareB = right;
        diffBusy = true;
        diffKind = "compare";
        compareText =
            "READING COMPARE // "
            + left.slice(0, 8)
            + " → "
            + right.slice(0, 8);

        startDiff([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'a="$2"',
                'b="$3"',
                'printf "=== SUMMARY ========================================\\n"',
                'git -C "$repo" diff --stat "$a" "$b" || exit $?',
                'printf "\\n=== FILES ==========================================\\n"',
                'git -C "$repo" diff --name-status "$a" "$b" || exit $?',
                'printf "\\n=== PATCH ==========================================\\n"',
                'git -C "$repo" diff --no-ext-diff "$a" "$b" || exit $?'
            ].join("\n"),
            "git-history-compare",
            repo,
            left,
            right
        ]);

        return true;
    }

    function showFileDiff(sha, path) {
        const repo = String(repositoryPath || "").trim();
        const target = String(sha || selectedSha || "").trim();
        const file = String(path || "").trim();

        if (!repo || !target || !file || diffBusy)
            return false;

        selectedFile = file;
        diffBusy = true;
        diffKind = "file";
        fileDiffText = "READING FILE // " + file;

        startDiff([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'sha="$2"',
                'path="$3"',
                'parent="$(git -C "$repo" rev-parse "$sha^" 2>/dev/null || true)"',
                'if [ -n "$parent" ]; then',
                '  git -C "$repo" diff --no-ext-diff "$parent" "$sha" -- "$path"',
                'else',
                '  git -C "$repo" show --no-ext-diff --format= "$sha" -- "$path"',
                'fi'
            ].join("\n"),
            "git-history-file",
            repo,
            target,
            file
        ]);

        return true;
    }

    function startDiff(command) {
        diffExitSeen = false;
        diffStdoutSeen = false;
        diffStderrSeen = false;
        diffExitCode = -1;
        diffStdoutText = "";
        diffStderrText = "";
        diffProcess.exec(command);
    }

    function maybeFinishDiff() {
        if (!diffBusy
                || !diffExitSeen
                || !diffStdoutSeen
                || !diffStderrSeen)
            return;

        diffBusy = false;

        const out = String(diffStdoutText || "").trim();
        const err = String(diffStderrText || "").trim();
        const value = out || err || "NO DIFFERENCE";

        if (diffKind === "file")
            fileDiffText = value;
        else
            compareText = value;

        if (diffExitCode !== 0)
            lastError = value;
    }

    function runAction(operation, a, b, c) {
        const repo = String(repositoryPath || "").trim();
        const op = String(operation || "").trim();

        if (!repo || !op || actionBusy || refreshing)
            return false;

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
                'dirty="$(git -C "$repo" status --porcelain=v1 2>/dev/null)"',
                'case "$op" in',
                '  cherry-pick)',
                '    [ -n "$a" ] || { printf "REFUSED\\tCOMMIT REQUIRED\\n"; exit 22; }',
                '    [ -z "$dirty" ] || { printf "REFUSED\\tWORKTREE DIRTY // COMMIT OR STASH FIRST\\n"; exit 23; }',
                '    git -C "$repo" cherry-pick "$a" || exit $?',
                '    printf "OK\\tCHERRY-PICKED // %s\\n" "$a"',
                '    ;;',
                '  revert)',
                '    [ -n "$a" ] || { printf "REFUSED\\tCOMMIT REQUIRED\\n"; exit 24; }',
                '    [ -z "$dirty" ] || { printf "REFUSED\\tWORKTREE DIRTY // COMMIT OR STASH FIRST\\n"; exit 25; }',
                '    GIT_EDITOR=true git -C "$repo" revert --no-edit "$a" || exit $?',
                '    printf "OK\\tREVERTED // %s\\n" "$a"',
                '    ;;',
                '  detach)',
                '    [ -n "$a" ] || { printf "REFUSED\\tCOMMIT REQUIRED\\n"; exit 26; }',
                '    [ -z "$dirty" ] || { printf "REFUSED\\tWORKTREE DIRTY // COMMIT OR STASH FIRST\\n"; exit 27; }',
                '    git -C "$repo" switch --detach "$a" || exit $?',
                '    printf "OK\\tDETACHED AT // %s\\n" "$a"',
                '    ;;',
                '  reset)',
                '    [ "$c" = "CONFIRM" ] || { printf "REFUSED\\tRESET REQUIRES CONFIRMATION\\n"; exit 28; }',
                '    [ -n "$a" ] || { printf "REFUSED\\tCOMMIT REQUIRED\\n"; exit 29; }',
                '    mode="$b"',
                '    case "$mode" in soft|mixed|hard) ;; *) printf "REFUSED\\tINVALID RESET MODE\\n"; exit 30 ;; esac',
                '    git -C "$repo" reset "--$mode" "$a" || exit $?',
                '    printf "OK\\tRESET %s // %s\\n" "$mode" "$a"',
                '    ;;',
                '  branch)',
                '    name="$a"; sha="$b"',
                '    git check-ref-format --branch "$name" >/dev/null 2>&1 || { printf "REFUSED\\tINVALID BRANCH NAME\\n"; exit 31; }',
                '    git -C "$repo" branch "$name" "$sha" || exit $?',
                '    printf "OK\\tBRANCH // %s @ %s\\n" "$name" "$sha"',
                '    ;;',
                '  tag)',
                '    name="$a"; sha="$b"',
                '    git check-ref-format "refs/tags/$name" >/dev/null 2>&1 || { printf "REFUSED\\tINVALID TAG NAME\\n"; exit 32; }',
                '    git -C "$repo" tag "$name" "$sha" || exit $?',
                '    printf "OK\\tTAG // %s @ %s\\n" "$name" "$sha"',
                '    ;;',
                '  copy-sha)',
                '    [ -n "$a" ] || { printf "REFUSED\\tSHA REQUIRED\\n"; exit 33; }',
                '    if command -v wl-copy >/dev/null 2>&1; then',
                '      printf "%s" "$a" | wl-copy || exit $?',
                '    elif command -v xclip >/dev/null 2>&1; then',
                '      printf "%s" "$a" | xclip -selection clipboard || exit $?',
                '    else',
                '      printf "REFUSED\\tNO CLIPBOARD COMMAND FOUND\\n"',
                '      exit 34',
                '    fi',
                '    printf "OK\\tCOPIED SHA // %s\\n" "$a"',
                '    ;;',
                '  *)',
                '    printf "REFUSED\\tUNKNOWN OPERATION // %s\\n" "$op"',
                '    exit 90',
                '    ;;',
                'esac'
            ].join("\n"),
            "git-history-action",
            repo,
            op,
            String(a || ""),
            String(b || ""),
            String(c || "")
        ]);

        return true;
    }

    function cherryPick(sha) {
        return runAction("cherry-pick", sha, "", "");
    }

    function revertCommit(sha) {
        return runAction("revert", sha, "", "");
    }

    function detachAt(sha) {
        return runAction("detach", sha, "", "");
    }

    function resetTo(sha, mode, confirmed) {
        return runAction(
            "reset",
            sha,
            mode || "mixed",
            confirmed ? "CONFIRM" : ""
        );
    }

    function createBranch(name, sha) {
        return runAction("branch", name, sha, "");
    }

    function createTag(name, sha) {
        return runAction("tag", name, sha, "");
    }

    function copySha(sha) {
        return runAction("copy-sha", sha, "", "");
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
        const lines = out.split("\n");
        let controlLine = "";

        for (let i = lines.length - 1; i >= 0; --i) {
            const line = String(lines[i] || "");
            if (line.indexOf("OK\t") === 0
                    || line.indexOf("REFUSED\t") === 0) {
                controlLine = line;
                break;
            }
        }

        const p = controlLine.split("\t");
        const kind = p.length > 0 ? p[0] : "";
        const detail =
            p.length > 1
            ? p.slice(1).join("\t")
            : String(err || out || ("EXIT " + actionExitCode)).trim();

        if (actionExitCode === 0 && kind === "OK") {
            actionStatus = detail || (actionName + " // OK");
            lastError = "";
            actionFinished(actionName, true, detail || "OK");
            refresh(selectedRef, selectedMode);
            return;
        }

        lastError = detail || (actionName + " FAILED");
        actionStatus = actionName + " // REFUSED";
        actionFinished(actionName, false, lastError);
    }

    Process {
        id: queryProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.queryStdoutText = this.text;
                root.queryStdoutSeen = true;
                root.maybeFinishQuery();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.queryStderrText = this.text;
                root.queryStderrSeen = true;
                root.maybeFinishQuery();
            }
        }

        onExited: function(code, exitStatus) {
            root.queryExitCode = Number(code);
            root.queryExitSeen = true;
            root.maybeFinishQuery();
        }
    }

    Process {
        id: reflogProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.reflogStdoutText = this.text;
                root.reflogStdoutSeen = true;
                root.maybeFinishReflog();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.reflogStderrText = this.text;
                root.reflogStderrSeen = true;
                root.maybeFinishReflog();
            }
        }

        onExited: function(code, exitStatus) {
            root.reflogExitCode = Number(code);
            root.reflogExitSeen = true;
            root.maybeFinishReflog();
        }
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
        id: detailProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.detailStdoutText = this.text;
                root.detailStdoutSeen = true;
                root.maybeFinishDetail();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.detailStderrText = this.text;
                root.detailStderrSeen = true;
                root.maybeFinishDetail();
            }
        }

        onExited: function(code, exitStatus) {
            root.detailExitCode = Number(code);
            root.detailExitSeen = true;
            root.maybeFinishDetail();
        }
    }

    Process {
        id: diffProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.diffStdoutText = this.text;
                root.diffStdoutSeen = true;
                root.maybeFinishDiff();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.diffStderrText = this.text;
                root.diffStderrSeen = true;
                root.maybeFinishDiff();
            }
        }

        onExited: function(code, exitStatus) {
            root.diffExitCode = Number(code);
            root.diffExitSeen = true;
            root.maybeFinishDiff();
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
