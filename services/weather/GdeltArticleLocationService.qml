import QtQuick
import Quickshell
import Quickshell.Io

// Manual NEWS article -> GDELT GKG 2.1 mentioned-location lookup.
// No polling. One selected article is resolved by exact/canonical URL against
// its nearby 15-minute GKG slice when the operator explicitly requests it.
Scope {
    id: locations

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var rows: []
    property string sourceName: "GDELT GKG 2.1"
    property string feedName: ""
    property string sliceUtc: ""
    property string matchMethod: ""
    property string gkgRecordId: ""
    property string sourceCommonName: ""
    property string semantics: ""
    property var attemptedSlices: []
    property string requestedUrl: ""
    property string requestedSeenDate: ""
    property string requestedLanguage: ""

    readonly property bool loading: lookupProcess.running
    readonly property int locationCount: rows.length

    function clear() {
        if (lookupProcess.running)
            return false;
        ready = false;
        failed = false;
        errorText = "";
        rows = [];
        feedName = "";
        sliceUtc = "";
        matchMethod = "";
        gkgRecordId = "";
        sourceCommonName = "";
        semantics = "";
        attemptedSlices = [];
        requestedUrl = "";
        requestedSeenDate = "";
        requestedLanguage = "";
        return true;
    }

    function request(article) {
        if (lookupProcess.running || !article)
            return false;
        const url = String(article.url || "");
        const seen = String(article.rawTime || "");
        const language = String(article.language || "");
        if (url === "" || seen === "") {
            failed = true;
            errorText = "ARTICLE URL / SEENDATE UNAVAILABLE";
            return false;
        }

        requestedUrl = url;
        requestedSeenDate = seen;
        requestedLanguage = language;
        ready = false;
        failed = false;
        errorText = "";
        rows = [];
        lookupProcess.command = [
            "python3", "-B",
            Quickshell.configDir
                + "/scripts/weather/gdelt_gkg_article_locations.py",
            url, seen, language
        ];
        lookupProcess.running = true;
        return true;
    }

    function accept(raw) {
        try {
            const parsed = JSON.parse(String(raw || ""));
            if (!parsed || parsed.error
                    || String(parsed.source || "") !== "GDELT GKG 2.1"
                    || !Array.isArray(parsed.locations))
                throw new Error("invalid GKG location response");

            sourceName = String(parsed.source || "GDELT GKG 2.1");
            feedName = String(parsed.feed || "");
            sliceUtc = String(parsed.sliceUtc || "");
            matchMethod = String(parsed.matchMethod || "");
            gkgRecordId = String(parsed.gkgRecordId || "");
            sourceCommonName = String(parsed.sourceCommonName || "");
            semantics = String(parsed.semantics || "");
            attemptedSlices = Array.isArray(parsed.attemptedSlices)
                              ? parsed.attemptedSlices : [];
            rows = parsed.locations;
            ready = true;
            failed = false;
            errorText = parsed.matchMethod === "NO MATCH"
                        ? "ARTICLE NOT FOUND IN NEARBY GKG SLICES"
                        : "";
        } catch (error) {
            ready = false;
            failed = true;
            errorText = "GDELT GKG LOCATION RESPONSE UNAVAILABLE";
        }
    }

    Process {
        id: lookupProcess
        command: []

        stdout: StdioCollector {
            onStreamFinished: locations.accept(text)
        }

        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && !locations.ready) {
                locations.failed = true;
                locations.errorText = "GDELT GKG LOCATION LOOKUP FAILED";
            }
        }
    }
}
