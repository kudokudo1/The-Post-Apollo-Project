pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Setup notes only. Provider authentication is handled separately.
Scope {
    id: accountDetails
    property string state: "loading"
    property string errorCode: ""
    property var saved: ({schema:"post-apollo.social-identity-account-details.v1",
                          revision:0, identities:({})})
    property var pending: null
    property string readText: ""
    property string writeText: ""

    function recordFor(identityId) {
        var item = saved.identities[String(identityId)];
        return item || {email:"",phone:"",accounts:({})};
    }

    // A saved display name is not proof of connection or authentication.
    // Preserve legacy one-label records without rewriting them on read.
    function accountNamesFor(identityId, serviceId) {
        var record = recordFor(identityId);
        var value = (record.accounts || {})[String(serviceId)];
        if (typeof value === "string" && value.length > 0)
            return [{id:"account-1", label:value}];
        return Array.isArray(value) ? value : [];
    }
    // After a conflict or invalid field, the operator can explicitly reload.
    // Read failure never initializes an empty file over corrupt/unsafe storage.
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
        writeText = "";
        writer.running = true;
        return true;
    }
    function saveContact(identityId, email, phone) {
        return update({action:"save_contact",identityId:String(identityId),
                       email:String(email),phone:String(phone)});
    }
    function setAccountLabel(identityId, serviceId, label) {
        // Backwards-compatible legacy operation. The helper refuses to
        // overwrite a multi-account list with a single old-client label.
        return update({action:"set_account_label",identityId:String(identityId),
                       serviceId:String(serviceId),label:String(label)});
    }
    function addAccountName(identityId, serviceId, label) {
        return update({action:"add_account",identityId:String(identityId),
                       serviceId:String(serviceId),label:String(label)});
    }
    function renameAccountName(identityId, serviceId, accountId, label) {
        return update({action:"rename_account",identityId:String(identityId),
                       serviceId:String(serviceId),accountId:String(accountId),
                       label:String(label)});
    }
    function removeAccountName(identityId, serviceId, accountId) {
        return update({action:"remove_account",identityId:String(identityId),
                       serviceId:String(serviceId),accountId:String(accountId)});
    }
    function moveAccountName(identityId, serviceId, accountId, direction) {
        return update({action:"move_account",identityId:String(identityId),
                       serviceId:String(serviceId),accountId:String(accountId),
                       direction:direction});
    }
    Process {
        id: reader
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialAccountDetails.py"),
                  "read"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: accountDetails.readText = String(text || "")
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(accountDetails.readText); } catch(e) {}
            if (exitCode === 0 && result && result.ok === true) {
                accountDetails.saved = result.document;
                accountDetails.state = "ready";
            } else {
                accountDetails.state = "error";
                accountDetails.errorCode = result && result.error
                    ? result.error : "READ_UNAVAILABLE";
            }
        }
    }
    Process {
        id: writer
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialAccountDetails.py"),
                  "update"]
        stdinEnabled: true
        stdout: StdioCollector {
            onStreamFinished: accountDetails.writeText = String(text || "")
        }
        onStarted: {
            writer.write(JSON.stringify(accountDetails.pending) + "\n");
            accountDetails.pending = null;
        }
        onExited: function(exitCode) {
            var result = null;
            try { result = JSON.parse(accountDetails.writeText); } catch(e) {}
            if (exitCode === 0 && result && result.ok === true) {
                accountDetails.saved = result.document;
                accountDetails.errorCode = "";
                accountDetails.state = "ready";
            } else {
                accountDetails.errorCode = result && result.error
                    ? result.error : "SAVE_UNAVAILABLE";
                accountDetails.state = "error";
            }
        }
    }
}
