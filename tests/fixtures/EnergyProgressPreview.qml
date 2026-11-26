import QtQuick
import QtQuick.Window
import Quickshell
import "../../components"

ShellRoot {
    Window {
        id: lab
        width: 620
        height: 490
        visible: true
        color: Colors.dark
        title: "Post-Apollo // Energy Progress Laboratory"
        property int responseMs: 6500
        property bool reduced: false
        property bool measured: false

        Column {
            anchors.fill: parent
            anchors.margins: 18
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
                model: [{name:"OMNITRIX",key:"omnitrix"},{name:"TRON",key:"tron"},
                    {name:"KI BLAST",key:"ki-blast"},{name:"FLAMETHROWER",key:"flamethrower"}]
                Item {
                    id: card
                    required property var modelData
                    width: parent.width
                    height: 84
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
                        // Stable click geometry; only the inner face vibrates.
                        available: true
                        interactive: card.phase !== "running"
                        onLeftClicked: card.start()
                        EnergyProgressFace {
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
}
