pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Local functional graph only; never Identity Center membership or staff access.
Scope {
    id: reporting
    property string state: "loading"
    property string errorCode: ""
    property var saved: ({
        schema: "post-apollo.social-local-functional-reporting.v1",
        revision: 0, nextId: 1, links: []
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
        pending = Object.assign({}, fields, {expectedRevision: saved.revision});
        state = "saving";
        errorCode = "";
        writeText = "";
        writer.running = true;
        return true;
    }
    function addRelationship(orgId, parentId, childId) {
        return update({action: "add", orgId: String(orgId),
                       parentId: String(parentId), childId: String(childId)});
    }
    function removeRelationship(linkId) {
        return update({action: "remove", linkId: String(linkId)});
    }

    Process {
        id: reader
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalFunctionalReporting.py"),
                  "read"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: reporting.readText = String(text || "")
        }
        onExited: function(exitCode) {
            var response = null;
            try { response = JSON.parse(reporting.readText); } catch (e) {}
            if (exitCode === 0 && response && response.ok === true) {
                reporting.saved = response.document;
                reporting.state = "ready";
                reporting.errorCode = "";
            } else {
                reporting.state = "error";
                reporting.errorCode = response && response.error
                    ? response.error : "READ_UNAVAILABLE";
            }
        }
    }
    Process {
        id: writer
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalFunctionalReporting.py"),
                  "update"]
        stdinEnabled: true
        stdout: StdioCollector {
            onStreamFinished: reporting.writeText = String(text || "")
        }
        onStarted: {
            writer.write(JSON.stringify(reporting.pending) + "\n");
            reporting.pending = null;
        }
        onExited: function(exitCode) {
            var response = null;
            try { response = JSON.parse(reporting.writeText); } catch (e) {}
            if (exitCode === 0 && response && response.ok === true) {
                reporting.saved = response.document;
                reporting.state = "ready";
                reporting.errorCode = "";
            } else {
                reporting.state = "error";
                reporting.errorCode = response && response.error
                    ? response.error : "SAVE_UNAVAILABLE";
            }
        }
    }
}
