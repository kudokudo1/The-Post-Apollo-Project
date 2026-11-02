pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Local organization structure labels only; not tenant grants or employee roles.
Scope {
    id: structure
    property string state: "loading"
    property string errorCode: ""
    property var saved: ({
        schema:"post-apollo.social-local-org-structure.v1",
        revision:0, nextId:1, units:[]
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

    function createUnit(orgId, kind, name) {
        return update({action:"create", orgId:String(orgId),
                       kind:String(kind), name:String(name)});
    }
    function renameUnit(unitId, name) {
        return update({action:"rename", unitId:String(unitId), name:String(name)});
    }
    function archiveUnit(unitId) {
        return update({action:"archive", unitId:String(unitId)});
    }
    function restoreUnit(unitId) {
        return update({action:"restore", unitId:String(unitId)});
    }

    Process {
        id: reader
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalOrganizationStructure.py"),
                  "read"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: structure.readText = String(text || "")
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(structure.readText); } catch (e) {}
            if (exitCode === 0 && result && result.ok === true) {
                structure.saved = result.document;
                structure.errorCode = "";
                structure.state = "ready";
            } else {
                structure.state = "error";
                structure.errorCode = result && result.error
                    ? result.error : "READ_UNAVAILABLE";
            }
        }
    }

    Process {
        id: writer
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalOrganizationStructure.py"),
                  "update"]
        stdinEnabled: true
        stdout: StdioCollector {
            onStreamFinished: structure.writeText = String(text || "")
        }
        onStarted: {
            writer.write(JSON.stringify(structure.pending) + "\n");
            structure.pending = null;
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(structure.writeText); } catch (e) {}
            if (exitCode === 0 && result && result.ok === true) {
                structure.saved = result.document;
                structure.errorCode = "";
                structure.state = "ready";
            } else {
                structure.state = "error";
                structure.errorCode = result && result.error
                    ? result.error : "SAVE_UNAVAILABLE";
            }
        }
    }
}
