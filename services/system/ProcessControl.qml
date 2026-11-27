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

    // Capture the original process, signal by pidfd and launch only after
    // its exit is observed. No SIGKILL, retry or numeric-PID fallback.
    function identityRestartCommand(pid, startTicks, name) {
        if (!Number.isSafeInteger(pid) || pid <= 1
                || !Number.isSafeInteger(startTicks) || startTicks <= 0
                || typeof name !== "string" || !name)
            return [];
        const script = "import os, select, signal, subprocess, sys\npid=int(sys.argv[1]); born=int(sys.argv[2]); comm=sys.argv[3]\ndef matches():\n    with open(f'/proc/{pid}/stat',encoding='utf-8') as source:\n        data=source.read().strip()\n    end=data.rfind(')')\n    fields=data[end+2:].split()\n    return data[data.index('(')+1:end]==comm and int(fields[19])==born and fields[0]!='Z'\ndef identity(st):\n    return (st.st_dev,st.st_ino)\ntry:\n    if pid<=1 or born<=0 or not comm: raise ValueError('invalid identity')\n    fd=os.pidfd_open(pid,0)\nexcept Exception:\n    sys.exit(2)\ntry:\n    try:\n        if not matches(): raise ValueError('stale target')\n        proc=os.fsencode(f'/proc/{pid}')\n        with open(proc+b'/cmdline','rb') as source: raw=source.read()\n        if not raw.endswith(b'\\0'): raise ValueError('invalid argv')\n        argv=raw[:-1].split(b'\\0')\n        if not argv[0]: raise ValueError('empty argv')\n        cwd=os.readlink(proc+b'/cwd')\n        exe=os.readlink(proc+b'/exe')\n        if not os.path.isabs(exe) or exe.endswith(b' (deleted)'): raise ValueError('unavailable executable')\n        original=identity(os.stat(proc+b'/exe'))\n        if identity(os.stat(exe))!=original: raise ValueError('executable changed')\n        with open(proc+b'/environ','rb') as source: envraw=source.read()\n        if envraw and not envraw.endswith(b'\\0'): raise ValueError('invalid environment')\n        env={}\n        for item in envraw[:-1].split(b'\\0') if envraw else []:\n            key,sep,value=item.partition(b'=')\n            if not key or not sep: raise ValueError('invalid environment')\n            env[key]=value\n        if not matches() or identity(os.stat(proc+b'/exe'))!=original:\n            raise ValueError('target changed during capture')\n    except Exception:\n        sys.exit(2)\n    try:\n        signal.pidfd_send_signal(fd,signal.SIGTERM)\n    except Exception:\n        sys.exit(5)\n    poll=select.poll()\n    poll.register(fd,select.POLLIN)\n    events=poll.poll(5000)\n    if not any(mask & (select.POLLIN | select.POLLHUP) and not mask & (select.POLLERR | select.POLLNVAL) for _,mask in events):\n        sys.exit(3)\n    try:\n        if identity(os.stat(exe))!=original: raise ValueError('executable changed after exit')\n        subprocess.Popen(argv,executable=exe,cwd=cwd,env=env,start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n    except Exception:\n        sys.exit(4)\nfinally:\n    os.close(fd)\n";
        return ["/usr/bin/python3", "-c", script, String(pid), String(startTicks), name];
    }
}
