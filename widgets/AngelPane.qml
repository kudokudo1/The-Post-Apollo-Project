import QtQuick
import QtQuick.Controls
import Quickshell
import qs.services.time
import "../components"
import "../services/time/AngelObservationPolicy.js" as AngelPolicy

// ANGEL M1: explicit local observations, structural filters and a scrollable
// history. Reference interpretations and MAGICK astronomy are separate lanes.
Item {
    id: pane
    property double currentEpochMs: 0
    property string selectedId: ""
    property string pendingDeleteId: ""
    property string activeFilter: "all"
    readonly property bool editingText:
        manualDigitsInput.activeFocus || angelSearchInput.activeFocus
    readonly property var clockCandidate:
        AngelPolicy.clockCapture(
            TimeSettings.adjustedEpochMs(currentEpochMs))
    readonly property var filteredRows:
        AngelPolicy.filter(AngelObservationsStore.observations,
                           angelSearchInput.text, activeFilter)
    readonly property var selectedObservation:
        AngelObservationsStore.observations.find(function(row) {
            return row.id === pane.selectedId;
        }) || null

    readonly property var filters: [
        {key: "all", label: "ALL"},
        {key: "repeat", label: "REP"},
        {key: "mirror", label: "MIR"},
        {key: "sequence", label: "SEQ"},
        {key: "add", label: "ADD"},
        {key: "subtract", label: "SUB"},
        {key: "other", label: "OTHER"}
    ]

    function recordObservation(inputDigits, mode) {
        const observedAtMs = Date.now();
        const displayEpochMs = TimeSettings.adjustedEpochMs(observedAtMs);
        const capture = AngelPolicy.clockCapture(displayEpochMs);
        if (capture === null)
            return false;
        const localDate = new Date(displayEpochMs);
        const zone = String(TimeSettings.hostInfo.timezone || "UNKNOWN");
        return AngelObservationsStore.record(
            inputDigits, {
                displayTime: capture.displayTime,
                zoneId: zone,
                utcOffsetMinutes: -localDate.getTimezoneOffset(),
                displayCalibrationMs: TimeSettings.displayOffsetMs,
                captureMode: mode
            }, observedAtMs);
    }

    function recordClock() {
        const observedAtMs = Date.now();
        const value = AngelPolicy.clockCapture(
            TimeSettings.adjustedEpochMs(observedAtMs));
        if (value !== null)
            recordObservation(value.digits, "clock");
    }

    function recordManual() {
        const digits = manualDigitsInput.text.trim();
        if (!AngelPolicy.validDigits(digits))
            return;
        if (recordObservation(digits, "manual"))
            manualDigitsInput.text = "";
    }

    Column {
        anchors.fill: parent
        spacing: 7

        GohuText {
            width: parent.width
            text: "ANGEL // PERSONAL OBSERVATIONS"
            font.pixelSize: 13
            color: Colors.magenta
        }

        Row {
            width: parent.width
            height: 34
            spacing: 7

            GohuText {
                width: Math.max(0, parent.width - recordClockButton.width
                                - parent.spacing)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 12
                color: Colors.white
                text: pane.clockCandidate
                      ? "CLOCK 12H // " + pane.clockCandidate.digits
                      : "CLOCK 12H // UNAVAILABLE"
                elide: Text.ElideRight
            }

            ActionButton {
                id: recordClockButton
                width: 113
                height: parent.height
                label: "RECORD NOW"
                labelPixelSize: 10
                trackLabelGlowLocally: true
                accentColor: Colors.white
                available: AngelObservationsStore.writable
                           && pane.clockCandidate !== null
                onLeftClicked: pane.recordClock()
            }
        }

        Row {
            width: parent.width
            height: 34
            spacing: 7

            TextField {
                id: manualDigitsInput
                width: Math.max(0, parent.width - recordManualButton.width
                                - parent.spacing)
                height: parent.height
                placeholderText: "NUMBER // 347, 101, 0222..."
                placeholderTextColor: Colors.cyan
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 11
                maximumLength: AngelPolicy.MAX_DIGITS
                inputMethodHints: Qt.ImhDigitsOnly
                validator: RegularExpressionValidator {
                    regularExpression: /[0-9]{0,8}/
                }
                selectByMouse: true
                background: Rectangle {
                    color: Colors.black
                    border.width: 1
                    border.color: manualDigitsInput.activeFocus
                                  ? Colors.magenta : Colors.cyan
                }
                onAccepted: pane.recordManual()
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Escape) {
                        manualDigitsInput.focus = false;
                        event.accepted = true;
                    }
                }
            }

            ActionButton {
                id: recordManualButton
                width: 113
                height: parent.height
                label: "RECORD ENTRY"
                labelPixelSize: 9
                trackLabelGlowLocally: true
                accentColor: Colors.white
                available: AngelObservationsStore.writable
                           && AngelPolicy.validDigits(manualDigitsInput.text)
                onLeftClicked: pane.recordManual()
            }
        }

        GohuText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.cyan
            wrapMode: Text.WordWrap
            text: "RECORD ONLY WHEN NOTICED // 12H CLOCK PATTERN OR MANUAL DIGITS. THE UTC INSTANT IS PRESERVED."
        }

        Rectangle {
            width: parent.width
            height: 2
            color: Colors.cyan
            opacity: 0.6
        }

        GohuText {
            width: parent.width
            text: "HISTORY // " + pane.filteredRows.length
                  + " SHOWN / " + AngelObservationsStore.total + " SAVED"
            font.pixelSize: 12
            color: Colors.white
        }

        TextField {
            id: angelSearchInput
            width: parent.width
            height: 31
            placeholderText: "SEARCH DIGITS // 222, 347, 101..."
            placeholderTextColor: Colors.cyan
            color: Colors.magenta
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 11
            maximumLength: AngelPolicy.MAX_DIGITS
            inputMethodHints: Qt.ImhDigitsOnly
            validator: RegularExpressionValidator {
                regularExpression: /[0-9]{0,8}/
            }
            selectByMouse: true
            background: Rectangle {
                color: Colors.black
                border.width: 1
                border.color: angelSearchInput.activeFocus
                              ? Colors.magenta : Colors.cyan
            }
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Escape) {
                    angelSearchInput.focus = false;
                    event.accepted = true;
                }
            }
        }

        Row {
            id: angelPatternFilters
            width: parent.width
            height: 29
            spacing: 3

            Repeater {
                model: pane.filters
                ActionButton {
                    width: (angelPatternFilters.width
                            - angelPatternFilters.spacing
                              * (pane.filters.length - 1))
                           / pane.filters.length
                    height: 28
                    label: modelData.label
                    labelPixelSize: 9
                    contentPadding: 1
                    trackLabelGlowLocally: true
                    accentColor: Colors.white
                    selected: pane.activeFilter === modelData.key
                    selectedFillColor: Colors.yellow
                    selectedForegroundColor: Colors.magenta
                    selectedBorderColor: Colors.magenta
                    onLeftClicked: pane.activeFilter = modelData.key
                }
            }
        }

        GohuText {
            width: parent.width
            text: "REP SAME // MIR PALINDROME // SEQ RUN // ADD/SUB 3-DIGIT EQUATION"
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight
        }

        Item {
            id: angelHistoryArea
            width: parent.width
            height: Math.max(110, pane.height - 325)

            ListView {
                id: angelHistoryList
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.rightMargin: 21
                height: parent.height
                clip: true
                spacing: 4
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentHeight > height
                model: pane.filteredRows

                delegate: ActionButton {
                    width: angelHistoryList.width
                    height: 41
                    label: modelData.digits + " // "
                           + AngelPolicy.patternTags(modelData.digits).join("+")
                           + " // " + modelData.displayTime
                    labelPixelSize: 10
                    labelHorizontalAlignment: Text.AlignLeft
                    contentPadding: 5
                    trackLabelGlowLocally: true
                    accentColor: Colors.white
                    selected: pane.selectedId === modelData.id
                    selectedFillColor: Colors.yellow
                    selectedForegroundColor: Colors.magenta
                    selectedBorderColor: Colors.magenta
                    onLeftClicked: {
                        pane.selectedId = modelData.id;
                        pane.pendingDeleteId = "";
                    }
                }
            }

            NeonScrollBar {
                flickable: angelHistoryList
                accountForContentOrigin: true
                geometryMode: "viewport"
                x: angelHistoryArea.width - width - 1
                y: angelHistoryList.y
                height: angelHistoryList.height
                handleStyle: "star"
                railColor: Colors.cyan
                handleColor: Colors.magenta
                handleBorderColor: Colors.magenta
                railGlowColor: Colors.white
                containGlow: true
                visible: scrollable
            }

            GohuText {
                anchors.centerIn: angelHistoryList
                visible: pane.filteredRows.length === 0
                width: angelHistoryList.width - 10
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                color: Colors.cyan
                text: AngelObservationsStore.total === 0
                      ? "NO OBSERVATIONS // RECORD ONE"
                      : "NO MATCHES // CHANGE SEARCH OR FILTER"
            }
        }

        Row {
            width: parent.width
            height: 31
            spacing: 7

            GohuText {
                width: Math.max(0, parent.width - deleteButton.width
                                - cancelDelete.width - parent.spacing * 2)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 9
                color: Colors.white
                elide: Text.ElideMiddle
                text: pane.selectedObservation
                      ? pane.selectedObservation.zoneId + " // "
                        + new Date(pane.selectedObservation.observedAtMs)
                              .toISOString()
                      : "SELECT HISTORY ROW FOR DETAIL"
            }
            ActionButton {
                id: cancelDelete
                width: pane.pendingDeleteId !== "" ? 57 : 0
                height: 30
                visible: pane.pendingDeleteId !== ""
                label: "CANCEL"
                labelPixelSize: 9
                accentColor: Colors.red
                destructive: true
                onLeftClicked: pane.pendingDeleteId = ""
            }
            ActionButton {
                id: deleteButton
                width: 111
                height: 30
                label: pane.pendingDeleteId !== ""
                       ? "CONFIRM ×" : "DELETE ×"
                labelPixelSize: 9
                accentColor: Colors.red
                destructive: true
                available: pane.selectedObservation !== null
                           && AngelObservationsStore.writable
                onLeftClicked: {
                    if (pane.selectedObservation === null)
                        return;
                    if (pane.pendingDeleteId !== pane.selectedObservation.id) {
                        pane.pendingDeleteId = pane.selectedObservation.id;
                        return;
                    }
                    if (AngelObservationsStore.deleteObservation(
                                pane.pendingDeleteId, true)) {
                        pane.pendingDeleteId = "";
                        pane.selectedId = "";
                    }
                }
            }
        }

        GohuText {
            width: parent.width
            text: "STORE // " + AngelObservationsStore.storageState.toUpperCase()
                  + " // " + AngelObservationsStore.feedback
            font.pixelSize: 9
            elide: Text.ElideRight
            color: AngelObservationsStore.storageState === "error"
                   || AngelObservationsStore.storageState === "unsupported"
                   ? Colors.orange : Colors.white
        }
    }
}
