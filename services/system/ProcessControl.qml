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

    function sendSignalMany(pids, signalName) {
        const signal = normalizedSignal(signalName);

        if (!signal || !Array.isArray(pids))
            return false;

        const command = ["kill", signal];

        for (let i = 0; i < pids.length; i++) {
            const pid = Number(pids[i] || 0);

            if (pid > 1)
                command.push(String(pid));
        }

        if (command.length <= 2)
            return false;

        Quickshell.execDetached(command);
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
