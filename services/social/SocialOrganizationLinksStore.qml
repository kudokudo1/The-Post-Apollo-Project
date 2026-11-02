pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Manual pointers to local org/branch, Social identity and account nicknames.
// Nothing in this store is verified membership, ownership or provider access.
Scope {
    id: links
    property string state: "loading"
    property string errorCode: ""
    property var saved: ({
        schema:"post-apollo.social-local-associations.v1",
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

    function linkIdentity(orgId, branchId, identityId) {
        return update({action:"add_link", orgId:String(orgId),
                       branchId:branchId || null, identityId:String(identityId),
                       serviceId:null, accountId:null});
    }
    function linkAccountLabel(orgId, branchId, identityId, serviceId, accountId) {
        return update({action:"add_link", orgId:String(orgId),
                       branchId:branchId || null, identityId:String(identityId),
                       serviceId:String(serviceId), accountId:String(accountId)});
    }
    function unlink(linkId) {
        return update({action:"remove_link", linkId:String(linkId)});
    }

    Process {
        id: reader
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialOrganizationLinks.py"),
                  "read"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: links.readText = String(text || "")
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(links.readText); } catch(e) {}
            if (exitCode === 0 && result && result.ok === true) {
                links.saved = result.document;
                links.errorCode = "";
                links.state = "ready";
            } else {
                links.state = "error";
                links.errorCode = result && result.error
                    ? result.error : "READ_UNAVAILABLE";
            }
        }
    }

    Process {
        id: writer
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialOrganizationLinks.py"),
                  "update"]
        stdinEnabled: true
        stdout: StdioCollector {
            onStreamFinished: links.writeText = String(text || "")
        }
        onStarted: {
            writer.write(JSON.stringify(links.pending) + "\n");
            links.pending = null;
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(links.writeText); } catch(e) {}
            if (exitCode === 0 && result && result.ok === true) {
                links.saved = result.document;
                links.errorCode = "";
                links.state = "ready";
            } else {
                links.state = "error";
                links.errorCode = result && result.error
                    ? result.error : "SAVE_UNAVAILABLE";
            }
        }
    }
}
