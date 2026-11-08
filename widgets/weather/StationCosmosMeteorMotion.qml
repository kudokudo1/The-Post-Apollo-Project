import QtQuick
import "../../components"

// C30 // Animated *equatorial schematic* of IAU radiants and artistic
// meteor trails. It does not claim to show a local live sky, actual meteors,
// intensity, hourly rate, or a forecast of visual activity.
Item {
    id: motion
    objectName: "cosmos-c30-meteor-motion"
    clip: true
    property var peak: null
    property bool playing: true
    readonly property bool motionRunning: motionDriver.running
    property real motionPhase: 0
    readonly property bool radiantValid: peak
        && peak.ra !== undefined && peak.ra !== null
        && peak.dec !== undefined && peak.dec !== null
        && isFinite(Number(peak.ra)) && isFinite(Number(peak.dec))
        && Number(peak.dec) >= -90 && Number(peak.dec) <= 90
    readonly property real radiantX: radiantValid
        ? (((Number(peak.ra)%360)+360)%360)/360 : 0.5
    readonly property real radiantY: radiantValid
        ? (90-Number(peak.dec))/180 : 0.5

    Timer {
        id: motionDriver
        objectName: "cosmos-c30-meteor-motion-driver"
        interval: 80
        repeat: true
        running: motion.visible && motion.playing
        onTriggered: {
            motion.motionPhase = (motion.motionPhase+0.017)%1000;
            skyCanvas.requestPaint();
        }
    }

    Canvas {
        id: skyCanvas
        objectName: "cosmos-c30-meteor-moving-sky"
        anchors.fill: parent
        renderStrategy: Canvas.Immediate
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx=getContext("2d");
            const w=width, h=height;
            ctx.clearRect(0,0,w,h);
            if (w<2 || h<2) return;
            ctx.fillStyle="#080918";
            ctx.fillRect(0,0,w,h);
            // RA/Dec grid: longitude-ish RA over 0..360, Dec +90..-90.
            // Not the local horizon, and explicitly labeled as schematic.
            ctx.strokeStyle="#35436A";
            ctx.lineWidth=0.7;
            ctx.globalAlpha=0.45;
            for(let k=1;k<4;k++) {
                const x=w*k/4;
                ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();
            }
            for(let k=1;k<3;k++) {
                const y=h*k/3;
                ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();
            }
            // Deterministic background particles; tiny temporal twinkle.
            for(let k=0;k<72;k++) {
                const x=((k*0.61803398875+0.17)%1)*w;
                const y=((k*0.75487766625+0.29)%1)*h;
                ctx.globalAlpha=0.25+0.53*(0.5+
                    0.5*Math.sin(motion.motionPhase*5+k*1.71));
                ctx.fillStyle=k%11===0?"#F2BE4E":"#B6E4F0";
                ctx.fillRect(x,y,k%9===0?2:1,k%9===0?2:1);
            }
            const rx=w*motion.radiantX, ry=h*motion.radiantY;
            // Animate 4 illustrative streaks from the selected source's
            // equatorial radiant when available; otherwise from center.
            // Their *rate is purely decorative*, not derived from IAU data.
            for(let k=0;k<4;k++) {
                const p=(motion.motionPhase*0.29+k*0.27)%1;
                const a=0.38+k*1.59;
                const distance=(6+p*1.2*Math.max(w,h));
                const hx=rx+Math.cos(a)*distance;
                const hy=ry+Math.sin(a)*distance;
                if(hx<-30||hx>w+30||hy<-30||hy>h+30)continue;
                const length=11+24*p;
                const tx=hx-Math.cos(a)*length;
                const ty=hy-Math.sin(a)*length;
                ctx.globalAlpha=(1-p)*0.85;
                ctx.strokeStyle=k%2===0?"#F2BE4E":"#55CFCA";
                ctx.lineWidth=k%3===0?2.1:1.4;
                ctx.beginPath();ctx.moveTo(tx,ty);ctx.lineTo(hx,hy);ctx.stroke();
                ctx.globalAlpha=(1-p);
                ctx.fillStyle="#DCF3FA";
                ctx.beginPath();ctx.arc(hx,hy,1.5,0,Math.PI*2);ctx.fill();
            }
            if(motion.radiantValid) {
                ctx.globalAlpha=0.96;
                ctx.strokeStyle="#ED981A";
                ctx.lineWidth=1.1;
                ctx.beginPath();ctx.arc(rx,ry,6,0,2*Math.PI);ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(rx-10,ry);ctx.lineTo(rx-3,ry);
                ctx.moveTo(rx+3,ry);ctx.lineTo(rx+10,ry);
                ctx.moveTo(rx,ry-10);ctx.lineTo(rx,ry-3);
                ctx.moveTo(rx,ry+3);ctx.lineTo(rx,ry+10);
                ctx.stroke();
            }
            ctx.globalAlpha=1;
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        height: 19
        color: "#D01B0623"
        QuietText {
            anchors.fill: parent
            anchors.margins: 4
            text: motion.radiantValid
                ? "SIMULATED TRAILS // RA " + Number(motion.peak.ra).toFixed(0)
                  + "° DEC " + Number(motion.peak.dec).toFixed(0)+"°"
                : "SIMULATED TRAILS // RADIANT UNAVAILABLE"
            font.pixelSize: 8
            color: Colors.yellow
            elide: Text.ElideRight
        }
    }
    onRadiantValidChanged: skyCanvas.requestPaint()
    onRadiantXChanged: skyCanvas.requestPaint()
    onRadiantYChanged: skyCanvas.requestPaint()
}
