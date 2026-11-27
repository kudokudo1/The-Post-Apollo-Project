import QtQuick
import QtQuick.Window
import Quickshell
import qs.components

ShellRoot {
    Window {
        id: lab
        width: 620
        height: 510
        visible: true
        color: Colors.dark
        title: "Post-Apollo // Energy Progress Laboratory"
        property int responseMs: 6500
        property bool reduced: false
        property bool measured: false

        EnergyPressureField {
            id: field
            reducedMotion: lab.reduced
        }

        // The physical window stays fixed; the laboratory's whole interior
        // panel responds as one unit. This is not a production input surface.
        Item {
            anchors.fill: parent
            anchors.margins: 6
            transform: Translate { x: field.offsetX; y: field.offsetY }

            Rectangle {
                anchors.fill: parent
                color: Colors.dark
                border.width: 1
                border.color: Colors.magenta
            }
            Rectangle {
                anchors.fill: parent
                anchors.margins: -2
                color: "transparent"
                border.width: 2
                border.color: field.pressureColor
                opacity: field.pressure * .55
            }
            // Small, rising fragments are deliberately outside the button.
            // They are driven by the same existing visual clock, no extra timer.
            Repeater {
                model: 12
                Rectangle {
                    required property int index
                    readonly property real drift: (field.fragmentTime*(.55+index*.035)+index*.19)%1
                    width: 2 + index%3
                    height: 1 + index%2
                    x: index%2===0 ? 3+drift*12 : parent.width-3-drift*12
                    y: parent.height*(.14+.066*index)-drift*18*field.fragmentPressure
                    color: field.fragmentColor
                    opacity: Math.max(0,(field.fragmentPressure-.38)*1.25)*(1-drift)
                    rotation: index*37+drift*65
                    visible: field.fragmentPressure>.38
                    z: 2
                }
            }

            // TRON's lateral light streaks suggest acceleration, not debris.
            Repeater {
                model: 10
                Rectangle {
                    required property int index
                    readonly property real drift: (field.motionTime*(.9+index*.08)+index*.21)%1
                    width: 8+index%4*7
                    height: 1
                    x: (1-drift)*(parent.width-width)
                    y: index%2===0 ? 3+index%3*2 : parent.height-5-index%3*2
                    color: Colors.cyan
                    opacity: field.pressure*(1-drift)*.65
                    visible: field.reactionStyle==="speed" && field.pressure>.1
                    z: 2
                }
            }

        Column {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10
            GohuText { text: "ENERGY PROGRESS // SIMULATION ONLY"; color: Colors.magenta; font.pixelSize: 16 }
            GohuText { text: "No services, files, GitHub requests or production actions."; color: Colors.white }
            Row {
                spacing: 6
                Repeater {
                    model: [{name:"FAST",ms:2500},{name:"NORMAL",ms:6500},{name:"SLOW",ms:14000},{name:"HOLD",ms:0}]
                    ActionButton {
                        required property var modelData
                        width: 86; height: 28
                        label: modelData.name
                        selected: lab.responseMs === modelData.ms
                        onLeftClicked: lab.responseMs = modelData.ms
                    }
                }
                ActionButton {
                    width: 104; height: 28
                    label: "REDUCED"
                    selected: lab.reduced
                    onLeftClicked: lab.reduced = !lab.reduced
                }
                ActionButton {
                    width: 100; height: 28
                    label: "MEASURED"
                    selected: lab.measured
                    onLeftClicked: lab.measured = !lab.measured
                }
            }
            Repeater {
                onItemAdded: function(index, item) {
                    field.sources = field.sources.concat([item.pressureSource]);
                }
                onItemRemoved: function(index, item) {
                    field.sources = field.sources.filter(source => source !== item.pressureSource);
                }
                model: [{name:"OMNITRIX",key:"omnitrix"},{name:"TRON",key:"tron"},
                    {name:"KI BLAST",key:"ki-blast"},{name:"FLAMETHROWER",key:"flamethrower"}]
                Item {
                    id: card
                    required property var modelData
                    width: parent.width
                    height: 84
                    property alias pressureSource: energyFace
                    property string phase: "idle"
                    property int duration: 6500
                    property double started: 0
                    property real fraction: 0
                    property bool exact: false
                    function start() {
                        if (phase === "running") return;
                        duration=lab.responseMs;
                        exact=lab.measured;
                        fraction=0;
                        started=Date.now();
                        phase="running";
                    }
                    function resolve(result) {
                        if (phase !== "running") return;
                        phase=result;
                    }
                    Timer {
                        interval: 33; repeat: true
                        running: card.phase === "running"
                        onTriggered: {
                            if (card.duration > 0) {
                                card.fraction=Math.min(1,(Date.now()-card.started)/card.duration);
                                if (card.fraction>=1) card.resolve("success");
                            }
                        }
                    }
                    GohuText {
                        text: card.modelData.name
                        color: Colors.magenta
                        font.pixelSize: 11
                    }
                    ActionButton {
                        id: host
                        anchors.top: parent.top
                        anchors.topMargin: 19
                        width: Math.max(0,parent.width-180)
                        height: 42
                        showLabel: false
                        contentGlowEnabled: false
                        softGlowEnabled: false
                        wideGlowEnabled: false
                        // The lab panel itself moves by a bounded offset.
                        available: true
                        interactive: card.phase !== "running"
                        onLeftClicked: card.start()
                        EnergyProgressFace {
                            id: energyFace
                            anchors.fill: parent
                            variant: card.modelData.key
                            phase: card.phase
                            reducedMotion: lab.reduced
                            progressMode: card.exact ? "measured" : "indeterminate"
                            progress: card.fraction
                            caption: card.phase === "idle" ? "START SIMULATION"
                                : card.phase === "running" ? "PROCESSING"
                                : card.phase === "success" ? "COMPLETE" : "FAILED // RETRY"
                        }
                    }
                    Row {
                        anchors.left: host.right
                        anchors.leftMargin: 9
                        anchors.verticalCenter: host.verticalCenter
                        spacing: 5
                        ActionButton {
                            width: 80; height: 28
                            label: "SUCCESS"; accentColor: Colors.green
                            available: card.phase === "running"
                            onLeftClicked: card.resolve("success")
                        }
                        ActionButton {
                            width: 80; height: 28
                            label: "FAIL"; accentColor: Colors.red
                            available: card.phase === "running"
                            onLeftClicked: card.resolve("failure")
                        }
                    }
                }
            }
        }
        }
        // Single soft pulse confined to the laboratory widget, not the
        // desktop or other monitors. No input handler; reduced motion opts out.
        Rectangle {
            anchors.fill: parent
            z: 20
            color: "#D8FFEA"
            opacity: field.completionFlash
            visible: opacity > 0
        }
    }
}
