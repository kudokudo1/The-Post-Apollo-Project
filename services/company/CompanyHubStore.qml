import QtQuick
import Quickshell
import Quickshell.Io

// One explicit, owner-local CRUD boundary for non-personal hub claims.
// Manual directory names are not authenticated organization memberships.
Item {
    id: store

    property string state: "loading"
    property string errorCode: ""
    property var saved: ({
        schema:"post-apollo.company-hubs.local.v1",
        revision:0, nextId:1, hubs:[]
    })
    property var pending: null
    property string readText: ""
    property string writeText: ""
    signal savedSuccessfully()

    function refresh() {
        if (state === "saving" || reader.running || writer.running)
            return false;
        state = "loading";
        errorCode = "";
        readText = "";
        reader.running = true;
        return true;
    }

    function update(request) {
        if (state !== "ready" || pending !== null || writer.running || reader.running)
            return false;
        pending = Object.assign({}, request, {expectedRevision:saved.revision});
        state = "saving";
        errorCode = "";
        writeText = "";
        writer.running = true;
        return true;
    }

    function createHub(label, organizationLabel, city, regionCode, countryCode,
                       longitude, latitude, serviceFamily) {
        return update({
            action:"create",
            label:String(label || ""),
            organizationLabel:String(organizationLabel || ""),
            city:String(city || ""),
            regionCode:String(regionCode || "").trim().toUpperCase(),
            countryCode:String(countryCode || "").trim().toUpperCase(),
            longitude:Number(longitude),
            latitude:Number(latitude),
            serviceFamily:String(serviceFamily || "")
        });
    }

    function archiveHub(id) {
        return update({action:"archive",hubId:String(id || "")});
    }

    function restoreHub(id) {
        return update({action:"restore",hubId:String(id || "")});
    }

    Process {
        id: reader
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/company/CompanyHubDirectory.py"), "read"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: store.readText = String(text || "")
        }
        onExited: function(code) {
            var result = null;
            try { result = JSON.parse(store.readText); } catch (e) {}
            if (code === 0 && result && result.ok === true) {
                store.saved = result.document;
                store.errorCode = "";
                store.state = "ready";
            } else {
                store.state = "error";
                store.errorCode = result && result.error
                    ? result.error : "READ_UNAVAILABLE";
            }
        }
    }

    Process {
        id: writer
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/company/CompanyHubDirectory.py"), "update"]
        stdinEnabled: true
        stdout: StdioCollector {
            onStreamFinished: store.writeText = String(text || "")
        }
        onStarted: {
            writer.write(JSON.stringify(store.pending) + "\n");
            store.pending = null;
        }
        onExited: function(code) {
            var result = null;
            try { result = JSON.parse(store.writeText); } catch (e) {}
            if (code === 0 && result && result.ok === true) {
                store.saved = result.document;
                store.state = "ready";
                store.errorCode = "";
                store.savedSuccessfully();
            } else {
                store.state = "error";
                store.errorCode = result && result.error
                    ? result.error : "SAVE_UNAVAILABLE";
            }
        }
    }
}
