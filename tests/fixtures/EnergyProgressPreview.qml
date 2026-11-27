import QtQuick
import QtQuick.Window
import Quickshell
import qs.components

ShellRoot {
    Window {
        id: lab
        width: 620
        height: 804
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
            // Foreground colored light washes over controls, not just the
            // background. Strong territory color with a narrow soft overlap.
            // Canvas has no input handler and stays below the success flash.
            Canvas {
                id: battlefieldLight
                anchors.fill: parent
                z: 10
                visible: field.clashLight !== null
                renderTarget: Canvas.Image
                onVisibleChanged: if(visible) requestPaint()
                onWidthChanged: if(visible) requestPaint()
                onHeightChanged: if(visible) requestPaint()
                Connections {
                    target: field
                    function onClashLightChanged() { if(battlefieldLight.visible) battlefieldLight.requestPaint(); }
                }
                onPaint: {
                    const c=getContext("2d");
                    c.reset(); c.clearRect(0,0,width,height);
                    const light=field.clashLight;
                    if(!light || width<=0 || height<=0) return;
                    const source=light.source;
                    const origin=source.mapToItem(battlefieldLight,source.headCenterX,source.headCenterY);
                    const split=Math.max(0,Math.min(width,origin.x));
                    const heat=light.heat;
                    const enemy=Qt.rgba(1,.67-.56*heat,.35-.20*heat,1);
                    const blue=source.energyColor;
                    const p=light.fraction, h=source.height;
                    const dominance=Math.min(1,Math.abs(p-.5)*2);
                    const playerWins=p>=.5+heat*(.22/2.4);
                    const winner=playerWins?blue:enemy;
                    function bloom(cx,cy,rx,ry,color,alpha) {
                        if(rx<=0 || ry<=0 || alpha<=0) return;
                        c.save(); c.translate(cx,cy); c.scale(rx,ry);
                        const g=c.createRadialGradient(0,0,0,0,0,1);
                        g.addColorStop(0,Qt.rgba(color.r,color.g,color.b,alpha));
                        g.addColorStop(.26,Qt.rgba(color.r,color.g,color.b,alpha*.75));
                        g.addColorStop(.60,Qt.rgba(color.r,color.g,color.b,alpha*.28));
                        g.addColorStop(1,Qt.rgba(color.r,color.g,color.b,0));
                        c.fillStyle=g; c.fillRect(-1,-1,2,2); c.restore();
                    }
                    const start=source.mapToItem(battlefieldLight,source.track.inset,source.headCenterY).x;
                    const end=source.mapToItem(battlefieldLight,source.track.inset+source.track.width,source.headCenterY).x;
                    // Extended sources follow the actual occupied beam lengths.
                    // Falloff occurs both vertically and horizontally. No flat
                    // territory tint or hard boundary is drawn.
                    const left=Math.max(0,split-start),right=Math.max(0,end-split);
                    const reach=Math.max(h*5,height*.78);
                    if(p>0) bloom(start+left*.53,origin.y,Math.max(h*2,left*.86),reach,
                        blue,light.level*(.62+.38*p));
                    if(p<1) bloom(split+right*.47,origin.y,Math.max(h*2,right*.86),reach,
                        enemy,light.level*(.62+.38*(1-p)));
                    // Broader collision-centered light is brighter than either
                    // beam, with the dominant hue extending into its opponent.
                    if(p>0 && p<1) {
                        const offset=(playerWins?1:-1)*h*(.5+dominance*2.0);
                        bloom(split+offset,origin.y,h*(4+dominance*4),h*5,
                            winner,light.level*(.55+.35*dominance));
                        bloom(split,origin.y,h*3.2,h*3.8,Qt.rgba(1,.96,.87,1),light.level*.85);
                    }

                }
            }
            // Local foreground spill is shared by all variants, including
            // Ki Blast. Soft falloff lights nearby controls, not the entire
            // widget. The stronger battlefield wash remains independent.
            Canvas {
                id: localRadiance
                anchors.fill: parent
                z: 11
                visible: field.localLights.length > 0
                renderTarget: Canvas.Image
                onVisibleChanged: if(visible) requestPaint()
                onWidthChanged: if(visible) requestPaint()
                onHeightChanged: if(visible) requestPaint()
                Connections {
                    target: field
                    function onLocalLightsChanged() { if(localRadiance.visible) localRadiance.requestPaint(); }
                }
                onPaint: {
                    const c=getContext("2d");
                    c.reset(); c.clearRect(0,0,width,height);
                    for(const light of field.localLights) {
                        const source=light.source;
                        const p=source.mapToItem(localRadiance,source.headCenterX,source.headCenterY);
                        const h=source.height;
                        const flame=light.fire?source.flameMotion:null;
                        const rx=h*(light.fire?5.2*flame.stretch:4.8);
                        const ry=h*(light.fire?3.7*flame.breath:3.5);
                        if(rx<=0 || ry<=0) continue;
                        const ink=light.color, a=light.level*(light.fire?.48*flame.pulse:1);
                        c.save(); c.translate(p.x+(light.fire?source.flameTipOffset-h*(.38+flame.drag):light.side*h*.38),
                            p.y+(light.fire?h*flame.sway:0)); c.scale(rx,ry);
                        const g=c.createRadialGradient(0,0,0,0,0,1);
                        if(light.fire || source.variant==="omnitrix") {
                            // Smooth, monotonic optical falloff. No bright ring
                            // or flat band over the source itself.
                            for(let i=0;i<=16;i++) {
                                const r=i/16, fade=(1-r)*(1-r)*(1+2*r);
                                g.addColorStop(r,Qt.rgba(ink.r,ink.g,ink.b,a*fade));
                            }
                        } else {
                            g.addColorStop(0,Qt.rgba(ink.r,ink.g,ink.b,a));
                            g.addColorStop(.25,Qt.rgba(ink.r,ink.g,ink.b,a*.85));
                            g.addColorStop(.62,Qt.rgba(ink.r,ink.g,ink.b,a*.40));
                            g.addColorStop(1,Qt.rgba(ink.r,ink.g,ink.b,0));
                        }
                        c.fillStyle=g; c.fillRect(-1,-1,2,2); c.restore();
                    }
                }
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
                model: [{name:"OMNITRIX",key:"omnitrix"},{name:"DEFAULT",key:"default"},{name:"TRON",key:"tron"},
                    {name:"KI BLAST",key:"ki-blast"},{name:"FLAMETHROWER",key:"flamethrower"},
                    {name:"FLAMETHROWER // ASH TRAIL",key:"flamethrower",fireMode:"ash-trail"},
                    {name:"FLAMETHROWER // BURN AWAY",key:"flamethrower",fireMode:"burn-away"}]
                Item {
                    id: card
                    required property var modelData
                    width: parent.width
                    height: 84
                    readonly property string fireMode: card.modelData.fireMode || "standard"
                    property alias pressureSource: energyFace
                    property string phase: "idle"
                    property int duration: 6500
                    property double started: 0
                    property real fraction: 0
                    property bool exact: false
                    function start() {
                        if (phase === "running" || energyFace.animationActive) return;
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
                        // Let Burn Away expose the actual panel instead of a
                        // duplicate opaque ActionButton chassis underneath.
                        idleFillColor: card.fireMode==="burn-away" ? "transparent" : Colors.black
                        hoverFillColor: card.fireMode==="burn-away" ? "transparent" : Colors.yellow
                        pressedFillColor: card.fireMode==="burn-away" ? "transparent" : Colors.magenta
                        idleBorderColor: card.fireMode==="burn-away" ? "transparent" : accentColor
                        hoverBorderColor: card.fireMode==="burn-away" ? "transparent" : Colors.orange
                        pressedBorderColor: card.fireMode==="burn-away" ? "transparent" : Colors.magenta
                        perimeterGlowEnabled: card.modelData.key==="default" ? false : (normalFace || (washSafePerimeter && softGlowEnabled))
                        contentGlowEnabled: false
                        softGlowEnabled: false
                        wideGlowEnabled: false
                        // The lab panel itself moves by a bounded offset.
                        available: true
                        interactive: card.phase !== "running" && !energyFace.animationActive
                        onLeftClicked: card.start()
                        EnergyProgressFace {
                            id: energyFace
                            anchors.fill: parent
                            variant: card.modelData.key
                            fireMode: card.fireMode
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
        // The flash is born at the Omnitrix head, then spreads through
        // this widget only. Map the nested source into overlay coordinates.
        Canvas {
            id: flashOverlay
            anchors.fill: parent
            z: 20
            visible: field.completionFlash>0 && field.flashSource!==null
            renderTarget: Canvas.Image
            onVisibleChanged: if (visible) requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            Connections {
                target: field
                function onCompletionFlashChanged() { flashOverlay.requestPaint(); }
                function onFlashSpreadChanged() { flashOverlay.requestPaint(); }
                function onFlashSourceChanged() { flashOverlay.requestPaint(); }
            }
            onPaint: {
                const c=getContext("2d");
                c.reset(); c.clearRect(0,0,width,height);
                const source=field.flashSource;
                if (!source || field.completionFlash<=0 || width<=0 || height<=0) return;
                const origin=source.mapToItem(flashOverlay,
                    source.headCenterX,source.headCenterY);
                const radius=Math.max(1,Math.hypot(Math.max(origin.x,width-origin.x),
                    Math.max(origin.y,height-origin.y))*(.10+1.25*field.flashSpread));
                const ink=field.flashColor, alpha=field.completionFlash;
                const g=c.createRadialGradient(origin.x,origin.y,0,origin.x,origin.y,radius);
                g.addColorStop(0,Qt.rgba(ink.r,ink.g,ink.b,alpha));
                g.addColorStop(.48,Qt.rgba(ink.r,ink.g,ink.b,alpha*.76));
                g.addColorStop(.78,Qt.rgba(ink.r,ink.g,ink.b,alpha*.42));
                g.addColorStop(1,Qt.rgba(ink.r,ink.g,ink.b,0));
                c.fillStyle=g; c.fillRect(0,0,width,height);
            }
        }
    }
}
