import QtQuick
import "EnergyProgressMotion.js" as Motion
import "EnergyVariantProfile.js" as Profiles

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
    readonly property var personality: Profiles.profile(variant)
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
        transform: Translate {
            x: root.visualFrame.dx * root.personality.x
            y: root.visualFrame.dy * root.personality.y
        }
        Canvas {
            id: surface
            objectName: "energyProgressCanvas"
            anchors.fill: parent
            readonly property real spill: Math.max(10, root.height * .65)
            anchors.margins: -spill
            renderTarget: Canvas.Image
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const c = getContext("2d");
                c.reset();
                c.clearRect(0,0,width,height);
                const x=spill, y=spill, w=Math.max(0,root.width), h=Math.max(0,root.height);
                if (w<4 || h<4) return;
                const f=root.visualFrame, p=f.fraction, mid=y+h/2;
                const ink=root.phase==="failure" ? Colors.red : root.energyColor;
                const hot=root.variant==="flamethrower";
                const ki=root.variant==="ki-blast";
                const tron=root.variant==="tron";
                const omni=root.variant==="omnitrix";
                const bright=f.brightness*root.personality.brightness;
                function tint(col,a) { return Qt.rgba(col.r,col.g,col.b,a); }
                function mix(a,b,k) {
                    return Qt.rgba(a.r+(b.r-a.r)*k,a.g+(b.g-a.g)*k,
                        a.b+(b.b-a.b)*k,1);
                }
                // Low-cost perimeter: three nested outlines, no full-face shadow.
                for (let i=3;i>=1;i--) {
                    c.strokeStyle=tint(root.chassisColor,Math.min(.35,(.035+f.intensity*.025)*(4-i)*root.personality.brightness));
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
                    g.addColorStop(.50,mix(Colors.dark,ink,ki?.92:hot?.72:omni?.80:.43));
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
                // Consuming fire: asymmetric curved tongues curl
                // around the advancing ember, not down the entire beam.
                // Soft flame lobes can spill beyond the beam vertically;
                // the plasma core remains independently centered.
                if (hot && p>0) {
                    const t=root.reducedMotion ? 0 : root.elapsed;
                    const length=Math.min(h*1.5,inner*p);
                    const reach=h*(.78+.12*f.intensity);
                    c.save();
                    // Constrain the fire to the terminal region, while
                    // letting it consume the full height of the beam tip.
                    c.beginPath();
                    c.rect(edge-length,mid-h*1.1,length+h*.46,h*2.2);
                    c.clip();
                    orb(h*.78, h*.90, [[0,tint(Colors.yellow,.75)],
                        [.32,tint(Colors.orange,.65)],[.64,tint(Colors.red,.28)],
                        [1,tint(Colors.red,0)]]);
                    for (let i=0;i<7;i++) {
                        const q=i/7;
                        const wave=Math.sin(t*(5.7+i*.69)+i*2.1);
                        // The upper curls rise more than the lower curls.
                        const sign=i%3===1 ? 1 : -1;
                        const tail=edge-length*(.25+q*.75);
                        const crest=mid+sign*reach*(.55+.28*wave+.12*q);
                        const base=mid-sign*h*.30;
                        const g=c.createRadialGradient(edge-length*.12,mid,0,
                            edge-length*.12,mid,Math.max(h*.95,length));
                        g.addColorStop(0,tint(Colors.yellow,.92));
                        g.addColorStop(.34,tint(Colors.orange,.88));
                        g.addColorStop(.65,tint(Colors.red,.48));
                        g.addColorStop(1,tint(Colors.red,0));
                        c.fillStyle=g;
                        c.beginPath();
                        c.moveTo(edge+h*.22,base);
                        c.bezierCurveTo(tail+length*.22,base,tail-h*.08,mid,tail,crest);
                        c.bezierCurveTo(tail+length*.18,crest+sign*h*.12,
                            tail+length*.35,crest-sign*h*.32,tail+length*.45,crest-sign*h*.08);
                        c.bezierCurveTo(edge-length*.10,crest+sign*h*.24,
                            edge+h*.44,mid+sign*h*.48,edge+h*.22,base);
                        c.closePath(); c.fill();
                    }
                    c.restore();
                }
                // TRON speed lines stream backward only in the terminal trail.
                if (tron && p>0 && !root.reducedMotion) {
                    c.save();
                    c.beginPath(); c.rect(x+1,y+1,inner*p,h-2); c.clip();
                    for (let i=0;i<5;i++) {
                        const drift=(root.elapsed*(1.1+i*.17)+i*.31)%1;
                        const span=Math.min(inner*p,h*(2+f.intensity*2));
                        const xx=edge-drift*span;
                        c.fillStyle=tint(Colors.white,(1-drift)*(.10+f.intensity*.18));
                        c.fillRect(xx-h*(.45+i*.10),mid+(i-2)*h*.14,h*(.45+i*.10),1);
                    }
                    c.restore();
                }
                const scale=f.power*root.personality.head;
                const rx=Math.min(h*(tron?.55:.78)*scale,w*.45);
                const ry=Math.min(h*.66,h*.47*(1+(scale-1)*.18));
                orb(rx*1.6,Math.min(h*.91,ry*1.55),[
                    [0,tint(ink,Math.min(.98,.35*bright))],
                    [.55,tint(ink,.22)],[1,tint(ink,0)]]);
                orb(rx,ry,[[0,Colors.white],[Math.min(.36,.12*bright),Colors.white],
                    [.38,mix(ink,Colors.white,Math.min(.98,.4*bright))],[.57,tint(ink,.84)],
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
