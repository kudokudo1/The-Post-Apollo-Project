pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Local management lenses only; no verified membership or tenant context.
Scope {
    id: portfolios
    property string state: "loading"
    property string errorCode: ""
    property var saved: ({
        schema:"post-apollo.social-local-portfolios.v1",
        revision:0, nextId:1, portfolios:[]
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
        pending = Object.assign({}, fields, {expectedRevision:saved.revision});
        state = "saving";
        errorCode = "";
        writeText = "";
        writer.running = true;
        return true;
    }
    function createPortfolio(name) {
        return update({action:"create", name:String(name)});
    }
    function renamePortfolio(portfolioId, name) {
        return update({action:"rename", portfolioId:String(portfolioId),
                       name:String(name)});
    }
    function archivePortfolio(portfolioId) {
        return update({action:"archive", portfolioId:String(portfolioId)});
    }
    function restorePortfolio(portfolioId) {
        return update({action:"restore", portfolioId:String(portfolioId)});
    }
    function attachOrganization(portfolioId, orgId) {
        return update({action:"attach", portfolioId:String(portfolioId),
                       orgId:String(orgId)});
    }
    function detachOrganization(portfolioId, orgId) {
        return update({action:"detach", portfolioId:String(portfolioId),
                       orgId:String(orgId)});
    }

    Process {
        id: reader
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalPortfolios.py"),
                  "read"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: portfolios.readText = String(text || "")
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(portfolios.readText); } catch(e) {}
            if (exitCode === 0 && result && result.ok === true) {
                portfolios.saved = result.document;
                portfolios.state = "ready";
                portfolios.errorCode = "";
            } else {
                portfolios.state = "error";
                portfolios.errorCode = result && result.error
                    ? result.error : "READ_UNAVAILABLE";
            }
        }
    }
    Process {
        id: writer
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalPortfolios.py"),
                  "update"]
        stdinEnabled: true
        stdout: StdioCollector {
            onStreamFinished: portfolios.writeText = String(text || "")
        }
        onStarted: {
            writer.write(JSON.stringify(portfolios.pending) + "\n");
            portfolios.pending = null;
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(portfolios.writeText); } catch(e) {}
            if (exitCode === 0 && result && result.ok === true) {
                portfolios.saved = result.document;
                portfolios.state = "ready";
                portfolios.errorCode = "";
            } else {
                portfolios.state = "error";
                portfolios.errorCode = result && result.error
                    ? result.error : "SAVE_UNAVAILABLE";
            }
        }
    }
}
