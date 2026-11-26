import QtQuick

// Passive mounting plate. Clearance is per side in local logical pixels.
Item {
    id: root
    property real faceDiameter: 106
    property real clearance: 10
    property string chassisStyle: "square"
    property bool showScrews: true
    property color structuralColor: Colors.cyan
    // The cross is deliberately larger than a decorative rivet.
    readonly property real screwDiameter: Math.min(12, Math.max(8, Math.round(Math.min(width,height)*0.105)))
    readonly property real screwSlotWidth: Math.max(1.5, Math.round(screwDiameter*0.20))
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
            const rad=root.screwDiameter/2;
            const p=Math.min(Math.max(rad+2,8),w/4,h/4);
            for(const x of [p,w-p]) for(const y of [p,h-p]) {
                c.beginPath(); c.arc(x,y+0.6,rad+0.5,0,2*Math.PI); c.fillStyle="#08050c"; c.fill();
                c.beginPath(); c.arc(x,y,rad,0,2*Math.PI); c.fillStyle="#b5c2c9"; c.fill();
                c.strokeStyle="#526069"; c.lineWidth=0.8; c.stroke();
                // High-contrast, square-ended Phillips recess, not a pinhole.
                const slot=root.screwSlotWidth, span=rad*1.42;
                c.fillStyle="#17121e";
                c.fillRect(x-span/2,y-slot/2,span,slot);
                c.fillRect(x-slot/2,y-span/2,slot,span);
                c.beginPath(); c.arc(x,y,rad-0.8,Math.PI,Math.PI*1.5);
                c.strokeStyle="#edf5f8"; c.lineWidth=0.8; c.stroke();
            }
        }
    }
}
