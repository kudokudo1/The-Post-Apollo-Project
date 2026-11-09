import QtQuick
import Quickshell
import Quickshell.Io

// One user-triggered, read-only check of an EXISTING Git directory.
// No shell interpolation: the Bed path is a separate python3 argv value.
// PX remains the authority for any eventual Room/Bed registration.
Scope {
    id: root
    property bool checking: false
    property bool checked: false
    property bool verified: false
    property string selectedPath: ""
    property string lastError: ""
    property string lastCheckedAt: ""
    property var evidence: ({})
    property int generation: 0

    function invalidate() {
        generation += 1;
        checked = false;
        verified = false;
        evidence = ({});
        lastError = "";
        lastCheckedAt = "";
    }

    function verify(path) {
        const selected = String(path || "").trim();
        root.invalidate();
        root.selectedPath = selected;
        if (!selected || !selected.startsWith("/") || probeProcess.running) {
            lastError = probeProcess.running
                ? "Previous Git probe still running // retry after it finishes"
                : "Select a discovered absolute Bed path first";
            return false;
        }
        const marker = root.generation;
        probeProcess.startedGeneration = marker;
        probeProcess.outputText = "";
        probeProcess.errorText = "";
        probeProcess.exitSeen = false;
        probeProcess.stdoutDone = false;
        probeProcess.exitCode = -1;
        checking = true;
        // Uses only Git read commands. Never runs checkout/switch/fetch/commit
        // or invokes a provider. Disable optional Git index lock creation.
        const inspect = [
            "import json, os, subprocess, sys",
            "bed = sys.argv[1]",
            "env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')",
            "def git(*args):",
            "    r = subprocess.run(['git','-c','core.fsmonitor=false','-C',bed,*args],",
            "        capture_output=True, text=True, timeout=8, env=env)",
            "    if r.returncode: raise RuntimeError('Git metadata unavailable: ' + args[0])",
            "    return r.stdout.strip()",
            "try:",
            "    if not os.path.isabs(bed) or os.path.realpath(bed) != bed:",
            "        raise RuntimeError('Bed path is not absolute and canonical')",
            "    live = os.path.realpath(os.path.expanduser('~/.config/quickshell'))",
            "    if bed == live: raise RuntimeError('Live Quickshell Bed is excluded')",
            "    if git('rev-parse','--show-toplevel') != bed:",
            "        raise RuntimeError('Selected path is not the Git worktree root')",
            "    branch = git('symbolic-ref','--quiet','--short','HEAD')",
            "    origin = git('remote','get-url','origin')",
            "    head = git('rev-parse','--verify','HEAD')",
            "    clean = not bool(git('status','--porcelain=v1','--untracked-files=all'))",
            "    print(json.dumps({'path':bed,'topLevel':bed,'branch':branch,",
            "        'origin':origin,'head':head,'clean':clean}))",
            "except Exception as error:",
            "    print(json.dumps({'error':str(error)[:180]}))",
            "    sys.exit(2)"
        ].join("\n");
        probeProcess.exec(["python3", "-c", inspect, selected]);
        return true;
    }

    function finishProbe() {
        if (!probeProcess.exitSeen || !probeProcess.stdoutDone)
            return;
        const current = probeProcess.startedGeneration === root.generation
            && root.selectedPath.length > 0;
        root.checking = false;
        if (!current)
            return;
        let data = {};
        try {
            data = JSON.parse(probeProcess.outputText);
        } catch (error) {
            data = {error:"Git probe returned invalid JSON"};
        }
        root.checked = true;
        root.lastCheckedAt = new Date().toLocaleString();
        root.verified = probeProcess.exitCode === 0
            && String(data.path || "") === root.selectedPath
            && !data.error;
        root.evidence = root.verified ? data : ({});
        root.lastError = root.verified ? ""
            : String(data.error || probeProcess.errorText
                || "Git probe failed").slice(0,180);
    }

    Process {
        id: probeProcess
        property int startedGeneration: -1
        property bool stdoutDone: false
        property bool exitSeen: false
        property int exitCode: -1
        property string outputText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: {
                probeProcess.outputText = String(this.text || "");
                probeProcess.stdoutDone = true;
                root.finishProbe();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: probeProcess.errorText = String(this.text || "")
        }
        onExited: function(code, status) {
            probeProcess.exitSeen = true;
            probeProcess.exitCode = Number(code);
            root.finishProbe();
        }
    }
}
