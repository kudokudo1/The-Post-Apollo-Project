import QtQuick
import Quickshell
import Quickshell.Io
import qs.services.publisher
import "../../components"

// P1.2 media references and previews only. No file mutation or publication.
// The optional file picker and video decoder are loaded on explicit actions.
Rectangle {
    id: mediaPane
    color: Colors.black
    clip: true

    property string activeDraftId: ""
    property string selectedAssetId: ""
    property string feedback: "LOCAL REFERENCES // ORIGINAL FILES UNCHANGED"
    property bool verifiedPreview: false
    property string verifiedUrl: ""
    property string verifiedKind: ""
    property string detachConfirmation: ""
    property string probeOperation: ""
    property string probeAssetId: ""

    readonly property var snapshot: PublisherMediaStore.snapshot
    readonly property var selectedAsset: {
        for (var i = 0; i < snapshot.assets.length; i++) {
            if (snapshot.assets[i].id === selectedAssetId)
                return snapshot.assets[i];
        }
        return null;
    }
    readonly property bool savedDraftExists: {
        if (activeDraftId === "") return false;
        var list = PublisherDraftStore.snapshot.drafts;
        return list.some(function(d) { return d.id === activeDraftId; });
    }
    readonly property bool alreadyAttached: snapshot.links.some(function(l) {
        return l.draftId === activeDraftId && l.assetId === selectedAssetId;
    })

    function clearPreview() {
        verifiedPreview = false;
        verifiedUrl = "";
        verifiedKind = "";
        detachConfirmation = "";
    }
    onVisibleChanged: if (!visible) clearPreview()
    onActiveDraftIdChanged: detachConfirmation = ""

    function openPicker() {
        if (mediaProbe.running || !snapshot.writable) return;
        if (mediaChooser.item) mediaChooser.item.openChooser();
        else mediaChooser.active = true;
    }
    function beginProbe(operation, fileUrl, assetId, stamp) {
        if (mediaProbe.running) {
            feedback = "FILE INSPECTION ALREADY RUNNING";
            return false;
        }
        clearPreview();
        probeOperation = operation;
        probeAssetId = assetId || "";
        mediaProbe.responseText = "";
        feedback = operation === "verify"
                   ? "VERIFYING ORIGINAL // READ ONLY"
                   : "INSPECTING SELECTED FILE // READ ONLY";
        var args = ["python3", "-I", "-B",
            Quickshell.shellPath("services/publisher/PublisherMediaProbe.py"),
            operation, fileUrl];
        if (operation === "verify") args.push(stamp);
        mediaProbe.exec(args);
        return true;
    }
    function chooseAsset(item) {
        if (!item || mediaProbe.running) return;
        selectedAssetId = item.id;
        beginProbe("verify", item.sourceUrl, item.id, item.stamp);
    }
    function acceptProbe(exitCode, raw, operation, assetId) {
        if (!visible) return;
        if (exitCode !== 0 || !raw) {
            feedback = "FILE INSPECTION UNAVAILABLE";
            return;
        }
        var result;
        try { result = JSON.parse(raw); }
        catch(e) {
            feedback = "INVALID INSPECTION RESPONSE";
            return;
        }
        if (!result || result.ok !== true) {
            feedback = "FILE REFUSED // " + String(result && result.reason
                                                    || "UNKNOWN_FILE_ERROR");
            return;
        }
        if (operation === "inspect") {
            var receipt = {
                sourceUrl:result.sourceUrl, title:result.title,
                kind:result.kind, mime:result.mime,
                sizeBytes:result.sizeBytes, stamp:result.stamp
            };
            if (PublisherMediaStore.registerMedia(receipt))
                feedback = "MEDIA REGISTER REQUESTED // WAIT FOR SAVE";
            else
                feedback = "MEDIA REFUSED // " + PublisherMediaStore.actionError;
            return;
        }
        if (operation !== "verify" || assetId !== selectedAssetId
                || !selectedAsset || selectedAsset.id !== assetId)
            return;
        var item = selectedAsset;
        if (result.sourceUrl !== item.sourceUrl || result.stamp !== item.stamp
                || result.kind !== item.kind || result.mime !== item.mime
                || result.sizeBytes !== item.sizeBytes) {
            feedback = "FILE CHANGED // REFUSING PREVIEW";
            return;
        }
        verifiedPreview = true;
        verifiedUrl = result.sourceUrl;
        verifiedKind = result.kind;
        feedback = "LOCAL FILE VERIFIED // REFERENCE ONLY";
    }

    Loader {
        id: mediaChooser
        active: false
        source: "PublisherMediaPicker.qml"
        onLoaded: if (item) item.openChooser()
        onStatusChanged: if (status === Loader.Error)
                             mediaPane.feedback = "FILE PICKER UNAVAILABLE"
    }
    Connections {
        target: mediaChooser.item
        function onFileSelected(fileUrl) {
            mediaPane.beginProbe("inspect", fileUrl, "", "");
        }
        function onCancelled() {
            mediaPane.feedback = "IMPORT CANCELLED // NO FILE CHANGES";
        }
    }
    Process {
        id: mediaProbe
        property string responseText: ""
        stdout: StdioCollector {
            onStreamFinished: mediaProbe.responseText = String(text || "").trim()
        }
        onExited: function(exitCode, exitStatus) {
            var op = mediaPane.probeOperation;
            var id = mediaPane.probeAssetId;
            // Deliver after collector completion; the probe never writes.
            Qt.callLater(function() {
                mediaPane.acceptProbe(exitCode, mediaProbe.responseText, op, id);
            });
        }
    }
    Connections {
        target: PublisherMediaStore
        function onOperationFinished(kind, draftId, assetId) {
            if (!mediaPane.visible) return;
            if (kind === "registered") {
                mediaPane.feedback = "MEDIA SAVED // " + assetId;
                var list = PublisherMediaStore.snapshot.assets;
                for (var i = 0; i < list.length; i++) {
                    if (list[i].id === assetId) {
                        mediaPane.chooseAsset(list[i]);
                        break;
                    }
                }
            } else if (kind === "attached") {
                mediaPane.feedback = "ATTACHMENT LINK SAVED // " + draftId;
            } else if (kind === "detached") {
                mediaPane.feedback = "LINK REMOVED // ORIGINAL FILE PRESERVED";
                mediaPane.detachConfirmation = "";
            }
        }
        function onStorageStateChanged() {
            if (PublisherMediaStore.storageState === "error"
                    || PublisherMediaStore.storageState === "unsupported") {
                mediaPane.clearPreview();
                mediaPane.feedback = "MEDIA STORE BLOCKED // "
                    + PublisherMediaStore.errorCode;
            }
        }
    }

    // Small Social layouts must remain operable, even with previews and rows.
    Flickable {
        id: mediaScroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: mediaContent.implicitHeight
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: mediaContent
            width: mediaScroll.width
            spacing: 7

        Text {
            width: parent.width
            height: 19
            color: Colors.cyan
            font.pixelSize: 12
            text: "MEDIA LIBRARY // " + mediaPane.snapshot.assets.length
                  + " REFERENCES // "
                  + mediaPane.snapshot.state.toUpperCase()
        }
        Row {
            width: parent.width
            height: 34
            spacing: 6
            ActionButton {
                width: (parent.width - parent.spacing) * 0.58
                height: 32
                label: "IMPORT IMAGE / VIDEO"
                accentColor: Colors.magenta
                available: mediaPane.snapshot.writable && !mediaProbe.running
                onTriggered: mediaPane.openPicker()
            }
            ActionButton {
                width: (parent.width - parent.spacing) * 0.42
                height: 32
                label: "RELOAD"
                accentColor: Colors.cyan
                available: PublisherMediaStore.storageState !== "saving"
                           && !mediaProbe.running
                onTriggered: {
                    mediaPane.clearPreview();
                    if (PublisherMediaStore.reloadFromDisk())
                        mediaPane.feedback = "RELOADING SAVED MEDIA REFERENCES";
                    else
                        mediaPane.feedback = "RELOAD REFUSED";
                }
            }
        }
        Flickable {
            id: mediaList
            width: parent.width
            height: Math.max(65, mediaPane.height * 0.29)
            contentWidth: width
            contentHeight: mediaRows.height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            Column {
                id: mediaRows
                width: mediaList.width
                spacing: 4
                Repeater {
                    model: mediaPane.snapshot.assets
                    ActionButton {
                        required property var modelData
                        width: mediaRows.width
                        height: 32
                        label: modelData.id + " // "
                               + (modelData.kind === "image" ? "IMG" : "VID")
                               + " // " + modelData.title
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        selected: mediaPane.selectedAssetId === modelData.id
                        available: !mediaProbe.running
                        onTriggered: mediaPane.chooseAsset(modelData)
                    }
                }
            }
        }
        Rectangle {
            id: previewFrame
            width: parent.width
            height: Math.max(100, mediaPane.height * 0.36)
            color: Colors.black
            border.color: Colors.cyan
            border.width: 1
            clip: true
            Image {
                anchors.fill: parent
                anchors.margins: 4
                visible: mediaPane.verifiedPreview
                         && mediaPane.verifiedKind === "image"
                source: visible ? mediaPane.verifiedUrl : ""
                cache: false
                asynchronous: true
                fillMode: Image.PreserveAspectFit
            }
            Loader {
                id: videoPreview
                anchors.fill: parent
                anchors.margins: 4
                active: mediaPane.verifiedPreview
                        && mediaPane.verifiedKind === "video"
                        && mediaPane.visible
                source: "PublisherVideoPreview.qml"
                onLoaded: if (item) item.source = mediaPane.verifiedUrl
            }
            Connections {
                target: mediaPane
                function onVerifiedUrlChanged() {
                    if (videoPreview.item)
                        videoPreview.item.source = mediaPane.verifiedUrl;
                }
            }
            Text {
                anchors.fill: parent
                anchors.margins: 10
                visible: !mediaPane.verifiedPreview
                color: Colors.white
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 12
                text: mediaPane.selectedAsset
                      ? "SELECTED ORIGINAL NOT VERIFIED.\nCLICK THE MEDIA ROW TO RECHECK."
                      : "SELECT A SAVED MEDIA REFERENCE.\nPREVIEW REQUIRES A FRESH LOCAL FILE CHECK."
            }
            Text {
                anchors.centerIn: parent
                visible: videoPreview.status === Loader.Error
                         && mediaPane.verifiedKind === "video"
                color: Colors.orange
                text: "VIDEO PREVIEW ENGINE UNAVAILABLE"
                font.pixelSize: 11
            }
        }
        Text {
            width: parent.width
            height: 25
            color: Colors.white
            font.pixelSize: 11
            elide: Text.ElideRight
            text: mediaPane.savedDraftExists
                  ? "OPEN DRAFT // " + mediaPane.activeDraftId
                    + (mediaPane.alreadyAttached ? " // ATTACHED" : "")
                  : "SAVE / OPEN A DRAFT TO LINK MEDIA"
        }
        Row {
            width: parent.width
            height: 34
            spacing: 6
            ActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 32
                label: mediaPane.alreadyAttached ? "ALREADY LINKED" : "ATTACH TO DRAFT"
                accentColor: Colors.magenta
                available: mediaPane.savedDraftExists && mediaPane.verifiedPreview
                           && mediaPane.snapshot.writable && !mediaPane.alreadyAttached
                onTriggered: {
                    if (!PublisherMediaStore.attachMedia(mediaPane.activeDraftId,
                                                         mediaPane.selectedAssetId))
                        mediaPane.feedback = "LINK REFUSED // "
                            + PublisherMediaStore.actionError;
                    else
                        mediaPane.feedback = "LINK REQUESTED // WAIT FOR SAVE";
                }
            }
            ActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 32
                label: mediaPane.detachConfirmation === mediaPane.activeDraftId
                       + ":" + mediaPane.selectedAssetId
                       ? "CONFIRM UNLINK" : "UNLINK"
                accentColor: Colors.orange
                available: mediaPane.savedDraftExists && mediaPane.alreadyAttached
                           && mediaPane.snapshot.writable
                onTriggered: {
                    var key = mediaPane.activeDraftId + ":"
                              + mediaPane.selectedAssetId;
                    if (mediaPane.detachConfirmation !== key) {
                        mediaPane.detachConfirmation = key;
                        mediaPane.feedback = "UNLINK THIS DRAFT ONLY? PRESS AGAIN";
                    } else if (!PublisherMediaStore.detachMedia(
                                   mediaPane.activeDraftId, mediaPane.selectedAssetId)) {
                        mediaPane.feedback = "UNLINK REFUSED // "
                            + PublisherMediaStore.actionError;
                    } else {
                        mediaPane.feedback = "UNLINK REQUESTED // WAIT FOR SAVE";
                    }
                }
            }
        }
        Text {
            width: parent.width
            height: 27
            color: Colors.orange
            elide: Text.ElideRight
            font.pixelSize: 10
            text: mediaPane.feedback
        }
        }
    }
}
