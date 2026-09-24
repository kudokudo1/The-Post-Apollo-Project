import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: hunterExecutor

    // Execution engine only. Candidate selection, favorites protection,
    // confirmation UI, and report presentation remain with AppControl.
    property bool running: false

    signal resultReady(var result)
    signal finished()
    signal errorRaised(string message)

    function script() {
        return "import json\nimport os\nimport signal\nimport sys\nimport time\n\ntargets = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []\n\ndef emit(payload):\n    print(json.dumps(payload), flush=True)\n\ndef snapshot(pid):\n    try:\n        with open(f\"/proc/{pid}/comm\", \"r\", encoding=\"utf-8\", errors=\"ignore\") as handle:\n            comm = handle.read().strip()\n        with open(f\"/proc/{pid}/stat\", \"r\", encoding=\"utf-8\", errors=\"ignore\") as handle:\n            stat = handle.read().strip()\n        close = stat.rfind(\")\")\n        rest = stat[close + 2:].split() if close >= 0 else []\n        state = rest[0] if rest else \"\"\n        return comm, state\n    except Exception:\n        return None, None\n\ndef original_alive(pid, expected_name):\n    comm, state = snapshot(pid)\n    if comm is None:\n        return False, \"gone\"\n    if expected_name and comm != expected_name:\n        return False, \"pid-reused\"\n    if state == \"Z\":\n        return False, \"zombie\"\n    return True, state or \"running\"\n\nfor target in targets:\n    pid = int(target.get(\"pid\") or 0)\n    name = str(target.get(\"name\") or \"PROCESS\").strip() or \"PROCESS\"\n    if pid <= 1:\n        emit({\"type\":\"result\",\"pid\":pid,\"name\":name,\"status\":\"escaped\",\"detail\":\"INVALID TARGET\"})\n        continue\n\n    alive, state = original_alive(pid, name)\n    if not alive:\n        detail = \"ALREADY GONE\" if state in (\"gone\", \"zombie\") else \"ORIGINAL PROCESS GONE; PID REUSED\"\n        emit({\"type\":\"result\",\"pid\":pid,\"name\":name,\"status\":\"gone\",\"detail\":detail})\n        continue\n\n    try:\n        os.kill(pid, signal.SIGTERM)\n    except ProcessLookupError:\n        emit({\"type\":\"result\",\"pid\":pid,\"name\":name,\"status\":\"gone\",\"detail\":\"ALREADY GONE\"})\n        continue\n    except PermissionError:\n        emit({\"type\":\"result\",\"pid\":pid,\"name\":name,\"status\":\"escaped\",\"detail\":\"GOT AWAY • PERMISSION DENIED\"})\n        continue\n    except Exception as exc:\n        emit({\"type\":\"result\",\"pid\":pid,\"name\":name,\"status\":\"escaped\",\"detail\":\"GOT AWAY • \" + str(exc)})\n        continue\n\n    deadline = time.monotonic() + 1.6\n    alive = True\n    state = \"running\"\n    while time.monotonic() < deadline:\n        alive, state = original_alive(pid, name)\n        if not alive:\n            break\n        time.sleep(0.10)\n\n    if alive:\n        emit({\"type\":\"result\",\"pid\":pid,\"name\":name,\"status\":\"escaped\",\"detail\":\"GOT AWAY • STILL RUNNING\"})\n    else:\n        detail = \"KILLED\" if state != \"pid-reused\" else \"KILLED/EXITED • PID REUSED SAFELY\"\n        emit({\"type\":\"result\",\"pid\":pid,\"name\":name,\"status\":\"killed\",\"detail\":detail})\n\nemit({\"type\":\"done\",\"count\":len(targets)})\n";
    }

    function start(targets) {
        if (running)
            return false;

        const captured = Array.isArray(targets) ? targets.slice() : [];

        if (captured.length === 0)
            return false;

        running = true;
        watchdog.restart();

        process.exec([
            "/usr/bin/python3",
            "-u",
            "-c",
            script(),
            JSON.stringify(captured)
        ]);

        return true;
    }

    function finish() {
        if (!running)
            return;

        running = false;
        watchdog.stop();
        finished();
    }

    function consumeLine(line) {
        const raw = String(line || "").trim();

        if (!raw || !running)
            return;

        try {
            const payload = JSON.parse(raw);

            if (payload.type === "result")
                resultReady(payload);
            else if (payload.type === "done")
                finish();
        } catch (error) {
            errorRaised("HUNTER progress parse: " + String(error));
        }
    }

    Process {
        id: process

        stdout: SplitParser {
            onRead: function(line) {
                hunterExecutor.consumeLine(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();

                if (message.length > 0)
                    hunterExecutor.errorRaised(message);
            }
        }
    }

    Timer {
        id: watchdog
        interval: 23000
        repeat: false

        onTriggered: hunterExecutor.finish()
    }
}
