import QtQuick
import QtQuick.Window
import Quickshell
import qs.components

ShellRoot {
    Window {
        id: lab
        width: 480
        height: 410
        visible: true
        color: Colors.dark
        property int stage: 0
        property double started: Date.now()
        property bool failed: false
        property bool sawFlash: false
        property double pulseStarted: 0
        function require(ok, message) {
            if (!ok) {
                failed = true;
                console.error("ENERGY_NATIVE_FAIL " + message);
                Qt.quit();
            }
            return ok;
        }
        EnergyPressureField { id: field }
        Column {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 20
            Repeater {
                id: faces
                onItemAdded: function(index, item) {
                    field.sources = field.sources.concat([item]);
                }
                onItemRemoved: function(index, item) {
                    field.sources = field.sources.filter(source => source !== item);
                }
                model: ["omnitrix","tron","ki-blast","flamethrower"]
                EnergyProgressFace {
                    required property string modelData
                    width: parent.width
                    height: 36
                    variant: modelData
                    caption: modelData
                }
            }
            EnergyProgressFace {
                id: ash
                width: parent.width; height: 36
                variant: "flamethrower"; fireMode: "ash-trail"
                caption: "ASH TRAIL"
            }
            EnergyProgressFace {
                id: erosion
                width: parent.width; height: 36
                variant: "flamethrower"; fireMode: "burn-away"
                caption: "BURN AWAY"
            }
        }
        Timer {
            interval: 120
            running: !lab.failed
            repeat: true
            onTriggered: {
                const elapsed = Date.now()-lab.started;
                if (!lab.require(faces.count===4,"variant count")) return;
                if (!lab.require(Math.abs(field.offsetX)<=3.000001 && Math.abs(field.offsetY)<=2.000001,
                        "bounded aggregate widget pressure")) return;
                if (lab.stage===0 || lab.stage===3 || (lab.stage>=4 && lab.stage<=6)) {
                    if (!lab.require(field.pressure===0 && field.offsetX===0 && field.offsetY===0,
                            "idle, hidden or reduced host pressure "+lab.stage)) return;
                } else if (lab.stage===1) {
                    if (!lab.require(field.pressure>0 && field.pressure<=1,
                            "running host pressure")) return;
                    const f=faces.itemAt(0);
                    if (elapsed>4800 && !lab.require(field.pressure>.5,
                            "overdrive host pressure")) return;
                }
                if (lab.stage>=14) {
                    const ki=faces.itemAt(2);
                    if (lab.stage===14) {
                        ki.reducedMotion=false;
                        ki.phase="running";
                        ki.progress=.68;
                    } else if (lab.stage===15) {
                        if (!lab.require(ki.visualFrame.clash && Math.abs(ki.visualFrame.enemyFraction-.32)<.00001,
                                "native opposing beam")) return;
                        ki.phase="failure";
                        lab.pulseStarted=Date.now();
                    } else if (lab.stage===16) {
                        if (!lab.require(ki.displayedFraction<.68 && ki.displayedFraction>=0,
                                "native defeat retreat")) return;
                        if (Date.now()-lab.pulseStarted<1300) return;
                        if (!lab.require(ki.visualFrame.enemyHeat===1 && ki.visualFrame.enemyOpacity===1 && ki.visualFrame.enemyFraction===1,
                                "native victorious red beam persists")) return;
                        if (!lab.require(ki.displayedFraction===0 && !ki.animationActive,
                                "native defeat drained and stopped")) return;
                        ki.phase="idle";
                        if (!lab.require(ki.visualFrame.enemyOpacity===0,"explicit reset clears winner")) return;
                        console.log("ENERGY_NATIVE_PASS variants; host pulse; pixel fire materials; persistent red defeat and reset");
                        Qt.quit(); return;
                    }
                    lab.stage++;
                    return;
                }
                if (lab.stage>=8) {
                    for (const f of [ash,erosion]) {
                        if (!lab.require(f.materialExperiment,"material mode mounted")) return;
                        if (lab.stage===8) {
                            f.progressMode="measured";
                            f.phase="running";
                            f.progress=.6;
                        } else if (lab.stage===9) {
                            if (!lab.require(f.displayedFraction===.6,"material exact progress")) return;
                            f.phase="failure";
                        } else if (lab.stage===10) {
                            if (!lab.require(f.displayedFraction===.6 && !f.animationActive,
                                    "material partial failure stays")) return;
                            f.phase="running";
                            f.progress=.7;
                        } else if (lab.stage===11) {
                            f.reducedMotion=true;
                            f.phase="success";
                        } else if (lab.stage===12) {
                            if (!lab.require(f.displayedFraction===1 && !f.animationActive,
                                    "material success settles")) return;
                            f.phase="idle";
                        } else if (lab.stage===13) {
                            if (!lab.require(f.displayedFraction===0,"material resets")) return;
                        }
                    }
                    if (lab.stage===13) {
                        lab.stage=14;
                        return;
                    }
                    lab.stage++;
                    return;
                }
                if (lab.stage===7) {
                    const omni=faces.itemAt(0);
                    if (!lab.require(Math.abs(field.offsetX)<=.300001 && Math.abs(field.offsetY)<=.100001,
                            "contained Omnitrix motion")) return;
                    if (field.completionFlash>.2) lab.sawFlash=true;
                    if (Date.now()-lab.pulseStarted>1000) {
                        if (!lab.require(lab.sawFlash && field.completionFlash===0 && !omni.animationActive,
                                "single completion pulse settles")) return;
                        lab.stage=8;
                    }
                    return;
                }
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
                    const omni=faces.itemAt(0);
                    omni.reducedMotion=false;
                    omni.phase="running";
                    omni.progress=.7;
                    omni.phase="success";
                    lab.pulseStarted=Date.now();
                    lab.stage=7;
                    return;
                }
                lab.stage++;
            }
        }
    }
}
