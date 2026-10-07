import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null

    property bool refreshing: false
    property bool actionBusy: false
    property string actionName: ""
    property string actionStatus: "READY"
    property string lastError: ""

    property string pendingJournalId: ""
    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property string pendingOperation: ""
    property var pendingArguments: []
    property bool pendingActionSuccess: false
    property string pendingActionDetail: ""

    property var remotes: []
    property var remoteBranches: []
    property var tags: []
    property var configRows: []

    property string tagRemoteCheckRemote: ""
    property string tagRemoteCheckTag: ""
    property string tagRemoteCheckState: "UNCHECKED"
    property string tagRemoteLocalTarget: ""
    property string tagRemoteTarget: ""
    property var submodules: []
    property var hooks: []
    property var ignoreLines: []
    property var attributeLines: []

    property string objectInfo: ""
    property string healthOutput: "RUN FSCK / GC / MAINTENANCE WHEN NEEDED"

    property int looseObjectCount: 0
    property int packedObjectCount: 0
    property int packCount: 0
    property int prunePackableCount: 0
    property int garbageObjectCount: 0
    property string looseObjectSize: "0 bytes"
    property string packedObjectSize: "0 bytes"
    property string garbageObjectSize: "0 bytes"

    property string healthState: "UNVERIFIED"
    property string healthSummary:
        "OBJECT GRAPH HAS NOT BEEN VERIFIED IN THIS SESSION"
    property string healthRecommendation:
        "Run FSCK for an integrity check. GC and maintenance are cleanup/optimization actions, not integrity tests."
    property int fsckDanglingCount: 0
    property int fsckUnreachableCount: 0
    property int fsckWarningCount: 0
    property int fsckErrorCount: 0

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
                '  remote_head="$(git -C "$repo" symbolic-ref --quiet --short "refs/remotes/$name/HEAD" 2>/dev/null || true)"',
                '  remote_head="${remote_head#"$name/"}"',
                '  prune="$(git -C "$repo" config --bool "remote.$name.prune" 2>/dev/null || true)"',
                '  [ -n "$prune" ] || prune="$(git -C "$repo" config --bool fetch.prune 2>/dev/null || true)"',
                '  [ -n "$prune" ] || prune="default"',
                '  printf "REMOTE\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$name" "$url" "$push" "$fetchspec" "$pushspec" "$remote_head" "$prune"',
                'done < <(git -C "$repo" remote 2>/dev/null)',
                'git -C "$repo" for-each-ref --sort=-committerdate --format="RBRANCH%x09%(refname:short)%09%(objectname:short=10)%09%(committerdate:unix)" refs/remotes 2>/dev/null || true',
                'head_sha="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                'git -C "$repo" for-each-ref --sort=-creatordate --format="%(refname:short)" refs/tags 2>/dev/null | while IFS= read -r tag; do',
                '  [ -n "$tag" ] || continue',
                '  object_sha="$(git -C "$repo" rev-parse "refs/tags/$tag" 2>/dev/null || true)"',
                '  object_type="$(git -C "$repo" cat-file -t "refs/tags/$tag" 2>/dev/null || true)"',
                '  peeled="$(git -C "$repo" rev-parse "refs/tags/$tag^{}" 2>/dev/null || true)"',
                '  target_type="$(git -C "$repo" cat-file -t "$peeled" 2>/dev/null || true)"',
                '  epoch="$(git -C "$repo" for-each-ref --format="%(creatordate:unix)" "refs/tags/$tag" 2>/dev/null)"',
                '  subject="$(git -C "$repo" for-each-ref --format="%(subject)" "refs/tags/$tag" 2>/dev/null)"',
                '  signed=0',
                '  if [ "$object_type" = "tag" ]; then',
                '    raw_tag="$(git -C "$repo" cat-file tag "refs/tags/$tag" 2>/dev/null || true)"',
                '    printf "%s" "$raw_tag" | grep -Eq -- "-----BEGIN (PGP|SSH) SIGNATURE-----" && signed=1',
                '  fi',
                '  at_head=0',
                '  [ -n "$head_sha" ] && [ "$peeled" = "$head_sha" ] && at_head=1',
                '  printf "TAG\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$tag" "${object_sha:0:10}" "$epoch" "$object_type" "$target_type" "$peeled" "$signed" "$at_head" "$subject"',
                'done',
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
                    pushSpec: p.length > 5 ? p[5] : "",
                    defaultBranch: p.length > 6 ? p[6] : "",
                    prune: p.length > 7 ? p[7] : "default"
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
                const objectType = p.length > 4 ? p[4] : "";
                const signed = p.length > 7 && p[7] === "1";
                const tagKind =
                    objectType === "tag"
                    ? (signed ? "signed" : "annotated")
                    : "lightweight";

                tagRows.push({
                    name: p.length > 1 ? p[1] : "",
                    shortSha: p.length > 2 ? p[2] : "",
                    epoch: p.length > 3 ? Number(p[3] || 0) : 0,
                    objectType: objectType,
                    targetType: p.length > 5 ? p[5] : "",
                    targetSha: p.length > 6 ? p[6] : "",
                    signed: signed,
                    atHead: p.length > 8 && p[8] === "1",
                    kind: tagKind,
                    subject: p.length > 9 ? p.slice(9).join("\t") : ""
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
        parseObjectMetrics(objects);
    }

    function parseObjectMetrics(lines) {
        const rows = Array.isArray(lines) ? lines : [];
        const values = {};

        for (let i = 0; i < rows.length; ++i) {
            const raw = String(rows[i] || "");
            const split = raw.indexOf(":");

            if (split <= 0)
                continue;

            const key =
                raw.slice(0, split).trim().toLowerCase();
            const value =
                raw.slice(split + 1).trim();

            values[key] = value;
        }

        looseObjectCount = Number(values["count"] || 0);
        packedObjectCount = Number(values["in-pack"] || 0);
        packCount = Number(values["packs"] || 0);
        prunePackableCount =
            Number(values["prune-packable"] || 0);
        garbageObjectCount =
            Number(values["garbage"] || 0);

        looseObjectSize =
            String(values["size"] || "0 bytes");
        packedObjectSize =
            String(values["size-pack"] || "0 bytes");
        garbageObjectSize =
            String(values["size-garbage"] || "0 bytes");
    }

    function interpretFsck(text, exitCode) {
        const raw = String(text || "");
        const lines = raw.split("\n");

        let dangling = 0;
        let unreachable = 0;
        let warnings = 0;
        let errors = 0;

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "").trim();
            const lower = line.toLowerCase();

            if (!line
                    || line.indexOf("OK\t") === 0
                    || line.indexOf("REFUSED\t") === 0)
                continue;

            if (lower.indexOf("dangling ") === 0) {
                dangling += 1;
                continue;
            }

            if (lower.indexOf("unreachable ") === 0) {
                unreachable += 1;
                continue;
            }

            if (lower.indexOf("warning:") === 0
                    || lower.indexOf("notice:") === 0) {
                warnings += 1;
                continue;
            }

            if (lower.indexOf("error:") === 0
                    || lower.indexOf("fatal:") === 0
                    || lower.indexOf("broken link") >= 0
                    || lower.indexOf("missing ") >= 0
                    || lower.indexOf("corrupt") >= 0
                    || lower.indexOf("hash mismatch") >= 0
                    || lower.indexOf("invalid sha1") >= 0
                    || lower.indexOf("bad object") >= 0)
                errors += 1;
        }

        const structuralErrors =
            Math.max(
                errors,
                Number(exitCode) !== 0 ? 1 : 0
            );

        fsckDanglingCount = dangling;
        fsckUnreachableCount = unreachable;
        fsckWarningCount = warnings;
        fsckErrorCount = structuralErrors;

        if (structuralErrors > 0) {
            healthState = "FAIL";
            healthSummary =
                "OBJECT GRAPH FAILED VERIFICATION // "
                + String(structuralErrors)
                + " STRUCTURAL ERROR"
                + (structuralErrors === 1 ? "" : "S");
            healthRecommendation =
                "Do not run cleanup as a first response. Preserve the repository, inspect the raw FSCK output, and compare against a known-good remote or backup before deleting objects.";
            return;
        }

        const recoverable = dangling + unreachable;

        if (recoverable > 0) {
            healthState = "RECOVERY";
            healthSummary =
                "OBJECT GRAPH VALID // "
                + String(recoverable)
                + " UNREFERENCED OBJECT"
                + (recoverable === 1 ? "" : "S");
            healthRecommendation =
                "This is not corruption. Rewrites, rebases, resets, and amended commits can leave recoverable objects. Use HISTORY → REFLOG before GC if you may want them back.";
            return;
        }

        if (warnings > 0) {
            healthState = "WARNING";
            healthSummary =
                "OBJECT GRAPH VERIFIED // "
                + String(warnings)
                + " WARNING"
                + (warnings === 1 ? "" : "S");
            healthRecommendation =
                "Read the raw FSCK warnings before cleanup. The graph verified, but Git reported conditions worth reviewing.";
            return;
        }

        healthState = "PASS";
        healthSummary = "OBJECT GRAPH VERIFIED // NO STRUCTURAL ERRORS";
        healthRecommendation =
            "No integrity problems were reported. GC --auto and maintenance are optional optimization steps, not repairs.";
    }

    function noteHealthAction(action, success) {
        const name = String(action || "");

        if (name === "GC-AUTO" && success) {
            healthRecommendation =
                "GC --auto completed. Existing FSCK integrity state is unchanged; run FSCK again if you want a post-cleanup verification.";
        } else if (name === "MAINTENANCE" && success) {
            healthRecommendation =
                "Maintenance completed. Existing FSCK integrity state is unchanged; run FSCK again if you want a post-maintenance verification.";
        }
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

    function shouldJournalOperation(operation) {
        const op = String(operation || "");

        return op !== "check-remote-tag"
            && op !== "fsck";
    }

    function forceEvidenceOnly(operation) {
        const op = String(operation || "");

        return [
            "remote-head",
            "add-remote",
            "rename-remote",
            "remove-remote",
            "set-url",
            "set-push-url",
            "set-fetchspec",
            "set-pushspec",
            "delete-remote-branch",
            "push-tag",
            "push-tags",
            "delete-remote-tag",
            "set-config",
            "unset-config",
            "submodule-sync",
            "hook-enable",
            "hook-disable",
            "worktree-prune",
            "worktree-lock",
            "worktree-unlock",
            "gc-auto",
            "maintenance"
        ].indexOf(op) >= 0;
    }

    function cloneSnapshot(snapshot) {
        try {
            return JSON.parse(JSON.stringify(snapshot || {}));
        } catch (error) {
            return {};
        }
    }

    function journalSnapshot(snapshot) {
        const out = cloneSnapshot(snapshot);

        if (forceEvidenceOnly(pendingOperation)) {
            out.recoveryClass = "EVIDENCE_ONLY";
            out.recoveryReason =
                "REPOSITORY OPERATION STATE IS NOT FULLY CAPTURED // "
                + String(pendingOperation || "").toUpperCase();
        }

        return out;
    }

    function clearPendingMutation() {
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        pendingOperation = "";
        pendingArguments = [];
        pendingActionSuccess = false;
        pendingActionDetail = "";
    }

    function mutationContext() {
        return {
            source: "GitRepositoryService",
            operation: String(pendingOperation || ""),
            arguments: pendingArguments.slice(),
            evidenceOnly: forceEvidenceOnly(pendingOperation)
        };
    }

    function failBeforeSnapshot(detail) {
        const action = String(actionName || pendingOperation || "ACTION");
        const message =
            "BEFORE SNAPSHOT FAILED // "
            + String(detail || "SNAPSHOT UNAVAILABLE");

        actionBusy = false;
        actionStatus = action + " // REFUSED";
        lastError = message;
        clearPendingMutation();
        actionFinished(action, false, message);
    }

    function executePendingAction() {
        const repo = String(repositoryPath || "").trim();
        const op = String(pendingOperation || "").trim();
        const args =
            Array.isArray(pendingArguments)
            ? pendingArguments
            : [];
        const a = args.length > 0 ? String(args[0] || "") : "";
        const b = args.length > 1 ? String(args[1] || "") : "";
        const c = args.length > 2 ? String(args[2] || "") : "";
        const d = args.length > 3 ? String(args[3] || "") : "";

        if (!repo || !op) {
            finalizeMutation(
                null,
                "PENDING REPOSITORY MUTATION IDENTITY LOST BEFORE EXECUTION"
            );
            return false;
        }

        actionProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'op="$2"',
                'a="$3"',
                'b="$4"',
                'c="$5"',
                'd="$6"',
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
                '  check-remote-tag)',
                '    remote="$a"; tag="$b"',
                '    [ -n "$remote" ] && [ -n "$tag" ] || { printf "REFUSED\\tREMOTE + TAG REQUIRED\\n"; exit 33; }',
                '    local_target="$(git -C "$repo" rev-parse "refs/tags/$tag^{}" 2>/dev/null || true)"',
                '    [ -n "$local_target" ] || { printf "REFUSED\\tLOCAL TAG NOT FOUND // %s\\n" "$tag"; exit 34; }',
                '    remote_rows="$(git -C "$repo" ls-remote --tags "$remote" "refs/tags/$tag" "refs/tags/$tag^{}" 2>&1)"; rc=$?',
                '    [ "$rc" -eq 0 ] || { printf "REFUSED\\tREMOTE TAG LOOKUP FAILED // %s\\n" "$remote_rows"; exit 35; }',
                '    remote_target="$(printf "%s\\n" "$remote_rows" | grep -F "refs/tags/$tag^{}" | head -n1 | cut -f1)"',
                '    [ -n "$remote_target" ] || remote_target="$(printf "%s\\n" "$remote_rows" | grep -F "refs/tags/$tag" | head -n1 | cut -f1)"',
                '    state="MISSING"',
                '    if [ -n "$remote_target" ]; then',
                '      if [ "$remote_target" = "$local_target" ]; then state="MATCH"; else state="DIVERGED"; fi',
                '    fi',
                '    printf "TAGCHECK\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$remote" "$tag" "$state" "$local_target" "$remote_target"',
                '    printf "OK\\tREMOTE TAG CHECK // %s/%s // %s\\n" "$remote" "$tag" "$state"',
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
                '    if grep -Fqx "$value" "$file" 2>/dev/null; then',
                '      printf "OK\\tLINE ALREADY EXISTS // %s\\n" "$value"',
                '    else',
                '      printf "%s\\n" "$value" >> "$file" || exit $?',
                '      printf "OK\\tAPPENDED %s // %s\\n" "$kind" "$value"',
                '    fi',
                '    ;;',
                '  remove-file-line)',
                '    kind="$a"; line="$b"; expected="$c"',
                '    if [ "$kind" = "ignore" ]; then file="$repo/.gitignore";',
                '    elif [ "$kind" = "attributes" ]; then file="$repo/.gitattributes";',
                '    else printf "REFUSED\\tUNKNOWN PROJECT FILE\\n"; exit 37; fi',
                '    [ -f "$file" ] || { printf "REFUSED\\tFILE NOT FOUND\\n"; exit 38; }',
                '    actual="$(sed -n "$' + '{line}p" "$file")"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tLINE CHANGED // REFRESH BEFORE REMOVING\\n"; exit 39; }',
                '    tmp="$(mktemp)"',
                '    awk -v n="$line" \'NR != n { print }\' "$file" > "$tmp" && cat "$tmp" > "$file" || { rm -f "$tmp"; exit 40; }',
                '    rm -f "$tmp"',
                '    printf "OK\\tREMOVED %s LINE // %s\\n" "$kind" "$line"',
                '    ;;',
                '  replace-file-line)',
                '    kind="$a"; line="$b"; expected="$c"; replacement="$d"',
                '    [ -n "$replacement" ] || { printf "REFUSED\\tREPLACEMENT LINE REQUIRED\\n"; exit 41; }',
                '    if [ "$kind" = "ignore" ]; then file="$repo/.gitignore";',
                '    elif [ "$kind" = "attributes" ]; then file="$repo/.gitattributes";',
                '    else printf "REFUSED\\tUNKNOWN PROJECT FILE\\n"; exit 42; fi',
                '    [ -f "$file" ] || { printf "REFUSED\\tFILE NOT FOUND\\n"; exit 43; }',
                '    actual="$(sed -n "$' + '{line}p" "$file")"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tLINE CHANGED // REFRESH BEFORE REPLACING\\n"; exit 44; }',
                '    if [ "$replacement" != "$expected" ] && grep -Fqx "$replacement" "$file" 2>/dev/null; then',
                '      printf "REFUSED\\tREPLACEMENT ALREADY EXISTS\\n"',
                '      exit 45',
                '    fi',
                '    tmp="$(mktemp)"',
                '    before=$((line - 1)); after=$((line + 1))',
                '    head -n "$before" "$file" > "$tmp" || { rm -f "$tmp"; exit 46; }',
                '    printf "%s\\n" "$replacement" >> "$tmp" || { rm -f "$tmp"; exit 46; }',
                '    tail -n "+$after" "$file" >> "$tmp" 2>/dev/null || true',
                '    cat "$tmp" > "$file" || { rm -f "$tmp"; exit 46; }',
                '    rm -f "$tmp"',
                '    printf "OK\\tREPLACED %s LINE // %s\\n" "$kind" "$line"',
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
                '    output="$(git -C "$repo" fsck --full --no-progress 2>&1)"; rc=$?',
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
            String(c || ""),
            String(d || "")
        ]);


        return true;
    }

    function runAction(operation, a, b, c, d) {
        const repo = String(repositoryPath || "").trim();
        const op = String(operation || "").trim();

        if (!repo || !op || refreshing || actionBusy)
            return false;

        if (shouldJournalOperation(op)
                && ((operationJournal && !snapshotService)
                    || (snapshotService && !operationJournal))) {
            lastError = "JOURNAL + SNAPSHOT SERVICES MUST BE PAIRED";
            return false;
        }

        clearPendingMutation();

        pendingOperation = op;
        pendingArguments = [
            String(a || ""),
            String(b || ""),
            String(c || ""),
            String(d || "")
        ];

        actionBusy = true;
        actionName = op.toUpperCase();
        actionStatus =
            shouldJournalOperation(op)
            && operationJournal
            && snapshotService
            ? actionName + " // SNAPSHOT BEFORE"
            : actionName + " // RUNNING";
        lastError = "";

        actionExitSeen = false;
        actionStdoutSeen = false;
        actionStderrSeen = false;
        actionExitCode = -1;
        actionStdoutText = "";
        actionStderrText = "";

        if (!shouldJournalOperation(op)
                || (!operationJournal && !snapshotService))
            return executePendingAction();

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "REPOSITORY BEFORE // " + actionName,
            mutationContext()
        );

        if (!pendingSnapshotRequest) {
            failBeforeSnapshot("SNAPSHOT SERVICE BUSY OR UNAVAILABLE");
            return false;
        }

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

    function clearTagRemoteCheck() {
        tagRemoteCheckRemote = "";
        tagRemoteCheckTag = "";
        tagRemoteCheckState = "UNCHECKED";
        tagRemoteLocalTarget = "";
        tagRemoteTarget = "";
    }

    function checkRemoteTag(remote, tag) {
        const remoteName = String(remote || "").trim();
        const tagName = String(tag || "").trim();

        if (!remoteName || !tagName)
            return false;

        tagRemoteCheckRemote = remoteName;
        tagRemoteCheckTag = tagName;
        tagRemoteCheckState = "CHECKING";
        tagRemoteLocalTarget = "";
        tagRemoteTarget = "";

        if (!runAction(
                "check-remote-tag",
                remoteName,
                tagName,
                ""
            )) {
            tagRemoteCheckState = "ERROR";
            return false;
        }

        return true;
    }

    function pushTag(remote, tag) {
        clearTagRemoteCheck();
        return runAction("push-tag", remote, tag, "");
    }

    function pushAllTags(remote) {
        return runAction("push-tags", remote, "", "");
    }

    function deleteRemoteTag(remote, tag, confirmed) {
        clearTagRemoteCheck();
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

    function removeProjectLine(kind, line, expectedText, confirmed) {
        if (!confirmed)
            return false;

        return runAction(
            "remove-file-line",
            kind,
            String(line),
            String(expectedText || ""),
            ""
        );
    }

    function replaceProjectLine(
        kind,
        line,
        expectedText,
        replacementText,
        confirmed
    ) {
        if (!confirmed)
            return false;

        return runAction(
            "replace-file-line",
            kind,
            String(line),
            String(expectedText || ""),
            String(replacementText || "")
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

    function finalizeMutation(afterSnapshot, snapshotWarning) {
        const action = String(actionName || pendingOperation || "ACTION");
        const detail = String(pendingActionDetail || "");
        const warning = String(snapshotWarning || "");
        const snapshot =
            afterSnapshot
            ? journalSnapshot(afterSnapshot)
            : {
                snapshotVersion: 1,
                repository: String(repositoryPath || ""),
                capturedAt: new Date().toISOString(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason:
                    warning
                    || "AFTER SNAPSHOT UNAVAILABLE"
            };

        if (pendingJournalId && operationJournal) {
            if (pendingActionSuccess)
                operationJournal.completeOperation(
                    pendingJournalId,
                    snapshot,
                    warning
                    ? detail + " // " + warning
                    : detail
                );
            else
                operationJournal.failOperation(
                    pendingJournalId,
                    snapshot,
                    warning
                    ? detail + " // " + warning
                    : detail
                );
        }

        actionBusy = false;

        if (pendingActionSuccess) {
            noteHealthAction(action, true);
            actionStatus = detail || (action + " // OK");
            if (warning)
                actionStatus += " // SNAPSHOT WARNING";
            lastError = warning;
        } else {
            if (action === "CHECK-REMOTE-TAG")
                tagRemoteCheckState = "ERROR";

            lastError = detail || (action + " FAILED");
            if (warning)
                lastError += " // " + warning;
            actionStatus = action + " // REFUSED";
        }

        const success = pendingActionSuccess;
        const finalDetail =
            warning
            ? (detail || (success ? "OK" : "FAILED"))
                + " // "
                + warning
            : (detail || (success ? "OK" : "FAILED"));

        clearPendingMutation();
        actionFinished(action, success, finalDetail);

        if (success)
            refresh();
    }

    function maybeFinishAction() {
        if (!actionBusy
                || !actionExitSeen
                || !actionStdoutSeen
                || !actionStderrSeen)
            return;

        const out = String(actionStdoutText || "").trim();
        const err = String(actionStderrText || "").trim();
        const lines = out.split("\n");
        let controlLine = "";

        if (actionName === "CHECK-REMOTE-TAG") {
            for (let i = 0; i < lines.length; ++i) {
                const line = String(lines[i] || "");
                if (line.indexOf("TAGCHECK\t") !== 0)
                    continue;

                const fields = line.split("\t");
                tagRemoteCheckRemote =
                    fields.length > 1 ? fields[1] : "";
                tagRemoteCheckTag =
                    fields.length > 2 ? fields[2] : "";
                tagRemoteCheckState =
                    fields.length > 3 ? fields[3] : "ERROR";
                tagRemoteLocalTarget =
                    fields.length > 4 ? fields[4] : "";
                tagRemoteTarget =
                    fields.length > 5 ? fields[5] : "";
                break;
            }
        }

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

        if (actionName === "FSCK")
            interpretFsck(out || err, actionExitCode);

        pendingActionSuccess =
            actionExitCode === 0
            && kind === "OK";
        pendingActionDetail =
            detail
            || (
                pendingActionSuccess
                ? "OK"
                : (actionName + " FAILED")
            );

        if (!shouldJournalOperation(pendingOperation)
                || !operationJournal
                || !snapshotService) {
            finalizeMutation(null, "");
            return;
        }

        actionStatus = actionName + " // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "REPOSITORY AFTER // " + actionName,
            mutationContext()
        );

        if (!pendingSnapshotRequest) {
            finalizeMutation(
                null,
                "AFTER SNAPSHOT COULD NOT START"
            );
        }
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
                const beforeSnapshot = root.journalSnapshot(snapshot);

                root.pendingJournalId =
                    root.operationJournal
                    ? root.operationJournal.beginOperation(
                        "REPOSITORY/"
                            + String(root.pendingOperation || "")
                                .toUpperCase(),
                        beforeSnapshot,
                        root.mutationContext()
                    )
                    : "";

                if (root.operationJournal
                        && !root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "JOURNAL RECORD COULD NOT START"
                    );
                    return;
                }

                root.actionStatus =
                    root.actionName + " // RUNNING";
                root.executePendingAction();
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeMutation(snapshot, "");
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
                root.finalizeMutation(
                    null,
                    "AFTER SNAPSHOT FAILED // "
                        + String(detail || "UNKNOWN ERROR")
                );
            }
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
