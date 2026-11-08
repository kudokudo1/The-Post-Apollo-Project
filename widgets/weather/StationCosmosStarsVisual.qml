import QtQuick
import "../../components"

// C32 // Decorative motion behind the *unchanged* USNO az/alt sample dots.
// Its twinkles and rotating visual scan are NOT celestial motion, new
// observations, a complete sky map, or a live camera view. Hubble archive
// frames are photographs of unrelated clusters, not the current local sky.
Item {
    id: visual
    objectName: "cosmos-c32-stars-visual"
    clip: true

    property bool playing: true
    property bool showArchive: false
    property real scanPhase: 0
    property int archiveIndex: 0
    property real zoom: 1
    property real panX: 0
    property real panY: 0
    readonly property bool motionRunning: scanDriver.running
    readonly property bool galleryRunning: galleryDriver.running
    readonly property var archiveFrames: [
        {
            name: "MESSIER 3",
            credit: "NASA / ESA · HUBBLE",
            url: "https://assets.science.nasa.gov/content/dam/science/missions/hubble/stars/globular-clusters/Hubble_M3_2019_potw1914a.jpg/jcr%3Acontent/renditions/cq5dam.web.1280.1280.jpeg"
        },
        {
            name: "MESSIER 28",
            credit: "ESA / HUBBLE",
            url: "https://cdn.esahubble.org/archives/images/large/potw1910a.jpg"
        }
    ]
    readonly property var archiveFrame: archiveFrames[archiveIndex]

    function resetPhoto() {
        zoom = 1;
        panX = 0;
        panY = 0;
    }
    function zoomTo(next) {
        zoom = Math.max(1,Math.min(3,Number(next)));
        if (zoom === 1) {
            panX=0;
            panY=0;
        }
    }
    function nextArchive() {
        archiveIndex = (archiveIndex+1)%archiveFrames.length;
        resetPhoto();
    }
    onShowArchiveChanged: resetPhoto()

    Timer {
        id: scanDriver
        objectName: "cosmos-c32-star-scan-driver"
        interval: 110
        repeat: true
        running: visual.visible && visual.playing && !visual.showArchive
        onTriggered: {
            visual.scanPhase = (visual.scanPhase+0.019)%1;
            starfield.requestPaint();
        }
    }
    Timer {
        id: galleryDriver
        objectName: "cosmos-c32-star-gallery-driver"
        interval: 10000
        repeat: true
        running: visual.visible && visual.playing && visual.showArchive
        onTriggered: visual.nextArchive()
    }
    Canvas {
        id: starfield
        objectName: "cosmos-c32-moving-star-field"
        anchors.fill: parent
        visible: !visual.showArchive
        renderStrategy: Canvas.Immediate
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx=getContext("2d");
            const w=width, h=height;
            ctx.clearRect(0,0,w,h);
            if (w<2 || h<2) return;
            ctx.fillStyle="#100719";
            ctx.fillRect(0,0,w,h);

            // This background is decorative; source stars are separate QML
            // rectangles positioned by the original C27 true azimuth and
            // altitude calculations.
            for (let k=0;k<48;k++) {
                const x=((k*0.61803398875+0.19)%1)*w;
                const y=((k*0.75487766625+0.37)%1)*h;
                const twinkle=0.5+0.5*Math.sin(visual.scanPhase*6.283*4+k*1.8);
                ctx.globalAlpha=0.12+twinkle*0.38;
                ctx.fillStyle=k%8===0?"#F2BE4E":"#BBD6F0";
                const size=k%9===0?1.6:0.9;
                ctx.fillRect(x,y,size,size);
            }
            const r=Math.min(96,Math.max(40,h-18))/2-10;
            const cx=w/2;
            const cy=h-4-Math.min(96,Math.max(40,h-18))/2;
            const az=visual.scanPhase*2*Math.PI;
            for (let k=3;k>=0;k--) {
                const a=az-k*0.12;
                ctx.globalAlpha=(4-k)/4*0.28;
                ctx.strokeStyle="#55CFCA";
                ctx.lineWidth=k===0?1.3:0.8;
                ctx.beginPath();
                ctx.moveTo(cx,cy);
                ctx.lineTo(cx+Math.sin(a)*r,cy-Math.cos(a)*r);
                ctx.stroke();
            }
            ctx.globalAlpha=0.7;
            ctx.strokeStyle="#5B5FD4";
            ctx.lineWidth=0.8;
            ctx.beginPath();
            ctx.arc(cx,cy,Math.max(1,r),0,2*Math.PI);
            ctx.stroke();
            ctx.globalAlpha=1;
        }
    }

    Image {
        id: archivePhoto
        objectName: "cosmos-c32-hubble-archive-photo"
        source: visual.showArchive ? visual.archiveFrame.url : ""
        asynchronous: true
        cache: true
        smooth: true
        fillMode: Image.PreserveAspectCrop
        width: Math.max(1,visual.width*visual.zoom)
        height: Math.max(1,visual.height*visual.zoom)
        x: (visual.width-width)/2+visual.panX
        y: (visual.height-height)/2+visual.panY
        visible: visual.showArchive && status===Image.Ready
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 16
        color: "#CF1B0623"
        z: 2
        QuietText {
            anchors.fill: parent
            anchors.margins: 3
            text: !visual.showArchive
                ? "ARTISTIC SCAN // USNO DOTS = SNAPSHOT"
                : archivePhoto.status===Image.Ready
                    ? visual.archiveFrame.name+" // "+visual.archiveFrame.credit
                    : "HUBBLE ARCHIVE OFFLINE"
            color: Colors.yellow
            font.pixelSize: 7
            elide: Text.ElideRight
        }
    }
    MouseArea {
        anchors.fill: parent
        enabled: visual.showArchive && archivePhoto.status===Image.Ready
        cursorShape: visual.zoom>1?Qt.OpenHandCursor:Qt.PointingHandCursor
        property real downX: 0
        property real downY: 0
        property real originalX: 0
        property real originalY: 0
        onPressed: function(mouse) {
            downX=mouse.x;
            downY=mouse.y;
            originalX=visual.panX;
            originalY=visual.panY;
        }
        onPositionChanged: function(mouse) {
            if(!pressed||visual.zoom<=1)return;
            const maxX=visual.width*(visual.zoom-1)/2;
            const maxY=visual.height*(visual.zoom-1)/2;
            visual.panX=Math.max(-maxX,Math.min(maxX,originalX+mouse.x-downX));
            visual.panY=Math.max(-maxY,Math.min(maxY,originalY+mouse.y-downY));
        }
        onWheel: function(wheel) {
            if(wheel.angleDelta.y===0)return;
            visual.zoomTo(visual.zoom+(wheel.angleDelta.y>0?0.25:-0.25));
            wheel.accepted=true;
        }
        onDoubleClicked: visual.resetPhoto()
    }
}
