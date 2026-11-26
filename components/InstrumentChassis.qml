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
    readonly property real screwDiameter: Math.min(11, Math.max(8, Math.round(Math.min(width,height)*0.09)))
    readonly property real screwSlotWidth: Math.max(1.5, Math.round(screwDiameter*0.20))
    // Centre the fasteners farther inside the border, but keep the complete
    // head outside the circular instrument. No screws on impossible mounts.
    readonly property real screwInset: Math.max(0,Math.min(screwDiameter/2+5,
        Math.min(width,height)/2-(faceDiameter/2+screwDiameter/2+1)/Math.SQRT2))
    readonly property real screwEdgeClearance: screwInset-screwDiameter/2
    readonly property bool screwsFit: screwEdgeClearance>=2.5
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
            function onScrewInsetChanged() { plate.requestPaint() }
            function onScrewsFitChanged() { plate.requestPaint() }
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
            if (!root.showScrews || !root.screwsFit) return;
            const rad=root.screwDiameter/2;
            const p=root.screwInset;
            for(const x of [p,w-p]) for(const y of [p,h-p]) {
                // One light source, upper left. Keep the metal face subdued,
                // a restrained catchlight and an opposing contact shadow.
                c.beginPath(); c.arc(x+0.35,y+0.55,rad+0.45,0,2*Math.PI); c.fillStyle="#08050c"; c.fill();
                const metal=c.createLinearGradient(x-rad,y-rad,x+rad,y+rad);
                metal.addColorStop(0,"#e1e9ed"); metal.addColorStop(0.38,"#b7c5cb");
                metal.addColorStop(0.72,"#81919b"); metal.addColorStop(1,"#9aabb3");
                c.beginPath(); c.arc(x,y,rad,0,2*Math.PI); c.fillStyle=metal; c.fill();
                c.strokeStyle="#64737c"; c.lineWidth=0.65; c.stroke();
                c.beginPath(); c.arc(x,y,rad-0.45,Math.PI*1.03,Math.PI*1.62);
                c.strokeStyle="#f2f8fb"; c.lineWidth=0.9; c.stroke();
                c.beginPath(); c.arc(x,y,rad-0.5,0.08,Math.PI*0.48);
                c.strokeStyle="#a7bac4"; c.lineWidth=0.65; c.stroke();
                const slot=root.screwSlotWidth, span=rad*1.42;
                c.fillStyle="#20212a";
                c.fillRect(x-span/2,y-slot/2,span,slot);
                c.fillRect(x-slot/2,y-span/2,slot,span);
                // The recessed slot catches a little light on the opposite lip.
                c.beginPath(); c.moveTo(x+slot/2,y+slot/2);c.lineTo(x+span/2,y+slot/2);
                c.moveTo(x+slot/2,y+slot/2);c.lineTo(x+slot/2,y+span/2);
                c.strokeStyle="#d5dfe3";c.lineWidth=0.55;c.stroke();
            }
        }
    }
}
