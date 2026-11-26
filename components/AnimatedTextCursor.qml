import QtQuick
import Qt5Compat.GraphicalEffects

// Original AppControl insertion cursor. Mount as sibling of a TextInput,
// outside the input's glow layer. Input must suppress the native cursor.
Item {
    id: cursor
    required property TextInput input
    // The decorative cursor should not reserve horizontal
    // space in the input. These properties only drive the
    // idle star blink.
    property bool typingRecently: false
    property bool cursorStarsVisible: true
    property int trailingStarPhase: 0

    Timer {
        id: typingPauseTimer

        interval: 500
        repeat: false

        onTriggered: {
            cursor.typingRecently = false;
            cursor.cursorStarsVisible = true;
        }
    }

    Timer {
        id: cursorStarsBlinkTimer

        interval: 420
        repeat: true
        running: cursor.input.activeFocus
                 && !cursor.typingRecently

        onTriggered: {
            cursor.cursorStarsVisible =
                !cursor.cursorStarsVisible;
        }
    }

    Timer {
        id: trailingStarWaveTimer

        interval: 360
        repeat: true
        running: cursor.input.activeFocus
                 && !cursor.typingRecently

        onTriggered: {
            cursor.trailingStarPhase =
                (cursor.trailingStarPhase + 1) % 5;
        }
    }


    Connections {
        target: cursor.input
        function onTextChanged() {
            cursor.typingRecently = true;
            cursor.cursorStarsVisible = true;
            cursor.trailingStarPhase = 0;
            typingPauseTimer.restart();
        }
    }
    visible: cursor.input.activeFocus

    // Match the real insertion point instead of trailing behind
    // it. The native bar itself is suppressed above.
    x: cursor.input.x + cursor.input.cursorRectangle.x - 1
    y: cursor.input.y + 3

    width: typingCursorVisual.implicitWidth
    height: cursor.input.height

    z: 50

    Row {
        id: typingCursorVisual

        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter

        spacing: -2

        GohuText {
            id: typingCursorStars

            text: "݁˖"

            font.pixelSize: 17
            color: Colors.orange

            opacity: cursor.typingRecently
                     || cursor.cursorStarsVisible
                     ? 1.0
                     : 0.02
        }

        Item {
            id: typingCursorHandGroup

            width: typingCursorHand.implicitWidth
            height: typingCursorHand.implicitHeight

            GohuText {
                id: typingCursorHand

                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                text: "✍︎"

                font.pixelSize: 17
                color: Colors.orange
            }

            // First decorative mark immediately behind the hand.
            // Including the hand in the shaping string prevents
            // the mark from becoming a detached/doubled glyph.
            GohuText {
                id: typingCursorNearStarOne

                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                text: "✍︎๋"

                font.pixelSize: 17
                color: Colors.orange

                opacity: cursor.typingRecently
                         ? 0.60
                         : cursor.trailingStarPhase === 0
                         ? 0.68
                         : cursor.trailingStarPhase === 1
                         ? 0.36
                         : cursor.trailingStarPhase === 4
                         ? 0.22
                         : 0.04
            }

            // Second decorative mark follows the first with an
            // overlapping phase instead of blinking one-by-one.
            GohuText {
                id: typingCursorNearStarTwo

                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                text: "✍︎࣭"

                font.pixelSize: 17
                color: Colors.orange

                opacity: cursor.typingRecently
                         ? 0.60
                         : cursor.trailingStarPhase === 0
                         ? 0.28
                         : cursor.trailingStarPhase === 1
                         ? 0.68
                         : cursor.trailingStarPhase === 2
                         ? 0.38
                         : 0.04
            }
        }

        GohuText {
            id: typingCursorTrailStar

            text: "⭑"

            font.pixelSize: 17
            color: Colors.orange

            opacity: cursor.typingRecently
                     ? 1.0
                     : cursor.trailingStarPhase === 0
                     ? 0.14
                     : cursor.trailingStarPhase === 1
                     ? 0.48
                     : cursor.trailingStarPhase === 2
                     ? 1.0
                     : cursor.trailingStarPhase === 3
                     ? 0.74
                     : 0.30
        }

        GohuText {
            id: typingCursorTrailPlus

            text: "₊ "

            font.pixelSize: 17
            color: Colors.orange

            opacity: cursor.typingRecently
                     ? 1.0
                     : cursor.trailingStarPhase === 0
                     ? 0.06
                     : cursor.trailingStarPhase === 1
                     ? 0.18
                     : cursor.trailingStarPhase === 2
                     ? 0.46
                     : cursor.trailingStarPhase === 3
                     ? 1.0
                     : 0.62
        }
    }

    DropShadow {
        anchors.fill: typingCursorVisual
        source: typingCursorVisual

        horizontalOffset: 0
        verticalOffset: 0

        radius: 5
        samples: 5

        opacity: 0.42
        color: Colors.orange

        transparentBorder: true
    }

}
