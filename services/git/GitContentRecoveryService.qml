import QtQuick
import Quickshell
import Quickshell.Io

// Durable content artifacts for future content-level Undo.
//
// An accepted transfer preview already has an exact SHA-256 fingerprint.
// Before mutation, this service regenerates that exact patch, verifies the
// fingerprint, and atomically stores the bytes in private XDG state.
Scope {
    id: root

    property string repositoryPath: ""
    property bool busy: false
    property string status: "CONTENT RECOVERY // READY"
    property string lastError: ""
    property string lastFingerprint: ""
    property string lastArtifactPath: ""
    property int lastArtifactBytes: 0

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal artifactReady(
        string fingerprint,
        string artifactPath,
        int bytes
    )
    signal artifactFailed(string detail)

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

    function capture(scope, path, hunkIndex, lineIndex, expectedFingerprint) {
        if (busy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const kind = String(scope || "").trim().toLowerCase();
        const target = safePath(path);
        const hunk = Number(hunkIndex);
        const line = Number(lineIndex);
        const expected =
            String(expectedFingerprint || "").trim().toLowerCase();

        lastError = "";

        if (!repo
                || ["file", "hunk", "line"].indexOf(kind) < 0
                || !target
                || !/^[0-9a-f]{64}$/.test(expected)
                || (kind !== "file"
                    && (!Number.isInteger(hunk) || hunk < 0))
                || (kind === "line"
                    && (!Number.isInteger(line) || line < 0))) {
            lastError = "CONTENT RECOVERY // INVALID CAPTURE REQUEST";
            status = "CONTENT RECOVERY // REFUSED";
            artifactFailed(lastError);
            return false;
        }

        busy = true;
        status = "CONTENT RECOVERY // PRESERVING";
        lastFingerprint = "";
        lastArtifactPath = "";
        lastArtifactBytes = 0;

        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        captureProcess.exec([
            "python3",
            "-c",
            captureScript(),
            repo,
            kind,
            target,
            String(hunk),
            String(line),
            expected
        ]);

        return true;
    }

    function captureScript() {
        return [
            'import difflib, hashlib, os, re, subprocess, sys, tempfile',
            'repo, scope, path, hi, li, expected = sys.argv[1:7]',
            'hunk_index, line_index = int(hi), int(li)',
            'def run(args): return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def git(*args): return run(["git", "-C", repo] + list(args))',
            'def refuse(msg, code=1): print("REFUSED\\t" + msg); sys.exit(code)',
            'if git("rev-parse", "--is-inside-work-tree").returncode != 0: refuse("SOURCE IS NOT A GIT WORKTREE")',
            'if git("ls-files", "--error-unmatch", "--", path).returncode != 0: refuse("UNTRACKED OR UNKNOWN SOURCE PATH // " + path)',
            'if git("ls-files", "-u", "--", path).stdout.strip(): refuse("CONFLICTED SOURCE PATH // " + path)',
            'cached = git("diff", "--cached", "--quiet", "--", path).returncode',
            'if cached != 0: refuse("SELECTED PATH HAS STAGED CHANGES" if cached == 1 else "STAGED DIFF CHECK FAILED")',
            'def worktree_diff(binary=False):',
            '    args = ["diff", "--no-ext-diff"]',
            '    if binary: args.append("--binary")',
            '    args += ["--", path]',
            '    p = git(*args)',
            '    if p.returncode != 0:',
            '        sys.stderr.buffer.write(p.stderr); sys.exit(p.returncode)',
            '    return p.stdout',
            'if scope == "file":',
            '    p = git("diff", "--binary", "--full-index", "--", path)',
            '    if p.returncode != 0:',
            '        sys.stderr.buffer.write(p.stderr); sys.exit(p.returncode)',
            '    patch = p.stdout',
            'elif scope == "hunk":',
            '    raw = worktree_diff(True)',
            '    lines = raw.decode("utf-8", "surrogateescape").splitlines(True)',
            '    header, hunks, current = [], [], None',
            '    for value in lines:',
            '        if value.startswith("@@"):',
            '            if current is not None: hunks.append(current)',
            '            current = [value]',
            '        elif current is None: header.append(value)',
            '        else: current.append(value)',
            '    if current is not None: hunks.append(current)',
            '    if hunk_index < 0 or hunk_index >= len(hunks): refuse("HUNK NOT FOUND")',
            '    patch = "".join(header + hunks[hunk_index]).encode("utf-8", "surrogateescape")',
            'else:',
            '    raw = worktree_diff(False)',
            '    lines = raw.decode("utf-8", "surrogateescape").splitlines(True)',
            '    hunks, current = [], None',
            '    for value in lines:',
            '        if value.startswith("@@"):',
            '            if current is not None: hunks.append(current)',
            '            current = [value]',
            '        elif current is not None: current.append(value)',
            '    if current is not None: hunks.append(current)',
            '    if hunk_index < 0 or hunk_index >= len(hunks): refuse("HUNK NOT FOUND")',
            '    hunk, body = hunks[hunk_index], hunks[hunk_index][1:]',
            '    if line_index < 0 or line_index >= len(body): refuse("LINE NOT FOUND")',
            '    selected = body[line_index]',
            '    if not selected or selected[0] not in "+-": refuse("LINE IS NOT A CHANGE")',
            '    match = re.match(r"^@@ -(\\d+)(?:,(\\d+))? \\+(\\d+)(?:,(\\d+))? @@", hunk[0])',
            '    if not match: refuse("HUNK HEADER INVALID")',
            '    old_cursor, new_cursor, selected_old = int(match.group(1)), int(match.group(3)), 0',
            '    for idx, value in enumerate(body):',
            '        prefix = value[:1]',
            '        if idx == line_index:',
            '            selected_old = old_cursor; break',
            '        if prefix == " ": old_cursor += 1; new_cursor += 1',
            '        elif prefix == "-": old_cursor += 1',
            '        elif prefix == "+": new_cursor += 1',
            '    basep = git("show", ":" + path)',
            '    if basep.returncode != 0:',
            '        sys.stderr.buffer.write(basep.stderr); sys.exit(basep.returncode)',
            '    base = basep.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
            '    target = list(base); pos = max(0, selected_old - 1)',
            '    if selected[0] == "+": target.insert(min(pos, len(target)), selected[1:])',
            '    else:',
            '        if pos >= len(target): refuse("SOURCE LINE OUT OF RANGE")',
            '        target.pop(pos)',
            '    patch = "".join(difflib.unified_diff(base, target, fromfile="a/" + path, tofile="b/" + path, n=3)).encode("utf-8", "surrogateescape")',
            'if not patch: refuse("RECOVERY PATCH IS EMPTY")',
            'actual = hashlib.sha256(patch).hexdigest()',
            'if actual != expected: refuse("RECOVERY PATCH DOES NOT MATCH ACCEPTED PREVIEW")',
            'state = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")',
            'directory = os.path.join(state, "post-apollo", "git-recovery")',
            'os.makedirs(directory, mode=0o700, exist_ok=True)',
            'os.chmod(directory, 0o700)',
            'destination = os.path.join(directory, expected + ".patch")',
            'fd, temporary = tempfile.mkstemp(prefix=expected + ".", suffix=".tmp", dir=directory)',
            'try:',
            '    os.fchmod(fd, 0o600)',
            '    with os.fdopen(fd, "wb") as handle:',
            '        handle.write(patch); handle.flush(); os.fsync(handle.fileno())',
            '    os.replace(temporary, destination)',
            '    os.chmod(destination, 0o600)',
            'except Exception:',
            '    try: os.unlink(temporary)',
            '    except OSError: pass',
            '    raise',
            'print("ARTIFACT\\t{}\\t{}\\t{}".format(expected, destination, len(patch)))'
        ].join("\n");
    }

    function maybeFinish() {
        if (!busy || !exitSeen || !stdoutSeen || !stderrSeen)
            return;

        busy = false;

        const out = String(stdoutText || "").trim();
        const err = String(stderrText || "").trim();
        const rows = out.split("\n");
        let control = "";

        for (let i = rows.length - 1; i >= 0; --i) {
            const row = String(rows[i] || "");

            if (row.indexOf("ARTIFACT\t") === 0
                    || row.indexOf("REFUSED\t") === 0) {
                control = row;
                break;
            }
        }

        const fields = control.split("\t");

        if (exitCode !== 0
                || fields.length < 4
                || fields[0] !== "ARTIFACT") {
            lastError =
                fields[0] === "REFUSED"
                ? fields.slice(1).join("\t")
                : String(err || out || ("CAPTURE EXIT " + exitCode));
            status = "CONTENT RECOVERY // REFUSED";
            artifactFailed(lastError);
            return;
        }

        lastFingerprint = String(fields[1] || "");
        lastArtifactPath = String(fields[2] || "");
        lastArtifactBytes = Number(fields[3] || 0);
        lastError = "";
        status =
            "CONTENT RECOVERY // PRESERVED // "
            + String(lastArtifactBytes)
            + " B";

        artifactReady(
            lastFingerprint,
            lastArtifactPath,
            lastArtifactBytes
        );
    }

    Process {
        id: captureProcess

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
