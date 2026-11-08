import QtQuick
import "../../components"

// C31 // Small interactive, visibly moving eclipse demonstration.
// The NASA GSFC provider supplies global DATE/TYPE only, not optical
// circumstances, apparent radii, contacts, or local observer coordinates.
// Animation phase and eclipse overlap are artistic/educational, never
// claimed to simulate a particular event or advance in real calendar time.
Item {
    id: visual
    objectName: "cosmos-c31-eclipse-visual"
    clip: true
    property string body: "SOLAR"
    property var eventRecord: null
    property bool playing: true
    property bool showArchive: false
    property real demoPhase: 0.12
    readonly property bool motionRunning: phaseDriver.running
    readonly property string eventKind:
        eventRecord && eventRecord.phase ? String(eventRecord.phase).toUpperCase() : ""
    readonly property bool isSolar: body === "SOLAR"

    // NASA visual references are *historical* and not images of the NASA
    // calendar's next event. Fallback remains the interactive schematic.
    readonly property string archiveUrl: isSolar
        ? "https://assets.science.nasa.gov/dynamicimage/assets/science/psd/lunar-science/2023/08/eclipse2017.jpg?crop=faces%2Cfocalpoint&fit=crop&h=2527&w=3186"
        : "https://assets.science.nasa.gov/dynamicimage/assets/science/psd/solar/2023/09/i/iss065e074511-full.jpeg?crop=faces%2Cfocalpoint&fit=clip&h=640&w=640"
    readonly property string archiveCredit: isSolar
        ? "NASA / AUBREY GEMIGNANI · 2017" : "NASA / ISS · 2021"

    function seek(nextPhase) {
        if (!isFinite(Number(nextPhase))) return;
        demoPhase = Math.max(0, Math.min(1, Number(nextPhase)));
    }

    Timer {
        id: phaseDriver
        objectName: "cosmos-c31-eclipse-motion-driver"
        interval: 100
        repeat: true
        running: visual.visible && visual.playing && !visual.showArchive
        onTriggered: visual.demoPhase = (visual.demoPhase+0.005)%1
    }

    Canvas {
        id: eclipseCanvas
        objectName: "cosmos-c31-eclipse-live-canvas"
        anchors.fill: parent
        visible: !visual.showArchive || archivePhoto.status !== Image.Ready
        renderStrategy: Canvas.Immediate
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d");
            const w = width, h = height;
            ctx.clearRect(0,0,w,h);
            if (w<2||h<2) return;
            ctx.fillStyle = "#0E071B";
            ctx.fillRect(0,0,w,h);
            const cx = w*0.5, cy = h*0.5;
            const r = Math.max(4,Math.min(w*0.32,h*0.36));
            const t = visual.demoPhase;
            const crossing = (t-0.5)*r*4.5;
            const penumbral = visual.eventKind.indexOf("PENUMBRAL")>=0;
            const annular = visual.eventKind.indexOf("ANNULAR")>=0;
            const partial = visual.eventKind.indexOf("PARTIAL")>=0;

            // Fine animated limb markers and star points are illustrative.
            for(let k=0;k<16;k++) {
                const x=((k*0.61803398875+0.17)%1)*w;
                const y=((k*0.75487766625+0.29)%1)*h;
                ctx.fillStyle="#55648D";
                ctx.globalAlpha=0.40 + 0.12*Math.sin(t*6.283+k);
                ctx.fillRect(x,y,1,1);
            }
            ctx.globalAlpha=1;
            ctx.save();
            if (visual.isSolar) {
                // Approximate corona / photosphere; this is NOT a lightcurve.
                const glow=ctx.createRadialGradient(cx,cy,r*0.45,cx,cy,r*1.55);
                glow.addColorStop(0,"#FCE7A3");
                glow.addColorStop(0.5,"#DA8731");
                glow.addColorStop(0.9,"#573016");
                glow.addColorStop(1,"#0E071B");
                ctx.fillStyle=glow;
                ctx.beginPath();ctx.arc(cx,cy,r*1.55,0,Math.PI*2);ctx.fill();
                ctx.fillStyle="#F6C148";
                ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fill();
                const moonR = annular ? r*0.80 : partial ? r*0.89 : r*1.015;
                const moonX = cx+crossing;
                // Partial event's offset is illustrative only.
                const moonY = cy+(partial?r*0.35:0);
                ctx.fillStyle="#090913";
                ctx.beginPath();ctx.arc(moonX,moonY,moonR,0,Math.PI*2);ctx.fill();
                ctx.strokeStyle="#51566A";
                ctx.lineWidth=0.9;
                ctx.stroke();
            } else {
                // Earth umbra/penumbra crossing the lunar disk, with a
                // modest amber hue to help show the shaded side.
                ctx.fillStyle="#BAC6D5";
                ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fill();
                ctx.save();
                ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.clip();
                for(let k=0;k<6;k++) {
                    const a=k*2.399;
                    const x=cx+Math.cos(a)*r*0.62;
                    const y=cy+Math.sin(a)*r*0.63;
                    ctx.fillStyle=k%2===0?"#8D97AB":"#9AA4B9";
                    ctx.globalAlpha=0.45;
                    ctx.beginPath();ctx.arc(x,y,r*(0.09+(k%3)*0.03),0,Math.PI*2);ctx.fill();
                }
                ctx.globalAlpha=penumbral?0.16:0.69;
                ctx.fillStyle=penumbral?"#6B5062":"#5F1D23";
                const shadowX=cx+crossing;
                const shadowY=cy+(partial?r*0.4:0);
                ctx.beginPath();ctx.arc(shadowX,shadowY,r*1.48,0,Math.PI*2);ctx.fill();
                ctx.restore();
                ctx.strokeStyle="#55CFCA";
                ctx.globalAlpha=0.6;
                ctx.lineWidth=1;
                ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke();
            }
            ctx.restore();
            ctx.globalAlpha=1;
        }
        onVisibleChanged: if (visible) requestPaint()
    }

    Image {
        id: archivePhoto
        objectName: "cosmos-c31-nasa-eclipse-archive"
        anchors.fill: parent
        source: visual.showArchive ? visual.archiveUrl : ""
        asynchronous: true
        cache: true
        fillMode: Image.PreserveAspectCrop
        smooth: true
        visible: visual.showArchive && status===Image.Ready
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 11
        color: "#CF1B0623"
        z: 2
        QuietText {
            anchors.fill: parent
            anchors.margins: 2
            font.pixelSize: 7
            text: visual.showArchive
                ? (archivePhoto.status===Image.Ready ? visual.archiveCredit
                   : "NASA ARCHIVE OFFLINE")
                : "DEMO // NOT PREDICTED"
            color: Colors.yellow
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
    }

    // Click the diagram's horizontal position to manually inspect a
    // representative eclipse phase. No made-up local UTC/contact time.
    MouseArea {
        anchors.fill: parent
        enabled: !visual.showArchive
        cursorShape: Qt.PointingHandCursor
        onClicked: function(mouse) {
            visual.seek(mouse.x / Math.max(1,width));
        }
    }
    onDemoPhaseChanged: eclipseCanvas.requestPaint()
    onBodyChanged: eclipseCanvas.requestPaint()
    onEventKindChanged: eclipseCanvas.requestPaint()
}
