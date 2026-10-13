import QtQuick
import qs.components

Item {
    id: root

    required property var receptionistService

    property string sourceFilter: "ALL"
    property string attentionFilter: "ALL"
    property int selectedIndex: -1

    signal eventActivated(var event)

    readonly property var sourceModes: [
        "ALL",
        "ROUNDS",
        "REPORTS",
        "INTERCOM",
        "PHONE",
        "STAFF"
    ]

    readonly property var attentionModes: [
        "ALL",
        "CRITICAL",
        "ACTION",
        "NOTICE",
        "ROUTINE"
    ]

    readonly property var filteredEvents: {
        const source =
            root.receptionistService
            && Array.isArray(root.receptionistService.activityEvents)
            ? root.receptionistService.activityEvents
            : [];
        const sourceNeedle =
            String(root.sourceFilter || "ALL").toLowerCase();
        const attentionNeedle =
            String(root.attentionFilter || "ALL").toUpperCase();
        const rows = source.filter(function(event) {
            const row = event || {};
            const rowSource =
                String(row.source || "").toLowerCase();

            if (sourceNeedle !== "all"
                    && rowSource !== sourceNeedle)
                return false;

            if (attentionNeedle === "ALL")
                return true;

            const score =
                Number(
                    root.receptionistService
                        .activityAttentionScore(row)
                    || 0
                );

            if (attentionNeedle === "CRITICAL")
                return score >= 90;
            if (attentionNeedle === "ACTION")
                return score >= 60;
            if (attentionNeedle === "NOTICE")
                return score >= 30 && score < 60;
            if (attentionNeedle === "ROUTINE")
                return score < 30;

            return true;
        });

        rows.sort(function(a, b) {
            return root.receptionistService.eventEpoch(b)
                - root.receptionistService.eventEpoch(a);
        });
        return rows;
    }

    readonly property var selectedEvent: {
        if (selectedIndex < 0
                || selectedIndex >= filteredEvents.length)
            return null;

        return filteredEvents[selectedIndex] || null;
    }

    function attentionColor(eventValue) {
        const score =
            Number(
                receptionistService
                    .activityAttentionScore(eventValue || {})
                || 0
            );

        if (score >= 90)
            return Colors.red;
        if (score >= 60)
            return Colors.orange;
        if (score >= 30)
            return Colors.yellow;

        return Colors.cyan;
    }

    function selectEvent(indexValue) {
        const requested = Number(indexValue);

        if (requested < 0
                || requested >= filteredEvents.length)
            return false;

        selectedIndex = requested;
        return true;
    }

    function resetSelection() {
        selectedIndex =
            filteredEvents.length > 0 ? 0 : -1;
        archiveList.contentY = 0;
    }

    function filterLabel() {
        return [
            "ARCHIVE",
            root.sourceFilter,
            root.attentionFilter
        ].join(" // ");
    }

    onFilteredEventsChanged: {
        if (filteredEvents.length === 0) {
            selectedIndex = -1;
            return;
        }

        if (selectedIndex < 0
                || selectedIndex >= filteredEvents.length)
            selectedIndex = 0;
    }

    component ArchiveButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property color accent: Colors.cyan

        signal triggered()

        height: 30
        color:
            selectedAction
            ? Colors.yellow
            : mouse.pressed
            ? Colors.orange
            : Colors.black
        border.width:
            selectedAction || mouse.containsMouse
            ? 2 : 1
        border.color:
            selectedAction
            ? Colors.orange
            : mouse.containsMouse
            ? Colors.orange
            : accent

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 9
            color:
                button.selectedAction
                ? Colors.magenta
                : mouse.pressed
                ? Colors.black
                : button.accent
            opacity: button.enabledAction ? 1.0 : 0.34
        }

        MouseArea {
            id: mouse

            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape:
                enabled
                ? Qt.PointingHandCursor
                : Qt.ArrowCursor

            onClicked: button.triggered()
        }
    }


    // Syntagma pilot: ordinary Archive actions use the shared ActionButton.
    // Source and attention filter controls remain the separate selector family.
    component ArchiveActionButton: ActionButton {
        id: action

        property string fullLabel: ""
        property string compactIcon: ""
        property string miniIcon: compactIcon
        property string actionDescription: fullLabel
        property bool specialAction: false
        property color specialHoverForeground: accentColor

        readonly property real contentWidthBudget: Math.max(0, width - 12)
        readonly property bool fullLabelFits:
            minimumLabelMeasure.implicitWidth <= contentWidthBudget
        readonly property bool compactIconFits:
            compactIconMeasure.implicitWidth <= contentWidthBudget

        height: 35
        implicitHeight: 35
        label: fullLabel
        showLabel: false
        contentItem.clip: true

        Accessible.role: Accessible.Button
        Accessible.name: actionDescription
        acceptedButtons: Qt.LeftButton

        idleFillColor: Colors.black
        hoverFillColor: Colors.yellow
        selectedFillColor: Colors.yellow
        keyboardSelectedFillColor: Colors.yellow
        pressedFillColor: Colors.magenta
        idleForegroundColor: accentColor
        hoverForegroundColor:
            specialAction ? specialHoverForeground : Colors.orange
        selectedForegroundColor: hoverForegroundColor
        keyboardSelectedForegroundColor: hoverForegroundColor
        pressedForegroundColor: Colors.black

        // Accent is semantic, independent of yellow hover and magenta press.
        idleBorderColor: accentColor
        hoverBorderColor: specialAction ? accentColor : Colors.orange
        selectedBorderColor: hoverBorderColor
        keyboardSelectedBorderColor: hoverBorderColor
        pressedBorderColor: specialAction ? accentColor : Colors.orange
        // Border thickness normalization is still a separate decision.
        idleBorderWidth: 1
        hoverBorderWidth: 1
        selectedBorderWidth: 1
        keyboardSelectedBorderWidth: 1
        pressedBorderWidth: 1

        contentGlowSource: actionText
        contentGlowEnabled: true
        idleContentGlowColor: accentColor
        hoverContentGlowColor:
            specialAction ? accentColor : Colors.orange
        selectedContentGlowColor: hoverContentGlowColor
        keyboardSelectedContentGlowColor: hoverContentGlowColor
        pressedContentGlowColor:
            specialAction ? accentColor : Colors.orange
        contentGlowIdleOpacity: 0.35
        contentGlowHoverOpacity: 0.75
        contentGlowSelectedOpacity: 0.75
        contentGlowKeyboardSelectedOpacity: 0.75
        contentGlowPressedOpacity: 1.0

        softGlowEnabled: true
        softGlowSpread: 3
        idleSoftGlowColor: accentColor
        hoverSoftGlowColor:
            specialAction ? accentColor : Colors.orange
        selectedSoftGlowColor: hoverSoftGlowColor
        keyboardSelectedSoftGlowColor: hoverSoftGlowColor
        pressedSoftGlowColor:
            specialAction ? accentColor : Colors.orange
        softGlowIdleOpacity: 0.25
        softGlowHoverOpacity: 0.55
        softGlowSelectedOpacity: 0.55
        softGlowKeyboardSelectedOpacity: 0.55
        softGlowPressedOpacity: 0.60

        // Wide halo is optional; preserve clearance between the three actions.
        wideGlowEnabled: false

        GohuText {
            id: minimumLabelMeasure
            visible: false
            text: action.fullLabel
            font.pixelSize: 8
        }
        GohuText {
            id: compactIconMeasure
            visible: false
            text: action.compactIcon
            font.pixelSize: 12
        }
        GohuText {
            id: actionText
            anchors.centerIn: parent
            width: action.contentWidthBudget
            height: Math.max(0, action.height - 8)
            visible: width > 0
            text: action.fullLabelFits ? action.fullLabel
                  : action.compactIconFits ? action.compactIcon
                  : action.miniIcon
            font.pixelSize: action.fullLabelFits ? 11
                            : action.compactIconFits ? 12 : 9
            fontSizeMode: Text.HorizontalFit
            minimumPixelSize: action.fullLabelFits ? 8 : 7
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideNone
            color: action.foregroundColor
        }
    }

    Column {
        anchors.fill: parent
        spacing: 8

        SectionFrame {
            width: parent.width
            height: 42
            fillColor: Colors.dark
            borderWidth: 1
            borderColor: Colors.cyan
            inset: 8

            Row {
                anchors.fill: parent

                spacing: 12

                GohuText {
                    width: 180
                    anchors.verticalCenter: parent.verticalCenter
                    text: "ARCHIVE // RECEPTION HISTORY"
                    font.pixelSize: 12
                    color: Colors.cyan
                    elide: Text.ElideRight
                }

                GohuText {
                    width: parent.width - 192
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        String(root.filteredEvents.length)
                        + " SHOWN // "
                        + String(
                            root.receptionistService.archiveCount
                        )
                        + " TOTAL // "
                        + String(
                            root.receptionistService.pinnedCount
                        )
                        + " FAVORITES"
                    font.pixelSize: 10
                    color: Colors.white
                    elide: Text.ElideRight
                }
            }
        }

        Row {
            width: parent.width
            height: 30
            spacing: 5

            Repeater {
                model: root.sourceModes

                ArchiveButton {
                    required property string modelData

                    width:
                        (
                            parent.width
                            - (
                                Math.max(
                                    0,
                                    root.sourceModes.length - 1
                                )
                                * parent.spacing
                              )
                        )
                        / root.sourceModes.length
                    label: modelData
                    selectedAction:
                        root.sourceFilter === modelData

                    onTriggered: {
                        root.sourceFilter = modelData;
                        root.resetSelection();
                    }
                }
            }
        }

        Row {
            width: parent.width
            height: 30
            spacing: 5

            Repeater {
                model: root.attentionModes

                ArchiveButton {
                    required property string modelData

                    width:
                        (
                            parent.width
                            - (
                                Math.max(
                                    0,
                                    root.attentionModes.length - 1
                                )
                                * parent.spacing
                              )
                        )
                        / root.attentionModes.length
                    label: modelData
                    accent:
                        modelData === "CRITICAL"
                        ? Colors.red
                        : modelData === "ACTION"
                        ? Colors.orange
                        : modelData === "NOTICE"
                        ? Colors.yellow
                        : Colors.cyan
                    selectedAction:
                        root.attentionFilter === modelData

                    onTriggered: {
                        root.attentionFilter = modelData;
                        root.resetSelection();
                    }
                }
            }
        }

        Row {
            width: parent.width
            height:
                Math.max(
                    140,
                    parent.height
                    - 42
                    - 30
                    - 30
                    - 28
                    - (parent.spacing * 4)
                )
            spacing: 8

            Rectangle {
                width: Math.floor((parent.width - parent.spacing) * 0.58)
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                clip: true

                Flickable {
                    id: archiveList

                    anchors {
                        fill: parent
                        margins: 6
                        rightMargin: 14
                    }

                    contentWidth: width
                    contentHeight: archiveRows.implicitHeight
                    boundsBehavior: Flickable.StopAtBounds
                    clip: true

                    Column {
                        id: archiveRows

                        width: archiveList.width
                        spacing: 4

                        Repeater {
                            model: root.filteredEvents

                            Rectangle {
                                id: archiveRow

                                required property var modelData
                                required property int index

                                readonly property bool selected:
                                    root.selectedIndex === index
                                readonly property color accent:
                                    root.attentionColor(modelData)

                                width: archiveRows.width
                                height: 58
                                color:
                                    selected
                                    ? Colors.yellow
                                    : archiveMouse.pressed
                                    ? Colors.dark
                                    : Colors.black
                                border.width:
                                    selected
                                    || archiveMouse.containsMouse
                                    ? 2 : 1
                                border.color:
                                    selected
                                    ? Colors.magenta
                                    : archiveMouse.containsMouse
                                    ? Colors.orange
                                    : accent

                                Column {
                                    anchors {
                                        fill: parent
                                        margins: 6
                                    }

                                    spacing: 2

                                    GohuText {
                                        width: parent.width
                                        text:
                                            String(
                                                archiveRow
                                                    .modelData.timeLabel
                                                || ""
                                            )
                                            + " // "
                                            + String(
                                                archiveRow
                                                    .modelData.source
                                                || "activity"
                                            ).toUpperCase()
                                            + " // "
                                            + String(
                                                root.receptionistService
                                                    .activityAttentionLabel(
                                                        archiveRow.modelData
                                                    )
                                            )
                                        font.pixelSize: 8
                                        color:
                                            archiveRow.selected
                                            ? Colors.magenta
                                            : archiveRow.accent
                                        elide: Text.ElideRight
                                    }

                                    GohuText {
                                        width: parent.width
                                        text:
                                            String(
                                                archiveRow
                                                    .modelData.title
                                                || "HOSPITAL ACTIVITY"
                                            )
                                        font.pixelSize: 10
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }

                                    GohuText {
                                        width: parent.width
                                        text:
                                            String(
                                                archiveRow
                                                    .modelData.detail
                                                || ""
                                            )
                                        font.pixelSize: 8
                                        color: Colors.white
                                        opacity: 0.58
                                        elide: Text.ElideRight
                                    }
                                }

                                MouseArea {
                                    id: archiveMouse

                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor

                                    onClicked:
                                        root.selectEvent(
                                            archiveRow.index
                                        )

                                    onDoubleClicked: {
                                        root.selectEvent(
                                            archiveRow.index
                                        );
                                        root.eventActivated(
                                            archiveRow.modelData
                                        );
                                    }
                                }
                            }
                        }

                        GohuText {
                            width: parent.width
                            visible:
                                root.filteredEvents.length === 0
                            text: "NO ARCHIVE EVENTS MATCH THESE FILTERS"
                            font.pixelSize: 10
                            color: Colors.cyan
                            opacity: 0.62
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }

                NeonScrollBar {
                    flickable: archiveList
                    handleStyle: "star"
                }
            }

            SectionFrame {
                width: parent.width
                    - Math.floor((parent.width - parent.spacing) * 0.58)
                    - parent.spacing
                height: parent.height
                fillColor: Colors.dark
                borderWidth: 1
                borderColor:
                    root.selectedEvent
                    ? root.attentionColor(root.selectedEvent)
                    : Colors.cyan
                inset: 9

                Column {
                    anchors.fill: parent

                    spacing: 7

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedEvent
                            ? String(
                                root.selectedEvent.title
                                || "HOSPITAL ACTIVITY"
                              )
                            : "ARCHIVE // SELECT EVENT"
                        font.pixelSize: 12
                        color: Colors.magenta
                        wrapMode: Text.WordWrap
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedEvent
                            ? (
                                String(
                                    root.selectedEvent.source
                                    || "activity"
                                ).toUpperCase()
                                + " // "
                                + String(
                                    root.receptionistService
                                        .activityAttentionLabel(
                                            root.selectedEvent
                                        )
                                )
                              )
                            : ""
                        font.pixelSize: 9
                        color:
                            root.selectedEvent
                            ? root.attentionColor(
                                root.selectedEvent
                              )
                            : Colors.cyan
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedEvent
                            ? String(
                                root.selectedEvent.recordedAt
                                || ""
                              )
                            : ""
                        font.pixelSize: 8
                        color: Colors.white
                        opacity: 0.58
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        height:
                            Math.max(
                                52,
                                parent.height - 163
                            )
                        text:
                            root.selectedEvent
                            ? String(
                                root.selectedEvent.detail
                                || "NO DETAIL"
                              )
                            : "Select an archived event to inspect it."
                        font.pixelSize: 10
                        color: Colors.white
                        opacity:
                            root.selectedEvent ? 0.92 : 0.52
                        wrapMode: Text.WordWrap
                    }

                    Row {
                        id: archiveActionRow
                        width: parent.width
                        height: 35
                        spacing: Math.min(8, Math.max(5, width * 0.02))

                        // All three widths + two gaps must fit the inset panel.
                        readonly property real actionWidth: Math.max(
                            0, (width - 2 * spacing) / 3
                        )

                        ArchiveActionButton {
                            width: archiveActionRow.actionWidth
                            fullLabel: "OPEN"
                            compactIcon: "↗"
                            miniIcon: "↗"
                            actionDescription: "Open selected archive event"
                            available: root.selectedEvent !== null

                            onTriggered:
                                root.eventActivated(
                                    root.selectedEvent
                                )
                        }

                        ArchiveActionButton {
                            width: archiveActionRow.actionWidth
                            fullLabel:
                                root.selectedEvent
                                && root.receptionistService
                                    .isPinned(root.selectedEvent)
                                ? "UNFAVORITE"
                                : "FAVORITE"
                            compactIcon:
                                root.selectedEvent
                                && root.receptionistService
                                    .isPinned(root.selectedEvent)
                                ? "★"
                                : "☆"
                            miniIcon: compactIcon
                            actionDescription:
                                fullLabel === "UNFAVORITE"
                                ? "Remove selected archive event from favorites"
                                : "Favorite selected archive event"
                            accentColor: Colors.yellow
                            specialAction: true
                            // Orange lettering stays visible on yellow hover.
                            specialHoverForeground: Colors.orange
                            available: root.selectedEvent !== null

                            onTriggered: {
                                root.receptionistService
                                    .togglePinned(
                                        root.selectedEvent
                                    );
                            }
                        }

                        ArchiveActionButton {
                            width: archiveActionRow.actionWidth
                            fullLabel: "EXPORT"
                            compactIcon: "⇧"
                            miniIcon: "⇧"
                            actionDescription: "Export filtered archive events"
                            accentColor: Colors.green
                            specialAction: true
                            specialHoverForeground: Colors.green
                            available: root.filteredEvents.length > 0

                            onTriggered:
                                root.receptionistService
                                    .exportArchive(
                                        root.filteredEvents,
                                        root.filterLabel()
                                    )
                        }
                    }
                }
            }
        }

        GohuText {
            width: parent.width
            height: 28
            text:
                root.receptionistService.lastArchiveExportStatus
                || (
                    "FILTER // "
                    + root.sourceFilter
                    + " // "
                    + root.attentionFilter
                    + " // DOUBLE-CLICK EVENT TO OPEN"
                   )
            font.pixelSize: 9
            color:
                root.receptionistService
                    .lastArchiveExportStatus
                    .indexOf("FAILED") >= 0
                ? Colors.red
                : root.receptionistService
                    .lastArchiveExportStatus
                    .length > 0
                ? Colors.green
                : Colors.cyan
            elide: Text.ElideRight
        }
    }
}
