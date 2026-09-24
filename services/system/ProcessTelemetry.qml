import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: processTelemetry

    // Read-only process telemetry. Mutation (freeze/limit/terminate/restart)
    // deliberately remains outside this service.
    property var rows: []
    property bool snapshotLoading: false
    property string snapshotError: ""
    property int processCount: 0

    property bool miniProbeLoading: false

    // Raw counters used only to derive live rates between samples.
    property var snapshotCpuSamples: ({})
    property var snapshotIoSamples: ({})
    property var miniCpuSamples: ({})
    property var miniIoSamples: ({})

    signal snapshotReady(var rows)
    signal miniProbeReady(var rows)

    function refreshSnapshot() {
        if (snapshotLoading)
            return;

        snapshotLoading = true;
        snapshotError = "";

        snapshotProcess.exec([
            "/bin/sh",
            "-lc",
            "clk=$(getconf CLK_TCK 2>/dev/null || printf 100); "
            + "LC_ALL=C ps -eo "
            + "pid=,ppid=,user=,stat=,tty=,pcpu=,pmem=,rss=,vsz=,nlwp=,etime=,comm=,args= "
            + "--sort=-pcpu | "
            + "while read -r pid rest; do "
            + "[ -n \"$pid\" ] || continue; "
            + "ticks=$(sed 's/^[^)]*) //' /proc/$pid/stat 2>/dev/null "
            + "| awk '{print $12+$13}'); "
            + "readb=$(awk '$1==\"read_bytes:\" {print $2; exit}' /proc/$pid/io 2>/dev/null); "
            + "writeb=$(awk '$1==\"write_bytes:\" {print $2; exit}' /proc/$pid/io 2>/dev/null); "
            + "printf '%s %s %s %s %s %s\\n' \"$clk\" \"${ticks:-0}\" "
            + "\"${readb:-0}\" \"${writeb:-0}\" \"$pid\" \"$rest\"; "
            + "done"
        ]);
    }

    function parseSnapshot(output) {
        const lines = String(output || "").split("\n");
        const parsed = [];
        const nowMs = Date.now();
        const previousTickSamples = snapshotCpuSamples;
        const nextTickSamples = ({});
        const previousIoSamples = snapshotIoSamples;
        const nextIoSamples = ({});

        for (let i = 0; i < lines.length; i++) {
            const line = String(lines[i] || "").trim();

            if (!line)
                continue;

            const fields = line.split(/\s+/);

            if (fields.length < 16)
                continue;

            const tickRate = Math.max(1, Number(fields[0] || 100));
            const cpuTicks = Math.max(0, Number(fields[1] || 0));
            const ioReadBytes = Math.max(0, Number(fields[2] || 0));
            const ioWriteBytes = Math.max(0, Number(fields[3] || 0));
            const pid = Number(fields[4] || 0);

            if (!pid)
                continue;

            const args =
                fields.length > 16
                ? fields.slice(16).join(" ")
                : String(fields[15] || "");

            const comm = String(fields[15] || "").trim();
            const tickKey = "pid:" + String(pid);
            const previousTick = previousTickSamples[tickKey];
            const previousIo = previousIoSamples[tickKey];
            let cpuInstant = Math.max(0, Number(fields[9] || 0));
            let ioReadRate = 0;
            let ioWriteRate = 0;

            if (previousTick
                    && cpuTicks >= Number(previousTick.ticks || 0)
                    && nowMs > Number(previousTick.ms || 0)) {
                const elapsedSeconds = Math.max(
                    0.001,
                    (nowMs - Number(previousTick.ms || 0)) / 1000.0
                );
                const tickDelta = Math.max(
                    0,
                    cpuTicks - Number(previousTick.ticks || 0)
                );
                cpuInstant = ((tickDelta / tickRate) / elapsedSeconds) * 100.0;
            }

            cpuInstant = Math.max(0, Math.min(100, cpuInstant));
            nextTickSamples[tickKey] = {
                ticks: cpuTicks,
                ms: nowMs
            };

            if (previousIo && nowMs > Number(previousIo.ms || 0)) {
                const ioElapsedSeconds = Math.max(
                    0.001,
                    (nowMs - Number(previousIo.ms || 0)) / 1000.0
                );
                ioReadRate = Math.max(
                    0,
                    (ioReadBytes - Number(previousIo.read || 0)) / ioElapsedSeconds
                );
                ioWriteRate = Math.max(
                    0,
                    (ioWriteBytes - Number(previousIo.write || 0)) / ioElapsedSeconds
                );
            }

            nextIoSamples[tickKey] = {
                read: ioReadBytes,
                write: ioWriteBytes,
                ms: nowMs
            };

            // The ps command used to collect the snapshot can appear in its own
            // output as a one-shot high-CPU task. It exits immediately and
            // cannot produce a meaningful continuous history, so hide it.
            if (comm === "ps"
                    && args.indexOf("pid=,ppid=,user=,stat=,tty=,pcpu=") !== -1)
                continue;

            parsed.push({
                _taskRecord: true,
                id: "task:" + String(pid),
                pid: pid,
                ppid: Number(fields[5] || 0),
                user: String(fields[6] || ""),
                state: String(fields[7] || ""),
                tty: String(fields[8] || "?"),
                cpu: Number(fields[9] || 0),
                cpuInstant: cpuInstant,
                mem: Number(fields[10] || 0),
                rss: Number(fields[11] || 0),
                vsz: Number(fields[12] || 0),
                threads: Number(fields[13] || 0),
                elapsed: String(fields[14] || ""),
                comm: String(fields[15] || ""),
                args: args,
                ioReadRate: ioReadRate,
                ioWriteRate: ioWriteRate,
                ioRate: ioReadRate + ioWriteRate,
                name: String(fields[15] || "PROCESS"),
                label: String(fields[15] || "PROCESS")
            });
        }

        snapshotCpuSamples = nextTickSamples;
        snapshotIoSamples = nextIoSamples;
        return parsed;
    }

    function miniProbeScript() {
        return "import json, os, sys, time\n"
             + "items=json.loads(sys.argv[1] if len(sys.argv)>1 else '[]')\n"
             + "clk=float(os.sysconf('SC_CLK_TCK'))\n"
             + "uptime=float(open('/proc/uptime','r',encoding='utf-8').read().split()[0])\n"
             + "mem_total=1.0\n"
             + "try:\n"
             + "    for line in open('/proc/meminfo','r',encoding='utf-8'):\n"
             + "        if line.startswith('MemTotal:'):\n"
             + "            mem_total=max(1.0,float(line.split()[1])); break\n"
             + "except Exception: pass\n"
             + "rows=[]\n"
             + "def elapsed_text(seconds):\n"
             + "    s=max(0,int(seconds)); d=s//86400; s%=86400; h=s//3600; s%=3600; m=s//60; sec=s%60\n"
             + "    clock=f'{h:02d}:{m:02d}:{sec:02d}'\n"
             + "    return (str(d)+'-'+clock) if d else clock\n"
             + "for item in items:\n"
             + "    try:\n"
             + "        pid=int(item.get('pid',0));\n"
             + "        if pid<=1: continue\n"
             + "        raw=open(f'/proc/{pid}/stat','r',encoding='utf-8').read().strip()\n"
             + "        r=raw.rfind(')'); parts=raw[r+2:].split()\n"
             + "        ticks=float(parts[11])+float(parts[12]); start=float(parts[19])\n"
             + "        rss=0.0\n"
             + "        try:\n"
             + "            for line in open(f'/proc/{pid}/status','r',encoding='utf-8'):\n"
             + "                if line.startswith('VmRSS:'): rss=float(line.split()[1]); break\n"
             + "        except Exception: pass\n"
             + "        rb=0.0; wb=0.0\n"
             + "        try:\n"
             + "            for line in open(f'/proc/{pid}/io','r',encoding='utf-8'):\n"
             + "                if line.startswith('read_bytes:'): rb=float(line.split()[1])\n"
             + "                elif line.startswith('write_bytes:'): wb=float(line.split()[1])\n"
             + "        except Exception: pass\n"
             + "        age=max(0.0,uptime-start/clk)\n"
             + "        comm=str(item.get('comm') or '').strip()\n"
             + "        if not comm:\n"
             + "            try: comm=open(f'/proc/{pid}/comm','r',encoding='utf-8').read().strip()\n"
             + "            except Exception: comm='PROCESS'\n"
             + "        rows.append({'pid':pid,'comm':comm,'ticks':ticks,'tickRate':clk,'read':rb,'write':wb,'rss':rss,'mem':(rss/mem_total)*100.0,'ageSeconds':age,'elapsed':elapsed_text(age),'fallbackCpu':float(item.get('fallbackCpu',0) or 0)})\n"
             + "    except Exception:\n"
             + "        continue\n"
             + "print(json.dumps(rows,separators=(',',':')))\n";
    }

    function refreshMiniProbe(request) {
        if (miniProbeLoading)
            return;

        const items = Array.isArray(request) ? request : [];
        if (items.length === 0)
            return;

        miniProbeLoading = true;
        miniProbeProcess.exec([
            "/usr/bin/python3",
            "-c",
            miniProbeScript(),
            JSON.stringify(items)
        ]);
    }

    function parseMiniProbe(output) {
        let payload = [];

        try {
            payload = JSON.parse(String(output || "[]"));
        } catch (error) {
            return [];
        }

        if (!Array.isArray(payload))
            return [];

        const nowMs = Date.now();
        const previousCpu = miniCpuSamples;
        const previousIo = miniIoSamples;
        const nextCpu = ({});
        const nextIo = ({});
        const parsed = [];

        for (let i = 0; i < payload.length; i++) {
            const sample = payload[i] || ({});
            const pid = Number(sample.pid || 0);

            if (pid <= 1)
                continue;

            const key = "pid:" + String(pid);
            const ticks = Math.max(0, Number(sample.ticks || 0));
            const tickRate = Math.max(1, Number(sample.tickRate || 100));
            const readBytes = Math.max(0, Number(sample.read || 0));
            const writeBytes = Math.max(0, Number(sample.write || 0));
            const oldCpu = previousCpu[key];
            const oldIo = previousIo[key];
            let cpuInstant = Math.max(
                0,
                Math.min(100, Number(sample.fallbackCpu || 0))
            );
            let ioRate = 0;

            if (oldCpu && nowMs > Number(oldCpu.ms || 0)
                    && ticks >= Number(oldCpu.ticks || 0)) {
                const dt = Math.max(
                    0.001,
                    (nowMs - Number(oldCpu.ms || 0)) / 1000.0
                );
                cpuInstant = Math.max(
                    0,
                    Math.min(
                        100,
                        (((ticks - Number(oldCpu.ticks || 0)) / tickRate) / dt)
                        * 100.0
                    )
                );
            }

            if (oldIo && nowMs > Number(oldIo.ms || 0)) {
                const dt = Math.max(
                    0.001,
                    (nowMs - Number(oldIo.ms || 0)) / 1000.0
                );
                ioRate = Math.max(
                    0,
                    ((readBytes - Number(oldIo.read || 0))
                     + (writeBytes - Number(oldIo.write || 0))) / dt
                );
            }

            nextCpu[key] = { ticks: ticks, ms: nowMs };
            nextIo[key] = {
                read: readBytes,
                write: writeBytes,
                ms: nowMs
            };

            parsed.push({
                _taskRecord: true,
                id: "task:" + String(pid),
                pid: pid,
                comm: String(sample.comm || "PROCESS"),
                name: String(sample.comm || "PROCESS"),
                label: String(sample.comm || "PROCESS"),
                cpu: cpuInstant,
                cpuInstant: cpuInstant,
                mem: Math.max(0, Number(sample.mem || 0)),
                rss: Math.max(0, Number(sample.rss || 0)),
                ioRate: ioRate,
                elapsed: String(sample.elapsed || ""),
                ageSeconds: Math.max(0, Number(sample.ageSeconds || 0))
            });
        }

        miniCpuSamples = nextCpu;
        miniIoSamples = nextIo;
        return parsed;
    }

    Process {
        id: snapshotProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const parsed = processTelemetry.parseSnapshot(text);
                processTelemetry.snapshotReady(parsed);
                processTelemetry.processCount = parsed.length;
                processTelemetry.snapshotLoading = false;
                processTelemetry.snapshotError = "";
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message.length > 0) {
                    processTelemetry.snapshotError = message;
                    console.log("ProcessTelemetry: task manager:", message);
                }

                processTelemetry.snapshotLoading = false;
            }
        }
    }

    Process {
        id: miniProbeProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const parsed = processTelemetry.parseMiniProbe(text);
                processTelemetry.miniProbeReady(parsed);
                processTelemetry.miniProbeLoading = false;
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                processTelemetry.miniProbeLoading = false;
            }
        }
    }
}
