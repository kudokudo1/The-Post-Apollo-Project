pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "." as SurfaceBackend

// T5-domain restart/recovery probe.
//
// This is intentionally separate from TabSurfaceProvider.active and from the
// SurfaceLaunchCoordinator lease authority:
// - it observes live endpoint occupancy,
// - it never launches applications,
// - it never owns semantic identity,
// - it never releases application-instance instrumentation.
//
// A future lifetime owner may call refresh() before preparing instrumented
// launches and feed the resulting snapshot into the shared coordinator.
QtObject {
    id: recovery

    property bool loading: false
    property string errorText: ""
    property bool partial: false
    property var observations: []
    property var completeKinds: []
    property int generation: 0

    signal snapshotChanged()
    signal refreshFinished(bool ok, string message)

    function probeScript() {
        return "import json\nimport os\n\nobservations = []\nseen = set()\nerrors = []\ncomplete = []\nuid = os.getuid()\n\ndef own_live_pid(pid):\n    try:\n        return os.stat('/proc/%s' % pid).st_uid == uid\n    except FileNotFoundError:\n        return False\n    except Exception:\n        return False\n\ndef note_error(prefix, pid, exc):\n    if len(errors) < 6:\n        errors.append('%s PID %s: %s' % (prefix, pid, str(exc)))\n\n# Kitty endpoint occupancy from same-user process environment.\nkitty_complete = True\ntry:\n    kitty_pids = os.listdir('/proc')\nexcept Exception as exc:\n    kitty_pids = []\n    kitty_complete = False\n    errors.append('KITTY PROC: ' + str(exc))\n\nfor pid in kitty_pids:\n    if not pid.isdigit() or not own_live_pid(pid):\n        continue\n    try:\n        items = open('/proc/%s/environ' % pid, 'rb').read().split(b'\\0')\n    except FileNotFoundError:\n        continue\n    except Exception as exc:\n        kitty_complete = False\n        note_error('KITTY ENV', pid, exc)\n        continue\n    for item in items:\n        if not item.startswith(b'KITTY_LISTEN_ON='):\n            continue\n        address = item.split(b'=', 1)[1].decode('utf-8', 'ignore').strip()\n        key = ('kitty-listen-on', address)\n        if address and key not in seen:\n            seen.add(key)\n            observations.append({\n                'kind': 'kitty-listen-on',\n                'value': address,\n                'providerKey': ''\n            })\n\nif kitty_complete:\n    complete.append('kitty-listen-on')\n\n# DevTools endpoint occupancy from same-user process argv.\ndevtools_complete = True\ntry:\n    devtools_pids = os.listdir('/proc')\nexcept Exception as exc:\n    devtools_pids = []\n    devtools_complete = False\n    errors.append('DEVTOOLS PROC: ' + str(exc))\n\nfor pid in devtools_pids:\n    if not pid.isdigit() or not own_live_pid(pid):\n        continue\n    try:\n        raw = open('/proc/%s/cmdline' % pid, 'rb').read()\n        argv = [part.decode('utf-8', 'ignore') for part in raw.split(b'\\0') if part]\n    except FileNotFoundError:\n        continue\n    except Exception as exc:\n        devtools_complete = False\n        note_error('DEVTOOLS CMD', pid, exc)\n        continue\n    if not argv:\n        continue\n    port = 0\n    for index, arg in enumerate(argv):\n        if arg.startswith('--remote-debugging-port='):\n            try:\n                port = int(arg.split('=', 1)[1])\n            except Exception:\n                port = 0\n            break\n        if arg == '--remote-debugging-port' and index + 1 < len(argv):\n            try:\n                port = int(argv[index + 1])\n            except Exception:\n                port = 0\n            break\n    key = ('devtools-port', port)\n    if port > 0 and key not in seen:\n        seen.add(key)\n        observations.append({\n            'kind': 'devtools-port',\n            'value': port,\n            'providerKey': ''\n        })\n\nif devtools_complete:\n    complete.append('devtools-port')\n\nprint(json.dumps({\n    'ok': not errors,\n    'observations': observations,\n    'completeKinds': complete,\n    'errors': errors\n}))\n";
    }

    function normalizedSnapshot(payload) {
        payload = payload || ({});

        const rawRows = Array.isArray(payload.observations)
            ? payload.observations
            : [];
        const rawKinds = Array.isArray(payload.completeKinds)
            ? payload.completeKinds
            : [];
        const rows = [];
        const kinds = [];
        const seen = {};

        for (let i = 0; i < rawRows.length; i++) {
            const item =
                SurfaceBackend.SurfaceLaunchCoordinator
                    .normalizedObservedLease(rawRows[i]);

            if (!item)
                continue;

            const key =
                String(item.kind) + ":" + String(item.value);

            if (seen[key])
                continue;

            seen[key] = true;
            rows.push({
                kind: item.kind,
                value: item.value,
                providerKey: String(item.providerKey || ""),
                capability: String(item.capability || "")
            });
        }

        for (let i = 0; i < rawKinds.length; i++) {
            const value = String(rawKinds[i] || "");

            if ((value === "devtools-port"
                    || value === "kitty-listen-on")
                    && kinds.indexOf(value) === -1) {
                kinds.push(value);
            }
        }

        return {
            observations: rows,
            completeKinds: kinds,
            partial: !!payload.partial,
            errorText:
                Array.isArray(payload.errors)
                ? payload.errors.join(" | ")
                : ""
        };
    }

    function applySnapshot(payload) {
        const snapshot = normalizedSnapshot(payload);

        observations = snapshot.observations;
        completeKinds = snapshot.completeKinds;
        partial = snapshot.partial;
        errorText = snapshot.errorText;
        generation += 1;
        snapshotChanged();

        return snapshot;
    }

    function reconcileSharedAuthority() {
        return SurfaceBackend.SurfaceLaunchCoordinator
            .reconcileObservedInstrumentation(
                observations,
                { completeKinds: completeKinds }
            );
    }

    function refresh() {
        if (probeProcess.running)
            return false;

        loading = true;
        errorText = "";
        partial = false;

        probeProcess.exec([
            "python3",
            "-c",
            probeScript()
        ]);
        return true;
    }

    Process {
        id: probeProcess

        stdout: StdioCollector {
            onStreamFinished: {
                let payload = null;

                try {
                    payload = JSON.parse(String(text || "").trim());
                    recovery.applySnapshot(payload);
                    recovery.reconcileSharedAuthority();

                    const ok = !!payload.ok;
                    recovery.refreshFinished(
                        ok,
                        recovery.errorText
                    );
                } catch (error) {
                    recovery.errorText =
                        "SURFACE RECOVERY PARSE: " + String(error);
                    recovery.refreshFinished(
                        false,
                        recovery.errorText
                    );
                }

                recovery.loading = false;
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message)
                    console.log(
                        "SurfaceInstrumentationRecovery stderr:",
                        message
                    );
            }
        }
    }
}
