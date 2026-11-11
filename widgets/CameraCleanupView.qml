import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import Quickshell
import Quickshell.Io
import "CameraHuntMotion.js" as HuntMotion
import "../components"

// CLEANUP // transplanted verbatim from Camera's former page. The single
// CameraW controller retains file validation, selection history and GIO moves.
// The visual page is mounted ONLY by Trash++ and owns no second queue.
Column {
    id: cleanupPage
    required property var camera
    // The 420px Trash++ chassis is a genuine narrow workspace. Keep all
    // Camera-owned actions, but do not force the wide two-column preview
    // or lengthy filter labels into it.
    readonly property bool compactHosted: width <= 450
    // Camera owns every queue item and file action. This component only
    // renders and selects, and now lives INSIDE the Trash++ PanelWindow.
    function focusSwipe() {
        if (camera && camera.hostedCleanupActive
                && camera.cleanupTechnique === "swipe")
            swipeDeck.forceActiveFocus();
    }

    anchors.fill: parent
    visible: camera.activeView === "cleanup"
    spacing: 7

    Row {
        width: parent.width
        height: 24
        spacing: 12
        GohuText {
            width: parent.width
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 13
            color: Colors.white
            text: "CLEANUP // FILE REVIEW"
        }
    }

    Row {
        id: cleanupModeRow
        width: parent.width
        height: 33
        spacing: 6
        Repeater {
            model: [
                {id: "batch", label: "BATCH SCROLL"},
                {id: "grid", label: "BATCH GRID"},
                {id: "swipe", label: "SWIPE"},
                {id: "hunt", label: "HUNT"},
                {id: "desktop", label: "DESKTOP"}
            ]
            ActionButton {
                width: (cleanupModeRow.width - 4 * cleanupModeRow.spacing) / 5
                height: 32
                label: cleanupPage.compactHosted
                       && modelData.id === "batch" ? "SCROLL"
                       : cleanupPage.compactHosted
                         && modelData.id === "grid" ? "GRID"
                       : modelData.label
                labelPixelSize: cleanupPage.compactHosted ? 9 : 9
                selected: camera.cleanupTechnique === modelData.id
                accentColor: modelData.id === "hunt"
                             ? Colors.cyan : Colors.magenta
                available: !camera.busy
                onLeftClicked: {
                    if (!camera.selectCleanupTechnique(modelData.id))
                        return;
                    if (modelData.id === "swipe")
                        Qt.callLater(function() {
                            swipeDeck.forceActiveFocus();
                        });
                }
            }
        }
    }

    Row {
        id: cleanupQueueActions
        width: parent.width
        height: 38
        spacing: 8
        visible: camera.cleanupTechnique !== "desktop"
        ActionButton {
            width: (parent.width - 8) * 0.68
            height: 37
            label: camera.cleanupQueueOpen
                   ? "QUEUE OPEN // " + camera.batchPaths.length
                   : "VIEW QUEUE // " + camera.batchPaths.length
            labelPixelSize: 12
            accentColor: Colors.magenta
            selected: camera.cleanupQueueOpen
            available: !camera.busy
            onLeftClicked: camera.cleanupToggleQueue()
        }
        ActionButton {
            width: (parent.width - 8) * 0.32
            height: 37
            label: "CLEAR MARKS"
            labelPixelSize: 10
            accentColor: Colors.cyan
            available: !camera.busy && camera.batchPaths.length > 0
            onLeftClicked: camera.batchClear()
        }
    }
    GohuText {
        width: parent.width
        height: 19
        visible: camera.cleanupTechnique !== "desktop"
        font.pixelSize: 9
        color: camera.batchReceipt ? Colors.yellow : Colors.cyan
        elide: Text.ElideRight
        text: camera.batchReceipt
              ? camera.batchReceipt
              : "REVIEW QUEUE // " + camera.batchPaths.length
                + " MARKED // RECOVERABLE TRASH"
    }

    Row {
        width: parent.width
        height: 32
        spacing: 6
        visible: camera.cleanupTechnique !== "desktop"
        TextField {
            id: cleanupSearch
            width: parent.width * 0.52
            height: 30
            text: camera.cleanupSearchQuery
            placeholderText: "SEARCH MEDIA BY NAME"
            placeholderTextColor: Colors.cyan
            color: Colors.white
            font.pixelSize: 10
            selectByMouse: true
            background: Rectangle {
                color: Colors.black
                border.width: 1
                border.color: cleanupSearch.activeFocus
                              ? Colors.magenta : Colors.cyan
            }
            onTextChanged: {
                camera.cleanupSearchQuery = text;
                if (camera.activeView === "cleanup")
                    camera.scheduleCleanupSearch();
            }
        }
        TextField {
            id: cleanupFolderInput
            width: parent.width * 0.30
            height: 30
            text: camera.cleanupCustomFolder
            placeholderText: "OPTIONAL FOLDER"
            placeholderTextColor: Colors.cyan
            color: Colors.white
            font.pixelSize: 9
            selectByMouse: true
            background: Rectangle {
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
            }
            onAccepted: {
                camera.cleanupCustomFolder = text.trim();
                camera.loadGallery(false, "cleanup");
            }
        }
        ActionButton {
            width: Math.max(45, parent.width * 0.18 - 12)
            height: 30
            label: "SCAN"
            labelPixelSize: 9
            accentColor: Colors.cyan
            available: !camera.busy
            onLeftClicked: {
                camera.cleanupCustomFolder = cleanupFolderInput.text.trim();
                camera.loadGallery(false, "cleanup");
            }
        }
    }

    Row {
        id: cleanupFilterRow
        width: parent.width
        height: 28
        spacing: 5
        visible: camera.cleanupTechnique !== "desktop"
        Repeater {
            model: [
                {id: "all", label: "ALL"},
                {id: "screenshots", label: "SHOTS"},
                {id: "webcam", label: "WEBCAM"},
                {id: "videos", label: "VIDEOS"},
                {id: "screen-recordings", label: "SCREEN VIDEO"}
            ]
            ActionButton {
                width: (cleanupFilterRow.width - 4 * cleanupFilterRow.spacing) / 5
                height: 27
                label: cleanupPage.compactHosted
                       && modelData.id === "screen-recordings"
                       ? "SCREEN" : modelData.label
                labelPixelSize: 9
                accentColor: Colors.white
                selected: camera.cleanupMediaFilter === modelData.id
                available: !camera.busy
                onLeftClicked: {
                    camera.cleanupMediaFilter = modelData.id;
                    camera.loadGallery(false, "cleanup");
                }
            }
        }
    }

    Item {
        id: cleanupWorkArea
        width: parent.width
        height: camera.cleanupTechnique === "desktop"
                ? Math.max(170, cleanupPage.height - 135)
                : Math.max(145, cleanupPage.height - 216)

        Rectangle {
            id: cleanupQueueView
            anchors.fill: parent
            z: 250
            visible: camera.cleanupQueueOpen
                     && camera.cleanupTechnique !== "desktop"
            color: Colors.black
            radius: 5
            border.width: 1
            border.color: Colors.magenta
            Column {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 5
                Row {
                    width: parent.width
                    height: 29
                    spacing: 6
                    GohuText {
                        width: parent.width - 117
                        height: 28
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 11
                        color: Colors.magenta
                        text: "QUEUED FILES // " + camera.batchPaths.length
                              + "/500"
                    }
                    ActionButton {
                        width: 111
                        height: 28
                        label: "BACK TO MODE"
                        labelPixelSize: 9
                        accentColor: Colors.cyan
                        onLeftClicked: camera.cleanupToggleQueue()
                    }
                }
                GohuText {
                    width: parent.width
                    height: 18
                    font.pixelSize: 9
                    color: Colors.yellow
                    text: "REVIEW ITEMS // REMOVE TO UNMARK // TRASH BELOW"
                    elide: Text.ElideRight
                }
                Item {
                    width: parent.width
                    height: Math.max(40, cleanupWorkArea.height - 112)
                    ListView {
                        id: cleanupQueuedList
                        anchors.fill: parent
                        anchors.rightMargin: 11
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        spacing: 3
                        model: camera.batchPaths
                        delegate: Row {
                            width: cleanupQueuedList.width
                            height: 33
                            spacing: 5
                            GohuText {
                                width: parent.width - 89
                                height: 32
                                font.pixelSize: 9
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideMiddle
                                color: Colors.white
                                text: String(modelData).split("/").pop()
                                      + " // " + String(modelData)
                            }
                            ActionButton {
                                width: 84
                                height: 31
                                label: "REMOVE"
                                labelPixelSize: 9
                                accentColor: Colors.yellow
                                available: !camera.busy
                                onLeftClicked: camera.batchRemovePath(modelData)
                            }
                        }
                    }
                    NeonScrollBar {
                        flickable: cleanupQueuedList
                        x: parent.width - width - 1
                        height: parent.height
                        geometryMode: "viewport"
                        handleStyle: "star"
                        visible: scrollable
                    }
                    GohuText {
                        anchors.centerIn: parent
                        visible: camera.batchPaths.length === 0
                        font.pixelSize: 11
                        color: Colors.cyan
                        text: "QUEUE EMPTY // SELECT MEDIA IN ANY MODE"
                    }
                }
                ActionButton {
                    width: parent.width
                    height: 36
                    label: "MOVE " + camera.batchPaths.length + " TO TRASH"
                    labelPixelSize: 12
                    accentColor: Colors.red
                    destructive: true
                    available: !camera.busy && camera.batchPaths.length > 0
                    onLeftClicked: camera.trashQueuedNow()
                }
            }
        }

        Item {
            id: cleanupBatchView
            anchors.fill: parent
            visible: camera.cleanupTechnique === "batch"
                     && !camera.cleanupQueueOpen

            // Wide: file list and preview side by side.
            // Compact: list above preview with both sections reachable via
            // the Trash++ outer scroll controls, never a clipped preview.
            Column {
                id: cleanupBatchListPane
                x: 0
                y: 0
                width: cleanupPage.compactHosted
                       ? parent.width : Math.floor(parent.width * 0.53)
                height: cleanupPage.compactHosted
                        ? Math.floor((parent.height - 9) * 0.57)
                        : parent.height
                spacing: 5
                Row {
                    width: parent.width
                    height: 28
                    spacing: 5
                    ActionButton {
                        width: (parent.width - 5) / 2
                        height: 27
                        label: "SELECT LOADED"
                        labelPixelSize: 9
                        accentColor: Colors.cyan
                        available: !camera.busy && camera.galleryFiles.length > 0
                        onLeftClicked: camera.batchSelectLoaded("")
                    }
                    ActionButton {
                        width: (parent.width - 5) / 2
                        height: 27
                        label: "CLEAR QUEUE"
                        labelPixelSize: 9
                        accentColor: Colors.yellow
                        available: !camera.busy && camera.batchPaths.length > 0
                        onLeftClicked: camera.batchClear()
                    }
                }
                Row {
                    width: parent.width
                    height: 29
                    spacing: 5
                    TextField {
                        id: batchNameNeedle
                        width: parent.width - 83
                        height: 28
                        placeholderText: "NAME CONTAINS..."
                        placeholderTextColor: Colors.cyan
                        color: Colors.white
                        font.pixelSize: 9
                        selectByMouse: true
                        background: Rectangle {
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                        }
                    }
                    ActionButton {
                        width: 78
                        height: 28
                        label: "MATCH"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        available: !camera.busy && batchNameNeedle.text.trim().length > 0
                        onLeftClicked: camera.batchSelectLoaded(batchNameNeedle.text)
                    }
                }
                Item {
                    width: parent.width
                    height: Math.max(75, cleanupBatchListPane.height - 101)
                    ListView {
                        id: cleanupBatchList
                        anchors.fill: parent
                        anchors.rightMargin: 12
                        model: camera.galleryFiles
                        spacing: 4
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        delegate: Row {
                            width: cleanupBatchList.width
                            height: 44
                            spacing: 5
                            ActionButton {
                                width: parent.width * 0.75 - 5
                                height: 43
                                label: "      " + modelData.name
                                labelPixelSize: 9
                                labelHorizontalAlignment: Text.AlignLeft
                                contentPadding: 5
                                selected: camera.selectedPath === modelData.path
                                accentColor: Colors.white
                                onLeftClicked: camera.selectImage(modelData)
                                Image {
                                    width: 30
                                    height: 30
                                    x: 3
                                    y: 6
                                    source: modelData.mediaType
                                            && modelData.mediaType.indexOf("video") >= 0
                                            ? "" : camera.fileUrl(modelData.path)
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                    cache: false
                                }
                            }
                            ActionButton {
                                width: parent.width * 0.25
                                height: 43
                                label: camera.batchContains(modelData.path)
                                       ? "QUEUED" : "+ QUEUE"
                                labelPixelSize: 9
                                selected: camera.batchContains(modelData.path)
                                accentColor: Colors.magenta
                                available: !camera.busy
                                onLeftClicked: camera.batchToggle(modelData)
                            }
                        }
                    }
                    NeonScrollBar {
                        flickable: cleanupBatchList
                        x: parent.width - width - 1
                        height: parent.height
                        geometryMode: "viewport"
                        handleStyle: "star"
                        visible: scrollable
                    }
                }
                Row {
                    width: parent.width
                    height: 29
                    spacing: 7
                    GohuText {
                        width: parent.width - 120
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 9
                        color: Colors.cyan
                        text: camera.galleryFiles.length + "/"
                              + camera.galleryTotal + " LOADED"
                    }
                    ActionButton {
                        width: 112
                        height: 28
                        label: "LOAD 120 MORE"
                        labelPixelSize: 8
                        accentColor: Colors.cyan
                        available: !camera.busy && camera.galleryHasMore
                        onLeftClicked: camera.loadGallery(true, "cleanup")
                    }
                }
            }
            Column {
                id: cleanupBatchPreviewPane
                x: cleanupPage.compactHosted
                   ? 0 : cleanupBatchListPane.width + 9
                y: cleanupPage.compactHosted
                   ? cleanupBatchListPane.height + 9 : 0
                width: cleanupPage.compactHosted
                       ? parent.width : parent.width - cleanupBatchListPane.width - 9
                height: cleanupPage.compactHosted
                        ? parent.height - cleanupBatchListPane.height - 9
                        : parent.height
                spacing: 5
                GohuText {
                    width: parent.width
                    height: 16
                    font.pixelSize: 10
                    color: Colors.cyan
                    text: "SELECTED PREVIEW"
                }
                CameraImageViewer {
                    id: cleanupViewer
                    width: parent.width
                    height: Math.max(65, cleanupBatchPreviewPane.height - 88)
                    source: camera.selectedRecord
                            && camera.selectedRecord.mediaType.indexOf("video") < 0
                            ? camera.fileUrl(camera.selectedPath) : ""
                }
                GohuText {
                    width: parent.width
                    height: 20
                    elide: Text.ElideRight
                    font.pixelSize: 9
                    color: Colors.white
                    text: camera.selectedRecord
                          ? camera.selectedRecord.name
                          : "SELECT MEDIA ON THE LEFT"
                }
                ActionButton {
                    width: parent.width
                    height: 29
                    visible: camera.selectedRecord
                             && camera.selectedRecord.mediaType.indexOf("video") >= 0
                    label: "PLAY VIDEO"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    onLeftClicked: Qt.openUrlExternally(
                                       camera.fileUrl(camera.selectedPath))
                }
            }
        }

        Column {
            id: cleanupGridView
            anchors.fill: parent
            spacing: 5
            visible: camera.cleanupTechnique === "grid"
                     && !camera.cleanupQueueOpen
            Row {
                width: parent.width
                height: 26
                spacing: 7
                GohuText {
                    width: parent.width * 0.55
                    height: 25
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 10
                    color: Colors.cyan
                    text: "BATCH GRID // " + camera.galleryFiles.length
                          + " LOADED // " + camera.batchPaths.length
                          + " SELECTED"
                }
                ActionButton {
                    width: parent.width * 0.45 - 7
                    height: 25
                    label: "SELECT LOADED"
                    labelPixelSize: 9
                    accentColor: Colors.yellow
                    available: !camera.busy
                               && camera.galleryFiles.length > 0
                    onLeftClicked: camera.batchSelectLoaded("")
                }
            }
            Item {
                width: parent.width
                height: Math.max(65, cleanupWorkArea.height - 61)
                GridView {
                    id: cleanupGridList
                    anchors.fill: parent
                    anchors.rightMargin: 12
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: camera.galleryFiles
                    cellWidth: width / Math.max(1, Math.floor(width / 140))
                    cellHeight: 132
                    cacheBuffer: 240
                    delegate: Item {
                        id: cleanupGridTile
                        width: cleanupGridList.cellWidth
                        height: cleanupGridList.cellHeight
                        readonly property bool queued:
                            camera.batchContains(modelData.path)
                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 3
                            radius: 5
                            color: Colors.black
                            border.width: cleanupGridTile.queued ? 3 : 1
                            border.color: cleanupGridTile.queued
                                          ? Colors.magenta : Colors.cyan
                            Image {
                                x: 4
                                y: 4
                                width: parent.width - 8
                                height: parent.height - 28
                                source: modelData.mediaType
                                        && modelData.mediaType.indexOf("video") >= 0
                                        ? "" : camera.fileUrl(modelData.path)
                                fillMode: Image.PreserveAspectFit
                                sourceSize.width: 220
                                sourceSize.height: 160
                                asynchronous: true
                                cache: false
                            }
                            GohuText {
                                anchors.centerIn: parent
                                visible: modelData.mediaType
                                         && modelData.mediaType.indexOf("video") >= 0
                                font.pixelSize: 11
                                color: Colors.yellow
                                text: "VIDEO"
                            }
                            Rectangle {
                                x: parent.width - 66
                                y: 3
                                width: 63
                                height: 17
                                color: cleanupGridTile.queued
                                       ? Colors.magenta : Colors.black
                                border.color: Colors.cyan
                                border.width: 1
                                GohuText {
                                    anchors.centerIn: parent
                                    font.pixelSize: 9
                                    color: cleanupGridTile.queued
                                           ? Colors.black : Colors.cyan
                                    text: cleanupGridTile.queued
                                          ? "QUEUED" : "+ SELECT"
                                }
                            }
                            GohuText {
                                x: 5
                                anchors.bottom: parent.bottom
                                width: parent.width - 10
                                height: 20
                                font.pixelSize: 9
                                color: Colors.white
                                elide: Text.ElideMiddle
                                text: modelData.name
                            }
                            MouseArea {
                                anchors.fill: parent
                                enabled: !camera.busy
                                cursorShape: Qt.PointingHandCursor
                                onClicked: camera.batchToggle(modelData)
                            }
                        }
                    }
                }
                NeonScrollBar {
                    flickable: cleanupGridList
                    x: parent.width - width - 1
                    height: parent.height
                    geometryMode: "viewport"
                    handleStyle: "star"
                    visible: scrollable
                }
            }
            Row {
                width: parent.width
                height: 28
                spacing: 6
                GohuText {
                    width: parent.width - 132
                    height: 27
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 9
                    color: Colors.cyan
                    text: camera.galleryFiles.length + "/"
                          + camera.galleryTotal
                          + " VISIBLE // CLICK ANY THUMBNAIL"
                }
                ActionButton {
                    width: 126
                    height: 27
                    label: "LOAD 120 MORE"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    available: !camera.busy && camera.galleryHasMore
                    onLeftClicked: camera.loadGallery(true, "cleanup")
                }
            }
        }

        Column {
            id: cleanupSwipeView
            anchors.fill: parent
            spacing: 6
            visible: camera.cleanupTechnique === "swipe"
                     && !camera.cleanupQueueOpen

            GohuText {
                width: parent.width
                height: 17
                font.pixelSize: 10
                color: Colors.magenta
                text: "SWIPE // LEFT TRASH QUEUE · RIGHT KEEP · DOWN SKIP · Z UNDO"
            }
            Item {
                id: swipeDeck
                width: parent.width
                height: Math.max(90, cleanupWorkArea.height - 91)
                focus: camera.activeView === "cleanup"
                       && camera.cleanupTechnique === "swipe"
                property var currentRecord:
                    camera.swipeIndex < camera.galleryFiles.length
                    ? camera.galleryFiles[camera.swipeIndex] : null
                property real dragX: 0
                property real dragY: 0
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Left) {
                        camera.swipeDecide("trash");
                        event.accepted = true;
                    } else if (event.key === Qt.Key_Right) {
                        camera.swipeDecide("keep");
                        event.accepted = true;
                    } else if (event.key === Qt.Key_Down) {
                        camera.swipeDecide("skip");
                        event.accepted = true;
                    } else if (event.key === Qt.Key_Z
                               || event.key === Qt.Key_Backspace) {
                        camera.swipeUndo();
                        event.accepted = true;
                    }
                }

                Item {
                    id: swipeVisualCard
                    anchors.fill: parent
                    transform: Translate {
                        x: swipeDeck.dragX
                        y: swipeDeck.dragY
                    }
                    rotation: swipeDeck.dragX / 24

                Rectangle {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 20, 580)
                    height: parent.height - 2
                    radius: 8
                    color: Colors.black
                    border.color: Colors.magenta
                    border.width: 1
                }
                Image {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 36, 550)
                    height: Math.max(40, parent.height - 55)
                    visible: swipeDeck.currentRecord !== null
                             && swipeDeck.currentRecord.mediaType.indexOf("video") < 0
                    source: visible
                            ? camera.fileUrl(swipeDeck.currentRecord.path) : ""
                    fillMode: Image.PreserveAspectFit
                    cache: false
                    asynchronous: true
                }
                GohuText {
                    anchors.centerIn: parent
                    visible: swipeDeck.currentRecord === null
                             || swipeDeck.currentRecord.mediaType.indexOf("video") >= 0
                    font.pixelSize: 13
                    color: Colors.cyan
                    text: swipeDeck.currentRecord === null
                          ? camera.galleryHasMore
                            ? "END OF LOADED PAGE // LOAD MORE"
                            : "ROUND COMPLETE"
                          : "VIDEO // USE BATCH PREVIEW TO PLAY"
                }
                GohuText {
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(parent.width - 35, 540)
                    height: 28
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideMiddle
                    font.pixelSize: 10
                    color: Colors.white
                    text: swipeDeck.currentRecord !== null
                          ? swipeDeck.currentRecord.name
                          : "NO MORE LOADED FILES"
                }
                GohuText {
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    height: 24
                    visible: Math.abs(swipeDeck.dragX) > 35
                             || swipeDeck.dragY > 40
                    font.pixelSize: 14
                    color: swipeDeck.dragX < -35 ? Colors.red
                           : swipeDeck.dragX > 35 ? Colors.cyan
                           : Colors.yellow
                    text: swipeDeck.dragX < -35 ? "QUEUE FOR TRASH"
                          : swipeDeck.dragX > 35 ? "KEEP"
                          : "SKIP"
                }
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: swipeDeck.currentRecord !== null && !camera.busy
                    property real startX: 0
                    property real startY: 0
                    onPressed: function(mouse) {
                        startX = mouse.x;
                        startY = mouse.y;
                        swipeDeck.dragX = 0;
                        swipeDeck.dragY = 0;
                        swipeDeck.forceActiveFocus();
                    }
                    onPositionChanged: function(mouse) {
                        if (pressed) {
                            swipeDeck.dragX = Math.max(-180, Math.min(
                                180, mouse.x - startX));
                            swipeDeck.dragY = Math.max(-120, Math.min(
                                120, mouse.y - startY));
                        }
                    }
                    onReleased: function(mouse) {
                        const dx = mouse.x - startX;
                        const dy = mouse.y - startY;
                        swipeDeck.dragX = 0;
                        swipeDeck.dragY = 0;
                        if (Math.abs(dx) >= 65 && Math.abs(dx) > Math.abs(dy))
                            camera.swipeDecide(dx < 0 ? "trash" : "keep");
                        else if (dy >= 65)
                            camera.swipeDecide("skip");
                    }
                    onCanceled: {
                        swipeDeck.dragX = 0;
                        swipeDeck.dragY = 0;
                    }
                }
            }
            Row {
                width: parent.width
                height: 32
                spacing: 6
                ActionButton {
                    width: (parent.width - 18) / 4
                    height: 31
                    label: "LEFT · QUEUE"
                    labelPixelSize: 10
                    accentColor: Colors.red
                    available: !camera.busy
                               && camera.swipeIndex < camera.galleryFiles.length
                    onLeftClicked: camera.swipeDecide("trash")
                }
                ActionButton {
                    width: (parent.width - 18) / 4
                    height: 31
                    label: "RIGHT · KEEP"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    available: !camera.busy
                               && camera.swipeIndex < camera.galleryFiles.length
                    onLeftClicked: camera.swipeDecide("keep")
                }
                ActionButton {
                    width: (parent.width - 18) / 4
                    height: 31
                    label: "DOWN · SKIP"
                    labelPixelSize: 10
                    accentColor: Colors.yellow
                    available: !camera.busy
                               && camera.swipeIndex < camera.galleryFiles.length
                    onLeftClicked: camera.swipeDecide("skip")
                }
                ActionButton {
                    width: (parent.width - 18) / 4
                    height: 31
                    label: "UNDO"
                    labelPixelSize: 10
                    accentColor: Colors.magenta
                    available: !camera.busy && camera.swipeHistory.length > 0
                    onLeftClicked: camera.swipeUndo()
                }
            }
            Row {
                width: parent.width
                height: 22
                spacing: 8
                GohuText {
                    width: parent.width - 130
                    height: parent.height
                    font.pixelSize: 9
                    color: Colors.cyan
                    text: "CARD " + Math.min(camera.swipeIndex + 1,
                                              camera.galleryFiles.length)
                          + "/" + camera.galleryFiles.length
                          + " // QUEUED " + camera.batchPaths.length
                }
                ActionButton {
                    width: 122
                    height: 22
                    label: "LOAD 120 MORE"
                    labelPixelSize: 8
                    accentColor: Colors.white
                    available: !camera.busy && camera.galleryHasMore
                               && camera.swipeIndex >= camera.galleryFiles.length
                    onLeftClicked: camera.loadGallery(true, "cleanup")
                }
            }
        }


        // Three moving media targets per round. Hits only mark
        // Gallery-validated file paths in the common review queue.
        Item {
            id: cleanupHuntView
            anchors.fill: parent
            visible: camera.cleanupTechnique === "hunt"
                     && !camera.cleanupQueueOpen
            focus: visible && camera.activeView === "cleanup"

            Keys.onPressed: function(event) {
                // While paused, only P closes the menu.
                // N/Z cannot mutate play under an overlay.
                if (camera.huntPauseMenuOpen && event.key !== Qt.Key_P) {
                    event.accepted = true;
                    return;
                }
                if (event.key === Qt.Key_N) {
                    camera.huntStartRound();
                    event.accepted = true;
                } else if (event.key === Qt.Key_P) {
                    camera.huntTogglePause();
                    event.accepted = true;
                } else if (event.key === Qt.Key_Z) {
                    camera.huntUndo();
                    event.accepted = true;
                }
            }
            Timer {
                id: huntAutoNextTimer
                interval: 1250
                repeat: false
                running: camera.hostedCleanupActive && camera.huntAutoRounds
                         && camera.huntAutoPending
                         && !camera.huntSettingsOpen
                         && !camera.huntPauseMenuOpen
                         && camera.activeView === "cleanup"
                         && camera.cleanupTechnique === "hunt"
                         && !camera.busy
                onTriggered: camera.huntAutoStartNext()
            }
            Timer {
                id: huntHitFlashTimer
                // 180ms of flight followed by a short
                // 140ms arrival echo. Kept under one-third second.
                interval: 320
                repeat: false
                running: camera.huntShotEffect !== null
                onTriggered: {
                    camera.huntHitFlash = false;
                    camera.huntShotEffect = null;
                }
            }
            Connections {
                target: camera
                function onHuntShotSerialChanged() {
                    // Restart the one-shot projectile even for
                    // quick successive hits and misses.
                    huntLaserFlight.restart();
                    huntHitFlashTimer.restart();
                }
            }
            Timer {
                id: huntClock
                interval: 100
                repeat: true
                running: camera.hostedCleanupActive
                         && camera.activeView === "cleanup"
                         && camera.cleanupTechnique === "hunt"
                         && !camera.busy && !camera.huntPaused
                         && camera.huntTargets.length > 0
                         && camera.huntSecondsLeft > 0
                onTriggered: camera.huntAdvance()
            }
            Column {
                width: parent.width
                height: parent.height
                spacing: 6

                Row {
                    width: parent.width
                    height: 22
                    spacing: 6
                    GohuText {
                        width: (parent.width - 12) / 3
                        height: 22
                        font.pixelSize: 10
                        color: Colors.magenta
                        text: "SCORE // " + camera.huntScore
                    }
                    GohuText {
                        width: (parent.width - 12) / 3
                        height: 22
                        font.pixelSize: 10
                        color: Colors.cyan
                        text: "HITS " + camera.huntHits
                              + " // MISSES " + camera.huntMisses
                    }
                    GohuText {
                        width: (parent.width - 12) / 3
                        height: 22
                        font.pixelSize: 10
                        color: camera.huntSecondsLeft < 6
                               ? Colors.red : Colors.yellow
                        text: "ROUND " + camera.huntRound
                              + " // " + camera.huntSecondsLeft + " SEC"
                              + " // " + camera.huntRoundSpeed.toFixed(2) + "X"
                    }
                }

                Row {
                    id: huntSpawnRow
                    width: parent.width
                    height: 27
                    spacing: 6
                    ActionButton {
                        width: (parent.width - 12) * 0.29
                        height: 26
                        label: "SPAWN -"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        available: !camera.busy && camera.huntSpawnCount > 1
                        onLeftClicked: camera.huntSetSpawnCount(
                                           camera.huntSpawnCount - 1)
                    }
                    GohuText {
                        width: (parent.width - 12) * 0.42
                        height: 26
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: 10
                        color: Colors.yellow
                        text: "TARGETS // " + camera.huntSpawnCount
                              + " / 10"
                    }
                    ActionButton {
                        width: (parent.width - 12) * 0.29
                        height: 26
                        label: "SPAWN +"
                        labelPixelSize: 10
                        accentColor: Colors.magenta
                        available: !camera.busy && camera.huntSpawnCount < 10
                        onLeftClicked: camera.huntSetSpawnCount(
                                           camera.huntSpawnCount + 1)
                    }
                }

                Rectangle {
                    id: huntArena
                    width: parent.width
                    height: Math.max(80, cleanupWorkArea.height - 132)
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    radius: 4
                    clip: true

                    Repeater {
                        model: 3
                        Rectangle {
                            x: 4
                            y: (index + 1) * huntArena.height / 3
                            width: huntArena.width - 8
                            height: 1
                            color: Colors.cyan
                            opacity: 0.18
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: !camera.huntPaused && !camera.busy
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        hoverEnabled: true
                        // The arena renders its own bright crosshair.
                        cursorShape: camera.huntPaused
                                     ? Qt.ArrowCursor : Qt.BlankCursor
                        onPositionChanged: function(mouse) {
                            camera.huntSetPointer(mouse.x, mouse.y,
                                                  huntArena.width,
                                                  huntArena.height);
                        }
                        onExited: {
                            camera.huntMouseActive = false;
                            camera.huntMouseMovingTicks = 0;
                        }
                        onPressed: function(mouse) {
                            huntArena.forceActiveFocus();
                            if (mouse.button === Qt.RightButton) {
                                camera.huntSetPointer(mouse.x, mouse.y,
                                                      huntArena.width,
                                                      huntArena.height);
                                camera.huntSetScoped(true);
                            }
                        }
                        onReleased: function(mouse) {
                            if (mouse.button === Qt.RightButton)
                                camera.huntSetScoped(false);
                        }
                        onCanceled: camera.huntSetScoped(false)
                        onClicked: function(mouse) {
                            if (mouse.button === Qt.LeftButton)
                                camera.huntFire(
                                    "", mouse.x / huntArena.width,
                                    mouse.y / huntArena.height);
                        }
                    }
                    Repeater {
                        id: huntTargetRepeater
                        // Count-only model preserves QML delegates and
                        // thumbnails while huntTargets changes 10x/sec.
                        model: camera.huntTargets.length
                        delegate: Item {
                            id: huntTargetItem
                            property var target: camera.huntTargets[index]
                            property bool hovered: false
                            readonly property color targetTint:
                                camera.huntTargetColor(target.profile)
                            readonly property color mediaTint:
                                camera.huntMediaTint(target.mediaKind)
                            // Dense rounds preserve usable hitboxes.
                            // Ox is larger and always above the other
                            // thumbnail actors if targets overlap.
                            readonly property real crowdScale: Math.max(
                                0.63, Math.min(1, Math.sqrt(
                                    3 / Math.max(3, camera.huntTargets.length))))
                            readonly property real unscopedWidth: Math.min(
                                Math.max(40, huntArena.width - 16),
                                Math.min(170, Math.max(90,
                                    huntArena.width / 4.6))
                                * target.sizeScale * crowdScale)
                            readonly property real unscopedHeight: Math.min(
                                Math.max(30, huntArena.height - 12),
                                Math.min(88, Math.max(51,
                                    huntArena.height / 4.3))
                                * target.sizeScale * crowdScale)
                            readonly property real unscopedX: 8 + Math.max(
                                0, huntArena.width - unscopedWidth - 16)
                                * target.xNorm
                            readonly property real unscopedY: 6 + Math.max(
                                0, huntArena.height - unscopedHeight - 12)
                                * target.yNorm
                            width: unscopedWidth * camera.huntScopeScale
                            height: unscopedHeight * camera.huntScopeScale
                            z: camera.huntTargetDepth(target.profile)
                            // The magnified *hitbox* follows the actual
                            // magnified thumbnail, not the old world rect.
                            x: (unscopedX - huntArena.width * camera.huntMouseX)
                               * camera.huntScopeScale
                               + huntArena.width * camera.huntMouseX
                               + camera.huntScopeSwayX
                            y: (unscopedY - huntArena.height * camera.huntMouseY)
                               * camera.huntScopeScale
                               + huntArena.height * camera.huntMouseY
                               + camera.huntScopeSwayY
                            Behavior on x {
                                NumberAnimation {
                                    duration: 100
                                    easing.type: Easing.Linear
                                }
                            }
                            Behavior on y {
                                NumberAnimation {
                                    duration: 100
                                    easing.type: Easing.Linear
                                }
                            }

                            RectangularShadow {
                                anchors.fill: huntTargetPlate
                                z: -1
                                // Keep hover feedback understated;
                                // the hit itself owns the strong cue.
                                spread: huntTargetItem.hovered ? 5 : 3
                                color: huntTargetItem.targetTint
                                opacity: huntTargetItem.hovered ? 0.18 : 0.10
                                visible: !camera.huntPaused
                                Behavior on opacity {
                                    NumberAnimation { duration: 170 }
                                }
                            }
                            Rectangle {
                                id: huntTargetPlate
                                anchors.fill: parent
                                radius: 5
                                border.width: 2
                                border.color: huntTargetItem.targetTint
                                color: Colors.black
                                clip: true
                                Image {
                                    x: 4
                                    y: 3
                                    width: parent.width - 8
                                    height: parent.height - 21
                                    source: huntTargetItem.target.mediaType.indexOf("video") >= 0
                                            ? ""
                                            : camera.fileUrl(huntTargetItem.target.path)
                                    sourceSize.width: 200
                                    sourceSize.height: 110
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                    cache: false
                                }
                                Rectangle {
                                    // 5.5% content tint, independent of
                                    // the much stronger animal border.
                                    x: 4
                                    y: 3
                                    width: parent.width - 8
                                    height: parent.height - 21
                                    z: 2
                                    color: huntTargetItem.mediaTint
                                    opacity: 0.055
                                }
                                GohuText {
                                    anchors.centerIn: parent
                                    visible: huntTargetItem.target.mediaType.indexOf("video") >= 0
                                    font.pixelSize: 12
                                    color: huntTargetItem.targetTint
                                    text: "VIDEO"
                                }
                                GohuText {
                                    x: 3
                                    y: 2
                                    z: 3
                                    font.pixelSize: 9
                                    color: huntTargetItem.targetTint
                                    text: huntTargetItem.target.profile.toUpperCase()
                                }
                                GohuText {
                                    x: parent.width * 0.41
                                    y: 2
                                    z: 3
                                    width: parent.width * 0.57
                                    horizontalAlignment: Text.AlignRight
                                    elide: Text.ElideRight
                                    font.pixelSize: 8
                                    color: huntTargetItem.mediaTint
                                    text: camera.huntMediaLabel(
                                        huntTargetItem.target.mediaKind)
                                }
                                GohuText {
                                    anchors.bottom: parent.bottom
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    width: parent.width - 6
                                    height: 17
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideMiddle
                                    font.pixelSize: 9
                                    color: Colors.white
                                    text: huntTargetItem.target.name
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: !camera.huntPaused && !camera.busy
                                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                                    hoverEnabled: true
                                    cursorShape: camera.huntPaused
                                                 ? Qt.ArrowCursor : Qt.BlankCursor
                                    onEntered: huntTargetItem.hovered = true
                                    onExited: huntTargetItem.hovered = false
                                    onPositionChanged: function(mouse) {
                                        const position = mapToItem(
                                            huntArena, mouse.x, mouse.y);
                                        camera.huntSetPointer(
                                            position.x, position.y,
                                            huntArena.width, huntArena.height);
                                    }
                                    onPressed: function(mouse) {
                                        huntArena.forceActiveFocus();
                                        if (mouse.button === Qt.RightButton) {
                                            const pos = mapToItem(
                                                huntArena, mouse.x, mouse.y);
                                            camera.huntSetPointer(
                                                pos.x, pos.y,
                                                huntArena.width, huntArena.height);
                                            camera.huntSetScoped(true);
                                        }
                                    }
                                    onReleased: function(mouse) {
                                        if (mouse.button === Qt.RightButton)
                                            camera.huntSetScoped(false);
                                    }
                                    onCanceled: camera.huntSetScoped(false)
                                    onClicked: function(mouse) {
                                        if (mouse.button !== Qt.LeftButton)
                                            return;
                                        if (huntTargetItem.target.protected) {
                                            // User's screen-recording SAFE rule.
                                            camera.huntKeepProtected(
                                                huntTargetItem.target.path);
                                            return;
                                        }
                                        // The exact click position, NOT
                                        // the target's rectangle center,
                                        // determines laser trajectory.
                                        const impact = mapToItem(
                                            huntArena, mouse.x, mouse.y);
                                        camera.huntSetPointer(
                                            impact.x, impact.y,
                                            huntArena.width, huntArena.height);
                                        camera.huntFire(
                                            huntTargetItem.target.path,
                                            impact.x / huntArena.width,
                                            impact.y / huntArena.height,
                                            huntTargetItem.x / huntArena.width,
                                            huntTargetItem.y / huntArena.height,
                                            huntTargetItem.width / huntArena.width,
                                            huntTargetItem.height / huntArena.height);
                                    }
                                }
                            }
                        }
                    }
                    // Hit feedback is intentionally restrained. Animal
                    // echoes flash red; the WORLD gets only 4.5% of
                    // the current laser color, never a full-screen blast.
                    Rectangle {
                        id: huntHitWash
                        anchors.fill: parent
                        z: 70
                        color: camera.huntShotEffect
                               ? camera.huntShotEffect.color : Colors.cyan
                        opacity: camera.huntHitFlash
                                 && huntLaserLayer.impactReached
                                 ? 0.045 : 0.0
                        visible: opacity > 0
                        Behavior on opacity {
                            NumberAnimation { duration: 100 }
                        }
                    }
                    Item {
                        id: huntLaserLayer
                        anchors.fill: parent
                        z: 74
                        visible: camera.huntShotEffect !== null
                        property real progress: 0.0
                        readonly property var shot: camera.huntShotEffect
                            || ({aimX: 0.5, aimY: 0.5, color: Colors.cyan})
                        // The cursor IS the aim point. The muzzle is
                        // attached to that aim and begins below the
                        // visible arena, like a hand-held waist gun,
                        // not a fixed weapon on the game board.
                        readonly property var trajectory:
                            HuntMotion.laserTrajectory(
                                shot.aimX, shot.aimY)
                        readonly property real muzzleX:
                            width * trajectory.originX
                        readonly property real muzzleY:
                            height * trajectory.originY
                        readonly property real impactX:
                            width * trajectory.aimX
                        readonly property real impactY:
                            height * trajectory.aimY
                        readonly property real dx: impactX - muzzleX
                        readonly property real dy: impactY - muzzleY
                        readonly property real length:
                            Math.sqrt(dx * dx + dy * dy)
                        readonly property real angle:
                            Math.atan2(dy, dx) * 180 / Math.PI
                        // A compact moving bolt, NOT a beam that
                        // grows all the way from the player's waist.
                        readonly property real streakPixels:
                            Math.min(42, Math.max(18, length * 0.14))
                        readonly property real tailProgress:
                            Math.max(0, progress - streakPixels
                                     / Math.max(1, length))
                        readonly property real tailX:
                            muzzleX + dx * tailProgress
                        readonly property real tailY:
                            muzzleY + dy * tailProgress
                        readonly property real visibleStreak:
                            length * (progress - tailProgress)
                        readonly property bool impactReached:
                            progress >= 0.999
                        NumberAnimation {
                            id: huntLaserFlight
                            target: huntLaserLayer
                            property: "progress"
                            from: 0
                            to: 1
                            duration: 180
                            easing.type: Easing.OutCubic
                        }
                        Rectangle {
                            // Outer faint streak follows the bolt's
                            // tail rather than illuminating its path.
                            visible: huntLaserLayer.progress > 0
                                     && !huntLaserLayer.impactReached
                            x: huntLaserLayer.tailX
                            y: huntLaserLayer.tailY - height / 2
                            width: huntLaserLayer.visibleStreak
                            height: 5
                            radius: 2
                            rotation: huntLaserLayer.angle
                            transformOrigin: Item.Left
                            color: huntLaserLayer.shot.color
                            opacity: 0.14
                        }
                        Rectangle {
                            visible: huntLaserLayer.progress > 0
                                     && !huntLaserLayer.impactReached
                            x: huntLaserLayer.tailX
                            y: huntLaserLayer.tailY - height / 2
                            width: huntLaserLayer.visibleStreak
                            height: 2
                            radius: 1
                            rotation: huntLaserLayer.angle
                            transformOrigin: Item.Left
                            color: huntLaserLayer.shot.color
                            opacity: 0.78
                        }
                        Rectangle {
                            visible: huntLaserLayer.progress > 0
                                     && !huntLaserLayer.impactReached
                            x: huntLaserLayer.muzzleX
                               + huntLaserLayer.dx * huntLaserLayer.progress
                               - width / 2
                            y: huntLaserLayer.muzzleY
                               + huntLaserLayer.dy * huntLaserLayer.progress
                               - height / 2
                            width: 7
                            height: 7
                            radius: 4
                            color: huntLaserLayer.shot.color
                            opacity: 0.88
                        }
                        Rectangle {
                            // Small light only when the bolt
                            // crosses the bottom viewport boundary.
                            x: huntLaserLayer.width
                               * huntLaserLayer.trajectory.entryX
                               - width / 2
                            y: huntLaserLayer.height - height / 2
                            width: 15
                            height: 5
                            radius: 3
                            color: huntLaserLayer.shot.color
                            opacity: huntLaserLayer.progress
                                        >= huntLaserLayer.trajectory.entryProgress
                                     && huntLaserLayer.progress
                                        < huntLaserLayer.trajectory.entryProgress + 0.14
                                     ? 0.28 : 0
                        }
                        Rectangle {
                            // A small contact spark when the laser
                            // arrives. Never global/fullscreen.
                            visible: huntLaserLayer.impactReached
                                     && huntLaserLayer.shot.hit
                            x: huntLaserLayer.impactX - width / 2
                            y: huntLaserLayer.impactY - height / 2
                            width: 14
                            height: 14
                            radius: 7
                            color: "transparent"
                            border.width: 2
                            border.color: huntLaserLayer.shot.color
                            opacity: 0.50
                        }
                    }
                    // Gameplay removes the target immediately, but
                    // the captured thumbnail stays visible during
                    // flight. It turns RED only after impact.
                    Item {
                        id: huntHitAnimalEcho
                        z: 77
                        visible: camera.huntShotEffect
                                 && camera.huntShotEffect.hit
                        readonly property var shot: camera.huntShotEffect
                            || ({rectX: 0, rectY: 0, rectW: 0, rectH: 0,
                                 path: "", mediaType: ""})
                        x: shot.rectX * huntArena.width
                        y: shot.rectY * huntArena.height
                        width: shot.rectW * huntArena.width
                        height: shot.rectH * huntArena.height
                        clip: true
                        Rectangle {
                            anchors.fill: parent
                            radius: 5
                            color: Colors.black
                            border.color: huntLaserLayer.impactReached
                                          ? Colors.red
                                          : camera.huntTargetColor(
                                              huntHitAnimalEcho.shot.profile)
                            border.width: 2
                            Image {
                                anchors.fill: parent
                                anchors.margins: 3
                                source: huntHitAnimalEcho.shot.mediaType.indexOf("video") >= 0
                                        ? ""
                                        : camera.fileUrl(huntHitAnimalEcho.shot.path)
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                                cache: false
                            }
                            Rectangle {
                                anchors.fill: parent
                                radius: 4
                                color: Colors.red
                                opacity: huntLaserLayer.impactReached
                                         ? 0.40 : 0
                            }
                            GohuText {
                                anchors.centerIn: parent
                                visible: huntLaserLayer.impactReached
                                text: "HIT"
                                font.pixelSize: 12
                                color: Colors.white
                            }
                        }
                    }
                    Item {
                        id: huntNormalCrosshair
                        width: 32
                        height: 32
                        z: 80
                        visible: camera.huntMouseActive
                                 && !camera.huntPaused
                                 && !camera.huntScoped
                                 && !camera.huntSettingsOpen
                        x: huntArena.width * camera.huntMouseX - width / 2
                        y: huntArena.height * camera.huntMouseY - height / 2
                        Rectangle {
                            anchors.centerIn: parent
                            width: 25
                            height: 25
                            radius: 13
                            color: "transparent"
                            border.width: 1
                            border.color: Colors.cyan
                            opacity: 0.75
                        }
                        Rectangle {
                            anchors.centerIn: parent
                            width: 1
                            height: 32
                            color: Colors.white
                        }
                        Rectangle {
                            anchors.centerIn: parent
                            width: 32
                            height: 1
                            color: Colors.white
                        }
                        Rectangle {
                            anchors.centerIn: parent
                            width: 5
                            height: 5
                            radius: 3
                            color: Colors.magenta
                        }
                    }
                    Item {
                        id: huntScopeReticle
                        anchors.fill: parent
                        z: 90
                        visible: camera.huntScoped
                        // Non-interactive optical overlay. Target
                        // MouseAreas underneath keep their exact bounds.
                        Rectangle {
                            x: parent.width * camera.huntMouseX - width / 2
                               + camera.huntScopeSwayX
                            y: parent.height * camera.huntMouseY - height / 2
                               + camera.huntScopeSwayY
                            width: 122
                            height: 122
                            radius: 61
                            color: "transparent"
                            border.width: 2
                            border.color: Colors.cyan
                            Rectangle {
                                anchors.centerIn: parent
                                width: 1
                                height: 110
                                color: Colors.cyan
                                opacity: 0.65
                            }
                            Rectangle {
                                anchors.centerIn: parent
                                width: 110
                                height: 1
                                color: Colors.cyan
                                opacity: 0.65
                            }
                            Rectangle {
                                anchors.centerIn: parent
                                width: 7
                                height: 7
                                radius: 4
                                color: Colors.magenta
                            }
                        }
                        GohuText {
                            x: 6
                            y: 5
                            color: Colors.yellow
                            font.pixelSize: 10
                            text: "SCOPE // 1.85X // HOLD RIGHT"
                        }
                    }
                    GohuText {
                        anchors.centerIn: parent
                        visible: camera.huntTargets.length === 0
                                 || camera.huntPaused
                        font.pixelSize: 13
                        color: Colors.yellow
                        text: camera.huntTargets.length === 0
                              ? "HUNT // PRESS NEW ROUND"
                              : camera.huntRoundComplete
                                ? "ROUND CLEARED"
                                : "PAUSED"
                    }
                }

                Row {
                    width: parent.width
                    height: 30
                    spacing: 6
                    ActionButton {
                        width: (parent.width - 18) / 4
                        height: 29
                        label: "NEW ROUND"
                        labelPixelSize: 10
                        accentColor: Colors.magenta
                        available: !camera.busy
                            && (camera.huntTargets.length === 0
                                || camera.huntRoundComplete)
                        onLeftClicked: {
                            camera.huntStartRound();
                            cleanupHuntView.forceActiveFocus();
                        }
                    }
                    ActionButton {
                        width: (parent.width - 18) / 4
                        height: 29
                        label: camera.huntPauseMenuOpen ? "RESUME" : "PAUSE"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        available: !camera.busy
                        onLeftClicked: camera.huntTogglePause()
                    }
                    ActionButton {
                        width: (parent.width - 18) / 4
                        height: 29
                        label: "UNDO SHOT"
                        labelPixelSize: 9
                        accentColor: Colors.yellow
                        available: !camera.busy
                            && camera.huntHistory.length > 0
                        onLeftClicked: camera.huntUndo()
                    }
                    ActionButton {
                        width: (parent.width - 18) / 4
                        height: 29
                        label: "LOAD MORE"
                        labelPixelSize: 9
                        accentColor: Colors.white
                        available: !camera.busy && camera.galleryHasMore
                            && camera.huntTargets.length === 0
                        onLeftClicked: camera.loadGallery(true, "cleanup")
                    }
                }
                GohuText {
                    width: parent.width
                    height: 19
                    font.pixelSize: 9
                    color: Colors.cyan
                    elide: Text.ElideRight
                    text: camera.huntLastEvent
                          + " // " + camera.batchPaths.length
                          + " MARKED // RIGHT-HOLD SCOPE"
                }
            }

            Rectangle {
                id: huntSettingsOverlay
                anchors.fill: parent
                z: 200
                visible: camera.huntPauseMenuOpen
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta
                radius: 5

                Column {
                    id: huntPauseContents
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10
                    visible: !camera.huntSettingsOpen
                    GohuText {
                        width: parent.width
                        height: 26
                        font.pixelSize: 15
                        color: Colors.magenta
                        text: "HUNT // PAUSED"
                    }
                    GohuText {
                        width: parent.width
                        height: 46
                        wrapMode: Text.WordWrap
                        font.pixelSize: 10
                        color: Colors.cyan
                        text: "ROUND " + camera.huntRound
                              + " // SCORE " + camera.huntScore
                              + " // " + camera.batchPaths.length
                              + " FILES IN REVIEW QUEUE"
                    }
                    ActionButton {
                        width: parent.width
                        height: 36
                        label: camera.huntTargets.length === 0
                               ? "RETURN TO ARENA" : "RESUME HUNT"
                        labelPixelSize: 11
                        accentColor: Colors.cyan
                        onLeftClicked: camera.huntTogglePause()
                    }
                    ActionButton {
                        width: parent.width
                        height: 36
                        label: "SETTINGS"
                        labelPixelSize: 11
                        accentColor: Colors.yellow
                        onLeftClicked: camera.huntToggleSettings()
                    }
                    ActionButton {
                        width: parent.width
                        height: 36
                        label: "RESTART GAME // ROUND 1"
                        labelPixelSize: 10
                        accentColor: Colors.magenta
                        onLeftClicked: camera.huntRestartGame()
                    }
                    GohuText {
                        width: parent.width
                        height: 40
                        wrapMode: Text.WordWrap
                        font.pixelSize: 10
                        color: Colors.yellow
                        text: "RESTART RESETS ROUNDS AND SCORE. YOUR TRASH REVIEW QUEUE IS PRESERVED."
                    }
                }

                Flickable {
                    id: huntSettingsScroll
                    visible: camera.huntSettingsOpen
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    contentHeight: huntSettingsColumn.implicitHeight
                    Column {
                        id: huntSettingsColumn
                        width: huntSettingsScroll.width
                        spacing: 7
                        GohuText {
                            width: parent.width
                            height: 23
                            color: Colors.magenta
                            font.pixelSize: 13
                            text: "HUNT // ROUND PROGRESSION"
                        }
                        GohuText {
                            width: parent.width
                            height: 23
                            color: Colors.cyan
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                            text: "START " + camera.huntSpawnCount
                                  + " // MAX 10 TARGETS // SPEED MAX 2.50X"
                        }
                        ActionButton {
                            width: parent.width
                            height: 30
                            label: camera.huntAutoRounds
                                   ? "AUTO NEXT ROUND // ON"
                                   : "AUTO NEXT ROUND // OFF"
                            labelPixelSize: 10
                            selected: camera.huntAutoRounds
                            accentColor: Colors.yellow
                            onLeftClicked: camera.huntSetAutoRounds(
                                               !camera.huntAutoRounds)
                        }
                        ActionButton {
                            width: parent.width
                            height: 32
                            label: "RESET DEFAULTS // SETTINGS"
                            labelPixelSize: 10
                            accentColor: Colors.orange
                            onLeftClicked: camera.huntResetDefaults()
                        }
                        Repeater {
                            model: [
                                {id: "targetGain", label: "ADD TARGETS / TIER", step: 1, low: 0, high: 5},
                                {id: "targetEvery", label: "ADD EVERY N ROUNDS", step: 1, low: 1, high: 50},
                                {id: "speedGain", label: "SPEED GAIN / TIER", step: 5, low: 0, high: 50},
                                {id: "speedEvery", label: "SPEED EVERY N ROUNDS", step: 1, low: 1, high: 50}
                            ]
                            delegate: Row {
                                id: huntProgressionRow
                                width: huntSettingsColumn.width
                                height: 34
                                spacing: 5
                                readonly property int currentValue:
                                    modelData.id === "targetGain" ? camera.huntTargetsPerTier
                                    : modelData.id === "targetEvery" ? camera.huntTargetsEvery
                                    : modelData.id === "speedGain" ? camera.huntSpeedGainPercent
                                    : camera.huntSpeedEvery
                                GohuText {
                                    width: (huntProgressionRow.width - 15) * 0.43
                                    height: 33
                                    verticalAlignment: Text.AlignVCenter
                                    color: Colors.white
                                    font.pixelSize: 9
                                    text: modelData.label
                                }
                                ActionButton {
                                    width: (huntProgressionRow.width - 15) * 0.17
                                    height: 32
                                    label: "−"
                                    accentColor: Colors.cyan
                                    available: !camera.busy
                                               && huntProgressionRow.currentValue > modelData.low
                                    onLeftClicked: camera.huntSetProgression(
                                        modelData.id,
                                        huntProgressionRow.currentValue - modelData.step)
                                }
                                GohuText {
                                    width: (huntProgressionRow.width - 15) * 0.23
                                    height: 33
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: Text.AlignHCenter
                                    color: Colors.yellow
                                    font.pixelSize: 11
                                    text: modelData.id === "speedGain"
                                          ? "+" + huntProgressionRow.currentValue + "%"
                                          : "" + huntProgressionRow.currentValue
                                }
                                ActionButton {
                                    width: (huntProgressionRow.width - 15) * 0.17
                                    height: 32
                                    label: "+"
                                    accentColor: Colors.magenta
                                    available: !camera.busy
                                               && huntProgressionRow.currentValue < modelData.high
                                    onLeftClicked: camera.huntSetProgression(
                                        modelData.id,
                                        huntProgressionRow.currentValue + modelData.step)
                                }
                            }
                        }
                        GohuText {
                            width: parent.width
                            height: 39
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                            color: Colors.cyan
                            text: "ROUND " + (camera.huntRound + 1)
                                + " FORECAST // "
                                + HuntMotion.spawnForRound(
                                    camera.huntSpawnCount,
                                    camera.huntTargetsPerTier,
                                    camera.huntTargetsEvery,
                                    camera.huntRound + 1)
                                + " TARGETS // "
                                + HuntMotion.speedForRound(
                                    camera.huntSpeedGainPercent,
                                    camera.huntSpeedEvery,
                                    camera.huntRound + 1).toFixed(2) + "X SPEED"
                        }
                        ActionButton {
                            width: parent.width
                            height: 34
                            label: "BACK TO PAUSE"
                            labelPixelSize: 11
                            accentColor: Colors.magenta
                            onLeftClicked: camera.huntToggleSettings()
                        }
                        GohuText {
                            width: parent.width
                            height: 28
                            wrapMode: Text.WordWrap
                            font.pixelSize: 9
                            color: Colors.yellow
                            text: "DEFAULTS: 3 TARGETS, +1 EVERY 5, +10% SPEED EVERY 5. CHANGES APPLY NEXT ROUND."
                        }
                    }
                }
            }
        }

        Flickable {
            id: cleanupDesktopView
            anchors.fill: parent
            visible: camera.cleanupTechnique === "desktop"
            clip: true
            contentHeight: desktopCleanupContent.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            Column {
                id: desktopCleanupContent
                width: cleanupWorkArea.width - 18
                spacing: 12
                GohuText {
                    width: parent.width
                    font.pixelSize: 14
                    color: Colors.white
                    text: "DESKTOP // SCREENSHOT CLEANUP"
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    color: Colors.cyan
                    text: "Matches Desktop screenshot-like PNG/JPEG/WEBP only. Other photos and subfolders remain untouched."
                }
                ActionButton {
                    width: 210
                    height: 40
                    label: "PREVIEW MATCHES"
                    labelPixelSize: 11
                    accentColor: Colors.white
                    available: !camera.busy
                    onLeftClicked: camera.previewCleanup()
                }
                GohuText {
                    width: parent.width
                    font.pixelSize: 12
                    color: Colors.white
                    text: camera.trashPreview
                          ? "MATCHES // " + camera.trashPreview.count
                            + " // BYTES " + camera.trashPreview.bytes
                          : "MATCHES // NOT PREVIEWED"
                }
                GohuText {
                    width: parent.width
                    height: 95
                    wrapMode: Text.WrapAnywhere
                    color: Colors.cyan
                    font.pixelSize: 10
                    text: camera.trashPreview && camera.trashPreview.sample
                          ? "EXAMPLES // " + camera.trashPreview.sample.join(" // ")
                          : "Preview before moving screenshot files to Trash."
                }
                ActionButton {
                    width: 225
                    height: 43
                    label: camera.trashPreview
                           ? "MOVE " + camera.trashPreview.count + " TO TRASH"
                           : "TRASH REQUIRES PREVIEW"
                    labelPixelSize: 11
                    accentColor: Colors.red
                    destructive: true
                    available: !camera.busy && camera.trashPreview !== null
                               && Number(camera.trashPreview.count) > 0
                               && !!camera.trashPreview.planId
                    onLeftClicked: camera.confirmCleanup()
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                    color: Colors.red
                    text: "RECOVERABLE TRASH ONLY // NO PERMANENT DELETE // PLAN EXPIRES IN 10 MINUTES"
                }
            }
        }
    }
}

