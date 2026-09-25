import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: remoteController

    // REMOTE service extracted from AppControl's certified post-FILES patient.
    // This object owns SSH discovery, normalized records, REMOTE submode state,
    // and SSH/SFTP actions. It deliberately has no AppControl back-reference.
    readonly property int viewConfigured: 0
    readonly property int viewKnown: 1
    readonly property int viewAll: 2

    property int viewMode: viewConfigured

    property var entries: []
    property bool scanLoading: false
    property string scanError: ""

    Process {
        id: scanProcess

        stdout: StdioCollector {
            onStreamFinished: remoteController.consumeScan(text)
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message)
                    remoteController.scanError = message;

                remoteController.scanLoading = false;
            }
        }
    }

    function scanScript() {
        return [
            "import json, os, re",
            "home=os.path.expanduser('~')",
            "rows=[]; seen=set(); seen_hosts=set()",
            "cfg=os.path.join(home,'.ssh','config')",
            "blocks=[]; cur=None",
            "try:",
            "  lines=open(cfg,'r',encoding='utf-8',errors='ignore').read().splitlines()",
            "except Exception:",
            "  lines=[]",
            "for raw in lines:",
            "  line=raw.strip()",
            "  if not line or line.startswith('#'): continue",
            "  parts=line.split(None,1)",
            "  key=parts[0].lower(); value=parts[1].strip() if len(parts)>1 else ''",
            "  if key=='host':",
            "    aliases=[a for a in value.split() if not any(c in a for c in '*!?')]",
            "    cur={'aliases':aliases,'hostname':'','user':'','port':'','identityFile':'','proxyJump':''}",
            "    blocks.append(cur)",
            "  elif cur is not None and key in ('hostname','user','port','identityfile','proxyjump'):",
            "    field={'hostname':'hostname','user':'user','port':'port','identityfile':'identityFile','proxyjump':'proxyJump'}[key]",
            "    if not cur.get(field): cur[field]=os.path.expanduser(value) if field=='identityFile' else value",
            "for block in blocks:",
            "  for alias in block['aliases']:",
            "    if not alias or alias in seen: continue",
            "    seen.add(alias)",
            "    host=block.get('hostname') or alias",
            "    seen_hosts.add(host.lower())",
            "    rows.append({'source':'config','alias':alias,'host':host,'hostname':host,'user':block.get('user',''),'port':block.get('port',''),'identityFile':block.get('identityFile',''),'proxyJump':block.get('proxyJump','')})",
            "kh=os.path.join(home,'.ssh','known_hosts')",
            "try:",
            "  lines=open(kh,'r',encoding='utf-8',errors='ignore').read().splitlines()",
            "except Exception:",
            "  lines=[]",
            "for raw in lines:",
            "  if not raw or raw.startswith('#'): continue",
            "  first=raw.split(None,1)[0] if raw.split() else ''",
            "  for token in first.split(','):",
            "    token=token.strip()",
            "    if not token or token.startswith('|'): continue",
            "    host=token",
            "    port=''",
            "    m=re.match(r'^\\[([^]]+)\\]:(\\d+)$', token)",
            "    if m: host=m.group(1); port=m.group(2)",
            "    key=host.lower()",
            "    if key in seen or key in seen_hosts: continue",
            "    seen.add(key); seen_hosts.add(key)",
            "    rows.append({'source':'known','alias':host,'host':host,'hostname':host,'user':'','port':port,'identityFile':'','proxyJump':''})",
            "print(json.dumps(rows))"
        ].join("\n");
    }

    function refresh() {
        if (scanLoading)
            return false;

        scanLoading = true;
        scanError = "";
        scanProcess.exec([
            "/usr/bin/python3",
            "-c",
            scanScript()
        ]);

        return true;
    }

    function setViewMode(mode) {
        viewMode =
            mode === viewKnown
            ? viewKnown
            : mode === viewAll
              ? viewAll
              : viewConfigured;

        return viewMode;
    }

    function target(entry) {
        if (!entry)
            return "";

        if (entry.source === "config")
            return String(entry.alias || entry.host || "").trim();

        let result = String(
            entry.host || entry.hostname || ""
        ).trim();

        if (entry.user)
            result = String(entry.user) + "@" + result;

        return result;
    }

    function command(entry, sftp) {
        if (!entry)
            return "";

        const program = sftp ? "sftp" : "ssh";
        const targetValue = target(entry);

        if (!targetValue)
            return "";

        if (entry.source === "config")
            return program + " " + targetValue;

        let result = program;

        if (entry.port)
            result += (sftp ? " -P " : " -p ") + String(entry.port);

        result += " " + targetValue;
        return result;
    }

    function consumeScan(text) {
        let raw = [];

        try {
            raw = JSON.parse(String(text || "[]"));
        } catch (error) {
            scanError = "SSH CONFIG PARSE FAILED";
            scanLoading = false;
            return;
        }

        const rows = [];

        for (let i = 0; i < raw.length; i++) {
            const item = raw[i] || ({});
            const source = String(item.source || "known");
            const alias = String(
                item.alias || item.host || ""
            ).trim();
            const host = String(
                item.hostname || item.host || alias
            ).trim();

            if (!alias || !host)
                continue;

            const userHost =
                (item.user ? String(item.user) + "@" : "")
                + host;
            const endpoint =
                userHost
                + (item.port ? ":" + String(item.port) : "");

            rows.push({
                _remoteRecord: true,
                id: "ssh:" + source + ":" + alias,
                name: alias,
                label:
                    source === "config"
                    ? "⌁  " + alias
                    : "◇  " + alias,
                alias: alias,
                host: host,
                hostname: host,
                user: String(item.user || ""),
                port: String(item.port || ""),
                identityFile: String(item.identityFile || ""),
                proxyJump: String(item.proxyJump || ""),
                source: source,
                endpoint: endpoint,
                detail:
                    source === "config"
                    ? "CONFIGURED • " + endpoint
                    : "KNOWN HOST • " + endpoint
            });
        }

        rows.sort(function(a, b) {
            if (a.source !== b.source)
                return a.source === "config" ? -1 : 1;

            return String(a.name || "")
                .localeCompare(String(b.name || ""));
        });

        entries = rows;
        scanLoading = false;
    }

    function activate(entry) {
        if (!entry)
            return false;

        const targetValue = target(entry);

        if (!targetValue)
            return false;

        const args = ["kitty", "--", "ssh"];

        if (entry.source !== "config" && entry.port)
            args.push("-p", String(entry.port));

        args.push(targetValue);
        Quickshell.execDetached(args);
        return true;
    }

    function activateSftp(entry) {
        if (!entry)
            return false;

        const targetValue = target(entry);

        if (!targetValue)
            return false;

        const args = ["kitty", "--", "sftp"];

        if (entry.source !== "config" && entry.port)
            args.push("-P", String(entry.port));

        args.push(targetValue);
        Quickshell.execDetached(args);
        return true;
    }

    function testConnection(entry) {
        if (!entry)
            return false;

        const targetValue = target(entry);

        if (!targetValue)
            return false;

        const args = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5"
        ];

        if (entry.source !== "config" && entry.port)
            args.push("-p", String(entry.port));

        args.push(targetValue, "exit");

        const quoted = args.map(function(part) {
            return "'" + String(part).replace(/'/g, "'\"'\"'") + "'";
        }).join(" ");

        Quickshell.execDetached([
            "/bin/sh",
            "-lc",
            quoted + " >/dev/null 2>&1 && "
            + "notify-send 'AppControl • REMOTE' 'SSH connection succeeded' || "
            + "notify-send -u critical 'AppControl • REMOTE' 'SSH connection failed or needs interactive authentication'"
        ]);

        return true;
    }

    function editSshConfig() {
        const configPath =
            String(Quickshell.env("HOME") || "")
            + "/.ssh/config";

        Quickshell.execDetached([
            "/bin/sh",
            "-lc",
            "cfg=$1; mkdir -p \"$(dirname \"$cfg\")\"; touch \"$cfg\"; "
            + "if command -v code >/dev/null 2>&1; then exec code \"$cfg\"; "
            + "elif command -v nvim >/dev/null 2>&1 && command -v kitty >/dev/null 2>&1; then exec kitty -- nvim \"$cfg\"; "
            + "else exec xdg-open \"$cfg\"; fi",
            "appcontrol-edit-ssh",
            configPath
        ]);

        return true;
    }
}
