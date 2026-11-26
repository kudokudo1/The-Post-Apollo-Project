import QtQuick

// Passive mounting plate. Clearance is per side in local logical pixels.
Item {
    id: root
    property real faceDiameter: 106
    property real clearance: 10
    property string chassisStyle: "square"
    property bool showScrews: true
    property color structuralColor: Colors.cyan
    readonly property real safeClearance: Math.max(0, Math.min(40, clearance))
    implicitWidth: faceDiameter + 2*safeClearance
    implicitHeight: implicitWidth
    width: implicitWidth
    height: implicitHeight
    objectName: "instrumentChassis"

    Canvas {
        id: plate
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onAvailableChanged: if (available) requestPaint()
        Connections {
            target: root
            function onChassisStyleChanged() { plate.requestPaint() }
            function onShowScrewsChanged() { plate.requestPaint() }
            function onStructuralColorChanged() { plate.requestPaint() }
        }
        onPaint: {
            const c=getContext("2d");
            c.reset(); c.clearRect(0,0,width,height);
            const w=width, h=height;
            function outline(inset) {
                const x=inset,y=inset,b=w-inset,d=h-inset;
                const k=Math.min(5,(b-x)/8,(d-y)/8);
                c.beginPath();
                if(root.chassisStyle==="chamfered") {
                    c.moveTo(x+k,y); c.lineTo(b-k,y); c.lineTo(b,y+k);
                    c.lineTo(b,d-k); c.lineTo(b-k,d); c.lineTo(x+k,d);
                    c.lineTo(x,d-k); c.lineTo(x,y+k);
                } else if(root.chassisStyle==="rounded") {
                    c.moveTo(x+k,y); c.lineTo(b-k,y); c.quadraticCurveTo(b,y,b,y+k);
                    c.lineTo(b,d-k); c.quadraticCurveTo(b,d,b-k,d);
                    c.lineTo(x+k,d); c.quadraticCurveTo(x,d,x,d-k);
                    c.lineTo(x,y+k); c.quadraticCurveTo(x,y,x+k,y);
                } else { c.rect(x,y,b-x,d-y); }
                c.closePath();
            }
            outline(0.75); c.fillStyle="#201526"; c.fill();
            c.strokeStyle="#78858a"; c.lineWidth=1; c.stroke();
            outline(2.5); c.strokeStyle=root.structuralColor; c.globalAlpha=0.28; c.lineWidth=0.7; c.stroke(); c.globalAlpha=1;
            if (!root.showScrews) return;
            const p=Math.min(7,w/8,h/8), rad=Math.min(3.5,p-1);
            for(const x of [p,w-p]) for(const y of [p,h-p]) {
                c.beginPath(); c.arc(x,y+0.6,rad+0.4,0,2*Math.PI); c.fillStyle="#08050c"; c.fill();
                c.beginPath(); c.arc(x,y,rad,0,2*Math.PI); c.fillStyle="#17121e"; c.fill(); c.strokeStyle=root.structuralColor; c.lineWidth=0.65; c.stroke();
                c.beginPath(); c.arc(x,y,rad*0.66,0,2*Math.PI); c.fillStyle="#78858a"; c.fill();
                c.beginPath(); c.moveTo(x-rad*0.45,y); c.lineTo(x+rad*0.45,y); c.moveTo(x,y-rad*0.45); c.lineTo(x,y+rad*0.45); c.strokeStyle="#09060e"; c.lineWidth=0.9; c.stroke();
            }
        }
    }
}
