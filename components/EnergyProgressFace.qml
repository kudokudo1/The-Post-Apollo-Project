import QtQuick
import "EnergyProgressMotion.js" as Motion

// Opt-in presentation only. No input handling or service calls.
// The owner supplies phase and, for measured/timed modes, actual progress.
Item {
    id: root
    property string variant: "omnitrix" // omnitrix | tron | ki-blast | flamethrower
    property string phase: "idle" // idle | queued | running | ready | success | failure
    property string progressMode: "indeterminate" // indeterminate | measured | timed
    property real progress: 0
    property string caption: ""
    property bool reducedMotion: false
    property color energyColor: variant === "omnitrix" ? Colors.omnitrix
        : variant === "tron" ? Colors.cyan
        : variant === "flamethrower" ? Colors.orange : "#55CFFF"
    property color chassisColor: phase === "failure" ? Colors.red : energyColor
    property color foregroundColor: Colors.white
    readonly property real displayedFraction: visualFrame.fraction
    readonly property real headCenterY: height / 2
    readonly property bool animationActive: visible && !reducedMotion
        && (phase === "running" || (phase === "success" && elapsed < .84))
    property real elapsed: 0
    property double startedAt: 0
    property real finishFrom: 0
    property bool initialized: false
    readonly property var visualFrame: Motion.frame(phase, progressMode, progress,
        elapsed, finishFrom, reducedMotion)
    implicitWidth: 150
    implicitHeight: 34

    function beginPhase() {
        // Capture the last rendered fraction, never a guessed success.
        finishFrom = lastFraction;
        elapsed = 0;
        startedAt = Date.now();
        lastFraction = visualFrame.fraction;
        surface.requestPaint();
    }
    property real lastFraction: 0
    Component.onCompleted: {
        initialized = true;
        beginPhase();
    }
    onPhaseChanged: if (initialized) beginPhase()
    onVisibleChanged: {
        if (initialized && visible) {
            if (animationActive) elapsed = Math.max(0, (Date.now()-startedAt)/1000);
            surface.requestPaint();
        }
    }
    onVisualFrameChanged: {
        if (initialized) {
            // Phase changes may reevaluate bindings before the handler.
            // Only capture running frames on explicit ticks/progress changes.
            surface.requestPaint();
        }
    }
    onProgressChanged: if (initialized && phase === "running")
        lastFraction = Motion.frame(phase, progressMode, progress, elapsed, finishFrom, reducedMotion).fraction
    onEnergyColorChanged: if (initialized) surface.requestPaint()
    onChassisColorChanged: if (initialized) surface.requestPaint()
    onVariantChanged: if (initialized) surface.requestPaint()
    Timer {
        interval: 33
        repeat: true
        running: root.animationActive
        onTriggered: {
            root.elapsed = Math.max(0, (Date.now()-root.startedAt)/1000);
            if (root.phase === "running") root.lastFraction = Motion.frame(root.phase,
                root.progressMode, root.progress, root.elapsed, root.finishFrom, root.reducedMotion).fraction;
        }
    }

    // Only the painted chassis moves. Host hit targets and layout stay fixed.
    Item {
        id: visual
        anchors.fill: parent
        transform: Translate { x: root.visualFrame.dx; y: root.visualFrame.dy }
        Canvas {
            id: surface
            objectName: "energyProgressCanvas"
            anchors.fill: parent
            anchors.margins: -10
            renderTarget: Canvas.Image
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const c = getContext("2d");
                c.reset();
                c.clearRect(0,0,width,height);
                const x=10, y=10, w=Math.max(0,root.width), h=Math.max(0,root.height);
                if (w<4 || h<4) return;
                const f=root.visualFrame, p=f.fraction, mid=y+h/2;
                const ink=root.phase==="failure" ? Colors.red : root.energyColor;
                const hot=root.variant==="flamethrower";
                const ki=root.variant==="ki-blast";
                const tron=root.variant==="tron";
                function tint(col,a) { return Qt.rgba(col.r,col.g,col.b,a); }
                function mix(a,b,k) {
                    return Qt.rgba(a.r+(b.r-a.r)*k,a.g+(b.g-a.g)*k,
                        a.b+(b.b-a.b)*k,1);
                }
                // Low-cost perimeter: three nested outlines, no full-face shadow.
                for (let i=3;i>=1;i--) {
                    c.strokeStyle=tint(root.chassisColor,(.035+f.intensity*.025)*(4-i));
                    c.lineWidth=i*2;
                    c.strokeRect(x,y,w,h);
                }
                c.fillStyle=Colors.dark;
                c.fillRect(x,y,w,h);
                c.strokeStyle=root.chassisColor;
                c.lineWidth=1;
                c.strokeRect(x+.5,y+.5,w-1,h-1);
                const inner=w-2, edge=x+1+inner*p;
                if (p>0) {
                    const g=c.createLinearGradient(0,y+1,0,y+h-1);
                    g.addColorStop(0,ink);
                    g.addColorStop(.18,mix(Colors.dark,ink,tron?.22:.42));
                    g.addColorStop(.50,mix(Colors.dark,ink,ki?.92:hot?.72:.43));
                    g.addColorStop(.82,mix(Colors.dark,ink,tron?.22:.42));
                    g.addColorStop(1,ink);
                    c.fillStyle=g;
                    c.fillRect(x+1,y+1,inner*p,h-2);
                    c.fillStyle=tint(Colors.white,.075);
                    for (let yy=y+4;yy<y+h-2;yy+=4)
                        c.fillRect(x+1,yy,inner*p,1);
                }
                if (!f.headVisible) return;
                // All core and aura layers share the exact centerline.
                function orb(rx,ry,stops) {
                    c.save();
                    c.translate(edge,mid);
                    c.scale(rx,ry);
                    const g=c.createRadialGradient(0,0,0,0,0,1);
                    for (const stop of stops) g.addColorStop(stop[0],stop[1]);
                    c.fillStyle=g;
                    c.beginPath(); c.arc(0,0,1,0,2*Math.PI); c.fill();
                    c.restore();
                }
                // Short surface-clinging fire: asymmetric curved tongues curl
                // upwards from the advancing ember, never a symmetric jet.
                // The entire flame is confined to the trailing side and chamber.
                if (hot && p>0) {
                    c.save();
                    c.beginPath(); c.rect(x+1,y+1,inner*p,h-2); c.clip();
                    const t=root.reducedMotion ? 0 : root.elapsed;
                    const length=Math.min(h*1.3,inner*p);
                    const flameHeight=h*.46;
                    for (let i=0;i<4;i++) {
                        const q=i/4, wave=Math.sin(t*(8+i*2)+i*2.1);
                        const tail=edge-length*(.35+q*.65);
                        const crest=mid-flameHeight*(.55+.32*wave+.12*q);
                        const base=mid+h*.17;
                        const g=c.createLinearGradient(tail,crest,edge,base);
                        g.addColorStop(0,tint(Colors.red,0));
                        g.addColorStop(.38,tint(Colors.red,.48));
                        g.addColorStop(.72,tint(Colors.orange,.82));
                        g.addColorStop(1,tint(Colors.yellow,.95));
                        c.fillStyle=g;
                        c.beginPath();
                        c.moveTo(edge,base);
                        c.bezierCurveTo(tail+length*.24,base+2,tail-2,mid+2,tail,crest+3);
                        c.bezierCurveTo(tail+length*.16,crest+12,tail+length*.35,crest+5,tail+length*.38,crest);
                        c.bezierCurveTo(tail+length*.54,crest-5,edge-length*.15,mid-2,edge,mid-h*.22);
                        c.closePath(); c.fill();
                    }
                    c.restore();
                }
                const scale=f.power;
                const rx=Math.min(h*(tron?.55:.78)*scale,w*.45);
                const ry=Math.min(h*.66,h*.47*(1+(scale-1)*.18));
                orb(rx*1.6,Math.min(h*.91,ry*1.55),[
                    [0,tint(ink,Math.min(.95,.35*f.brightness))],
                    [.55,tint(ink,.22)],[1,tint(ink,0)]]);
                orb(rx,ry,[[0,Colors.white],[Math.min(.34,.12*f.brightness),Colors.white],
                    [.38,mix(ink,Colors.white,Math.min(.95,.4*f.brightness))],[.57,tint(ink,.84)],
                    [1,tint(ink,0)]]);
                if (f.intensity>.08) {
                    const flare=c.createLinearGradient(edge-rx*1.4,mid,edge+rx*1.4,mid);
                    flare.addColorStop(0,tint(ink,0));
                    flare.addColorStop(.5,tint(Colors.white,f.intensity*.8));
                    flare.addColorStop(1,tint(ink,0));
                    c.fillStyle=flare; c.fillRect(edge-rx*1.4,mid-1,rx*2.8,2);
                }
            }
        }
        GohuText {
            anchors.fill: parent
            anchors.margins: 4
            text: root.caption
            color: root.foregroundColor
            font.pixelSize: 10
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            style: Text.Outline
            styleColor: Colors.dark
        }
    }
}
