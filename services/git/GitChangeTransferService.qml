import QtQuick
import Quickshell
import Quickshell.Io

// Safe first slice of GitButler-style change transfer.
//
// Scope:
//   - tracked, unstaged whole-file changes
//   - source is repositoryPath
//   - destination is an existing worktree of the same repository
//   - COPY or MOVE
//
// MOVE applies to the destination first, then reverses the exact previewed
// patch in the source. If source removal fails, destination application is
// rolled back. Staged, untracked, conflicted, or in-progress-operation state
// is refused rather than reconstructed implicitly.
Scope {
    id: root

    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null

    property bool previewBusy: false
    property bool transferBusy: false
    property string status: "TRANSFER // READY"
    property string lastError: ""

    property string pendingPreviewDestination: ""
    property string pendingPreviewScope: "file"
    property string pendingPreviewLayer: "worktree"
    property int pendingPreviewHunkIndex: -1
    property string previewDestinationPath: ""
    property string previewMode: "move"
    property string previewScope: "file"
    property string previewLayer: "worktree"
    property int previewHunkIndex: -1
    property var previewFiles: []
    property string previewFingerprint: ""
    property string previewPatchBase64: ""
    property int maxRecoveryPatchBytes: 524288
    property string previewSourceBranch: ""
    property string previewDestinationBranch: ""
    property string previewSourceHead: ""
    property string previewDestinationHead: ""
    property int previewPatchBytes: 0
    property int previewPatchLines: 0

    property string pendingJournalId: ""
    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property bool pendingTransferSuccess: false
    property string pendingTransferDetail: ""

    property bool previewExitSeen: false
    property bool previewStdoutSeen: false
    property bool previewStderrSeen: false
    property int previewExitCode: -1
    property string previewStdoutText: ""
    property string previewStderrText: ""

    property bool transferExitSeen: false
    property bool transferStdoutSeen: false
    property bool transferStderrSeen: false
    property int transferExitCode: -1
    property string transferStdoutText: ""
    property string transferStderrText: ""

    signal previewReady(var preview)
    signal previewFailed(string detail)
    signal transferFinished(bool success, string detail)

    readonly property bool hasPreview:
        previewFingerprint.length > 0
        && previewFiles.length > 0
        && previewDestinationPath.length > 0

    function normalizedMode(mode) {
        const value = String(mode || "move").trim().toLowerCase();
        return value === "copy" ? "copy" : "move";
    }

    function normalizedFiles(files) {
        const source = Array.isArray(files) ? files : [];
        const out = [];
        const seen = {};

        for (let i = 0; i < source.length; ++i) {
            const value = String(source[i] || "").trim();

            if (!value
                    || value.charAt(0) === "/"
                    || value === ".."
                    || value.indexOf("../") === 0
                    || value.indexOf("/../") >= 0
                    || seen[value])
                continue;

            seen[value] = true;
            out.push(value);
        }

        return out;
    }

    function clearPreview() {
        pendingPreviewDestination = "";
        pendingPreviewScope = "file";
        pendingPreviewLayer = "worktree";
        pendingPreviewHunkIndex = -1;
        previewDestinationPath = "";
        previewMode = "move";
        previewScope = "file";
        previewLayer = "worktree";
        previewHunkIndex = -1;
        previewFiles = [];
        previewFingerprint = "";
        previewPatchBase64 = "";
        previewSourceBranch = "";
        previewDestinationBranch = "";
        previewSourceHead = "";
        previewDestinationHead = "";
        previewPatchBytes = 0;
        previewPatchLines = 0;
    }

    function journalKind() {
        if (previewLayer === "staged")
            return "CHANGES/TRANSFER_STAGED";

        return previewScope === "hunk"
            ? "CHANGES/TRANSFER_HUNK"
            : "CHANGES/TRANSFER";
    }

    function contentRecoverable() {
        return previewPatchBase64.length > 0
            && previewPatchBytes > 0
            && previewPatchBytes <= maxRecoveryPatchBytes;
    }

    function transferContext() {
        return {
            source: "GitChangeTransferService",
            operation:
                previewScope === "hunk"
                ? "TRANSFER_HUNK"
                : "TRANSFER",
            scope: String(previewScope || "file"),
            layer: String(previewLayer || "worktree"),
            hunkIndex: Number(previewHunkIndex),
            mode: String(previewMode || "move"),
            sourcePath: String(repositoryPath || ""),
            destinationPath: String(previewDestinationPath || ""),
            sourceBranch: String(previewSourceBranch || ""),
            destinationBranch: String(previewDestinationBranch || ""),
            sourceHead: String(previewSourceHead || ""),
            destinationHead: String(previewDestinationHead || ""),
            files: previewFiles.slice(),
            fingerprint: String(previewFingerprint || ""),
            patchBytes: Number(previewPatchBytes || 0),
            patchBase64:
                contentRecoverable()
                ? String(previewPatchBase64 || "")
                : "",
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
                "EXACT TRANSFER PATCH STORED IN JOURNAL";
        } else {
            out.recoveryClass = "EVIDENCE_ONLY";
            out.recoveryReason =
                previewPatchBytes > maxRecoveryPatchBytes
                ? "TRANSFER PATCH EXCEEDS RECOVERY PAYLOAD LIMIT"
                : "TRANSFER PATCH RECOVERY PAYLOAD UNAVAILABLE";
        }
        return out;
    }

    function preview(destinationPath, files, mode) {
        if (previewBusy || transferBusy)
            return false;

        const source = String(repositoryPath || "").trim();
        const destination = String(destinationPath || "").trim();
        const selected = normalizedFiles(files);
        const transferMode = normalizedMode(mode);

        clearPreview();
        lastError = "";

        if (!source || !destination || selected.length === 0) {
            lastError =
                !source
                ? "TRANSFER PREVIEW // NO SOURCE REPOSITORY"
                : !destination
                ? "TRANSFER PREVIEW // NO DESTINATION WORKTREE"
                : "TRANSFER PREVIEW // NO FILES SELECTED";
            status = lastError;
            previewFailed(lastError);
            return false;
        }

        const args = [
            "bash",
            "-lc",
            [
                'source="$1"',
                'destination="$2"',
                'mode="$3"',
                'shift 3',
                'files=("$@")',
                'refuse() { printf "REFUSED\\t%s\\n" "$1"; exit 1; }',
                'is_git_worktree() { git -C "$1" rev-parse --is-inside-work-tree >/dev/null 2>&1; }',
                'absolute_common() {',
                '  dir="$(git -C "$1" rev-parse --git-common-dir 2>/dev/null)" || return 1',
                '  case "$dir" in /*) ;; *) dir="$1/$dir" ;; esac',
                '  realpath "$dir" 2>/dev/null',
                '}',
                'active_state() {',
                '  repo="$1"',
                '  gitdir="$(git -C "$repo" rev-parse --git-dir 2>/dev/null)" || return 0',
                '  case "$gitdir" in /*) ;; *) gitdir="$repo/$gitdir" ;; esac',
                '  if [ -f "$gitdir/MERGE_HEAD" ]; then printf "MERGE";',
                '  elif [ -d "$gitdir/rebase-merge" ] || [ -d "$gitdir/rebase-apply" ]; then printf "REBASE";',
                '  elif [ -f "$gitdir/CHERRY_PICK_HEAD" ]; then printf "CHERRY_PICK";',
                '  elif [ -f "$gitdir/REVERT_HEAD" ]; then printf "REVERT";',
                '  else printf "NONE"; fi',
                '}',
                'is_git_worktree "$source" || refuse "SOURCE IS NOT A GIT WORKTREE"',
                'is_git_worktree "$destination" || refuse "DESTINATION IS NOT A GIT WORKTREE"',
                'source="$(realpath "$source")" || refuse "SOURCE PATH CANNOT BE RESOLVED"',
                'destination="$(realpath "$destination")" || refuse "DESTINATION PATH CANNOT BE RESOLVED"',
                '[ "$source" != "$destination" ] || refuse "SOURCE AND DESTINATION ARE THE SAME WORKTREE"',
                'src_common="$(absolute_common "$source")" || refuse "SOURCE COMMON GIT DIR UNAVAILABLE"',
                'dst_common="$(absolute_common "$destination")" || refuse "DESTINATION COMMON GIT DIR UNAVAILABLE"',
                '[ "$src_common" = "$dst_common" ] || refuse "DESTINATION BELONGS TO A DIFFERENT REPOSITORY"',
                'src_branch="$(git -C "$source" branch --show-current 2>/dev/null || true)"',
                'dst_branch="$(git -C "$destination" branch --show-current 2>/dev/null || true)"',
                'src_head="$(git -C "$source" rev-parse HEAD 2>/dev/null || true)"',
                'dst_head="$(git -C "$destination" rev-parse HEAD 2>/dev/null || true)"',
                '[ -n "$src_branch" ] || refuse "SOURCE WORKTREE IS DETACHED"',
                '[ -n "$dst_branch" ] || refuse "DESTINATION WORKTREE IS DETACHED"',
                '[ "$src_branch" != "$dst_branch" ] || refuse "SOURCE AND DESTINATION USE THE SAME BRANCH"',
                '[ "$(active_state "$source")" = "NONE" ] || refuse "SOURCE HAS AN ACTIVE GIT OPERATION"',
                '[ "$(active_state "$destination")" = "NONE" ] || refuse "DESTINATION HAS AN ACTIVE GIT OPERATION"',
                '[ -z "$(git -C "$destination" status --porcelain=v1 --untracked-files=all 2>/dev/null)" ] || refuse "DESTINATION WORKTREE IS NOT CLEAN"',
                'for path in "${files[@]}"; do',
                '  git -C "$source" ls-files --error-unmatch -- "$path" >/dev/null 2>&1 || refuse "UNTRACKED OR UNKNOWN SOURCE PATH // $path"',
                '  [ -z "$(git -C "$source" ls-files -u -- "$path" 2>/dev/null)" ] || refuse "CONFLICTED SOURCE PATH // $path"',
                'done',
                'git -C "$source" diff --cached --quiet -- "${files[@]}"',
                'rc=$?',
                '[ "$rc" -eq 0 ] || { [ "$rc" -eq 1 ] && refuse "SELECTED PATH HAS STAGED CHANGES"; refuse "STAGED DIFF CHECK FAILED"; }',
                'git -C "$source" diff --quiet -- "${files[@]}"',
                'rc=$?',
                '[ "$rc" -eq 1 ] || { [ "$rc" -eq 0 ] && refuse "SELECTED PATHS HAVE NO UNSTAGED CHANGES"; refuse "WORKTREE DIFF CHECK FAILED"; }',
                'patch="$(mktemp "${TMPDIR:-/tmp}/pa-transfer-preview.XXXXXX")" || refuse "TEMP PATCH CREATE FAILED"',
                'trap \'rm -f "$patch"\' EXIT INT TERM',
                'git -C "$source" diff --binary --full-index -- "${files[@]}" >"$patch" || refuse "PATCH GENERATION FAILED"',
                '[ -s "$patch" ] || refuse "PATCH IS EMPTY"',
                'git -C "$destination" apply --check --binary "$patch" >/dev/null 2>&1 || refuse "PATCH DOES NOT APPLY CLEANLY TO DESTINATION"',
                'fingerprint="$(sha256sum "$patch" | awk "{print \\$1}")"',
                'bytes="$(wc -c <"$patch" | tr -d " ")"',
                'lines="$(wc -l <"$patch" | tr -d " ")"',
                'if [ "$bytes" -le "524288" ]; then printf "PATCH64\\t"; base64 -w0 "$patch"; printf "\\n"; fi',
                'printf "PREVIEW\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$fingerprint" "$bytes" "$lines" "$src_branch" "$dst_branch" "$src_head" "$dst_head" "$mode"',
                'for path in "${files[@]}"; do printf "FILE\\t%s\\n" "$path"; done'
            ].join("\n"),
            "git-change-transfer-preview",
            source,
            destination,
            transferMode
        ];

        for (let i = 0; i < selected.length; ++i)
            args.push(selected[i]);

        pendingPreviewDestination = destination;
        pendingPreviewScope = "file";
        pendingPreviewLayer = "worktree";
        pendingPreviewHunkIndex = -1;
        previewBusy = true;
        status = "TRANSFER // PREVIEWING";
        previewExitSeen = false;
        previewStdoutSeen = false;
        previewStderrSeen = false;
        previewExitCode = -1;
        previewStdoutText = "";
        previewStderrText = "";

        previewProcess.exec(args);
        return true;
    }

    function previewStaged(destinationPath, files, mode) {
        if (previewBusy || transferBusy)
            return false;

        const source = String(repositoryPath || "").trim();
        const destination = String(destinationPath || "").trim();
        const selected = normalizedFiles(files);
        const transferMode = normalizedMode(mode);

        clearPreview();
        lastError = "";

        if (!source || !destination || selected.length === 0) {
            lastError =
                !source
                ? "STAGED TRANSFER PREVIEW // NO SOURCE REPOSITORY"
                : !destination
                ? "STAGED TRANSFER PREVIEW // NO DESTINATION WORKTREE"
                : "STAGED TRANSFER PREVIEW // NO FILES SELECTED";
            status = lastError;
            previewFailed(lastError);
            return false;
        }

        const args = [
            "bash",
            "-lc",
            [
                'source="$1"',
                'destination="$2"',
                'mode="$3"',
                'shift 3',
                'files=("$@")',
                'refuse() { printf "REFUSED\\t%s\\n" "$1"; exit 1; }',
                'is_git_worktree() { git -C "$1" rev-parse --is-inside-work-tree >/dev/null 2>&1; }',
                'absolute_common() {',
                '  dir="$(git -C "$1" rev-parse --git-common-dir 2>/dev/null)" || return 1',
                '  case "$dir" in /*) ;; *) dir="$1/$dir" ;; esac',
                '  realpath "$dir" 2>/dev/null',
                '}',
                'active_state() {',
                '  repo="$1"',
                '  gitdir="$(git -C "$repo" rev-parse --git-dir 2>/dev/null)" || return 0',
                '  case "$gitdir" in /*) ;; *) gitdir="$repo/$gitdir" ;; esac',
                '  if [ -f "$gitdir/MERGE_HEAD" ]; then printf "MERGE";',
                '  elif [ -d "$gitdir/rebase-merge" ] || [ -d "$gitdir/rebase-apply" ]; then printf "REBASE";',
                '  elif [ -f "$gitdir/CHERRY_PICK_HEAD" ]; then printf "CHERRY_PICK";',
                '  elif [ -f "$gitdir/REVERT_HEAD" ]; then printf "REVERT";',
                '  else printf "NONE"; fi',
                '}',
                'is_git_worktree "$source" || refuse "SOURCE IS NOT A GIT WORKTREE"',
                'is_git_worktree "$destination" || refuse "DESTINATION IS NOT A GIT WORKTREE"',
                'source="$(realpath "$source")" || refuse "SOURCE PATH CANNOT BE RESOLVED"',
                'destination="$(realpath "$destination")" || refuse "DESTINATION PATH CANNOT BE RESOLVED"',
                '[ "$source" != "$destination" ] || refuse "SOURCE AND DESTINATION ARE THE SAME WORKTREE"',
                'src_common="$(absolute_common "$source")" || refuse "SOURCE COMMON GIT DIR UNAVAILABLE"',
                'dst_common="$(absolute_common "$destination")" || refuse "DESTINATION COMMON GIT DIR UNAVAILABLE"',
                '[ "$src_common" = "$dst_common" ] || refuse "DESTINATION BELONGS TO A DIFFERENT REPOSITORY"',
                'src_branch="$(git -C "$source" branch --show-current 2>/dev/null || true)"',
                'dst_branch="$(git -C "$destination" branch --show-current 2>/dev/null || true)"',
                'src_head="$(git -C "$source" rev-parse HEAD 2>/dev/null || true)"',
                'dst_head="$(git -C "$destination" rev-parse HEAD 2>/dev/null || true)"',
                '[ -n "$src_branch" ] || refuse "SOURCE WORKTREE IS DETACHED"',
                '[ -n "$dst_branch" ] || refuse "DESTINATION WORKTREE IS DETACHED"',
                '[ "$src_branch" != "$dst_branch" ] || refuse "SOURCE AND DESTINATION USE THE SAME BRANCH"',
                '[ "$(active_state "$source")" = "NONE" ] || refuse "SOURCE HAS AN ACTIVE GIT OPERATION"',
                '[ "$(active_state "$destination")" = "NONE" ] || refuse "DESTINATION HAS AN ACTIVE GIT OPERATION"',
                '[ -z "$(git -C "$destination" status --porcelain=v1 --untracked-files=all 2>/dev/null)" ] || refuse "DESTINATION WORKTREE IS NOT CLEAN"',
                'for path in "$@"; do',
                '  git -C "$source" ls-files --error-unmatch -- "$path" >/dev/null 2>&1 || refuse "UNTRACKED OR UNKNOWN SOURCE PATH // $path"',
                '  [ -z "$(git -C "$source" ls-files -u -- "$path" 2>/dev/null)" ] || refuse "CONFLICTED SOURCE PATH // $path"',
                'done',
                'git -C "$source" diff --cached --quiet -- "$@"',
                'rc=$?',
                '[ "$rc" -eq 1 ] || { [ "$rc" -eq 0 ] && refuse "SELECTED PATHS HAVE NO STAGED CHANGES"; refuse "STAGED DIFF CHECK FAILED"; }',
                'git -C "$source" diff --quiet -- "$@"',
                'rc=$?',
                '[ "$rc" -eq 0 ] || { [ "$rc" -eq 1 ] && refuse "SELECTED PATH HAS UNSTAGED CHANGES // PARTIALLY STAGED TRANSFER IS NOT IMPLEMENTED"; refuse "WORKTREE DIFF CHECK FAILED"; }',
                'patch="$(mktemp /tmp/pa-staged-transfer-preview.XXXXXX)" || refuse "TEMP PATCH CREATE FAILED"',
                'trap \'rm -f "$patch"\' EXIT INT TERM',
                'git -C "$source" diff --cached --binary --full-index -- "$@" >"$patch" || refuse "STAGED PATCH GENERATION FAILED"',
                '[ -s "$patch" ] || refuse "STAGED PATCH IS EMPTY"',
                'git -C "$destination" apply --check --index --binary "$patch" >/dev/null 2>&1 || refuse "STAGED PATCH DOES NOT APPLY CLEANLY TO DESTINATION INDEX"',
                'if [ "$mode" = "move" ]; then git -C "$source" apply -R --check --index --binary "$patch" >/dev/null 2>&1 || refuse "SOURCE STAGED PATCH CANNOT BE REMOVED CLEANLY"; fi',
                'fingerprint="$(sha256sum "$patch" | awk "{print \\$1}")"',
                'bytes="$(wc -c <"$patch" | tr -d " ")"',
                'lines="$(wc -l <"$patch" | tr -d " ")"',
                'if [ "$bytes" -le "524288" ]; then printf "PATCH64\\t"; base64 -w0 "$patch"; printf "\\n"; fi',
                'printf "PREVIEW\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$fingerprint" "$bytes" "$lines" "$src_branch" "$dst_branch" "$src_head" "$dst_head" "$mode"',
                'for path in "$@"; do printf "FILE\\t%s\\n" "$path"; done'
            ].join("\n"),
            "git-staged-change-transfer-preview",
            source,
            destination,
            transferMode
        ];

        for (let i = 0; i < selected.length; ++i)
            args.push(selected[i]);

        pendingPreviewDestination = destination;
        pendingPreviewScope = "file";
        pendingPreviewLayer = "staged";
        pendingPreviewHunkIndex = -1;
        previewBusy = true;
        status = "TRANSFER // PREVIEWING STAGED";
        previewExitSeen = false;
        previewStdoutSeen = false;
        previewStderrSeen = false;
        previewExitCode = -1;
        previewStdoutText = "";
        previewStderrText = "";

        previewProcess.exec(args);
        return true;
    }

    function previewHunk(destinationPath, path, hunkIndex, mode) {
        if (previewBusy || transferBusy)
            return false;

        const source = String(repositoryPath || "").trim();
        const destination = String(destinationPath || "").trim();
        const target = String(path || "").trim();
        const index = Number(hunkIndex);
        const transferMode = normalizedMode(mode);

        clearPreview();
        lastError = "";

        if (!source
                || !destination
                || !target
                || !Number.isInteger(index)
                || index < 0) {
            lastError =
                !source
                ? "HUNK TRANSFER PREVIEW // NO SOURCE REPOSITORY"
                : !destination
                ? "HUNK TRANSFER PREVIEW // NO DESTINATION WORKTREE"
                : !target
                ? "HUNK TRANSFER PREVIEW // NO FILE SELECTED"
                : "HUNK TRANSFER PREVIEW // INVALID HUNK";
            status = lastError;
            previewFailed(lastError);
            return false;
        }

        const args = [
            "bash",
            "-lc",
            [
                'source="$1"',
                'destination="$2"',
                'mode="$3"',
                'path="$4"',
                'hunk_index="$5"',
                'refuse() { printf "REFUSED\\t%s\\n" "$1"; exit 1; }',
                'is_git_worktree() { git -C "$1" rev-parse --is-inside-work-tree >/dev/null 2>&1; }',
                'absolute_common() {',
                '  dir="$(git -C "$1" rev-parse --git-common-dir 2>/dev/null)" || return 1',
                '  case "$dir" in /*) ;; *) dir="$1/$dir" ;; esac',
                '  realpath "$dir" 2>/dev/null',
                '}',
                'active_state() {',
                '  repo="$1"',
                '  gitdir="$(git -C "$repo" rev-parse --git-dir 2>/dev/null)" || return 0',
                '  case "$gitdir" in /*) ;; *) gitdir="$repo/$gitdir" ;; esac',
                '  if [ -f "$gitdir/MERGE_HEAD" ]; then printf "MERGE";',
                '  elif [ -d "$gitdir/rebase-merge" ] || [ -d "$gitdir/rebase-apply" ]; then printf "REBASE";',
                '  elif [ -f "$gitdir/CHERRY_PICK_HEAD" ]; then printf "CHERRY_PICK";',
                '  elif [ -f "$gitdir/REVERT_HEAD" ]; then printf "REVERT";',
                '  else printf "NONE"; fi',
                '}',
                'is_git_worktree "$source" || refuse "SOURCE IS NOT A GIT WORKTREE"',
                'is_git_worktree "$destination" || refuse "DESTINATION IS NOT A GIT WORKTREE"',
                'source="$(realpath "$source")" || refuse "SOURCE PATH CANNOT BE RESOLVED"',
                'destination="$(realpath "$destination")" || refuse "DESTINATION PATH CANNOT BE RESOLVED"',
                '[ "$source" != "$destination" ] || refuse "SOURCE AND DESTINATION ARE THE SAME WORKTREE"',
                'src_common="$(absolute_common "$source")" || refuse "SOURCE COMMON GIT DIR UNAVAILABLE"',
                'dst_common="$(absolute_common "$destination")" || refuse "DESTINATION COMMON GIT DIR UNAVAILABLE"',
                '[ "$src_common" = "$dst_common" ] || refuse "DESTINATION BELONGS TO A DIFFERENT REPOSITORY"',
                'src_branch="$(git -C "$source" branch --show-current 2>/dev/null || true)"',
                'dst_branch="$(git -C "$destination" branch --show-current 2>/dev/null || true)"',
                'src_head="$(git -C "$source" rev-parse HEAD 2>/dev/null || true)"',
                'dst_head="$(git -C "$destination" rev-parse HEAD 2>/dev/null || true)"',
                '[ -n "$src_branch" ] || refuse "SOURCE WORKTREE IS DETACHED"',
                '[ -n "$dst_branch" ] || refuse "DESTINATION WORKTREE IS DETACHED"',
                '[ "$src_branch" != "$dst_branch" ] || refuse "SOURCE AND DESTINATION USE THE SAME BRANCH"',
                '[ "$(active_state "$source")" = "NONE" ] || refuse "SOURCE HAS AN ACTIVE GIT OPERATION"',
                '[ "$(active_state "$destination")" = "NONE" ] || refuse "DESTINATION HAS AN ACTIVE GIT OPERATION"',
                '[ -z "$(git -C "$destination" status --porcelain=v1 --untracked-files=all 2>/dev/null)" ] || refuse "DESTINATION WORKTREE IS NOT CLEAN"',
                'git -C "$source" ls-files --error-unmatch -- "$path" >/dev/null 2>&1 || refuse "UNTRACKED OR UNKNOWN SOURCE PATH // $path"',
                '[ -z "$(git -C "$source" ls-files -u -- "$path" 2>/dev/null)" ] || refuse "CONFLICTED SOURCE PATH // $path"',
                'git -C "$source" diff --cached --quiet -- "$path"',
                'rc=$?',
                '[ "$rc" -eq 0 ] || { [ "$rc" -eq 1 ] && refuse "SELECTED PATH HAS STAGED CHANGES"; refuse "STAGED DIFF CHECK FAILED"; }',
                'patch="$(mktemp "${TMPDIR:-/tmp}/pa-hunk-transfer-preview.XXXXXX")" || refuse "TEMP PATCH CREATE FAILED"',
                'trap \'rm -f "$patch"\' EXIT INT TERM',
                'python3 - "$source" "$path" "$hunk_index" "$patch" <<\'PY\'',
                'import subprocess, sys',
                'repo, path, idx_text, output = sys.argv[1:5]',
                'try:',
                '    idx = int(idx_text)',
                'except ValueError:',
                '    print("INVALID HUNK INDEX", file=sys.stderr); sys.exit(41)',
                'proc = subprocess.run(["git", "-C", repo, "diff", "--no-ext-diff", "--binary", "--", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
                'if proc.returncode != 0:',
                '    sys.stderr.buffer.write(proc.stderr); sys.exit(proc.returncode)',
                'lines = proc.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
                'header, hunks, current = [], [], None',
                'for line in lines:',
                '    if line.startswith("@@"):',
                '        if current is not None: hunks.append(current)',
                '        current = [line]',
                '    elif current is None:',
                '        header.append(line)',
                '    else:',
                '        current.append(line)',
                'if current is not None: hunks.append(current)',
                'if idx < 0 or idx >= len(hunks):',
                '    print("HUNK NOT FOUND", file=sys.stderr); sys.exit(42)',
                'patch = "".join(header + hunks[idx]).encode("utf-8", "surrogateescape")',
                'with open(output, "wb") as handle: handle.write(patch)',
                'PY',
                'rc=$?',
                '[ "$rc" -eq 0 ] || refuse "HUNK PATCH GENERATION FAILED"',
                '[ -s "$patch" ] || refuse "HUNK PATCH IS EMPTY"',
                'git -C "$destination" apply --check --binary "$patch" >/dev/null 2>&1 || refuse "HUNK DOES NOT APPLY CLEANLY TO DESTINATION"',
                'fingerprint="$(sha256sum "$patch" | awk "{print \\$1}")"',
                'bytes="$(wc -c <"$patch" | tr -d " ")"',
                'lines="$(wc -l <"$patch" | tr -d " ")"',
                'if [ "$bytes" -le "524288" ]; then printf "PATCH64\\t"; base64 -w0 "$patch"; printf "\\n"; fi',
                'printf "PREVIEW\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$fingerprint" "$bytes" "$lines" "$src_branch" "$dst_branch" "$src_head" "$dst_head" "$mode"',
                'printf "FILE\\t%s\\n" "$path"'
            ].join("\n"),
            "git-change-hunk-transfer-preview",
            source,
            destination,
            transferMode,
            target,
            String(index)
        ];

        pendingPreviewDestination = destination;
        pendingPreviewScope = "hunk";
        pendingPreviewLayer = "worktree";
        pendingPreviewHunkIndex = index;
        previewBusy = true;
        status = "HUNK TRANSFER // PREVIEWING";
        previewExitSeen = false;
        previewStdoutSeen = false;
        previewStderrSeen = false;
        previewExitCode = -1;
        previewStdoutText = "";
        previewStderrText = "";

        previewProcess.exec(args);
        return true;
    }

    function maybeFinishPreview() {
        if (!previewBusy
                || !previewExitSeen
                || !previewStdoutSeen
                || !previewStderrSeen)
            return;

        previewBusy = false;

        const out = String(previewStdoutText || "").trim();
        const err = String(previewStderrText || "").trim();
        const lines = out.split("\n");
        let header = null;
        let patchBase64 = "";
        const files = [];

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");

            if (line.indexOf("PREVIEW\t") === 0)
                header = line.split("\t");
            else if (line.indexOf("PATCH64\t") === 0)
                patchBase64 = line.slice(8);
            else if (line.indexOf("FILE\t") === 0)
                files.push(line.slice(5));
        }

        if (previewExitCode !== 0 || !header || header.length < 9) {
            let refused = "";

            for (let i = 0; i < lines.length; ++i) {
                if (String(lines[i] || "").indexOf("REFUSED\t") === 0) {
                    refused = String(lines[i] || "");
                    break;
                }
            }

            const detail =
                refused
                ? refused.slice(8)
                : String(err || out || ("PREVIEW EXIT " + previewExitCode)).trim();

            clearPreview();
            lastError = detail || "TRANSFER PREVIEW FAILED";
            status = "TRANSFER // REFUSED";
            previewFailed(lastError);
            return;
        }

        previewFingerprint = String(header[1] || "");
        previewPatchBase64 = String(patchBase64 || "");
        previewPatchBytes = Number(header[2] || 0);
        previewPatchLines = Number(header[3] || 0);
        previewSourceBranch = String(header[4] || "");
        previewDestinationBranch = String(header[5] || "");
        previewSourceHead = String(header[6] || "");
        previewDestinationHead = String(header[7] || "");
        previewMode = normalizedMode(header[8]);
        previewDestinationPath = String(pendingPreviewDestination || "");
        previewScope = String(pendingPreviewScope || "file");
        previewLayer = String(pendingPreviewLayer || "worktree");
        previewHunkIndex =
            previewScope === "hunk"
            ? Number(pendingPreviewHunkIndex)
            : -1;
        previewFiles = files;
        pendingPreviewDestination = "";
        pendingPreviewScope = "file";
        pendingPreviewLayer = "worktree";
        pendingPreviewHunkIndex = -1;
        lastError = "";
        status =
            "TRANSFER // PREVIEW READY // "
            + String(files.length)
            + " FILE"
            + (files.length === 1 ? "" : "S");

        previewReady({
            sourcePath: String(repositoryPath || ""),
            destinationPath: previewDestinationPath,
            sourceBranch: previewSourceBranch,
            destinationBranch: previewDestinationBranch,
            sourceHead: previewSourceHead,
            destinationHead: previewDestinationHead,
            mode: previewMode,
            scope: previewScope,
            layer: previewLayer,
            hunkIndex: previewHunkIndex,
            files: previewFiles.slice(),
            fingerprint: previewFingerprint,
            patchBytes: previewPatchBytes,
            recoveryClass:
                contentRecoverable()
                ? "CONTENT_RECOVERABLE"
                : "EVIDENCE_ONLY",
            patchLines: previewPatchLines
        });
    }

    function execute() {
        if (previewBusy || transferBusy || !hasPreview)
            return false;

        if ((operationJournal && !snapshotService)
                || (snapshotService && !operationJournal)) {
            lastError = "JOURNAL + SNAPSHOT SERVICES MUST BE PAIRED";
            status = "TRANSFER // REFUSED";
            return false;
        }

        transferBusy = true;
        status = "TRANSFER // SNAPSHOT BEFORE";
        lastError = "";
        pendingTransferSuccess = false;
        pendingTransferDetail = "";

        transferExitSeen = false;
        transferStdoutSeen = false;
        transferStderrSeen = false;
        transferExitCode = -1;
        transferStdoutText = "";
        transferStderrText = "";

        if (!operationJournal && !snapshotService)
            return executeTransferProcess();

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "CHANGES BEFORE // TRANSFER",
            transferContext()
        );

        if (!pendingSnapshotRequest) {
            failBeforeSnapshot("SNAPSHOT SERVICE BUSY OR UNAVAILABLE");
            return false;
        }

        return true;
    }

    function failBeforeSnapshot(detail) {
        const message =
            "TRANSFER BEFORE SNAPSHOT FAILED // "
            + String(detail || "SNAPSHOT UNAVAILABLE");

        transferBusy = false;
        status = "TRANSFER // REFUSED";
        lastError = message;
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        transferFinished(false, message);
    }

    function executeTransferProcess() {
        const source = String(repositoryPath || "").trim();
        const destination = String(previewDestinationPath || "").trim();
        const mode = normalizedMode(previewMode);
        const files =
            Array.isArray(previewFiles)
            ? previewFiles.slice()
            : [];
        const fingerprint = String(previewFingerprint || "");
        const sourceHead = String(previewSourceHead || "");
        const destinationHead = String(previewDestinationHead || "");
        const scope = String(previewScope || "file");
        const hunkIndex = Number(previewHunkIndex);

        if (!source
                || !destination
                || files.length === 0
                || !fingerprint
                || !sourceHead
                || !destinationHead) {
            finalizeTransfer(
                null,
                "TRANSFER PREVIEW IDENTITY LOST BEFORE EXECUTION"
            );
            return false;
        }

        const args = [
            "bash",
            "-lc",
            [
                'source="$1"',
                'destination="$2"',
                'mode="$3"',
                'expected="$4"',
                'expected_source_head="$5"',
                'expected_destination_head="$6"',
                'scope="$7"',
                'hunk_index="$8"',
                'shift 8',
                'files=("$@")',
                'refuse() { printf "REFUSED\\t%s\\n" "$1"; exit 1; }',
                'source="$(realpath "$source")" || refuse "SOURCE PATH CANNOT BE RESOLVED"',
                'destination="$(realpath "$destination")" || refuse "DESTINATION PATH CANNOT BE RESOLVED"',
                '[ "$source" != "$destination" ] || refuse "SOURCE AND DESTINATION ARE THE SAME WORKTREE"',
                'src_common="$(git -C "$source" rev-parse --git-common-dir 2>/dev/null)" || refuse "SOURCE COMMON GIT DIR UNAVAILABLE"',
                'dst_common="$(git -C "$destination" rev-parse --git-common-dir 2>/dev/null)" || refuse "DESTINATION COMMON GIT DIR UNAVAILABLE"',
                'case "$src_common" in /*) ;; *) src_common="$source/$src_common" ;; esac',
                'case "$dst_common" in /*) ;; *) dst_common="$destination/$dst_common" ;; esac',
                'src_common="$(realpath "$src_common")"',
                'dst_common="$(realpath "$dst_common")"',
                '[ "$src_common" = "$dst_common" ] || refuse "DESTINATION BELONGS TO A DIFFERENT REPOSITORY"',
                '[ "$(git -C "$source" rev-parse HEAD 2>/dev/null || true)" = "$expected_source_head" ] || refuse "SOURCE HEAD CHANGED SINCE PREVIEW"',
                '[ "$(git -C "$destination" rev-parse HEAD 2>/dev/null || true)" = "$expected_destination_head" ] || refuse "DESTINATION HEAD CHANGED SINCE PREVIEW"',
                '[ -z "$(git -C "$destination" status --porcelain=v1 --untracked-files=all 2>/dev/null)" ] || refuse "DESTINATION CHANGED SINCE PREVIEW"',
                'for path in "${files[@]}"; do',
                '  git -C "$source" ls-files --error-unmatch -- "$path" >/dev/null 2>&1 || refuse "SOURCE PATH NO LONGER TRACKED // $path"',
                '  [ -z "$(git -C "$source" ls-files -u -- "$path" 2>/dev/null)" ] || refuse "SOURCE PATH BECAME CONFLICTED // $path"',
                'done',
                'git -C "$source" diff --cached --quiet -- "${files[@]}"',
                'rc=$?',
                '[ "$rc" -eq 0 ] || refuse "SELECTED PATH STAGING CHANGED SINCE PREVIEW"',
                'patch="$(mktemp "${TMPDIR:-/tmp}/pa-transfer-exec.XXXXXX")" || refuse "TEMP PATCH CREATE FAILED"',
                'trap \'rm -f "$patch"\' EXIT INT TERM',
                'if [ "$scope" = "hunk" ]; then',
                '  [ "${#files[@]}" -eq 1 ] || refuse "HUNK TRANSFER REQUIRES EXACTLY ONE FILE"',
                '  python3 - "$source" "${files[0]}" "$hunk_index" "$patch" <<\'PY\'',
                'import subprocess, sys',
                'repo, path, idx_text, output = sys.argv[1:5]',
                'try:',
                '    idx = int(idx_text)',
                'except ValueError:',
                '    print("INVALID HUNK INDEX", file=sys.stderr); sys.exit(43)',
                'proc = subprocess.run(["git", "-C", repo, "diff", "--no-ext-diff", "--binary", "--", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
                'if proc.returncode != 0:',
                '    sys.stderr.buffer.write(proc.stderr); sys.exit(proc.returncode)',
                'lines = proc.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
                'header, hunks, current = [], [], None',
                'for line in lines:',
                '    if line.startswith("@@"):',
                '        if current is not None: hunks.append(current)',
                '        current = [line]',
                '    elif current is None:',
                '        header.append(line)',
                '    else:',
                '        current.append(line)',
                'if current is not None: hunks.append(current)',
                'if idx < 0 or idx >= len(hunks):',
                '    print("HUNK NOT FOUND", file=sys.stderr); sys.exit(44)',
                'patch = "".join(header + hunks[idx]).encode("utf-8", "surrogateescape")',
                'with open(output, "wb") as handle: handle.write(patch)',
                'PY',
                '  rc=$?',
                '  [ "$rc" -eq 0 ] || refuse "HUNK PATCH REGENERATION FAILED"',
                'else',
                '  git -C "$source" diff --binary --full-index -- "${files[@]}" >"$patch" || refuse "PATCH REGENERATION FAILED"',
                'fi',
                '[ -s "$patch" ] || refuse "SOURCE PATCH DISAPPEARED SINCE PREVIEW"',
                'actual="$(sha256sum "$patch" | awk "{print \\$1}")"',
                '[ "$actual" = "$expected" ] || refuse "SOURCE CHANGES DIFFER FROM PREVIEW"',
                'git -C "$destination" apply --check --binary "$patch" >/dev/null 2>&1 || refuse "PATCH NO LONGER APPLIES TO DESTINATION"',
                'git -C "$destination" apply --binary "$patch" || refuse "DESTINATION APPLY FAILED"',
                'if [ "$mode" = "move" ]; then',
                '  if ! git -C "$source" apply -R --check --binary "$patch" >/dev/null 2>&1; then',
                '    git -C "$destination" apply -R --binary "$patch" >/dev/null 2>&1 || { printf "REFUSED\\tSOURCE REMOVE CHECK FAILED // DESTINATION ROLLBACK FAILED\\n"; exit 8; }',
                '    refuse "SOURCE REMOVE CHECK FAILED // DESTINATION ROLLED BACK"',
                '  fi',
                '  if ! git -C "$source" apply -R --binary "$patch"; then',
                '    git -C "$destination" apply -R --binary "$patch" >/dev/null 2>&1 || { printf "REFUSED\\tSOURCE REMOVE FAILED // DESTINATION ROLLBACK FAILED\\n"; exit 9; }',
                '    refuse "SOURCE REMOVE FAILED // DESTINATION ROLLED BACK"',
                '  fi',
                '  printf "OK\\tMOVED %s FILE(S) // %s -> %s\\n" "${#files[@]}" "$source" "$destination"',
                'else',
                '  printf "OK\\tCOPIED %s FILE(S) // %s -> %s\\n" "${#files[@]}" "$source" "$destination"',
                'fi'
            ].join("\n"),
            "git-change-transfer-execute",
            source,
            destination,
            mode,
            fingerprint,
            sourceHead,
            destinationHead,
            scope,
            String(hunkIndex)
        ];

        for (let i = 0; i < files.length; ++i)
            args.push(files[i]);

        status = "TRANSFER // EXECUTING";
        transferProcess.exec(args);
        return true;
    }

    function maybeFinishTransfer() {
        if (!transferBusy
                || !transferExitSeen
                || !transferStdoutSeen
                || !transferStderrSeen)
            return;

        const out = String(transferStdoutText || "").trim();
        const err = String(transferStderrText || "").trim();
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

        const parts = controlLine.split("\t");
        const kind = parts.length > 0 ? parts[0] : "";
        const detail =
            parts.length > 1
            ? parts.slice(1).join("\t")
            : String(err || out || ("TRANSFER EXIT " + transferExitCode)).trim();

        pendingTransferSuccess =
            transferExitCode === 0
            && kind === "OK";
        pendingTransferDetail =
            detail
            || (
                pendingTransferSuccess
                ? "TRANSFER COMPLETE"
                : "TRANSFER FAILED"
            );

        if (!operationJournal || !snapshotService) {
            finalizeTransfer(null, "");
            return;
        }

        status = "TRANSFER // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "CHANGES AFTER // TRANSFER",
            transferContext()
        );

        if (!pendingSnapshotRequest) {
            finalizeTransfer(
                null,
                "AFTER SNAPSHOT COULD NOT START"
            );
        }
    }

    function finalizeTransfer(afterSnapshot, snapshotWarning) {
        const warning = String(snapshotWarning || "");
        const detail = String(pendingTransferDetail || "");
        const success = pendingTransferSuccess;
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
                    warning
                    || "TRANSFER AFTER SNAPSHOT UNAVAILABLE"
            };

        if (pendingJournalId && operationJournal) {
            if (success)
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

        transferBusy = false;
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";

        if (success) {
            status =
                warning
                ? "TRANSFER // COMPLETE // SNAPSHOT WARNING"
                : "TRANSFER // COMPLETE";
            lastError = warning;
            clearPreview();
        } else {
            status = "TRANSFER // REFUSED";
            lastError = detail || "TRANSFER FAILED";
            if (warning)
                lastError += " // " + warning;
        }

        transferFinished(
            success,
            warning
            ? (detail || (success ? "OK" : "FAILED"))
                + " // "
                + warning
            : (detail || (success ? "OK" : "FAILED"))
        );
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
                const beforeSnapshot =
                    root.evidenceSnapshot(snapshot);

                root.pendingJournalId =
                    root.operationJournal
                    ? root.operationJournal.beginOperation(
                        root.journalKind(),
                        beforeSnapshot,
                        root.transferContext()
                    )
                    : "";

                if (root.operationJournal
                        && !root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "JOURNAL RECORD COULD NOT START"
                    );
                    return;
                }

                root.executeTransferProcess();
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
        id: previewProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.previewStdoutText = this.text;
                root.previewStdoutSeen = true;
                root.maybeFinishPreview();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.previewStderrText = this.text;
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
        id: transferProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.transferStdoutText = this.text;
                root.transferStdoutSeen = true;
                root.maybeFinishTransfer();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.transferStderrText = this.text;
                root.transferStderrSeen = true;
                root.maybeFinishTransfer();
            }
        }

        onExited: function(code, exitStatus) {
            root.transferExitCode = Number(code);
            root.transferExitSeen = true;
            root.maybeFinishTransfer();
        }
    }
}
