import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import "../components"
import "../services/time/AngelInterpretationPolicy.js" as Interpret
import "../services/time/AngelObservationPolicy.js" as Journal

// ANGEL M2: read-only structural lens and one explicitly requested publisher
// excerpt. No notes, observation writes, passive HTTP, or astronomy inference.
Item {
    id: meaning

    property string initialDigits: ""
    property string requestDigits: ""
    property string requestState: "idle"
    property string requestMessage: "SOURCE NOT REQUESTED"
    property var sourceResult: null
    readonly property bool editingText:
        numberInput.activeFocus || sourceUrlField.activeFocus
    readonly property string digits: numberInput.text
    readonly property var arithmetic: Interpret.arithmeticReduction(digits)
    readonly property var patternTags: Journal.patternTags(digits)
    readonly property string sourceUrl:
        sourceResult !== null ? sourceResult.url : ""
    readonly property bool sourceReady:
        requestState === "ready" && sourceResult !== null
    readonly property bool sourceEligible: Interpret.lookupEligible(digits)

    onInitialDigitsChanged: {
        numberInput.text = initialDigits;
        resetSource();
    }

    function resetSource() {
        requestState = "idle";
        requestMessage = "SOURCE NOT REQUESTED";
        sourceResult = null;
    }

    function requestSource() {
        const requested = digits;
        if (!Interpret.lookupEligible(requested) || sourceProcess.running)
            return false;
        requestDigits = requested;
        sourceResult = null;
        requestState = "loading";
        requestMessage = "CONTACTING SOURCE // ONE REQUEST";
        sourceProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/time/AngelSourceLookup.py"),
            requested
        ]);
        return true;
    }

    function acceptSource(raw) {
        if (requestDigits !== digits) {
            resetSource();
            return;
        }
        const parsed = Interpret.interpretResponse(raw, requestDigits);
        if (!parsed.ok) {
            sourceResult = null;
            requestState = "unavailable";
            requestMessage = parsed.reason;
            return;
        }
        sourceResult = parsed;
        requestState = "ready";
        requestMessage = "PUBLISHER EXCERPT VERIFIED // READ ONLY";
    }

    Process {
        id: sourceProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: meaning.acceptSource(this.text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && meaning.requestState === "loading") {
                meaning.requestState = "unavailable";
                meaning.requestMessage = "LOOKUP PROCESS UNAVAILABLE";
            }
        }
    }

    Column {
        anchors.fill: parent
        spacing: 11

        GohuText {
            width: parent.width
            text: "ANGEL // INTERPRETATION LENSES"
            color: Colors.magenta
            font.pixelSize: 13
        }

        GohuText {
            width: parent.width
            text: "An observation is a recorded event. Published meanings are beliefs or traditions, not measured clock or astronomy results."
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }

        Row {
            width: parent.width
            height: 34
            spacing: 7

            TextField {
                id: numberInput
                width: Math.max(0, parent.width - sourceButton.width
                                - parent.spacing)
                height: parent.height
                text: meaning.initialDigits
                placeholderText: "NUMBER // EXACT DIGITS"
                placeholderTextColor: Colors.cyan
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 12
                maximumLength: Interpret.MAX_DIGITS
                validator: RegularExpressionValidator {
                    regularExpression: /[0-9]{0,8}/
                }
                inputMethodHints: Qt.ImhDigitsOnly
                selectByMouse: true
                background: Rectangle {
                    color: Colors.black
                    border.width: 1
                    border.color: numberInput.activeFocus
                                  ? Colors.magenta : Colors.cyan
                }
                onTextEdited: meaning.resetSource()
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Escape) {
                        numberInput.focus = false;
                        event.accepted = true;
                    }
                }
                onAccepted: meaning.requestSource()
            }

            ActionButton {
                id: sourceButton
                width: 116
                height: parent.height
                label: sourceProcess.running ? "FETCHING..." : "FETCH SOURCE"
                labelPixelSize: 10
                accentColor: Colors.yellow
                trackLabelGlowLocally: true
                available: meaning.sourceEligible && !sourceProcess.running
                onLeftClicked: meaning.requestSource()
            }
        }

        GohuText {
            width: parent.width
            text: "LOCAL // STRUCTURAL ANALYSIS"
            font.pixelSize: 11
            color: Colors.cyan
        }

        GohuText {
            width: parent.width
            color: Colors.white
            font.pixelSize: 11
            text: Journal.validDigits(meaning.digits)
                  ? "PATTERNS // " + meaning.patternTags.join(" + ")
                  : "PATTERNS // ENTER 1–8 DIGITS"
            wrapMode: Text.WordWrap
        }

        GohuText {
            width: parent.width
            color: Colors.white
            font.pixelSize: 11
            text: meaning.arithmetic !== null
                  ? "DIGIT SUM // " + meaning.arithmetic.sum
                    + " // REDUCED TO " + meaning.arithmetic.digit
                  : "DIGIT SUM // UNAVAILABLE"
            wrapMode: Text.WordWrap
        }

        GohuText {
            width: parent.width
            color: Colors.cyan
            font.pixelSize: 9
            text: "Reduction is arithmetic only. No universal angel-number interpretation is inferred."
            wrapMode: Text.WordWrap
        }

        Rectangle {
            width: parent.width
            height: 2
            color: Colors.cyan
            opacity: 0.6
        }

        GohuText {
            width: parent.width
            text: "PUBLISHER // ASTROLOGY.COM"
            font.pixelSize: 12
            color: Colors.magenta
        }

        GohuText {
            width: parent.width
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.WordWrap
            text: meaning.sourceEligible
                  ? "FETCH contacts this publisher once and exposes your IP to it. No automatic searches and no stored meanings."
                  : "Publisher lookup supports 1–4 exact digits; longer patterns are local analysis only."
        }

        Item {
            id: resultBox
            width: parent.width
            height: Math.max(95, meaning.height - 313)

            Flickable {
                id: resultScroll
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.rightMargin: 18
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: width
                contentHeight: Math.max(height, resultContent.y
                                        + resultContent.implicitHeight + 8)

                Column {
                    id: resultContent
                    x: 4
                    y: 5
                    width: Math.max(0, resultScroll.width - 8)
                    spacing: 12

                    GohuText {
                        width: parent.width
                        color: meaning.sourceReady ? Colors.cyan : Colors.yellow
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                        text: "STATUS // " + meaning.requestMessage
                    }
                    GohuText {
                        visible: meaning.sourceReady
                        width: parent.width
                        color: Colors.magenta
                        font.pixelSize: 11
                        text: meaning.sourceReady
                              ? "NUMEROLOGY MEANING // " + meaning.digits : ""
                    }
                    GohuText {
                        visible: meaning.sourceReady
                        width: parent.width
                        color: Colors.white
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        text: meaning.sourceReady ? meaning.sourceResult.excerpt : ""
                    }
                    GohuText {
                        visible: meaning.sourceReady
                        width: parent.width
                        color: Colors.cyan
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        text: "SHORT PUBLISHER EXCERPT // NOT AN ENDORSEMENT OR VERIFIED PREDICTION"
                    }
                    TextField {
                        id: sourceUrlField
                        visible: meaning.sourceReady
                        width: parent.width
                        height: 32
                        color: Colors.white
                        font.family: "GohuFont 11 Nerd Font Mono"
                        font.pixelSize: 9
                        readOnly: true
                        selectByMouse: true
                        text: meaning.sourceUrl
                        background: Rectangle {
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                        }
                    }
                    GohuText {
                        visible: meaning.sourceReady
                        width: parent.width
                        color: Colors.cyan
                        font.pixelSize: 9
                        text: "SOURCE URL SELECTABLE TO COPY // NO BROWSER REDIRECT"
                    }
                    GohuText {
                        visible: !meaning.sourceReady
                        width: parent.width
                        font.pixelSize: 10
                        color: Colors.white
                        wrapMode: Text.WordWrap
                        text: meaning.requestState === "unavailable"
                              ? "No verified excerpt. Nothing invented, and the observation remains unchanged."
                              : "Select or enter a number, then explicitly FETCH SOURCE for a short cited publisher excerpt."
                    }
                }
            }

            NeonScrollBar {
                flickable: resultScroll
                geometryMode: "viewport"
                x: resultBox.width - width - 1
                height: resultScroll.height
                handleStyle: "star"
                containGlow: true
                visible: scrollable
            }
        }
    }
}
