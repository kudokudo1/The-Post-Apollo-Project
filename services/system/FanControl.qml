import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: fanControl

    // Fan writes are isolated from read-only telemetry. This service owns all
    // mutable PWM state, safety unlocks, privileged writes, and read-back
    // reconciliation. Consumers receive refresh/error signals instead of the
    // service reaching into a particular window or telemetry implementation.
    property string pendingPwmPath: ""
    property real pendingPercent: -1
    property double pendingSinceMs: 0

    property var desiredPercents: ({})
    property var unlockedKeys: ({})

    signal refreshRequested()
    signal errorRaised(string message)

    function safetyKey(entry) {
        if (!entry)
            return "";

        return String(
            entry.pwmPath
            || entry.inputPath
            || entry.id
            || (String(entry.chip || "") + "|" + String(entry.name || ""))
        );
    }

    function unlocked(entry) {
        const key = safetyKey(entry);
        return key.length > 0 && unlockedKeys[key] === true;
    }

    function toggleUnlocked(entry) {
        const key = safetyKey(entry);
        if (!key)
            return;

        const next = Object.assign({}, unlockedKeys);
        next[key] = !(next[key] === true);
        unlockedKeys = next;
    }

    function desiredPercentFor(entry) {
        const path = String(entry && entry.pwmPath || "");
        if (!path || desiredPercents[path] === undefined)
            return -1;

        const value = Number(desiredPercents[path]);
        return isNaN(value) ? -1 : Math.max(0, Math.min(100, value));
    }

    function setDesiredPercent(entry, percent) {
        const path = String(entry && entry.pwmPath || "");
        if (!path)
            return;

        const next = Object.assign({}, desiredPercents);
        next[path] = Math.max(0, Math.min(100, Number(percent || 0)));
        desiredPercents = next;
    }

    function clearDesiredPercent(entry) {
        const path = String(entry && entry.pwmPath || "");
        if (!path || desiredPercents[path] === undefined)
            return;

        const next = Object.assign({}, desiredPercents);
        delete next[path];
        desiredPercents = next;
    }

    function pendingPercentFor(entry) {
        if (!entry || pendingPercent < 0)
            return -1;

        if (String(entry.pwmPath || "") !== pendingPwmPath)
            return -1;

        return Math.max(0, Math.min(100, Number(pendingPercent)));
    }

    function clearPendingPercent() {
        pendingPwmPath = "";
        pendingPercent = -1;
        pendingSinceMs = 0;
        pendingClearTimer.stop();
    }

    function reconcilePendingPercent(rows) {
        if (pendingPercent < 0 || !pendingPwmPath)
            return;

        const list = Array.isArray(rows) ? rows : [];
        for (let i = 0; i < list.length; i++) {
            const row = list[i];
            if (String(row && row.pwmPath || "") !== pendingPwmPath)
                continue;

            const actual = Number(row.pwmPercent);
            if (!isNaN(actual)
                    && actual >= 0
                    && Math.abs(actual - pendingPercent) <= 2.5) {
                clearPendingPercent();
            }
            return;
        }
    }

    Timer {
        id: pendingClearTimer
        interval: 5500
        repeat: false

        onTriggered: {
            if (fanControl.pendingPercent >= 0) {
                fanControl.errorRaised(
                    "FAN PWM WRITE DID NOT STAY AT THE REQUESTED VALUE"
                );
                fanControl.clearPendingPercent();
                fanControl.refreshRequested();
            }
        }
    }

    function controlScript() {
        return "import json\nimport os\nimport re\nimport sys\nimport time\n\npayload = json.loads(sys.argv[1] if len(sys.argv) > 1 else \"{}\")\naction = str(payload.get(\"action\") or \"\")\npwm_path = str(payload.get(\"pwmPath\") or \"\")\nenable_path = str(payload.get(\"pwmEnablePath\") or \"\")\n\ndef valid(path, suffix):\n    return bool(\n        re.match(r\"^/sys/class/hwmon/hwmon[0-9]+/\" + suffix + r\"$\", path)\n    )\n\nif not valid(pwm_path, r\"pwm[0-9]+\"):\n    raise SystemExit(\"invalid pwm path\")\n\nif enable_path and not valid(enable_path, r\"pwm[0-9]+_enable\"):\n    raise SystemExit(\"invalid enable path\")\n\nif not os.path.exists(pwm_path):\n    raise SystemExit(\"fan pwm control file unavailable\")\n\nif enable_path and not os.path.exists(enable_path):\n    enable_path = \"\"\n\nif not os.access(pwm_path, os.W_OK):\n    raise SystemExit(\"fan pwm control file is not writable\")\n\nif enable_path and not os.access(enable_path, os.W_OK):\n    raise SystemExit(\"fan pwm mode file is not writable\")\n\ndef read_int(path, default):\n    try:\n        return int(open(path, \"r\", encoding=\"utf-8\").read().strip())\n    except Exception:\n        return default\n\ndef write_int(path, value):\n    with open(path, \"w\", encoding=\"utf-8\") as handle:\n        handle.write(str(int(value)))\n        handle.flush()\n\ncurrent = max(0, min(255, read_int(pwm_path, 255)))\nrequested_pwm = current\n\nif action == \"auto\":\n    if not enable_path:\n        raise SystemExit(\"automatic mode control is not exposed for this channel\")\n    write_int(enable_path, 2)\n    time.sleep(0.08)\nelif action == \"manual\":\n    requested_pwm = max(current, 180)\n    if enable_path:\n        write_int(enable_path, 1)\n        time.sleep(0.06)\n    write_int(pwm_path, requested_pwm)\n    time.sleep(0.10)\nelif action == \"boost\":\n    requested_pwm = min(255, max(current, 180) + 26)\n    if enable_path:\n        write_int(enable_path, 1)\n        time.sleep(0.06)\n    write_int(pwm_path, requested_pwm)\n    time.sleep(0.10)\nelif action == \"max\":\n    requested_pwm = 255\n    if enable_path:\n        write_int(enable_path, 1)\n        time.sleep(0.06)\n    write_int(pwm_path, requested_pwm)\n    time.sleep(0.10)\nelif action == \"set\":\n    percent_raw = payload.get(\"percent\", None)\n    if percent_raw is None:\n        raise SystemExit(\"missing fan percent\")\n    percent = max(0.0, min(100.0, float(percent_raw)))\n    requested_pwm = int(round((percent / 100.0) * 255.0))\n    if enable_path:\n        write_int(enable_path, 1)\n        # Some hwmon drivers need a small gap after switching out of firmware\n        # automatic mode before a manual duty write will stick.\n        time.sleep(0.08)\n    write_int(pwm_path, requested_pwm)\n    time.sleep(0.12)\n\n    # A few drivers accept the first write but immediately restore the old\n    # value. Retry once while still in manual mode before reporting read-back.\n    first_readback = max(0, min(255, read_int(pwm_path, requested_pwm)))\n    if abs(first_readback - requested_pwm) > 3:\n        if enable_path:\n            write_int(enable_path, 1)\n            time.sleep(0.06)\n        write_int(pwm_path, requested_pwm)\n        time.sleep(0.14)\nelse:\n    raise SystemExit(\"unknown action\")\n\nreadback = max(0, min(255, read_int(pwm_path, requested_pwm)))\nenable_value = read_int(enable_path, -1) if enable_path else -1\nprint(json.dumps({\n    \"ok\": True,\n    \"action\": action,\n    \"requestedPwm\": requested_pwm,\n    \"pwmValue\": readback,\n    \"percent\": (readback / 255.0) * 100.0,\n    \"enable\": enable_value,\n    \"pwmPath\": pwm_path\n}))\n";
    }

    function writeControl(entry, action, percent) {
        if (!entry
                || entry.sensorKind !== "fan"
                || (!entry.controlWritable && !entry.controlRequiresAuth))
            return;

        const payload = JSON.stringify({
            action: String(action || ""),
            percent:
                percent === undefined || percent === null
                ? null
                : Math.max(0, Math.min(100, Number(percent))),
            pwmPath: String(entry.pwmPath || ""),
            pwmEnablePath: String(entry.pwmEnablePath || "")
        });

        const command = entry.controlWritable
                        ? [
                              "/usr/bin/python3",
                              "-c",
                              controlScript(),
                              payload
                          ]
                        : [
                              "pkexec",
                              "/usr/bin/python3",
                              "-c",
                              controlScript(),
                              payload
                          ];

        controlProcess.exec(command);
    }

    function writePercent(entry, percent) {
        if (!entry)
            return;

        const target =
            Math.max(0, Math.min(100, Number(percent || 0)));

        setDesiredPercent(entry, target);
        pendingPwmPath = String(entry.pwmPath || "");
        pendingPercent = target;
        pendingSinceMs = Date.now();
        pendingClearTimer.restart();

        writeControl(entry, "set", target);
    }

    Process {
        id: controlProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const raw = String(text || "").trim();

                if (raw.length > 0) {
                    try {
                        const payload = JSON.parse(raw);
                        if (payload.ok
                                && String(payload.pwmPath || "")
                                   === fanControl.pendingPwmPath) {
                            const actual = Number(payload.percent);
                            if (!isNaN(actual)
                                    && Math.abs(
                                        actual
                                        - fanControl.pendingPercent
                                    ) > 2.5) {
                                fanControl.errorRaised(
                                    "FAN PWM WRITE READ BACK "
                                    + actual.toFixed(0)
                                    + "% INSTEAD OF "
                                    + fanControl.pendingPercent.toFixed(0)
                                    + "%"
                                );
                            }
                        }
                    } catch (error) {
                        console.log(
                            "FanControl: readback parse:",
                            String(error)
                        );
                    }
                }

                Qt.callLater(function() {
                    fanControl.refreshRequested();
                });
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message.length > 0) {
                    fanControl.errorRaised(message);
                    fanControl.clearPendingPercent();
                    console.log("FanControl:", message);
                }

                Qt.callLater(function() {
                    fanControl.refreshRequested();
                });
            }
        }
    }
}
