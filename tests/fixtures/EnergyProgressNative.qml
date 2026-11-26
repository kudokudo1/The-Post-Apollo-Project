import QtQuick
import QtQuick.Window
import Quickshell
import qs.components

ShellRoot {
    Window {
        id: lab
        width: 480
        height: 300
        visible: true
        color: Colors.dark
        property int stage: 0
        property double started: Date.now()
        property bool failed: false
        function require(ok, message) {
            if (!ok) {
                failed = true;
                console.error("ENERGY_NATIVE_FAIL " + message);
                Qt.quit();
            }
            return ok;
        }
        Column {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 20
            Repeater {
                id: faces
                model: ["omnitrix","tron","ki-blast","flamethrower"]
                EnergyProgressFace {
                    required property string modelData
                    width: parent.width
                    height: 36
                    variant: modelData
                    caption: modelData
                }
            }
        }
        Timer {
            interval: 120
            running: !lab.failed
            repeat: true
            onTriggered: {
                const elapsed = Date.now()-lab.started;
                if (!lab.require(faces.count===4,"variant count")) return;
                for (let i=0;i<faces.count;i++) {
                    const f=faces.itemAt(i);
                    if (!lab.require(f && f.headCenterY===f.height/2,"centerline "+i)) return;
                    if (!lab.require(Number.isFinite(f.displayedFraction),"finite fraction "+i)) return;
                    if (lab.stage===0) {
                        f.phase="running";
                    } else if (lab.stage===1) {
                        if (!lab.require(f.animationActive && f.displayedFraction<1,"running "+i)) return;
                        if (elapsed>4800) {
                            if (!lab.require(f.displayedFraction>.7,"midpoint breakthrough "+i)) return;
                            f.progressMode="measured";
                            f.progress=.63;
                        }
                    } else if (lab.stage===2) {
                        if (!lab.require(Math.abs(f.displayedFraction-.63)<.00001,"measured "+i)) return;
                        f.height=24;
                        f.visible=false;
                    } else if (lab.stage===3) {
                        if (!lab.require(!f.animationActive,"hidden animation "+i)) return;
                        f.visible=true;
                        f.reducedMotion=true;
                    } else if (lab.stage===4) {
                        if (!lab.require(!f.animationActive && f.displayedFraction===.63,"reduced measured "+i)) return;
                        f.phase=i%2 ? "failure":"success";
                    } else if (lab.stage===5) {
                        if (!lab.require(!f.animationActive && Math.abs(f.displayedFraction-(i%2?.63:1))<.00001,"result "+i)) return;
                        f.phase="idle";
                    } else if (lab.stage===6) {
                        if (!lab.require(!f.animationActive && f.displayedFraction===0,"idle "+i)) return;
                    }
                }
                if (lab.stage===1 && elapsed<=4800) return;
                if (lab.stage===6) {
                    console.log("ENERGY_NATIVE_PASS four variants; centerline; breakthrough; exact fraction; resize; hide; reduced motion; success; failure; reset");
                    Qt.quit();
                    return;
                }
                lab.stage++;
            }
        }
    }
}
