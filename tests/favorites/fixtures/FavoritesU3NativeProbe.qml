import QtQuick
import Quickshell
import "components"
import "services/favorites" as Fav

// U3 synthetic Fedora native lifecycle test. Isolated HOME/XDG storage only.
ShellRoot {
    id: root
    readonly property string phase: Quickshell.env("U3_PHASE")
    readonly property var store: Fav.FavoritesCollectionsStore
    readonly property string zoneKey: "fav1:local:time:timezone:UTC"
    readonly property string placeKey: "fav1:local:places:saved-place:12"
    property bool done: false
    property bool announced: false

    FloatingWindow {
        id: win
        title: "U3-COLLECTIONS"
        visible: true
        implicitWidth: 425
        implicitHeight: 260
        FavoritesCollectionPanel {
            id: panel
            anchors.fill: parent
            collectionStore: root.store
            resource: ({
                provider:"time",kind:"timezone",resourceId:"UTC",
                label:"UTC",capabilities:["collection"]
            })
            onCreateAccepted: function(collectionId) {
                if(root.phase!=="save" || collectionId!=="c1"){
                    root.fail("BAD_CREATE");
                    return;
                }
                if(!store.setMember(collectionId,root.zoneKey,true)
                    || !store.setMember(collectionId,root.placeKey,true)
                    || !store.moveMember(collectionId,root.placeKey,-1)
                    || store.revision!==4) {
                    root.fail("RAPID_EDITS_REJECTED");
                }
            }
        }
    }

    function fail(reason){
        if(done) return;
        done=true;
        console.error("U3_FAIL // "+reason+" // phase="+phase
            + " state="+store.storageState
            + " visibleRevision="+store.revision
            + " saved="+store.savedRevision
            + " error="+store.errorCode);
        Qt.quit();
    }

    Connections {
        target: root.store
        function onCollectionsSaved(revision){
            if(root.phase!=="save") {
                root.fail("UNEXPECTED_WRITE");
                return;
            }
            if(revision===4 && !root.store.busy
                && root.store.savedRevision===4){
                const rows=root.store.collections;
                if(rows.length!==1 || rows[0].name!=="Synthetic Group"
                    || rows[0].members.join(",")!==[
                       root.placeKey,root.zoneKey].join(",")
                    || !root.store.hasMember("c1",root.zoneKey)) {
                    root.fail("FINAL_SAVE_WRONG");
                    return;
                }
                root.done=true;
                console.log("U3_PASS // NATIVE_CLICK_RAPID_WRITE_ORDER");
                Qt.quit();
            }
        }
        function onCollectionsSaveFailed(reason) {
            root.fail("SAVE_FAILED_"+reason);
        }
    }
    Timer {
        interval: 70
        repeat: true
        running: !root.done
        onTriggered: {
            if(root.phase==="save"){
                if(root.announced || root.store.storageState!=="empty")
                    return;
                panel.draftName="Synthetic Group";
                if(!panel.createControl.available)
                    return;
                const pt=panel.createControl.mapToItem(
                    win.contentItem,
                    panel.createControl.width/2,
                    panel.createControl.height/2);
                root.announced=true;
                console.log("U3_READY // x="+Math.round(pt.x)
                    +" y="+Math.round(pt.y));
            } else if(root.phase==="read") {
                if(root.store.storageState!=="ready") return;
                if(root.store.revision!==4 || root.store.collections.length!==1
                    || root.store.collections[0].members[0]!==root.placeKey
                    || root.store.collections[0].members[1]!==root.zoneKey
                    || !root.store.hasMember("c1",root.zoneKey)
                    || !panel.createControl.available) {
                    root.fail("READBACK_WRONG");
                    return;
                }
                root.done=true;
                console.log("U3_PASS // RESTART_READBACK");
                Qt.quit();
            } else if(root.phase==="corrupt" || root.phase==="unsupported") {
                const expected=root.phase==="corrupt"?"error":"unsupported";
                if(root.store.storageState!==expected) return;
                if(root.store.canEdit || panel.createControl.available
                    || root.store.createCollection("New")!==""
                    || root.store.toggleMember("c1",root.zoneKey)) {
                    root.fail("BAD_DOCUMENT_WRITABLE");
                    return;
                }
                root.done=true;
                console.log("U3_PASS // "+root.phase.toUpperCase()
                    +"_PRESERVED");
                Qt.quit();
            } else root.fail("UNKNOWN_PHASE");
        }
    }
    Timer {
        interval: 12000
        repeat: false
        running: !root.done
        onTriggered: root.fail("TIMEOUT")
    }
    Component.onCompleted: console.log("U3_BOOT // "+phase)
}
