import QtQuick
import QtQuick.Controls
import Quickshell
import qs.services.time
import qs.services.favorites
import "../components"
import "../services/time/AngelObservationPolicy.js" as AngelPolicy

// ANGEL M1: explicit local observations, structural filters and a scrollable
// history. Reference interpretations and MAGICK astronomy are separate lanes.
Item {
    id: pane
    property double currentEpochMs: 0
    property string selectedId: ""
    property string pendingDeleteId: ""
    property string editingNoteId: ""
    property string noteInFlightId: ""
    property bool reviewingDraft: false
    property string noteSaveFeedback: ""
    property string activeFilter: "all"
    property string activeView: "journal"
    property string meaningSelection: ""
    readonly property bool editingText:
        manualDigitsInput.activeFocus || angelSearchInput.activeFocus
        || noteField.activeFocus || angelMeaningPane.editingText
    readonly property var clockCandidate:
        AngelPolicy.clockCapture(
            TimeSettings.adjustedEpochMs(currentEpochMs))
    readonly property var filteredRows:
        AngelPolicy.filter(AngelObservationsStore.observations,
                           angelSearchInput.text, activeFilter,
                           FavoritesDefaultStore.favoriteKeys)
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
        {key: "multiply", label: "MUL"},
        {key: "divide", label: "DIV"},
        {key: "favorite", label: "FAV"},
        {key: "other", label: "OTHER"},
        {key: "err", label: "ERR"}
    ]

    // Color grammar is shared by the filter buttons and history rows.
    // An observation can match several patterns; the first structural tag
    // takes visual precedence unless its number is favorited or ERR-marked.
    function filterInk(key) {
        switch (key) {
        case "favorite": return Colors.magenta;
        case "mirror": return Colors.yellow;
        case "add": return Colors.cyan;
        case "subtract": return Colors.blue;
        case "multiply": return Colors.omnitrix;
        case "divide": return Colors.green; // regular green, NOT Omnitrix
        case "sequence": return Colors.orange;
        case "err": return Colors.red;
        default: return Colors.white; // ALL, REPEAT, OTHER
        }
    }

    function filterEdge(key) {
        return filterInk(key);
    }

    function primaryPattern(digits) {
        const tags = AngelPolicy.patternTags(digits);
        return tags.length ? tags[0].toLowerCase() : "other";
    }

    function visiblePattern(digits) {
        // In a specific pattern filter, show that filter's color even when
        // the number overlaps several classifications (e.g. ADD and MUL).
        // ALL, FAV and ERR fall back to the normal primary pattern.
        const patterns = ["repeat", "mirror", "sequence", "add", "subtract",
                          "multiply", "divide", "other"];
        return patterns.indexOf(activeFilter) >= 0
            ? activeFilter : primaryPattern(digits);
    }

    function showMeaning() {
        const chosen = pane.selectedObservation !== null
            ? pane.selectedObservation.digits
            : AngelPolicy.validDigits(manualDigitsInput.text)
              ? manualDigitsInput.text
              : pane.clockCandidate !== null ? pane.clockCandidate.digits : "";
        // Explicit view navigation is not a network request and does not
        // write anything to the journal. It only chooses the number in focus.
        pane.meaningSelection = chosen;
        pane.activeView = "meaning";
    }

    function recordObservation(inputDigits, mode, observedAtMs) {
        const displayEpochMs = TimeSettings.adjustedEpochMs(observedAtMs);
        const capture = AngelPolicy.clockCapture(displayEpochMs);
        if (capture === null)
            return false;
        // Preserve the physical zone offset at the true observation instant.
        // A manual display calibration can cross a DST boundary independently.
        const localDate = new Date(observedAtMs);
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

    function editObservationNote(row) {
        if (!row || pane.noteInFlightId !== "")
            return;
        pane.selectedId = row.id;
        pane.pendingDeleteId = "";
        pane.reviewingDraft = false;
        pane.noteSaveFeedback = "";
        pane.editingNoteId = row.id;
        noteField.text = String(row.note || "");
        noteField.forceActiveFocus();
    }

    function reviewNoteDraft() {
        const draft = AngelObservationsStore.noteDraft;
        if (!draft || pane.noteInFlightId !== "")
            return;
        pane.selectedId = draft.id;
        pane.pendingDeleteId = "";
        pane.reviewingDraft = true;
        pane.editingNoteId = draft.id;
        noteField.text = draft.after;
        pane.noteSaveFeedback = "RECOVERY REVIEW // READ ONLY";
        noteField.forceActiveFocus();
    }

    function closeNoteEditor() {
        if (pane.noteInFlightId !== "")
            return; // Never discard the visible note during a write.
        pane.editingNoteId = "";
        pane.reviewingDraft = false;
        noteField.focus = false;
    }

    function saveNote() {
        if (pane.editingNoteId === "" || pane.reviewingDraft
                || pane.noteInFlightId !== ""
                || !AngelObservationsStore.writable)
            return;
        const id = pane.editingNoteId;
        if (AngelObservationsStore.saveObservationNote(id, noteField.text)) {
            // Accepted for staging is NOT saved. Close only on the actual
            // journal FileView.onSaved receipt below.
            pane.noteInFlightId = id;
            pane.noteSaveFeedback = "WRITING // NOTE KEPT OPEN";
        } else {
            pane.noteSaveFeedback = AngelObservationsStore.feedback;
        }
    }

    function retryDraft() {
        if (AngelObservationsStore.retryNoteDraft()) {
            pane.noteInFlightId = AngelObservationsStore.noteDraft.id;
            pane.noteSaveFeedback = "RECOVERY WRITE // WAITING FOR RECEIPT";
        }
    }

    Connections {
        target: AngelObservationsStore
        function onNoteSaved(id) {
            if (pane.noteInFlightId !== id)
                return;
            pane.noteInFlightId = "";
            pane.noteSaveFeedback = "SAVED TO LOCAL JOURNAL";
            pane.closeNoteEditor();
        }
        function onNoteSaveFailed(id, reason) {
            if (pane.noteInFlightId !== id)
                return;
            pane.noteInFlightId = "";
            // Do not erase/reconstruct noteField.text on a timeout or failure.
            pane.noteSaveFeedback = "SAVE NOT CONFIRMED // " + reason
                                    + " // COPY TEXT BEFORE EXIT";
        }
    }

    function recordClock() {
        const observedAtMs = Date.now();
        const value = AngelPolicy.clockCapture(
            TimeSettings.adjustedEpochMs(observedAtMs));
        if (value !== null)
            recordObservation(value.digits, "clock", observedAtMs);
    }

    function recordManual() {
        const digits = manualDigitsInput.text.trim();
        if (!AngelPolicy.validDigits(digits))
            return;
        if (recordObservation(digits, "manual", Date.now()))
            manualDigitsInput.text = "";
    }

    Row {
        id: angelViewStrip
        width: parent.width
        height: 32
        spacing: 7

        AngelActionButton {
            width: (parent.width - parent.spacing) / 2
            height: parent.height
            label: "JOURNAL"
            labelPixelSize: 11
            trackLabelGlowLocally: true
            accentColor: Colors.white
            selected: pane.activeView === "journal"
            highlightWhenSelected: true
            selectedForegroundColor: Colors.magenta
            selectedBorderColor: Colors.magenta
            onLeftClicked: pane.activeView = "journal"
        }

        AngelActionButton {
            width: (parent.width - parent.spacing) / 2
            height: parent.height
            label: "MEANING"
            labelPixelSize: 11
            trackLabelGlowLocally: true
            accentColor: Colors.white
            selected: pane.activeView === "meaning"
            highlightWhenSelected: true
            selectedForegroundColor: Colors.magenta
            selectedBorderColor: Colors.magenta
            onLeftClicked: pane.showMeaning()
        }
    }

    AngelMeaningPane {
        id: angelMeaningPane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: angelViewStrip.bottom
        anchors.bottom: parent.bottom
        anchors.topMargin: 8
        visible: pane.activeView === "meaning"
        initialDigits: pane.meaningSelection
    }

    Column {
        id: angelJournalView
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: angelViewStrip.bottom
        anchors.bottom: parent.bottom
        anchors.topMargin: 8
        visible: pane.activeView === "journal"
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

            AngelActionButton {
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

            AngelActionButton {
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

        Row {
            width: parent.width
            height: 18
            spacing: 4
            GohuText {
                text: "HISTORY //"
                font.pixelSize: 12
                color: Colors.white
            }
            GohuText {
                text: String(pane.filteredRows.length)
                font.pixelSize: 12
                color: Colors.magenta
            }
            GohuText {
                text: "SHOWN //"
                font.pixelSize: 12
                color: Colors.white
            }
            GohuText {
                text: String(AngelObservationsStore.total)
                font.pixelSize: 12
                color: Colors.orange
            }
            GohuText {
                text: "SAVED"
                font.pixelSize: 12
                color: Colors.white
            }
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
                AngelActionButton {
                    width: (angelPatternFilters.width
                            - angelPatternFilters.spacing
                              * (pane.filters.length - 1))
                           / pane.filters.length
                    height: 28
                    readonly property color ink: pane.filterInk(modelData.key)
                    readonly property color edge: pane.filterEdge(modelData.key)
                    label: modelData.label
                    labelPixelSize: 9
                    contentPadding: 1
                    trackLabelGlowLocally: true
                    // Filters stay black when idle; their active state
                    // still uses the intentional yellow/magenta selection.
                    washByDefault: false
                    accentColor: ink
                    idleBorderColor: edge
                    idleContentGlowColor: edge
                    idleSoftGlowColor: edge
                    selected: pane.activeFilter === modelData.key
                    highlightWhenSelected: true
                    selectedForegroundColor: Colors.magenta
                    selectedBorderColor: Colors.magenta
                    selectedContentGlowColor: Colors.magenta
                    selectedSoftGlowColor: Colors.magenta
                    onLeftClicked: pane.activeFilter = modelData.key
                }
            }
        }

        GohuText {
            width: parent.width
            text: "OTHER = NO PATTERN // ERR = OTHER + USER-MARKED"
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight
        }

        Item {
            id: angelHistoryArea
            width: parent.width
            height: Math.max(96, angelJournalView.height - 325
                                 - (noteEditor.visible ? 40 : 0))

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

                delegate: Item {
                    id: observationEntry
                    readonly property bool isMarkedErr: modelData.errMarked === true
                    readonly property string numberKey:
                        AngelPolicy.favoriteKey(modelData.digits)
                    readonly property bool isFavoriteNumber:
                        FavoritesDefaultStore.isFavorite(numberKey)
                    readonly property string pattern:
                        pane.visiblePattern(modelData.digits)
                    readonly property color entryInk:
                        isMarkedErr ? Colors.red
                        : isFavoriteNumber ? Colors.magenta
                        : pane.filterInk(pattern)
                    readonly property color entryEdge:
                        isMarkedErr ? Colors.red
                        : isFavoriteNumber ? Colors.magenta
                        : pane.filterEdge(pattern)
                    width: angelHistoryList.width
                    height: 47

                    AngelActionButton {
                        id: observationSelect
                        x: favoriteObservation.width + 4
                        width: Math.max(0, parent.width - 68)
                        height: parent.height
                        label: (observationEntry.isMarkedErr ? "ERR* // " : "")
                               + modelData.digits + " // "
                               + AngelPolicy.patternTags(modelData.digits).join("+")
                               + "\nDATE // " + AngelPolicy.observedDate(modelData)
                               + " // " + modelData.displayTime
                        labelPixelSize: 10
                        labelHorizontalAlignment: Text.AlignLeft
                        contentPadding: 5
                        trackLabelGlowLocally: true
                        // Every row has its category/favorite color wash;
                        // only the opened entry switches to yellow/magenta.
                        accentColor: observationEntry.entryInk
                        idleBorderColor: observationEntry.entryEdge
                        idleContentGlowColor: observationEntry.entryEdge
                        idleSoftGlowColor: observationEntry.entryEdge
                        selected: pane.selectedId === modelData.id
                        highlightWhenSelected: true
                        selectedForegroundColor: Colors.magenta
                        selectedBorderColor: Colors.magenta
                        selectedContentGlowColor: Colors.magenta
                        selectedSoftGlowColor: Colors.magenta
                        onLeftClicked: {
                            pane.selectedId = modelData.id;
                            pane.pendingDeleteId = "";
                        }
                    }
                    AngelActionButton {
                        id: favoriteObservation
                        x: 0
                        width: 30
                        height: parent.height
                        washByDefault: false
                        label: "★"
                        labelPixelSize: 13
                        contentPadding: 2
                        accentColor: observationEntry.isFavoriteNumber
                                     ? Colors.magenta : Colors.white
                        selected: observationEntry.isFavoriteNumber
                        selectedForegroundColor: Colors.magenta
                        selectedBorderColor: Colors.magenta
                        available: FavoritesDefaultStore.canEdit
                        onLeftClicked: FavoritesDefaultStore.toggleFavorite(
                                           observationEntry.numberKey)
                    }
                    AngelActionButton {
                        id: noteObservation
                        x: observationSelect.x + observationSelect.width + 4
                        width: 30
                        height: parent.height
                        washByDefault: false
                        label: "+"
                        labelPixelSize: 14
                        contentPadding: 2
                        accentColor: modelData.note ? Colors.orange : Colors.cyan
                        selected: pane.editingNoteId === modelData.id
                        highlightWhenSelected: true
                        selectedForegroundColor: Colors.magenta
                        available: AngelObservationsStore.writable
                                   && pane.noteInFlightId === ""
                        onLeftClicked: pane.editObservationNote(modelData)
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
            id: noteEditor
            width: parent.width
            height: visible ? 33 : 0
            visible: pane.editingNoteId !== ""
            spacing: 5

            TextField {
                id: noteField
                width: Math.max(0, parent.width - saveNoteButton.width
                                - cancelNoteButton.width - parent.spacing * 2)
                height: parent.height
                placeholderText: "NOTE FOR SELECTED SIGHTING"
                placeholderTextColor: Colors.cyan
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 11
                maximumLength: AngelPolicy.MAX_NOTE_LENGTH
                readOnly: pane.reviewingDraft || pane.noteInFlightId !== ""
                selectByMouse: true
                background: Rectangle {
                    color: Colors.black
                    border.width: 1
                    border.color: noteField.activeFocus ? Colors.magenta : Colors.cyan
                }
                onAccepted: pane.saveNote()
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Escape) {
                        pane.closeNoteEditor();
                        event.accepted = true;
                    }
                }
            }
            AngelActionButton {
                id: saveNoteButton
                width: 54
                height: parent.height
                label: "SAVE"
                labelPixelSize: 9
                accentColor: Colors.orange
                available: AngelObservationsStore.writable
                           && pane.noteInFlightId === ""
                           && !pane.reviewingDraft
                onLeftClicked: pane.saveNote()
            }
            AngelActionButton {
                id: cancelNoteButton
                width: 60
                height: parent.height
                label: "CANCEL"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: pane.noteInFlightId === ""
                onLeftClicked: pane.closeNoteEditor()
            }
        }

        Row {
            width: parent.width
            height: 31
            spacing: 7

            GohuText {
                width: Math.max(0, parent.width - errMarkButton.width
                                - deleteButton.width - cancelDelete.width
                                - parent.spacing * 3)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 9
                color: Colors.white
                elide: Text.ElideMiddle
                text: pane.selectedObservation
                      ? "DATE // "
                        + AngelPolicy.observedDate(pane.selectedObservation)
                        + " // " + pane.selectedObservation.zoneId
                        + " // UTC "
                        + new Date(pane.selectedObservation.observedAtMs)
                              .toISOString()
                      : "SELECT HISTORY ROW FOR DETAIL"
            }
            AngelActionButton {
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
            AngelActionButton {
                id: errMarkButton
                width: 82
                height: 30
                label: pane.selectedObservation !== null
                       && pane.selectedObservation.errMarked === true
                       ? "CLEAR ERR" : "MARK ERR"
                labelPixelSize: 9
                accentColor: Colors.red
                trackLabelGlowLocally: true
                destructive: true
                selected: pane.selectedObservation !== null
                          && pane.selectedObservation.errMarked === true
                selectedForegroundColor: Colors.white
                selectedBorderColor: Colors.red
                available: pane.selectedObservation !== null
                           && AngelObservationsStore.writable
                onLeftClicked: {
                    if (pane.selectedObservation === null)
                        return;
                    pane.pendingDeleteId = "";
                    AngelObservationsStore.toggleErrObservation(pane.selectedId);
                }
            }
            AngelActionButton {
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

        Column {
            id: noteRecoveryControls
            width: parent.width
            height: visible ? 65 : 0
            spacing: 4
            visible: AngelObservationsStore.draftState === "ready"
                     || (AngelObservationsStore.storageState === "stalled"
                         && AngelObservationsStore.pendingKind === "note")

            GohuText {
                width: parent.width
                font.pixelSize: 9
                color: Colors.orange
                text: "NOTE RECOVERY // "
                      + AngelObservationsStore.noteDraftDisposition.toUpperCase()
                      + (AngelObservationsStore.noteDraft
                         ? " // " + AngelObservationsStore.noteDraft.id : "")
            }
            Row {
                width: parent.width
                height: 30
                spacing: 4
                AngelActionButton {
                    width: Math.max(20, (parent.width - parent.spacing * 2) / 3)
                    height: parent.height
                    label: "CHECK DISK"
                    labelPixelSize: 8
                    accentColor: Colors.cyan
                    available: AngelObservationsStore.writePhase === ""
                               && AngelObservationsStore.draftState === "ready"
                    onLeftClicked: AngelObservationsStore.checkRecoveryFromDisk()
                }
                AngelActionButton {
                    width: Math.max(20, (parent.width - parent.spacing * 2) / 3)
                    height: parent.height
                    label: AngelObservationsStore.noteDraftDisposition === "already-saved"
                           ? "CLEAR" : "RETRY"
                    labelPixelSize: 8
                    accentColor: Colors.orange
                    available: AngelObservationsStore.writePhase === ""
                               && AngelObservationsStore.recoveryDiskChecked
                               && AngelObservationsStore.draftState === "ready"
                               && (AngelObservationsStore.noteDraftDisposition === "recoverable"
                                   || AngelObservationsStore.noteDraftDisposition === "already-saved")
                    onLeftClicked: {
                        if (AngelObservationsStore.noteDraftDisposition === "already-saved")
                            AngelObservationsStore.clearVerifiedDraft();
                        else
                            pane.retryDraft();
                    }
                }
                AngelActionButton {
                    width: Math.max(20, (parent.width - parent.spacing * 2) / 3)
                    height: parent.height
                    label: "REVIEW"
                    labelPixelSize: 8
                    accentColor: Colors.magenta
                    available: AngelObservationsStore.draftState === "ready"
                    onLeftClicked: pane.reviewNoteDraft()
                }
            }
        }

        GohuText {
            width: parent.width
            text: pane.noteSaveFeedback
            visible: pane.noteSaveFeedback !== ""
            font.pixelSize: 9
            color: Colors.orange
            elide: Text.ElideRight
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
