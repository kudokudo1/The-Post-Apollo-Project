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
    // Favorite identity/reconstruction is intentionally NOT defined here yet.
    // Team 2 + Team 3-F will establish that contract in the coordinated
    // Favorites/FILES reconstruction wave.

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

    function parentPath(path) {
        const current =
            String(path || "/").replace(/\/+$/, "") || "/";

        if (current === "/")
            return "/";

        const slash = current.lastIndexOf("/");

        return slash <= 0 ? "/" : current.slice(0, slash);
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

            const kind = fields[0];
            const name = fields[1];
            const path = fields[2];
            const isDir = kind === "d";
            const sizeBytes = Number(fields[3] || 0);
            const permissions = String(fields[4] || "");
            const modifiedEpoch = Number(fields[5] || 0);

            const suffix =
                name.indexOf(".") >= 0
                ? name.slice(name.lastIndexOf(".") + 1).toLowerCase()
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

            rows.push({
                _fileRecord: true,
                id: "file:" + path,
                name: name,
                label:
                    (isDir
                     ? "⌯🗁๋࣭⭑  "
                     : kind === "l"
                     ? "↗  "
                     : "◇  ")
                    + name
                    + (isDir ? "/" : ""),
                path: path,
                isDir: isDir,
                isParent: false,
                kind: kind,
                sizeBytes: sizeBytes,
                permissions: permissions,
                modifiedEpoch: modifiedEpoch,
                mime: mime,
                detail: path
            });
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
