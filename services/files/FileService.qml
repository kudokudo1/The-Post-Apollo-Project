import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: fileService

    // FILES provider/service extracted from AppControl's fused 943d273
    // baseline. This object owns filesystem behavior and data only.
    //
    // AppControl keeps:
    //   - FILES presentation
    //   - BROWSE/SEARCH navigation state
    //   - search-field/focus integration
    //   - result/detail routing
    //   - Favorites integration
    //
    // FILES also owns reconstruction of persisted canonical FILE identities.
    // Favorites may persist / migrate provider keys, but it must hand canonical
    // identities back here for current filesystem truth.

    readonly property string homeDir:
        String(Quickshell.env("HOME") || "/")

    property string currentDir: homeDir

    property var entries: []
    property var searchEntries: []

    property bool scanLoading: false
    property bool searchLoading: false

    property string scanError: ""
    property string searchError: ""

    property string searchActiveQuery: ""
    property string pendingSearchQuery: ""

    readonly property int searchResultLimit: 700

    // Capture the directory associated with an in-flight browse process.
    // AppControl currently serializes scans; keeping the context here makes
    // the provider self-contained without reaching back into host state.
    property string scanActiveDir: currentDir

    // Favorite reconstruction is asynchronous because filesystem truth comes
    // from the same external provider machinery as normal FILES scans. Requests
    // are serialized so one resolver Process never aliases two identities.
    property var favoriteResolutionQueue: []
    property bool favoriteResolutionBusy: false
    property string favoriteResolutionActiveIdentity: ""
    property string favoriteResolutionActivePath: ""

    signal favoriteResolutionFinished(string identity, var resolution)

    Process {
        id: favoriteResolutionProcess

        stdout: StdioCollector {
            onStreamFinished: {
                fileService.consumeFavoriteResolution(text);
            }
        }
    }

    Process {
        id: scanProcess

        stdout: StdioCollector {
            onStreamFinished: {
                fileService.consumeScan(text, false);
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message)
                    fileService.scanError = message;

                fileService.scanLoading = false;
            }
        }
    }

    Process {
        id: searchProcess

        stdout: StdioCollector {
            onStreamFinished: {
                fileService.consumeScan(text, true);
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message)
                    fileService.searchError = message;

                fileService.searchLoading = false;

                if (String(fileService.pendingSearchQuery || "").trim()
                        !== fileService.searchActiveQuery)
                    searchDebounce.restart();
            }
        }
    }

    Timer {
        id: searchDebounce

        interval: 180
        repeat: false

        onTriggered: {
            fileService.refreshSearch(
                fileService.pendingSearchQuery
            );
        }
    }

    function humanBytes(value) {
        let bytes = Math.max(0, Number(value || 0));
        const units = ["B", "KiB", "MiB", "GiB", "TiB"];
        let index = 0;

        while (bytes >= 1024 && index < units.length - 1) {
            bytes /= 1024;
            index += 1;
        }

        if (index === 0)
            return Math.round(bytes) + " " + units[index];

        return bytes.toFixed(bytes >= 100 ? 0 : bytes >= 10 ? 1 : 2)
               + " " + units[index];
    }

    function breadcrumbText() {
        const current = String(currentDir || "/");

        if (homeDir && current.indexOf(homeDir) === 0)
            return "~" + current.slice(homeDir.length);

        return current;
    }

    function kindLabel(entry) {
        if (!entry)
            return "FILE";

        if (entry.isParent)
            return "PARENT DIRECTORY";

        if (entry.isDir)
            return "DIRECTORY";

        if (entry.kind === "l")
            return "SYMLINK";

        return String(entry.mime || "FILE").toUpperCase();
    }

    function modifiedText(entry) {
        const epoch = Number(entry && entry.modifiedEpoch || 0);

        if (!(epoch > 0))
            return "UNKNOWN";

        return Qt.formatDateTime(
            new Date(epoch * 1000),
            "yyyy-MM-dd  HH:mm:ss"
        );
    }

    function parentPath(path) {
        const current =
            String(path || "/").replace(/\/+$/, "") || "/";

        if (current === "/")
            return "/";

        const slash = current.lastIndexOf("/");

        return slash <= 0 ? "/" : current.slice(0, slash);
    }

    function favoritePathFromIdentity(identity) {
        const value =
            identity === undefined || identity === null
            ? ""
            : String(identity);

        if (value.indexOf("file:parent:") === 0)
            return "";

        if (value.indexOf("file:") !== 0)
            return "";

        const path = value.slice(5);

        // FileService emits canonical identities from absolute provider paths.
        // Do not normalize, expand, decode, or guess malformed identities.
        if (!path || path[0] !== "/" || path.indexOf("\u0000") !== -1)
            return "";

        return path;
    }

    function invalidFavoriteResolution(identity, reason) {
        return {
            status: "invalid",
            identity:
                identity === undefined || identity === null
                ? ""
                : String(identity),
            path: "",
            reason: String(reason || "invalid-identity"),
            row: null
        };
    }

    function resolveFavoriteIdentity(identity) {
        const value =
            identity === undefined || identity === null
            ? ""
            : String(identity);
        const path = favoritePathFromIdentity(value);

        if (!path) {
            favoriteResolutionFinished(
                value,
                invalidFavoriteResolution(
                    value,
                    value.indexOf("file:parent:") === 0
                    ? "parent-navigation-record"
                    : "invalid-canonical-file-identity"
                )
            );
            return false;
        }

        const next = favoriteResolutionQueue.slice();
        next.push({
            identity: value,
            path: path
        });
        favoriteResolutionQueue = next;

        pumpFavoriteResolutionQueue();
        return true;
    }

    function pumpFavoriteResolutionQueue() {
        if (favoriteResolutionBusy
                || favoriteResolutionQueue.length === 0)
            return;

        const next = favoriteResolutionQueue.slice();
        const request = next.shift();
        favoriteResolutionQueue = next;

        favoriteResolutionBusy = true;
        favoriteResolutionActiveIdentity =
            String(request.identity || "");
        favoriteResolutionActivePath =
            String(request.path || "");

        favoriteResolutionProcess.exec([
            "/bin/sh",
            "-lc",
            "p=$1; "
            + "if [ ! -e \"$p\" ] && [ ! -L \"$p\" ]; then "
            + "printf 'M\\n'; exit 0; fi; "
            + "record=$(find \"$p\" -maxdepth 0 "
            + "-printf 'R\\t%y\\t%f\\t%p\\t%s\\t%M\\t%T@\\n' "
            + "2>/dev/null); rc=$?; "
            + "if [ \"$rc\" -ne 0 ] || [ -z \"$record\" ]; then "
            + "printf 'U\\n'; exit 0; fi; "
            + "printf '%s\\n' \"$record\"",
            "appcontrol-file-favorite-resolve",
            favoriteResolutionActivePath
        ]);
    }

    function finishFavoriteResolution(resolution) {
        const identity = favoriteResolutionActiveIdentity;

        favoriteResolutionBusy = false;
        favoriteResolutionActiveIdentity = "";
        favoriteResolutionActivePath = "";

        favoriteResolutionFinished(identity, resolution);

        Qt.callLater(function() {
            fileService.pumpFavoriteResolutionQueue();
        });
    }

    function consumeFavoriteResolution(text) {
        const identity = favoriteResolutionActiveIdentity;
        const path = favoriteResolutionActivePath;
        const lines = String(text || "").split("\n");
        const first = lines.length > 0 ? lines[0] : "";

        if (first === "M") {
            finishFavoriteResolution({
                status: "missing",
                identity: identity,
                path: path,
                reason: "target-does-not-exist",
                row: null
            });
            return;
        }

        if (first === "U" || first.indexOf("R\t") !== 0) {
            finishFavoriteResolution({
                status: "unavailable",
                identity: identity,
                path: path,
                reason: "filesystem-record-unavailable",
                row: null
            });
            return;
        }

        const fields = first.split("\t");

        if (fields.length < 7 || fields[3] !== path) {
            finishFavoriteResolution({
                status: "unavailable",
                identity: identity,
                path: path,
                reason: "filesystem-record-mismatch",
                row: null
            });
            return;
        }

        const row = recordFromFields(
            fields[1],
            fields[2],
            fields[3],
            Number(fields[4] || 0),
            String(fields[5] || ""),
            Number(fields[6] || 0)
        );

        if (!row || row.isParent || row.id !== identity) {
            finishFavoriteResolution({
                status: "unavailable",
                identity: identity,
                path: path,
                reason: "provider-record-invalid",
                row: null
            });
            return;
        }

        finishFavoriteResolution({
            status: "resolved",
            identity: identity,
            path: path,
            reason: "",
            row: row
        });
    }

    function recordFromFields(
        kind,
        name,
        path,
        sizeBytes,
        permissions,
        modifiedEpoch
    ) {
        const safeKind = String(kind || "");
        const safeName = String(name || "");
        const safePath = String(path || "");
        const isDir = safeKind === "d";
        const suffix =
            safeName.indexOf(".") >= 0
            ? safeName.slice(safeName.lastIndexOf(".") + 1).toLowerCase()
            : "";

        let mime = isDir ? "inode/directory" : "file";

        if (!isDir
                && ["png", "jpg", "jpeg", "gif", "webp", "svg"]
                    .indexOf(suffix) >= 0) {
            mime = "image/" + (suffix === "jpg" ? "jpeg" : suffix);
        } else if (!isDir
                   && ["mp4", "mkv", "webm", "mov", "avi"]
                       .indexOf(suffix) >= 0) {
            mime = "video/" + suffix;
        } else if (!isDir
                   && ["mp3", "flac", "wav", "ogg", "m4a"]
                       .indexOf(suffix) >= 0) {
            mime = "audio/" + suffix;
        } else if (!isDir
                   && [
                       "txt", "md", "qml", "js", "ts", "py",
                       "lua", "sh", "json", "yaml", "yml",
                       "toml", "conf", "ini"
                   ].indexOf(suffix) >= 0) {
            mime = "text/" + (suffix || "plain");
        }

        return {
            _fileRecord: true,
            id: "file:" + safePath,
            name: safeName,
            label:
                (isDir
                 ? "⌯🗁๋࣭⭑  "
                 : safeKind === "l"
                 ? "↗  "
                 : "◇  ")
                + safeName
                + (isDir ? "/" : ""),
            path: safePath,
            isDir: isDir,
            isParent: false,
            kind: safeKind,
            sizeBytes: Number(sizeBytes || 0),
            permissions: String(permissions || ""),
            modifiedEpoch: Number(modifiedEpoch || 0),
            mime: mime,
            detail: safePath
        };
    }

    function refreshBrowse() {
        if (scanLoading)
            return false;

        scanLoading = true;
        scanError = "";
        scanActiveDir = String(currentDir || "/");

        // %y type, %f basename, %p full path, %s bytes,
        // %M permissions, %T@ mtime.
        scanProcess.exec([
            "find",
            scanActiveDir,
            "-mindepth", "1",
            "-maxdepth", "1",
            "-printf", "%y\\t%f\\t%p\\t%s\\t%M\\t%T@\\n"
        ]);

        return true;
    }

    function scheduleSearch(query) {
        pendingSearchQuery = String(query || "");
        searchDebounce.restart();
    }

    function refreshSearch(query) {
        const requested =
            arguments.length > 0
            ? String(query || "")
            : String(pendingSearchQuery || "");

        pendingSearchQuery = requested;

        if (searchLoading)
            return false;

        const trimmed = requested.trim();

        if (!trimmed) {
            searchEntries = [];
            searchError = "";
            searchActiveQuery = "";
            return true;
        }

        searchLoading = true;
        searchError = "";
        searchActiveQuery = trimmed;
        searchEntries = [];

        searchProcess.exec([
            "/bin/sh",
            "-lc",
            "root=$1; q=$2; lim=$3; pattern=\"*$q*\"; "
            + "find \"$root\" -mindepth 1 "
            + "\\( -path \"$root/.cache\" -o -path \"$root/.local/share/Trash\" \\) -prune -o "
            + "\\( -type d -o -type f -o -type l \\) -iname \"$pattern\" "
            + "-printf '%y\\t%f\\t%p\\t%s\\t%M\\t%T@\\n' 2>/dev/null | head -n \"$lim\"",
            "appcontrol-files",
            homeDir,
            trimmed,
            String(searchResultLimit)
        ]);

        return true;
    }

    function consumeScan(text, recursive) {
        const rows = [];
        const contextDir =
            recursive
            ? homeDir
            : String(scanActiveDir || currentDir || "/");

        if (!recursive && contextDir !== "/") {
            const parent = parentPath(contextDir);

            rows.push({
                _fileRecord: true,
                id: "file:parent:" + contextDir,
                name: "..",
                label: "⌯🗁๋࣭⭑  ..",
                path: parent,
                isDir: true,
                isParent: true,
                kind: "d",
                sizeBytes: 0,
                permissions: "",
                modifiedEpoch: 0,
                mime: "inode/directory",
                detail: parent
            });
        }

        const rawLines = String(text || "").split("\n");

        for (let i = 0; i < rawLines.length; i++) {
            if (!rawLines[i])
                continue;

            const fields = rawLines[i].split("\t");

            if (fields.length < 3)
                continue;

            rows.push(
                recordFromFields(
                    fields[0],
                    fields[1],
                    fields[2],
                    Number(fields[3] || 0),
                    String(fields[4] || ""),
                    Number(fields[5] || 0)
                )
            );
        }

        rows.sort(function(a, b) {
            if (a.isParent !== b.isParent)
                return a.isParent ? -1 : 1;

            if (a.isDir !== b.isDir)
                return a.isDir ? -1 : 1;

            return String(a.name || "")
                .localeCompare(String(b.name || ""));
        });

        if (recursive) {
            searchEntries = rows;
            searchLoading = false;

            if (String(pendingSearchQuery || "").trim()
                    !== searchActiveQuery)
                searchDebounce.restart();
        } else {
            entries = rows;
            scanLoading = false;
        }
    }

    function enterDirectory(entry) {
        if (!entry || !entry.isDir)
            return false;

        currentDir = String(entry.path || "/");
        refreshBrowse();

        return true;
    }

    function goUp() {
        const parent = parentPath(currentDir);

        if (parent === currentDir)
            return false;

        currentDir = parent;
        refreshBrowse();

        return true;
    }

    function openEntry(entry) {
        if (!entry)
            return false;

        if (entry.isDir)
            return enterDirectory(entry);

        const path = String(entry.path || "");

        if (!path)
            return false;

        Quickshell.execDetached([
            "xdg-open",
            path
        ]);

        return true;
    }

    function revealEntry(entry) {
        if (!entry)
            return false;

        const path = String(entry.path || "");

        if (!path)
            return false;

        const parent =
            entry.isDir
            ? path
            : parentPath(path);

        Quickshell.execDetached([
            "/bin/sh",
            "-lc",
            "p=$1; f=$2; "
            + "if command -v nautilus >/dev/null 2>&1 && [ -n \"$f\" ]; then nautilus --select \"$f\"; "
            + "elif command -v dolphin >/dev/null 2>&1 && [ -n \"$f\" ]; then dolphin --select \"$f\"; "
            + "elif command -v thunar >/dev/null 2>&1; then thunar \"$p\"; "
            + "else xdg-open \"$p\"; fi",
            "appcontrol-reveal",
            parent,
            entry.isDir ? "" : path
        ]);

        return true;
    }

    function openTerminalHere(entry) {
        if (!entry)
            return false;

        const path = String(entry.path || "");

        if (!path)
            return false;

        const cwd =
            entry.isDir
            ? path
            : parentPath(path);

        Quickshell.execDetached([
            "/bin/sh",
            "-lc",
            "cwd=$1; "
            + "if command -v kitty >/dev/null 2>&1; then exec kitty --directory \"$cwd\"; "
            + "elif command -v foot >/dev/null 2>&1; then exec foot --working-directory=\"$cwd\"; "
            + "elif command -v wezterm >/dev/null 2>&1; then exec wezterm start --cwd \"$cwd\"; "
            + "else notify-send 'AppControl' 'No supported terminal found for OPEN TERMINAL HERE'; fi",
            "appcontrol-file-terminal",
            cwd
        ]);

        return true;
    }
}
