pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Manual local unit ↔ location relationships, never authority or login state.
Scope {
    id: placement
    property string state: "loading"
    property string errorCode: ""
    property var saved: ({
        schema:"post-apollo.social-local-unit-location-links.v1",
        revision:0, nextId:1, links:[]
    })
    property var pending: null
    property string readText: ""
    property string writeText: ""

    function refresh() {
        if (state === "saving" || reader.running || writer.running)
            return false;
        state = "loading";
        errorCode = "";
        readText = "";
        reader.running = true;
        return true;
    }
    function update(fields) {
        if (state !== "ready" || pending !== null || writer.running)
            return false;
        pending = Object.assign({}, fields, {expectedRevision:saved.revision});
        state = "saving";
        errorCode = "";
        writeText = "";
        writer.running = true;
        return true;
    }

    function linkToLocation(orgId, functionId, locationId) {
        return update({action:"add", orgId:String(orgId),
                       functionId:String(functionId),
                       locationId:String(locationId)});
    }
    function unlinkFromLocation(linkId) {
        return update({action:"remove", linkId:String(linkId)});
    }

    Process {
        id: reader
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalUnitLocationLinks.py"),
                  "read"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: placement.readText = String(text || "")
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(placement.readText); } catch (e) {}
            if (exitCode === 0 && result && result.ok === true) {
                placement.saved = result.document;
                placement.state = "ready";
                placement.errorCode = "";
            } else {
                placement.state = "error";
                placement.errorCode = result && result.error
                    ? result.error : "READ_UNAVAILABLE";
            }
        }
    }
    Process {
        id: writer
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalUnitLocationLinks.py"),
                  "update"]
        stdinEnabled: true
        stdout: StdioCollector {
            onStreamFinished: placement.writeText = String(text || "")
        }
        onStarted: {
            writer.write(JSON.stringify(placement.pending) + "\n");
            placement.pending = null;
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(placement.writeText); } catch (e) {}
            if (exitCode === 0 && result && result.ok === true) {
                placement.saved = result.document;
                placement.state = "ready";
                placement.errorCode = "";
            } else {
                placement.state = "error";
                placement.errorCode = result && result.error
                    ? result.error : "SAVE_UNAVAILABLE";
            }
        }
    }
}
