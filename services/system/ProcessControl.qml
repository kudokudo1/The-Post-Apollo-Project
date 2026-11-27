import QtQuick
import Quickshell

Scope {
    id: processControl

    // Mutation primitives only. Safety classification, confirmation UI,
    // target identity checks, optimistic state, and refresh scheduling stay
    // with their respective higher-level controllers.
    function normalizedSignal(signalName) {
        const value = String(signalName || "").trim();

        if (value === "-STOP" || value === "-CONT" || value === "-TERM")
            return value;

        return "";
    }

    // Open the kernel reference before checking birth/name; no numeric fallback.
    function identitySignalCommand(pid, startTicks, name, signalName) {
        const signal = normalizedSignal(signalName);
        if (!Number.isSafeInteger(pid) || pid <= 1
                || !Number.isSafeInteger(startTicks) || startTicks <= 0
                || typeof name !== "string" || !name || !signal)
            return [];
        const script = "import os, signal, sys\npid=int(sys.argv[1]); born=int(sys.argv[2]); comm=sys.argv[3]\nsignals={'-STOP':signal.SIGSTOP,'-CONT':signal.SIGCONT,'-TERM':signal.SIGTERM}\ntry:\n    if pid<=1 or born<=0 or sys.argv[4] not in signals: raise ValueError('invalid target')\n    fd=os.pidfd_open(pid,0)\n    try:\n        with open(f'/proc/{pid}/stat',encoding='utf-8') as source: data=source.read().strip()\n        end=data.rfind(')')\n        if data[data.index('(')+1:end]!=comm or int(data[end+2:].split()[19])!=born:\n            raise ValueError('stale identity')\n        signal.pidfd_send_signal(fd,signals[sys.argv[4]])\n    finally:\n        os.close(fd)\nexcept Exception:\n    sys.exit(1)\n";
        return ["/usr/bin/python3", "-c", script, String(pid), String(startTicks), name, signal];
    }

    function sendSignal(pid, signalName) {
        const targetPid = Number(pid || 0);
        const signal = normalizedSignal(signalName);

        if (targetPid <= 1 || !signal)
            return false;

        Quickshell.execDetached([
            "kill",
            signal,
            String(targetPid)
        ]);

        return true;
    }

    function restart(pid) {
        const targetPid = Number(pid || 0);

        if (targetPid <= 1)
            return false;

        // Capture argv/cwd/environment before SIGTERM, then relaunch the same
        // process image. This preserves the existing AppControl restart
        // behavior without reparsing display-only ps argument text.
        const script =
            "import os, signal, subprocess, sys, time\n"
            + "pid=int(sys.argv[1])\n"
            + "try:\n"
            + "    raw=open(f'/proc/{pid}/cmdline','rb').read().split(b'\\0')\n"
            + "    argv=[x.decode('utf-8','surrogateescape') for x in raw if x]\n"
            + "    if not argv: raise RuntimeError('EMPTY CMDLINE')\n"
            + "    try: cwd=os.readlink(f'/proc/{pid}/cwd')\n"
            + "    except Exception: cwd=None\n"
            + "    env=dict(os.environ)\n"
            + "    try:\n"
            + "        eraw=open(f'/proc/{pid}/environ','rb').read().split(b'\\0')\n"
            + "        for item in eraw:\n"
            + "            if b'=' in item:\n"
            + "                k,v=item.split(b'=',1); env[k.decode('utf-8','ignore')]=v.decode('utf-8','surrogateescape')\n"
            + "    except Exception: pass\n"
            + "    os.kill(pid, signal.SIGTERM)\n"
            + "    time.sleep(0.35)\n"
            + "    subprocess.Popen(argv, cwd=cwd, env=env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
            + "except Exception as exc:\n"
            + "    print(str(exc), file=sys.stderr)\n";

        Quickshell.execDetached([
            "/usr/bin/python3",
            "-c",
            script,
            String(targetPid)
        ]);

        return true;
    }
}
