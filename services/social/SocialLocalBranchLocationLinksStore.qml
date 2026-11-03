pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Manual local branch ↔ location labels. No company switching or access grants.
Scope {
    id: branches
    property string state: "loading"
    property string errorCode: ""
    property var saved: ({
        schema: "post-apollo.social-local-branch-location-links.v1",
        revision: 0, nextId: 1, links: []
    })
    property var pending: null
    property string readText: ""
    property string writeText: ""

    function refresh() {
        if (state === "saving" || reader.running || writer.running)
            return false;
        errorCode = "";
        state = "loading";
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
    function linkBranch(orgId, branchId, locationId) {
        return update({action: "add", orgId: String(orgId),
                       branchId: String(branchId), locationId: String(locationId)});
    }
    function unlinkBranch(linkId) {
        return update({action: "remove", linkId: String(linkId)});
    }

    Process {
        id: reader
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalBranchLocationLinks.py"),
                  "read"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: branches.readText = String(text || "")
        }
        onExited: function(exitCode) {
            var response = null;
            try { response = JSON.parse(branches.readText); } catch (e) {}
            if (exitCode === 0 && response && response.ok === true) {
                branches.saved = response.document;
                branches.state = "ready";
                branches.errorCode = "";
            } else {
                branches.state = "error";
                branches.errorCode = response && response.error
                    ? response.error : "READ_UNAVAILABLE";
            }
        }
    }
    Process {
        id: writer
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalBranchLocationLinks.py"),
                  "update"]
        stdinEnabled: true
        stdout: StdioCollector {
            onStreamFinished: branches.writeText = String(text || "")
        }
        onStarted: {
            writer.write(JSON.stringify(branches.pending) + "\n");
            branches.pending = null;
        }
        onExited: function(exitCode) {
            var response = null;
            try { response = JSON.parse(branches.writeText); } catch (e) {}
            if (exitCode === 0 && response && response.ok === true) {
                branches.saved = response.document;
                branches.state = "ready";
                branches.errorCode = "";
            } else {
                branches.state = "error";
                branches.errorCode = response && response.error
                    ? response.error : "SAVE_UNAVAILABLE";
            }
        }
    }
}
