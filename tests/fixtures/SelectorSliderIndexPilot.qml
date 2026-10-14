import QtQuick
import qs.components

// F1 INDEX lab for GitW. MOCK VALUES ONLY:
// No Git/GitHub/Hospital service is imported or called.
Item {
    id: root

    width: 490
    height: 330

    property int repoSelection: 1
    property int remoteSelection: 2

    Rectangle {
        anchors.fill: parent
        color: Colors.black
        border.width: 2
        border.color: Colors.cyan
        radius: 3
    }

    // Block accidental clicks/wheel actions on the Git controls underneath.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onPressed: function(mouse) { mouse.accepted = true; }
        onWheel: function(wheel) { wheel.accepted = true; }
    }

    GohuText {
        anchors {
            top: parent.top
            left: parent.left
            topMargin: 10
            leftMargin: 15
        }
        text: "F1 // SELECTOR INDEX LAB"
        color: Colors.cyan
        font.pixelSize: 12
    }

    GohuText {
        anchors {
            top: parent.top
            right: parent.right
            topMargin: 11
            rightMargin: 14
        }
        text: "MOCK DATA // NO GIT COMMANDS"
        color: Colors.orange
        font.pixelSize: 8
    }

    Item {
        x: 55
        y: 43
        width: 174
        height: 244

        SelectorSlider {
            id: previewRepo
            x: 8
            y: 0
            height: 210
            count: 6
            currentIndex: root.repoSelection
            indexInteraction: "preview-release"
            optionLabels: ["ALPHA", "BETA", "GAMMA", "DELTA", "EPS", "ZETA"]
            accentColor: Colors.magenta
            handleGlowColor: Colors.orange
            sideLabel: "REPO"
            onIndexRequested: function(index) {
                root.repoSelection = index;
            }
        }

        GohuText {
            x: 0
            y: 220
            text: "COMMIT // " + previewRepo.indexLabel(root.repoSelection)
            color: Colors.magenta
            font.pixelSize: 9
        }
    }

    Item {
        x: 283
        y: 43
        width: 180
        height: 244

        SelectorSlider {
            id: previewRemote
            x: 8
            y: 0
            height: 210
            count: 7
            currentIndex: root.remoteSelection
            indexInteraction: "preview-release"
            optionLabels: ["MAIN", "DEV", "FIX", "OPS", "ARCH", "TEST", "DOCS"]
            accentColor: Colors.orange
            handleGlowColor: Colors.cyan
            activityGlowColor: Colors.orange
            sideLabel: "REMOTE"
            // No simulated remote-activity lights: those must reflect real data.
            onIndexRequested: function(index) {
                root.remoteSelection = index;
            }
        }

        GohuText {
            x: 0
            y: 220
            text: "COMMIT // " + previewRemote.indexLabel(root.remoteSelection)
            color: Colors.orange
            font.pixelSize: 9
        }
    }

    GohuText {
        anchors {
            horizontalCenter: parent.horizontalCenter
            bottom: parent.bottom
            bottomMargin: 12
        }
        text: "DRAG // RELEASE TO COMMIT   ~   ESC // CANCEL   ~   WHEEL / ARROWS"
        color: Colors.white
        font.pixelSize: 9
    }
}
