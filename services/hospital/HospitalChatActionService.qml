import QtQuick
import Quickshell

QtObject {
    id: root

    property string bedPath: ""
    property string lastAction: ""
    property string lastError: ""

    function copyText(value) {
        const text = String(value || "");
        if (!text)
            return false;

        Quickshell.execDetached([
            "bash",
            "-lc",
            'command -v wl-copy >/dev/null 2>&1 || exit 127; printf "%s" "$1" | wl-copy',
            "hospital-chat-copy",
            text
        ]);
        lastAction = "COPY";
        lastError = "";
        return true;
    }

    function openFile(referenceValue) {
        const bed = String(bedPath || "").trim();
        const reference = String(referenceValue || "").trim();

        if (!bed || !reference) {
            lastError = "CHAT FILE // BED OR FILE MISSING";
            return false;
        }

        Quickshell.execDetached([
            "bash",
            "-lc",
            [
                'bed="$(realpath -e -- "$1")" || exit 2',
                'case "$2" in',
                '  /*) target="$(realpath -e -- "$2")" || exit 3 ;;',
                '  *) target="$(realpath -e -- "$bed/$2")" || exit 3 ;;',
                'esac',
                'case "$target" in',
                '  "$bed"/*) ;;',
                '  *) exit 13 ;;',
                'esac',
                'exec xdg-open "$target"'
            ].join("\n"),
            "hospital-chat-open-file",
            bed,
            reference
        ]);
        lastAction = "OPEN_FILE";
        lastError = "";
        return true;
    }

    function openExternal(urlValue) {
        const url = String(urlValue || "").trim();

        if (!/^https?:\/\//i.test(url)) {
            lastError = "CHAT LINK // EXTERNAL URL REFUSED";
            return false;
        }

        Qt.openUrlExternally(url);
        lastAction = "OPEN_EXTERNAL";
        lastError = "";
        return true;
    }

    function classifyLink(value) {
        const link = String(value || "").trim();

        if (link.indexOf("hospital:file:") === 0)
            return {
                action: "OPEN_FILE",
                value: decodeURIComponent(link.slice(14))
            };

        if (link === "hospital:diff")
            return { action: "OPEN_DIFF", value: "" };

        if (link.indexOf("hospital:room:") === 0)
            return {
                action: "OPEN_ROOM",
                value: decodeURIComponent(link.slice(14))
            };

        if (link.indexOf("hospital:report:") === 0)
            return {
                action: "OPEN_REPORT",
                value: decodeURIComponent(link.slice(16))
            };

        if (/^https?:\/\//i.test(link))
            return { action: "OPEN_EXTERNAL", value: link };

        return { action: "UNKNOWN", value: link };
    }

    function handleLocal(actionValue, value) {
        const action = String(actionValue || "").toUpperCase();

        if (action === "COPY" || action === "COPY_CODE")
            return copyText(value);

        if (action === "OPEN_FILE")
            return openFile(value);

        if (action === "OPEN_EXTERNAL")
            return openExternal(value);

        return false;
    }
}
