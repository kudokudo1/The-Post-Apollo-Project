import QtQuick
import QtQuick.Window
import Quickshell
import qs.components

ShellRoot {
    Window {
        id: lab
        width: 880
        height: 450
        visible: true
        color: Colors.dark
        property int stage: 0
        property double started: 0
        property var baseline: []
        property bool failed: false
        function fail(message) {
            failed = true;
            console.error("ENERGY_LOAD_FAIL " + message);
            Qt.quit();
        }
        function findCanvas(item) {
            if (item.objectName === "energyProgressCanvas") return item;
            for (const child of item.children || []) {
                const found = findCanvas(child);
                if (found) return found;
            }
            return null;
        }
        function face(i) { return faces.itemAt(i); }
        function snapshot() {
            return Array.from({length:faces.count},(_,i)=>face(i).paintCount);
        }
        function begin() {
            baseline=snapshot();
            started=Date.now();
        }
        function report(name, activeCount) {
            const ms=Date.now()-started;
            const delta=snapshot().map((v,i)=>v-baseline[i]);
            const active=delta.slice(0,activeCount);
            const rest=delta.slice(activeCount);
            const sum=active.reduce((a,b)=>a+b,0);
            console.log("ENERGY_LOAD_SAMPLE " + JSON.stringify({
                state:name, sampleMs:ms, activeCount:activeCount,
                activePaints:sum, inactivePaints:rest.reduce((a,b)=>a+b,0),
                minActivePaints:active.length?Math.min(...active):0,
                maxActivePaints:active.length?Math.max(...active):0,
                meanPaintHz:activeCount?sum*1000/(ms*activeCount):0
            }));
            if (rest.some(v=>v!==0)) { fail(name+" inactive paint activity"); return false; }
            // Liveness, not a hardware-independent FPS performance SLA.
            if (active.some(v=>v===0)) { fail(name+" active canvas never painted"); return false; }
            return true;
        }
        Grid {
            anchors.fill: parent
            anchors.margins: 18
            columns: 4
            spacing: 12
            Repeater {
                id: faces
                model: 32
                EnergyProgressFace {
                    required property int index
                    property int paintCount: 0
                    width: 195; height: 36
                    variant: ["omnitrix","tron","ki-blast","flamethrower"][index%4]
                    caption: variant
                }
            }
        }
        Timer {
            interval: 250
            repeat: true
            running: !lab.failed
            onTriggered: {
                if (lab.stage===0) {
                    if (faces.count!==32) { lab.fail("count"); return; }
                    for(let i=0;i<32;i++){
                        const f=lab.face(i), canvas=lab.findCanvas(f);
                        if(!canvas) { lab.fail("missing real canvas "+i); return; }
                        canvas.painted.connect(function(){ f.paintCount++; });
                    }
                    lab.started=Date.now(); lab.stage=1;
                    return;
                }
                const elapsed=Date.now()-lab.started;
                if (lab.stage%2===1) {
                    // Drain initial paints, pending scene updates and terminal
                    // impact animation before measuring a steady state.
                    if (elapsed<(lab.stage===9?2200:1250)) return;
                    lab.begin(); lab.stage++;
                    return;
                }
                if (elapsed<2000) return;
                if (lab.stage===2) {
                    if(!lab.report("idle32",0)) return;
                    for(let i=0;i<4;i++) lab.face(i).phase="running";
                } else if (lab.stage===4) {
                    if(!lab.report("active4",4)) return;
                    for(let i=4;i<32;i++) lab.face(i).phase="running";
                } else if (lab.stage===6) {
                    if(!lab.report("active32",32)) return;
                    for(let i=4;i<32;i++) lab.face(i).visible=false;
                } else if (lab.stage===8) {
                    if(!lab.report("active4_hidden28",4)) return;
                    for(let i=0;i<32;i++){
                        const f=lab.face(i); f.phase="success"; f.visible=true;
                    }
                } else if (lab.stage===10) {
                    if(!lab.report("completed32",0)) return;
                    console.log("ENERGY_LOAD_PASS idle; active4; active32; hidden28; completed");
                    Qt.quit(); return;
                }
                lab.started=Date.now(); lab.stage++;
            }
        }
    }
}
