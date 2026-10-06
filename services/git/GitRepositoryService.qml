import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repositoryPath: ""

    property bool refreshing: false
    property bool actionBusy: false
    property string actionName: ""
    property string actionStatus: "READY"
    property string lastError: ""

    property var remotes: []
    property var remoteBranches: []
    property var tags: []
    property var configRows: []
    property var submodules: []
    property var hooks: []
    property var ignoreLines: []
    property var attributeLines: []

    property string objectInfo: ""
    property string healthOutput: "RUN FSCK / GC / MAINTENANCE WHEN NEEDED"

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

    function remoteAt(index) {
        if (index < 0 || index >= remotes.length)
            return null;
        return remotes[index];
    }

    function tagAt(index) {
        if (index < 0 || index >= tags.length)
            return null;
        return tags[index];
    }

    function refresh() {
        const repo = String(repositoryPath || "").trim();

        if (!repo || refreshing || actionBusy)
            return false;

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
                '  printf "ERROR\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'gitdir="$(git -C "$repo" rev-parse --git-dir 2>/dev/null)"',
                'case "$gitdir" in /*) ;; *) gitdir="$repo/$gitdir" ;; esac',
                'while IFS= read -r name; do',
                '  [ -z "$name" ] && continue',
                '  url="$(git -C "$repo" remote get-url "$name" 2>/dev/null || true)"',
                '  push="$(git -C "$repo" remote get-url --push "$name" 2>/dev/null || true)"',
                '  fetchspec="$(git -C "$repo" config --get-all "remote.$name.fetch" 2>/dev/null | paste -sd ";" -)"',
                '  pushspec="$(git -C "$repo" config --get-all "remote.$name.push" 2>/dev/null | paste -sd ";" -)"',
                '  printf "REMOTE\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$name" "$url" "$push" "$fetchspec" "$pushspec"',
                'done < <(git -C "$repo" remote 2>/dev/null)',
                'git -C "$repo" for-each-ref --sort=-committerdate --format="RBRANCH%x09%(refname:short)%09%(objectname:short=10)%09%(committerdate:unix)" refs/remotes 2>/dev/null || true',
                'git -C "$repo" for-each-ref --sort=-creatordate --format="TAG%x09%(refname:short)%09%(objectname:short=10)%09%(creatordate:unix)%09%(subject)" refs/tags 2>/dev/null',
                'git -C "$repo" config --local --list 2>/dev/null | while IFS= read -r line; do',
                '  key="${line%%=*}"; value="${line#*=}"',
                '  printf "CONFIG\\t%s\\t%s\\n" "$key" "$value"',
                'done',
                'git -C "$repo" submodule status --recursive 2>/dev/null | while IFS= read -r line; do',
                '  state="${line%${line#?}}"',
                '  rest="${line#?}"',
                '  sha="${rest%% *}"',
                '  rest="${rest#* }"',
                '  path="${rest%% *}"',
                '  printf "SUBMODULE\\t%s\\t%s\\t%s\\n" "$state" "$sha" "$path"',
                'done || true',
                'if [ -d "$gitdir/hooks" ]; then',
                '  for hook in "$gitdir"/hooks/*; do',
                '    [ -f "$hook" ] || continue',
                '    case "$hook" in *.sample) continue ;; esac',
                '    name="$(basename "$hook")"',
                '    if [ -x "$hook" ]; then enabled=1; else enabled=0; fi',
                '    printf "HOOK\\t%s\\t%s\\n" "$name" "$enabled"',
                '  done',
                'fi',
                'if [ -f "$repo/.gitignore" ]; then',
                '  awk \'{ printf "IGNORE\\t%d\\t%s\\n", NR, $0 }\' "$repo/.gitignore"',
                'fi',
                'if [ -f "$repo/.gitattributes" ]; then',
                '  awk \'{ printf "ATTR\\t%d\\t%s\\n", NR, $0 }\' "$repo/.gitattributes"',
                'fi',
                'git -C "$repo" count-objects -vH 2>/dev/null | while IFS= read -r line; do',
                '  printf "OBJECT\\t%s\\n" "$line"',
                'done'
            ].join("\n"),
            "git-repository-inspect",
            repo
        ]);

        return true;
    }

    function parseInspection(text) {
        const remoteRows = [];
        const remoteBranchRows = [];
        const tagRows = [];
        const configs = [];
        const modules = [];
        const hookRows = [];
        const ignores = [];
        const attrs = [];
        const objects = [];

        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            if (!line)
                continue;

            const p = line.split("\t");
            const kind = p.length > 0 ? p[0] : "";

            if (kind === "REMOTE") {
                remoteRows.push({
                    name: p.length > 1 ? p[1] : "",
                    url: p.length > 2 ? p[2] : "",
                    pushUrl: p.length > 3 ? p[3] : "",
                    fetchSpec: p.length > 4 ? p[4] : "",
                    pushSpec: p.length > 5 ? p[5] : ""
                });
            } else if (kind === "RBRANCH") {
                const name = p.length > 1 ? p[1] : "";
                if (name && name.indexOf("/HEAD") < 0) {
                    remoteBranchRows.push({
                        name: name,
                        remote:
                            name.indexOf("/") >= 0
                            ? name.split("/")[0]
                            : "",
                        shortSha: p.length > 2 ? p[2] : "",
                        epoch: p.length > 3 ? Number(p[3] || 0) : 0
                    });
                }
            } else if (kind === "TAG") {
                tagRows.push({
                    name: p.length > 1 ? p[1] : "",
                    shortSha: p.length > 2 ? p[2] : "",
                    epoch: p.length > 3 ? Number(p[3] || 0) : 0,
                    subject: p.length > 4 ? p.slice(4).join("\t") : ""
                });
            } else if (kind === "CONFIG") {
                configs.push({
                    key: p.length > 1 ? p[1] : "",
                    value: p.length > 2 ? p.slice(2).join("\t") : ""
                });
            } else if (kind === "SUBMODULE") {
                modules.push({
                    state: p.length > 1 ? p[1] : "",
                    sha: p.length > 2 ? p[2] : "",
                    path: p.length > 3 ? p.slice(3).join("\t") : ""
                });
            } else if (kind === "HOOK") {
                hookRows.push({
                    name: p.length > 1 ? p[1] : "",
                    enabled: p.length > 2 && p[2] === "1"
                });
            } else if (kind === "IGNORE") {
                ignores.push({
                    line: p.length > 1 ? Number(p[1] || 0) : 0,
                    text: p.length > 2 ? p.slice(2).join("\t") : ""
                });
            } else if (kind === "ATTR") {
                attrs.push({
                    line: p.length > 1 ? Number(p[1] || 0) : 0,
                    text: p.length > 2 ? p.slice(2).join("\t") : ""
                });
            } else if (kind === "OBJECT") {
                objects.push(p.length > 1 ? p.slice(1).join("\t") : "");
            } else if (kind === "ERROR") {
                lastError = p.length > 1
                    ? p.slice(1).join("\t")
                    : "REPOSITORY ERROR";
            }
        }

        remotes = remoteRows;
        remoteBranches = remoteBranchRows;
        tags = tagRows;
        configRows = configs;
        submodules = modules;
        hooks = hookRows;
        ignoreLines = ignores;
        attributeLines = attrs;
        objectInfo = objects.join("\n");
    }

    function maybeFinishInspection() {
        if (!refreshing
                || !inspectExitSeen
                || !inspectStdoutSeen
                || !inspectStderrSeen)
            return;

        refreshing = false;

        if (inspectExitCode !== 0) {
            lastError = String(
                inspectStderrText
                || inspectStdoutText
                || ("REPOSITORY EXIT " + inspectExitCode)
            ).trim();
            return;
        }

        parseInspection(inspectStdoutText);
        lastError = "";
        refreshed();
    }

    function runAction(operation, a, b, c) {
        const repo = String(repositoryPath || "").trim();
        const op = String(operation || "").trim();

        if (!repo || !op || refreshing || actionBusy)
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
                'gitdir="$(git -C "$repo" rev-parse --git-dir 2>/dev/null)"',
                'case "$gitdir" in /*) ;; *) gitdir="$repo/$gitdir" ;; esac',
                'case "$op" in',
                '  fetch)',
                '    [ -n "$a" ] || { printf "REFUSED\\tREMOTE REQUIRED\\n"; exit 22; }',
                '    git -C "$repo" fetch "$a" || exit $?',
                '    printf "OK\\tFETCHED // %s\\n" "$a"',
                '    ;;',
                '  prune-remote)',
                '    [ -n "$a" ] || { printf "REFUSED\\tREMOTE REQUIRED\\n"; exit 23; }',
                '    git -C "$repo" remote prune "$a" || exit $?',
                '    printf "OK\\tPRUNED REMOTE // %s\\n" "$a"',
                '    ;;',
                '  remote-head)',
                '    [ -n "$a" ] || { printf "REFUSED\\tREMOTE REQUIRED\\n"; exit 23; }',
                '    git -C "$repo" remote set-head "$a" -a || exit $?',
                '    printf "OK\\tSYNCHRONIZED REMOTE HEAD // %s\\n" "$a"',
                '    ;;',
                '  add-remote)',
                '    [ -n "$a" ] && [ -n "$b" ] || { printf "REFUSED\\tREMOTE NAME + URL REQUIRED\\n"; exit 24; }',
                '    git -C "$repo" remote get-url "$a" >/dev/null 2>&1 && { printf "REFUSED\\tREMOTE ALREADY EXISTS // %s\\n" "$a"; exit 25; }',
                '    git -C "$repo" remote add "$a" "$b" || exit $?',
                '    printf "OK\\tADDED REMOTE // %s\\n" "$a"',
                '    ;;',
                '  rename-remote)',
                '    [ -n "$a" ] && [ -n "$b" ] || { printf "REFUSED\\tOLD + NEW REMOTE NAMES REQUIRED\\n"; exit 26; }',
                '    git -C "$repo" remote rename "$a" "$b" || exit $?',
                '    printf "OK\\tRENAMED REMOTE // %s -> %s\\n" "$a" "$b"',
                '    ;;',
                '  remove-remote)',
                '    [ "$b" = "CONFIRM" ] || { printf "REFUSED\\tREMOTE REMOVE REQUIRES CONFIRMATION\\n"; exit 27; }',
                '    git -C "$repo" remote remove "$a" || exit $?',
                '    printf "OK\\tREMOVED REMOTE // %s\\n" "$a"',
                '    ;;',
                '  set-url)',
                '    git -C "$repo" remote set-url "$a" "$b" || exit $?',
                '    printf "OK\\tUPDATED FETCH URL // %s\\n" "$a"',
                '    ;;',
                '  set-push-url)',
                '    git -C "$repo" remote set-url --push "$a" "$b" || exit $?',
                '    printf "OK\\tUPDATED PUSH URL // %s\\n" "$a"',
                '    ;;',
                '  set-fetchspec)',
                '    git -C "$repo" config --local --replace-all "remote.$a.fetch" "$b" || exit $?',
                '    printf "OK\\tFETCH REFSPEC // %s\\n" "$a"',
                '    ;;',
                '  set-pushspec)',
                '    git -C "$repo" config --local --replace-all "remote.$a.push" "$b" || exit $?',
                '    printf "OK\\tPUSH REFSPEC // %s\\n" "$a"',
                '    ;;',
                '  delete-remote-branch)',
                '    [ "$c" = "CONFIRM" ] || { printf "REFUSED\\tREMOTE BRANCH DELETE REQUIRES CONFIRMATION\\n"; exit 28; }',
                '    remote="$a"; branch="$b"',
                '    [ -n "$remote" ] && [ -n "$branch" ] || { printf "REFUSED\\tREMOTE + BRANCH REQUIRED\\n"; exit 29; }',
                '    git -C "$repo" push "$remote" --delete "$branch" || exit $?',
                '    printf "OK\\tDELETED REMOTE BRANCH // %s/%s\\n" "$remote" "$branch"',
                '    ;;',
                '  create-tag-light|create-tag-annotated|create-tag-signed)',
                '    name="$a"; target="$b"; message="$c"; [ -n "$target" ] || target="HEAD"',
                '    git check-ref-format "refs/tags/$name" >/dev/null 2>&1 || { printf "REFUSED\\tINVALID TAG NAME\\n"; exit 30; }',
                '    case "$op" in',
                '      create-tag-annotated)',
                '        [ -n "$message" ] || message="$name"',
                '        git -C "$repo" tag -a "$name" "$target" -m "$message" || exit $?',
                '        ;;',
                '      create-tag-signed)',
                '        [ -n "$message" ] || message="$name"',
                '        git -C "$repo" tag -s "$name" "$target" -m "$message" || exit $?',
                '        ;;',
                '      *)',
                '        git -C "$repo" tag "$name" "$target" || exit $?',
                '        ;;',
                '    esac',
                '    printf "OK\\tCREATED TAG // %s\\n" "$name"',
                '    ;;',
                '  delete-tag)',
                '    [ "$b" = "CONFIRM" ] || { printf "REFUSED\\tTAG DELETE REQUIRES CONFIRMATION\\n"; exit 31; }',
                '    git -C "$repo" tag -d "$a" || exit $?',
                '    printf "OK\\tDELETED LOCAL TAG // %s\\n" "$a"',
                '    ;;',
                '  push-tag)',
                '    remote="$a"; tag="$b"',
                '    git -C "$repo" push "$remote" "refs/tags/$tag" || exit $?',
                '    printf "OK\\tPUSHED TAG // %s -> %s\\n" "$tag" "$remote"',
                '    ;;',
                '  push-tags)',
                '    git -C "$repo" push "$a" --tags || exit $?',
                '    printf "OK\\tPUSHED ALL TAGS // %s\\n" "$a"',
                '    ;;',
                '  delete-remote-tag)',
                '    [ "$c" = "CONFIRM" ] || { printf "REFUSED\\tREMOTE TAG DELETE REQUIRES CONFIRMATION\\n"; exit 32; }',
                '    [ -n "$a" ] && [ -n "$b" ] || { printf "REFUSED\\tREMOTE + TAG REQUIRED\\n"; exit 32; }',
                '    git -C "$repo" push "$a" ":refs/tags/$b" || exit $?',
                '    printf "OK\\tDELETED REMOTE TAG // %s/%s\\n" "$a" "$b"',
                '    ;;',
                '  set-config)',
                '    [ -n "$a" ] && [ -n "$b" ] || { printf "REFUSED\\tCONFIG KEY + VALUE REQUIRED\\n"; exit 32; }',
                '    case "$a" in *[!A-Za-z0-9._-]*|"") printf "REFUSED\\tINVALID CONFIG KEY\\n"; exit 33 ;; esac',
                '    git -C "$repo" config --local "$a" "$b" || exit $?',
                '    printf "OK\\tCONFIG // %s = %s\\n" "$a" "$b"',
                '    ;;',
                '  unset-config)',
                '    git -C "$repo" config --local --unset-all "$a" >/dev/null 2>&1 || true',
                '    printf "OK\\tUNSET CONFIG // %s\\n" "$a"',
                '    ;;',
                '  submodule-update)',
                '    git -C "$repo" submodule update --init --recursive || exit $?',
                '    printf "OK\\tSUBMODULES INITIALIZED + UPDATED\\n"',
                '    ;;',
                '  submodule-sync)',
                '    git -C "$repo" submodule sync --recursive || exit $?',
                '    printf "OK\\tSUBMODULE URLS SYNCED\\n"',
                '    ;;',
                '  hook-enable|hook-disable)',
                '    hook="$a"',
                '    path="$gitdir/hooks/$hook"',
                '    [ -f "$path" ] || { printf "REFUSED\\tHOOK NOT FOUND // %s\\n" "$hook"; exit 34; }',
                '    if [ "$op" = "hook-enable" ]; then chmod +x "$path"; state="ENABLED"; else chmod -x "$path"; state="DISABLED"; fi',
                '    printf "OK\\tHOOK %s // %s\\n" "$state" "$hook"',
                '    ;;',
                '  append-file-line)',
                '    kind="$a"; value="$b"',
                '    [ -n "$value" ] || { printf "REFUSED\\tLINE REQUIRED\\n"; exit 35; }',
                '    if [ "$kind" = "ignore" ]; then file="$repo/.gitignore";',
                '    elif [ "$kind" = "attributes" ]; then file="$repo/.gitattributes";',
                '    else printf "REFUSED\\tUNKNOWN PROJECT FILE\\n"; exit 36; fi',
                '    touch "$file" || exit $?',
                '    grep -Fqx "$value" "$file" 2>/dev/null || printf "%s\\n" "$value" >> "$file"',
                '    printf "OK\\tAPPENDED %s // %s\\n" "$kind" "$value"',
                '    ;;',
                '  remove-file-line)',
                '    [ "$c" = "CONFIRM" ] || { printf "REFUSED\\tLINE REMOVE REQUIRES CONFIRMATION\\n"; exit 37; }',
                '    kind="$a"; line="$b"',
                '    if [ "$kind" = "ignore" ]; then file="$repo/.gitignore";',
                '    elif [ "$kind" = "attributes" ]; then file="$repo/.gitattributes";',
                '    else printf "REFUSED\\tUNKNOWN PROJECT FILE\\n"; exit 38; fi',
                '    [ -f "$file" ] || { printf "REFUSED\\tFILE NOT FOUND\\n"; exit 39; }',
                '    tmp="$(mktemp)"',
                '    awk -v n="$line" \'NR != n { print }\' "$file" > "$tmp" && cat "$tmp" > "$file"',
                '    rm -f "$tmp"',
                '    printf "OK\\tREMOVED %s LINE // %s\\n" "$kind" "$line"',
                '    ;;',
                '  worktree-prune)',
                '    git -C "$repo" worktree prune -v || exit $?',
                '    printf "OK\\tPRUNED STALE WORKTREE METADATA\\n"',
                '    ;;',
                '  worktree-lock)',
                '    git -C "$repo" worktree lock "$a" || exit $?',
                '    printf "OK\\tLOCKED WORKTREE // %s\\n" "$a"',
                '    ;;',
                '  worktree-unlock)',
                '    git -C "$repo" worktree unlock "$a" || exit $?',
                '    printf "OK\\tUNLOCKED WORKTREE // %s\\n" "$a"',
                '    ;;',
                '  fsck)',
                '    output="$(git -C "$repo" fsck --no-progress 2>&1)"; rc=$?',
                '    printf "%s\\n" "$output"',
                '    [ "$rc" -eq 0 ] || exit "$rc"',
                '    printf "OK\\tFSCK PASS\\n"',
                '    ;;',
                '  gc-auto)',
                '    git -C "$repo" gc --auto || exit $?',
                '    printf "OK\\tGC AUTO COMPLETE\\n"',
                '    ;;',
                '  maintenance)',
                '    git -C "$repo" maintenance run --auto || exit $?',
                '    printf "OK\\tMAINTENANCE AUTO COMPLETE\\n"',
                '    ;;',
                '  *)',
                '    printf "REFUSED\\tUNKNOWN OPERATION // %s\\n" "$op"',
                '    exit 90',
                '    ;;',
                'esac'
            ].join("\n"),
            "git-repository-action",
            repo,
            op,
            String(a || ""),
            String(b || ""),
            String(c || "")
        ]);

        return true;
    }

    function fetchRemote(name) {
        return runAction("fetch", name, "", "");
    }

    function pruneRemote(name) {
        return runAction("prune-remote", name, "", "");
    }

    function syncRemoteHead(name) {
        return runAction("remote-head", name, "", "");
    }

    function addRemote(name, url) {
        return runAction("add-remote", name, url, "");
    }

    function renameRemote(oldName, newName) {
        return runAction("rename-remote", oldName, newName, "");
    }

    function removeRemote(name, confirmed) {
        return runAction(
            "remove-remote",
            name,
            confirmed ? "CONFIRM" : "",
            ""
        );
    }

    function setRemoteUrl(name, url) {
        return runAction("set-url", name, url, "");
    }

    function setPushUrl(name, url) {
        return runAction("set-push-url", name, url, "");
    }

    function setFetchSpec(name, spec) {
        return runAction("set-fetchspec", name, spec, "");
    }

    function setPushSpec(name, spec) {
        return runAction("set-pushspec", name, spec, "");
    }

    function deleteRemoteBranch(remote, branch, confirmed) {
        return runAction(
            "delete-remote-branch",
            remote,
            branch,
            confirmed ? "CONFIRM" : ""
        );
    }

    function createTag(name, target, mode, message) {
        const kind = String(mode || "lightweight");
        const operation =
            kind === "annotated"
            ? "create-tag-annotated"
            : kind === "signed"
            ? "create-tag-signed"
            : "create-tag-light";

        return runAction(
            operation,
            name,
            target || "HEAD",
            String(message || "").trim()
        );
    }

    function deleteTag(name, confirmed) {
        return runAction(
            "delete-tag",
            name,
            confirmed ? "CONFIRM" : "",
            ""
        );
    }

    function pushTag(remote, tag) {
        return runAction("push-tag", remote, tag, "");
    }

    function pushAllTags(remote) {
        return runAction("push-tags", remote, "", "");
    }

    function deleteRemoteTag(remote, tag, confirmed) {
        return runAction(
            "delete-remote-tag",
            remote,
            tag,
            confirmed ? "CONFIRM" : ""
        );
    }

    function setConfig(key, value) {
        return runAction("set-config", key, value, "");
    }

    function unsetConfig(key) {
        return runAction("unset-config", key, "", "");
    }

    function updateSubmodules() {
        return runAction("submodule-update", "", "", "");
    }

    function syncSubmodules() {
        return runAction("submodule-sync", "", "", "");
    }

    function setHookEnabled(name, enabled) {
        return runAction(
            enabled ? "hook-enable" : "hook-disable",
            name,
            "",
            ""
        );
    }

    function appendProjectLine(kind, value) {
        return runAction("append-file-line", kind, value, "");
    }

    function removeProjectLine(kind, line, confirmed) {
        return runAction(
            "remove-file-line",
            kind,
            String(line),
            confirmed ? "CONFIRM" : ""
        );
    }

    function pruneWorktrees() {
        return runAction("worktree-prune", "", "", "");
    }

    function lockWorktree(path) {
        return runAction("worktree-lock", path, "", "");
    }

    function unlockWorktree(path) {
        return runAction("worktree-unlock", path, "", "");
    }

    function runFsck() {
        return runAction("fsck", "", "", "");
    }

    function runGcAuto() {
        return runAction("gc-auto", "", "", "");
    }

    function runMaintenance() {
        return runAction("maintenance", "", "", "");
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

        if (actionName === "FSCK"
                || actionName === "GC-AUTO"
                || actionName === "MAINTENANCE")
            healthOutput = out || err || detail;

        if (actionExitCode === 0 && kind === "OK") {
            actionStatus = detail || (actionName + " // OK");
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
