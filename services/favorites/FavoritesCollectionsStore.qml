pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "FavoritesCollectionsPolicy.js" as Policy

// U3a one-writer local Collections metadata. Does NOT save a resource favorite
// or change any legacy owner's storage, availability, recall, or permissions.
Scope {
    id: root
    readonly property string storagePath:
        Quickshell.dataDir + "/favorites-collections-v1.json"
    property string storageState: "loading"
    property string errorCode: ""
    property string lastResultCode: ""
    property var document: Policy.empty()
    property var pendingDocument: null
    property var queuedDocument: null
    readonly property var visibleDocument:
        queuedDocument !== null ? queuedDocument
        : pendingDocument !== null ? pendingDocument : document
    readonly property var collections: visibleDocument.collections
    readonly property int revision: visibleDocument.revision
    readonly property int savedRevision: document.revision
    readonly property bool canEdit: storageState==="ready"
        || storageState==="empty" || storageState==="saving"
    readonly property bool busy: storageState==="saving"

    signal collectionsLoaded()
    signal collectionsSaved(int revision)
    signal collectionsSaveFailed(string reason)

    function acceptsKey(key) {
        return Policy.checkMemberKey(key).ok;
    }
    function hasMember(id,key) {
        return Policy.memberOf(visibleDocument,id,key);
    }
    function startWrite(next) {
        pendingDocument=next;
        queuedDocument=null;
        storageState="saving";
        lastResultCode="SAVING";
        // Avoid FileView write inside onSaved and coalesce same-tick edits.
        writeDispatchTimer.start();
    }
    function requestChange(result) {
        if (!canEdit) {
            lastResultCode="STORE_UNAVAILABLE";
            return false;
        }
        if (!result || !result.ok) {
            lastResultCode=result ? result.reason : "INVALID_CHANGE";
            return false;
        }
        if (!result.changed) {
            lastResultCode="UNCHANGED";
            return true;
        }
        errorCode="";
        if (pendingDocument !== null) {
            queuedDocument=result.document;
            lastResultCode="QUEUED";
        } else startWrite(result.document);
        // An accepted edit is NOT a durable save confirmation.
        return true;
    }
    function createCollection(name) {
        const result=Policy.change(visibleDocument,{type:"create",name:name});
        return requestChange(result) ? String(result.collectionId || "") : "";
    }
    function renameCollection(id,name) {
        return requestChange(Policy.change(visibleDocument,{
            type:"rename",collectionId:id,name:name
        }));
    }
    function deleteCollection(id) {
        return requestChange(Policy.change(visibleDocument,{
            type:"delete",collectionId:id
        }));
    }
    function setMember(id,key,enabled) {
        return requestChange(Policy.change(visibleDocument,{
            type:"set-member",collectionId:id,key:key,enabled:enabled
        }));
    }
    function toggleMember(id,key) {
        return setMember(id,key,!hasMember(id,key));
    }
    function moveMember(id,key,direction) {
        return requestChange(Policy.change(visibleDocument,{
            type:"move-member",collectionId:id,key:key,direction:direction
        }));
    }
    function acceptLoaded(raw) {
        if (storageState==="saving") return;
        const result=Policy.parse(raw);
        if (!result.ok) {
            pendingDocument=null;
            queuedDocument=null;
            storageState=result.reason==="UNSUPPORTED_VERSION"
                ? "unsupported" : "error";
            errorCode=result.reason;
            lastResultCode=result.reason;
            // No silent overwrite, repair, migration or retry.
            return;
        }
        document=result.document;
        pendingDocument=null;
        queuedDocument=null;
        storageState="ready";
        errorCode="";
        lastResultCode="";
        collectionsLoaded();
    }

    Timer {
        id: writeDispatchTimer
        interval: 0
        repeat: false
        onTriggered: {
            if (root.storageState!=="saving" || root.pendingDocument===null)
                return;
            preferencesFile.setText(JSON.stringify(root.pendingDocument,null,2)+"\n");
        }
    }
    FileView {
        id: preferencesFile
        path: root.storagePath
        atomicWrites: true
        watchChanges: false
        blockWrites: false
        printErrors: false
        onLoaded: root.acceptLoaded(preferencesFile.text())
        onLoadFailed: function(error) {
            if (root.storageState==="saving") return;
            root.pendingDocument=null;
            root.queuedDocument=null;
            if (error===FileViewError.FileNotFound) {
                root.document=Policy.empty();
                root.errorCode="";
                root.lastResultCode="";
                root.storageState="empty";
                root.collectionsLoaded();
            } else {
                root.storageState="error";
                root.errorCode="FILE_LOAD_FAILED";
                root.lastResultCode=root.errorCode;
            }
        }
        onSaved: {
            if(root.storageState!=="saving" || root.pendingDocument===null)
                return;
            const saved=root.pendingDocument;
            const waiting=root.queuedDocument;
            root.document=saved;
            root.pendingDocument=null;
            root.queuedDocument=null;
            root.errorCode="";
            if (waiting!==null) root.startWrite(waiting);
            else {
                root.storageState="ready";
                root.lastResultCode="SAVED";
            }
            root.collectionsSaved(saved.revision);
        }
        onSaveFailed: function(error) {
            root.pendingDocument=null;
            root.queuedDocument=null;
            root.storageState="error";
            root.errorCode="FILE_SAVE_FAILED";
            root.lastResultCode=root.errorCode;
            // Confirmed document remains the last successfully saved state.
            root.collectionsSaveFailed(root.errorCode);
        }
    }
}
