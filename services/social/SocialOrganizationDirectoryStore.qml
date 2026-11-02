pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Manual organization directory only. It is NOT the Identity Center membership
// feed, contains no grants/tokens and cannot switch a verified organization.
Scope {
    id: directory
    property string state: "loading"
    property string errorCode: ""
    property var saved: ({schema:"post-apollo.social-local-organizations.v1",
                          revision:0, nextId:1, organizations:[]})
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
        errorCode = "";
        state = "saving";
        writeText = "";
        writer.running = true;
        return true;
    }

    function addOrganization(name, kind) {
        return update({action:"add_org", name:String(name), kind:String(kind)});
    }
    function renameOrganization(orgId, name) {
        return update({action:"rename_org", orgId:String(orgId), name:String(name)});
    }
    function archiveOrganization(orgId) {
        return update({action:"archive_org", orgId:String(orgId)});
    }
    function restoreOrganization(orgId) {
        return update({action:"restore_org", orgId:String(orgId)});
    }
    function addBranch(orgId, name) {
        return update({action:"add_branch", orgId:String(orgId), name:String(name)});
    }
    function renameBranch(orgId, branchId, name) {
        return update({action:"rename_branch", orgId:String(orgId),
                       branchId:String(branchId), name:String(name)});
    }
    function archiveBranch(orgId, branchId) {
        return update({action:"archive_branch", orgId:String(orgId),
                       branchId:String(branchId)});
    }
    function restoreBranch(orgId, branchId) {
        return update({action:"restore_branch", orgId:String(orgId),
                       branchId:String(branchId)});
    }

    Process {
        id: reader
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialOrganizationDirectory.py"),
                  "read"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: directory.readText = String(text || "")
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(directory.readText); } catch(e) {}
            if (exitCode === 0 && result && result.ok === true) {
                directory.saved = result.document;
                directory.errorCode = "";
                directory.state = "ready";
            } else {
                directory.state = "error";
                directory.errorCode = result && result.error
                    ? result.error : "READ_UNAVAILABLE";
            }
        }
    }

    Process {
        id: writer
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialOrganizationDirectory.py"),
                  "update"]
        stdinEnabled: true
        stdout: StdioCollector {
            onStreamFinished: directory.writeText = String(text || "")
        }
        onStarted: {
            writer.write(JSON.stringify(directory.pending) + "\n");
            directory.pending = null;
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(directory.writeText); } catch(e) {}
            if (exitCode === 0 && result && result.ok === true) {
                directory.saved = result.document;
                directory.errorCode = "";
                directory.state = "ready";
            } else {
                directory.errorCode = result && result.error
                    ? result.error : "SAVE_UNAVAILABLE";
                directory.state = "error";
            }
        }
    }
}
