import QtQuick
import QtQuick.Window
import Quickshell
import qs.components

ShellRoot {
    Window {
        id: lab
        width: 480
        height: 480
        visible: true
        color: Colors.dark
        property int stage: 0
        property double started: Date.now()
        property bool failed: false
        property bool sawFlash: false
        property bool sawRepair: false
        property string mockBurnStage: ""
        property bool mockBurnVerified: false
        property bool mockArmed: false
        property bool mockArmReady: false
        property real mockArmProgress: 0
        property string mockSavePhase: "idle"
        property real mockSaveProgress: 0
        property double pulseStarted: 0
        property real pausedAt: 0
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
                id: quiet
                width: parent.width; height: 36
                variant: "default"
                progressMode: "measured"
                caption: "DEFAULT"
                Component.onCompleted: field.sources=field.sources.concat([quiet])
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
        // Disposable host slots: no GitHub or Trash backend is instantiated.
        Item {
            id: mockWorkSlot
            x: 18; y: 385; width: 184; height: 43
            clip: true
            visible: lab.stage>=26 && !mockBurn.receiptReady
            EnergyProgressBurnSequence {
                id: mockBurn
                anchors.fill: parent
                armed: lab.mockArmed
                armReady: lab.mockArmReady
                armProgress: lab.mockArmProgress
                operationStage: lab.mockBurnStage
                verified: lab.mockBurnVerified
            }
        }
        Item {
            id: mockReceiptSlot
            x: 220; y: 385; width: 184; height: 43
            visible: lab.stage>=26 && mockBurn.receiptReady
        }
        Loader {
            id: mockSave
            x: 18; y: 430; width: 184; height: 38
            visible: lab.stage>=26 && lab.mockSavePhase!=="idle"
            clip: true
            sourceComponent: EnergyProgressFace {
                variant: "omnitrix"; energyColor: Colors.blue
                progressMode: "timed"; progress: lab.mockSaveProgress
                phase: lab.mockSavePhase
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
                if (lab.stage===0 || lab.stage===3) {
                    const all=[quiet,ash,erosion];
                    for(let i=0;i<faces.count;i++) all.push(faces.itemAt(i));
                    for(const f of all) {
                        if (!lab.require(Math.abs(f.fillGap-3*f.height/34)<.00001,
                                "height-scaled fill gap "+f.variant)) return;
                        if (!lab.require(Math.abs(f.headCenterX-(f.track.inset+f.track.width*f.displayedFraction))<.00001,
                                "inset head center "+f.variant)) return;
                    }
                }
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
                if (lab.stage>=26) {
                    if(lab.stage===26) {
                        lab.mockArmed=true; lab.mockArmProgress=.55;
                        lab.mockSaveProgress=.90; lab.mockSavePhase="running";
                    } else if(lab.stage===27) {
                        if(!lab.require(mockBurn.ashVisible && mockBurn.ashPhase==="running"
                            && mockBurn.ashFraction===.55 && !mockBurn.operationVisible,
                            "arming is timed ash without deletion")) return;
                        if(!lab.require(mockSave.item.variant==="omnitrix"
                            && mockSave.item.displayedFraction===.90,
                            "timed save preserves prefill")) return;
                        lab.mockArmProgress=1; lab.mockArmReady=true;
                    } else if(lab.stage===28) {
                        if(!lab.require(mockBurn.ashPhase==="ready" && mockBurn.ashFraction===1,
                            "armed ash stays full")) return;
                        lab.mockBurnStage="clicked";
                    } else if(lab.stage===29) {
                        if(!lab.require(mockBurn.ashVisible && !mockBurn.operationVisible,
                            "second click acknowledgement retains ash")) return;
                        lab.mockBurnStage="working";
                        lab.mockSaveProgress=1; lab.mockSavePhase="success";
                        lab.pulseStarted=Date.now();
                    } else if(lab.stage===30) {
                        if(Date.now()-lab.pulseStarted<400) return;
                        if(!lab.require(mockBurn.operationVisible && mockBurn.burnFraction>0
                            && !mockBurn.receiptReady && mockWorkSlot.visible,
                            "burn remains on original confirmation")) return;
                        lab.mockBurnVerified=false; lab.mockBurnStage="result";
                        lab.pulseStarted=Date.now();
                    } else if(lab.stage===31) {
                        if(Date.now()-lab.pulseStarted<1650) return;
                        if(!lab.require(mockBurn.receiptReady && mockBurn.burnPhase==="failure"
                            && mockReceiptSlot.visible && !mockWorkSlot.visible,
                            "unverified receipt only after failure cooldown")) return;
                        lab.mockBurnStage=""; lab.mockArmed=false; lab.mockArmReady=false;
                        lab.mockSavePhase="idle";
                    } else if(lab.stage===32) {
                        if(!lab.require(!mockBurn.receiptReady && !mockBurn.operationVisible
                            && !mockSave.visible,"dismissed operation faces inactive")) return;
                        lab.mockArmed=true; lab.mockArmReady=true; lab.mockArmProgress=1;
                        lab.mockBurnStage="clicked";
                    } else if(lab.stage===33) {
                        // Synchronous fast success: backend must not skip the sweep.
                        lab.mockBurnStage="working";
                        lab.mockBurnVerified=true; lab.mockBurnStage="result";
                        lab.pulseStarted=Date.now();
                    } else if(lab.stage===34) {
                        if(Date.now()-lab.pulseStarted<900) return;
                        if(!lab.require(mockBurn.burnPhase==="running" && !mockBurn.receiptReady
                            && mockBurn.burnFraction>0 && mockBurn.burnFraction<.9
                            && mockWorkSlot.visible,"fast result preserves visible burn sweep")) return;
                    } else if(lab.stage===35) {
                        if(Date.now()-lab.pulseStarted<4700) return;
                        if(!lab.require(mockBurn.receiptReady && mockBurn.burnPhase==="success"
                            && mockBurn.burnFraction===1 && mockReceiptSlot.visible
                            && !mockWorkSlot.visible,"verified receipt after full repair")) return;
                        quiet.reducedMotion=false;
                        quiet.progressMode="measured"; quiet.progress=.4;
                        quiet.phase="running"; quiet.activityMotionEnabled=true;
                        lab.pulseStarted=Date.now();
                    } else if(lab.stage===36) {
                        if(Date.now()-lab.pulseStarted<400) return;
                        if(!lab.require(quiet.animationActive && quiet.displayedFraction===.4,
                            "operation visual starts with exact progress")) return;
                        quiet.activityMotionEnabled=false;
                        lab.pausedAt=quiet.elapsed;
                        lab.pulseStarted=Date.now();
                    } else if(lab.stage===37) {
                        if(Date.now()-lab.pulseStarted<500) return;
                        if(!lab.require(!quiet.animationActive && quiet.displayedFraction===.4
                            && Math.abs(quiet.elapsed-lab.pausedAt)<.001,
                            "quiet operation freezes motion without changing progress")) return;
                        quiet.activityMotionEnabled=true;
                        lab.pulseStarted=Date.now();
                    } else if(lab.stage===38) {
                        if(Date.now()-lab.pulseStarted<400) return;
                        if(!lab.require(quiet.animationActive && quiet.displayedFraction===.4
                            && quiet.elapsed>lab.pausedAt && quiet.elapsed<lab.pausedAt+1,
                            "fresh activity resumes without a clock jump")) return;
                        quiet.phase="idle";
                        console.log("ENERGY_NATIVE_PASS seven treatments; timed save; two-stage burn; evidence-clock pause");
                        Qt.quit(); return;
                    }
                    lab.stage++; return;
                }
                if (lab.stage>=22) {
                    const fires=[faces.itemAt(3),ash,erosion];
                    if(lab.stage===22) {
                        for(const f of fires) {
                            f.reducedMotion=false; f.visible=true; f.progressMode="measured";
                            f.phase="running"; f.progress=.65;
                        }
                    } else if(lab.stage===23) {
                        for(const f of fires) f.phase="success";
                        lab.pulseStarted=Date.now();
                    } else if(lab.stage===24) {
                        const t=Date.now()-lab.pulseStarted;
                        if(t<850) return;
                        for(const f of fires) {
                            if(!lab.require(f.displayedFraction===1 && f.animationActive && f.fireState.cooling
                                && f.fireState.flame<1 && f.fireState.heat>0,
                                "fire extinguishes after actual success "+f.fireMode)) return;
                        }
                    } else if(lab.stage===25) {
                        if(erosion.fireState.repairing && erosion.fireState.repair>0) lab.sawRepair=true;
                        if(Date.now()-lab.pulseStarted<2800) return;
                        if(!lab.require(lab.sawRepair,"native visible repair phase")) return;
                        for(const f of fires) {
                            if(!lab.require(f.displayedFraction===1 && !f.animationActive
                                && !f.fireState.active && f.fireState.heat===0 && f.fireState.repair===1,
                                "fire settles repaired without changing progress "+f.fireMode)) return;
                        }
                        lab.stage=26; return;
                    }
                    lab.stage++; return;
                }
                if (lab.stage>=17) {
                    if (!lab.require(field.pressure===0 && field.offsetX===0 && field.offsetY===0
                        && field.localLights.length===0 && field.completionFlash===0,
                        "default emits no host effects")) return;
                    if(lab.stage===17) {
                        quiet.phase="running"; quiet.progress=.63;
                    } else if(lab.stage===18) {
                        if(!lab.require(quiet.displayedFraction===.63 && !quiet.visualFrame.headVisible,
                            "default measured fill without head")) return;
                        quiet.phase="failure";
                    } else if(lab.stage===19) {
                        if(!lab.require(quiet.displayedFraction===.63 && !quiet.animationActive,
                            "default failure retains extent")) return;
                        quiet.phase="running"; quiet.progress=.8; quiet.phase="success";
                        lab.pulseStarted=Date.now();
                    } else if(lab.stage===20) {
                        if(Date.now()-lab.pulseStarted<1000) return;
                        if(!lab.require(quiet.displayedFraction===1 && !quiet.animationActive,
                            "default success settles")) return;
                        quiet.phase="idle";
                    } else if(lab.stage===21) {
                        if(!lab.require(quiet.displayedFraction===0,"default resets")) return;
                        lab.stage=22; return;
                    }
                    lab.stage++; return;
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
                        lab.stage=17; return;
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
                            lab.pulseStarted=Date.now();
                        } else if (lab.stage===10) {
                            if(Date.now()-lab.pulseStarted<1600) return;
                            if (!lab.require(f.displayedFraction===.6 && !f.animationActive && f.fireState.repair===0,
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
