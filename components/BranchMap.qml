import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: branchMap

    property var topologyService: null
    property string titleText: "BRANCH MAP"
    property string selectedSha: ""
    property int headerHeight: 28
    property int rowHeight: 24
    property int laneWidth: 22
    property int maxVisibleLanes: 7

    signal commitSelected(string sha)

    color: Colors.dark
    border.width: 1
    border.color: Colors.cyan

    RectangularShadow {
        anchors.fill: parent
        spread: 4
        z: -1
        opacity: 0.20
        color: Colors.cyan
    }

    function laneColor(laneNumber) {
        const lane = Number(laneNumber || 0) % 6;

        if (lane === 0)
            return Colors.orange;
        if (lane === 1)
            return Colors.cyan;
        if (lane === 2)
            return Colors.magenta;
        if (lane === 3)
            return Colors.blue;
        if (lane === 4)
            return Colors.green;

        return Colors.red;
    }

    function nodeX(laneNumber) {
        return 14 + Number(laneNumber || 0) * laneWidth;
    }

    function escapeStyled(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function refPieces(refValue) {
        return String(refValue || "")
            .split(" • ")
            .filter(function(name) { return name.length > 0; });
    }

    function graphMetadataMarkup(refValue, subjectValue, headRow) {
        const refs = String(refValue || "")
            .split(" • ")
            .filter(function(name) { return name.length > 0; });
        const pieces = [];

        for (let i = 0; i < refs.length; ++i) {
            const name = refs[i];
            const color = name.indexOf("origin/") === 0
                ? String(Colors.white)
                : String(Colors.cyan);

            pieces.push(
                "<font color=\"" + color + "\">"
                + escapeStyled(name)
                + "</font>"
            );
        }

        let result = pieces.join(
            "<font color=\"" + String(Colors.white) + "\"> • </font>"
        );

        const subject = String(subjectValue || "");

        if (subject) {
            if (result)
                result += "<font color=\"" + String(Colors.white) + "\">  //  </font>";
            else
                result += "<font color=\"" + String(Colors.white) + "\">//  </font>";

            result += "<font color=\""
                + String(
                    headRow
                    ? Colors.yellow
                    : refs.length > 0
                    ? Colors.cyan
                    : Colors.blue
                )
                + "\">"
                + escapeStyled(subject)
                + "</font>";
        }

        return result;
    }

    Item {
        anchors {
            fill: parent
            margins: 10
        }

        Item {
            id: header
            width: parent.width
            height: branchMap.headerHeight

            GohuText {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: branchMap.selectedSha
                      ? branchMap.titleText + " // SELECTED " + branchMap.selectedSha.slice(0, 8)
                      : branchMap.titleText
                font.pixelSize: 12
                color: Colors.magenta

                layer.enabled: true
                layer.effect: DropShadow {
                    radius: 6
                    samples: 7
                    opacity: 0.46
                    color: Colors.magenta
                    transparentBorder: true
                }
            }

            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4

                GohuText {
                    visible: branchMap.topologyService && branchMap.topologyService.refreshing
                    text: "READING GIT GRAPH"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                GohuText {
                    visible: branchMap.topologyService && !branchMap.topologyService.refreshing
                    text: branchMap.topologyService ? String(branchMap.topologyService.commitCount) : "0"
                    font.pixelSize: 10
                    color: Colors.orange
                }

                GohuText {
                    visible: branchMap.topologyService && !branchMap.topologyService.refreshing
                    text: "COMMITS //"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                GohuText {
                    visible: branchMap.topologyService && !branchMap.topologyService.refreshing
                    text: branchMap.topologyService ? String(branchMap.topologyService.branchCount) : "0"
                    font.pixelSize: 10
                    color: Colors.orange
                }

                GohuText {
                    visible: branchMap.topologyService && !branchMap.topologyService.refreshing
                    text: "REFS"
                    font.pixelSize: 9
                    color: Colors.cyan
                }
            }
        }

        Flickable {
            id: topologyFlick

            anchors {
                top: header.bottom
                topMargin: 4
                left: parent.left
                right: parent.right
                bottom: parent.bottom
            }

            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentWidth: width
            contentHeight: Math.max(
                height,
                (branchMap.topologyService ? branchMap.topologyService.commitCount : 0)
                    * branchMap.rowHeight
            )

            Item {
                id: topologyBody

                width: topologyFlick.width
                height: topologyFlick.contentHeight

                readonly property real laneAreaWidth:
                    Math.min(
                        190,
                        44 + (
                            branchMap.topologyService
                            ? Math.min(branchMap.maxVisibleLanes, branchMap.topologyService.maxLane + 1)
                            : 1
                        ) * branchMap.laneWidth
                    )

                Canvas {
                    id: graphCanvas

                    anchors.fill: parent

                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()

                    onPaint: {
                        const ctx = getContext("2d");

                        ctx.globalAlpha = 1.0;
                        ctx.clearRect(0, 0, width, height);
                        ctx.lineWidth = 1.35;

                        if (!branchMap.topologyService)
                            return;

                        for (let i = 0; i < branchMap.topologyService.commitCount; ++i) {
                            const row = branchMap.topologyService.commitAt(i);

                            if (!row)
                                continue;

                            const parents = String(row.parents || "").trim();

                            if (!parents)
                                continue;

                            const parentList = parents.split(/\s+/);
                            const x1 = branchMap.nodeX(row.lane);
                            const y1 = i * branchMap.rowHeight + branchMap.rowHeight / 2;

                            for (let p = 0; p < parentList.length; ++p) {
                                const parentIndex =
                                    branchMap.topologyService.indexOfSha(parentList[p]);

                                if (parentIndex < 0)
                                    continue;

                                const parentRow =
                                    branchMap.topologyService.commitAt(parentIndex);

                                if (!parentRow)
                                    continue;

                                const x2 = branchMap.nodeX(parentRow.lane);
                                const y2 = parentIndex * branchMap.rowHeight
                                         + branchMap.rowHeight / 2;
                                const middleY = y1 + (y2 - y1) * 0.52;

                                ctx.beginPath();
                                ctx.strokeStyle = String(branchMap.laneColor(row.lane));
                                ctx.globalAlpha = 0.72;
                                ctx.moveTo(x1, y1);
                                ctx.lineTo(x1, middleY);
                                ctx.lineTo(x2, middleY);
                                ctx.lineTo(x2, y2);
                                ctx.stroke();
                            }
                        }

                        ctx.globalAlpha = 1.0;
                    }
                }

                Repeater {
                    model: branchMap.topologyService
                           ? branchMap.topologyService.topologyModel
                           : null

                    delegate: Item {
                        id: topologyRow

                        width: topologyBody.width
                        height: branchMap.rowHeight
                        y: index * branchMap.rowHeight

                        readonly property bool selected:
                            branchMap.selectedSha === String(sha || "")
                        readonly property bool refLandmark:
                            String(refsText || "").length > 0

                        Rectangle {
                            width: isHead || topologyRow.refLandmark ? 10 : 8
                            height: width
                            radius: width / 2
                            x: branchMap.nodeX(lane) - width / 2
                            anchors.verticalCenter: parent.verticalCenter
                            color: Colors.dark
                            z: 1
                        }

                        NotoText {
                            width: 20
                            height: parent.height
                            x: branchMap.nodeX(lane) - width / 2
                            anchors.verticalCenter: parent.verticalCenter
                            z: 2
                            visible: topologyRow.selected

                            text: isHead || topologyRow.refLandmark ? "★" : "✧"
                            font.pixelSize: isHead ? 15 : 13
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            color: Colors.white

                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 12
                                samples: 17
                                opacity: 0.72
                                color: Colors.cyan
                                transparentBorder: true
                            }
                        }

                        NotoText {
                            id: topologyStar

                            width: 20
                            height: parent.height
                            x: branchMap.nodeX(lane) - width / 2
                            anchors.verticalCenter: parent.verticalCenter
                            z: 3

                            text: isHead || topologyRow.refLandmark ? "★" : "✧"
                            font.pixelSize: isHead ? 15 : 13
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            color: Colors.white

                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: isHead ? 8 : 6
                                samples: isHead ? 11 : 9
                                opacity: isHead
                                         ? 0.58
                                         : topologyRow.refLandmark
                                         ? 0.40
                                         : 0.30
                                color: Colors.cyan
                                transparentBorder: true
                            }
                        }

                        Row {
                            id: metadataRow

                            x: topologyBody.laneAreaWidth
                            width: parent.width - x - 6
                            height: parent.height
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 4

                            GohuText {
                                id: shaText

                                anchors.verticalCenter: parent.verticalCenter
                                text: shortSha
                                font.pixelSize: 9
                                color: Colors.orange

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 7
                                    samples: 9
                                    opacity: 0.30
                                    color: Colors.orange
                                    transparentBorder: true
                                }
                            }

                            Item {
                                id: metadataDetails

                                width: Math.max(
                                    0,
                                    metadataRow.width
                                    - shaText.implicitWidth
                                    - metadataRow.spacing
                                )
                                height: parent.height
                                clip: true

                                Row {
                                    id: metadataTextRow

                                    anchors.verticalCenter: parent.verticalCenter
                                    height: parent.height
                                    spacing: 0

                                    Repeater {
                                        id: refsRepeater
                                        model: branchMap.refPieces(refsText)

                                        delegate: Row {
                                            height: metadataTextRow.height
                                            spacing: 0

                                            GohuText {
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: modelData
                                                font.pixelSize: 9
                                                color:
                                                    String(modelData).indexOf("origin/") === 0
                                                    ? Colors.white
                                                    : Colors.cyan

                                                layer.enabled: true
                                                layer.effect: DropShadow {
                                                    radius: 7
                                                    samples: 9
                                                    opacity: 0.18
                                                    color: Colors.cyan
                                                    transparentBorder: true
                                                }
                                            }

                                            GohuText {
                                                anchors.verticalCenter: parent.verticalCenter
                                                visible: index < refsRepeater.count - 1
                                                text: " • "
                                                font.pixelSize: 9
                                                color: Colors.white

                                                layer.enabled: true
                                                layer.effect: DropShadow {
                                                    radius: 7
                                                    samples: 9
                                                    opacity: 0.16
                                                    color: Colors.cyan
                                                    transparentBorder: true
                                                }
                                            }
                                        }
                                    }

                                    GohuText {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: Math.max(
                                            0,
                                            metadataDetails.width - x
                                        )
                                        text:
                                            (refsRepeater.count > 0 ? "  //  " : "//  ")
                                            + String(subject || "")
                                        font.pixelSize: 9
                                        color:
                                            isHead
                                            ? Colors.yellow
                                            : refsRepeater.count > 0
                                            ? Colors.cyan
                                            : Colors.blue
                                        elide: Text.ElideRight

                                        layer.enabled: true
                                        layer.effect: DropShadow {
                                            radius: 7
                                            samples: 9
                                            opacity:
                                                isHead
                                                ? 0.16
                                                : refsRepeater.count > 0
                                                ? 0.16
                                                : 0.08
                                            color:
                                                isHead
                                                ? Colors.orange
                                                : Colors.cyan
                                            transparentBorder: true
                                        }
                                    }
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            z: 20
                            acceptedButtons: Qt.LeftButton
                            hoverEnabled: true
                            preventStealing: false
                            cursorShape: Qt.PointingHandCursor

                            onClicked: branchMap.commitSelected(String(sha || ""))
                        }
                    }
                }

                Connections {
                    target: branchMap.topologyService
                    enabled: branchMap.topologyService !== null
                    ignoreUnknownSignals: true

                    function onTopologyRevisionChanged() {
                        graphCanvas.requestPaint();

                        if (
                            branchMap.selectedSha
                            && branchMap.topologyService
                            && branchMap.topologyService.indexOfSha(branchMap.selectedSha) < 0
                        )
                            branchMap.commitSelected("");
                    }
                }
            }
        }

        Item {
            id: scrollIndicator

            anchors {
                top: header.bottom
                topMargin: 4
                bottom: parent.bottom
                right: parent.right
            }

            width: 14
            z: 50

            readonly property bool canScroll:
                topologyFlick.contentHeight > topologyFlick.height + 1
            readonly property bool active:
                canScroll
                && (
                    topologyFlick.moving
                    || topologyFlick.dragging
                    || topologyFlick.flicking
                )

            opacity: active ? 1.0 : 0.0

            Behavior on opacity {
                NumberAnimation {
                    duration: 120
                }
            }

            Rectangle {
                width: 1
                anchors {
                    top: parent.top
                    bottom: parent.bottom
                    horizontalCenter: parent.horizontalCenter
                }

                color: Colors.cyan
                opacity: 0.62
            }

            NotoText {
                width: parent.width
                height: 16
                x: 0

                readonly property real scrollRange:
                    Math.max(0.0001, 1.0 - topologyFlick.visibleArea.heightRatio)
                readonly property real scrollFraction:
                    Math.max(
                        0.0,
                        Math.min(
                            1.0,
                            topologyFlick.visibleArea.yPosition / scrollRange
                        )
                    )

                y: scrollFraction * Math.max(0, parent.height - height)

                text: "★"
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                color: Colors.orange
            }
        }
    }
}
