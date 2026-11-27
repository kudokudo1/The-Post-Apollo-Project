import QtQuick

// Passive mounting plate. Clearance is per side in local logical pixels.
Item {
    id: root
    property real faceDiameter: 106
    property real clearance: 10
    property string chassisStyle: "square"
    property bool showScrews: true
    property color structuralColor: Colors.cyan
    // Approved cyan gunmetal. The finish is independent of the dial accent.
    property color screwColor: "#40899b"
    // Semantic finishes blend 75% toward the selected hue from gunmetal.
    // Set 1.0 for an exact legacy/custom metal tone.
    property real screwColorStrength: 0.75
    readonly property real boundedScrewColorStrength: Number.isFinite(screwColorStrength) ? Math.max(0,Math.min(1,screwColorStrength)) : 0.75
    readonly property real screwShadow: 0.75
    readonly property real screwDirectLight: 0.20
    readonly property real screwReflectedLight: 0.10
    readonly property real screwCatchlight: 0.40
    readonly property real screwRecessDepth: 0.14
    // Map the approved palette to a caller-selected metal color. Alpha is
    // deliberately ignored: these are opaque metal surfaces, not glow.
    function screwTone(r,g,b) {
        const t=boundedScrewColorStrength;
        return Qt.rgba(Math.min(1,((64/255)*(1-t)+screwColor.r*t)*r/64),
                       Math.min(1,((137/255)*(1-t)+screwColor.g*t)*g/137),
                       Math.min(1,((155/255)*(1-t)+screwColor.b*t)*b/155),1);
    }
    function screwLightingAngle(x,y) {
        return Math.atan2(height/2-y,width/2-x)-Math.PI/4;
    }
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
            function onScrewColorChanged() { plate.requestPaint() }
            function onScrewColorStrengthChanged() { plate.requestPaint() }
            function onScrewDiameterChanged() { plate.requestPaint() }
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
                // Normalized approved 26-unit head, drawn at actual size.
                // The seat, outer head, wall and floor descend into the plate.
                // All local lighting rotates inward; the final catchlight
                // remains at screen top-right on every fastener.
                c.save();
                c.translate(x,y);
                c.rotate(root.screwLightingAngle(x,y));
                const u=rad/13, head=12.5*u, wall=10.8*u;
                const floor=(10.8-10*root.screwRecessDepth)*u;
                function disk(radius,fill,stroke,strokeWidth) {
                    c.beginPath(); c.arc(0,0,radius,0,2*Math.PI);
                    c.fillStyle=fill; c.fill();
                    if(stroke) { c.strokeStyle=stroke; c.lineWidth=strokeWidth; c.stroke(); }
                }
                function metal(radius,stops) {
                    const g=c.createLinearGradient(-radius,-radius,radius,radius);
                    for(const p of stops) g.addColorStop(p[0],root.screwTone(p[1],p[2],p[3]));
                    return g;
                }
                function lip(radius,a,b,ink,alpha,width) {
                    c.beginPath(); c.arc(0,0,radius,a,b);
                    c.globalAlpha=alpha; c.strokeStyle=ink; c.lineWidth=width; c.stroke(); c.globalAlpha=1;
                }
                function cross(half,arm,fill) {
                    c.beginPath();
                    c.moveTo(-half,-arm); c.lineTo(half,-arm);
                    c.lineTo(half,-half); c.lineTo(arm,-half);
                    c.lineTo(arm,half); c.lineTo(half,half);
                    c.lineTo(half,arm); c.lineTo(-half,arm);
                    c.lineTo(-half,half); c.lineTo(-arm,half);
                    c.lineTo(-arm,-half); c.lineTo(-half,-half);
                    c.closePath(); c.fillStyle=fill; c.fill();
                }
                const fine=Math.max(0.35,0.7*u);
                disk(rad,"#101b21","#34494f",Math.max(0.35,0.5*u));
                disk(head,metal(head,[[0,64,137,155],[0.4,47,101,117],[1,27,62,72]]));
                disk(wall,metal(wall,[[0,13,34,44],[0.45,25,63,76],[1,50,109,126]]),"#080e13",fine);
                disk(floor,metal(floor,[[0,43,94,110],[0.55,32,75,89],[1,27,62,72]]),"#0c151b",fine);
                // Preserve the native minimum legible cross at compact sizes.
                const half=root.screwSlotWidth/2, arm=Math.max(6*u,half+0.6);
                cross(half+0.45*u,arm+0.8*u,root.screwTone(15,41,51));
                cross(half,arm,metal(arm,[[0,5,9,13],[0.6,11,30,38],[1,25,66,79]]));
                // One continuous shadow over every level, including the slot.
                const shade=c.createLinearGradient(-head,-head,head,head);
                shade.addColorStop(0,"rgba(8,14,19,0)");
                shade.addColorStop(0.35,"rgba(8,14,19,0.04)");
                shade.addColorStop(0.7,Qt.rgba(8/255,14/255,19/255,root.screwShadow/2));
                shade.addColorStop(1,Qt.rgba(8/255,14/255,19/255,root.screwShadow));
                disk(head,shade);
                lip(10.2*u,Math.PI*1.06,Math.PI*1.44,"#a3d9df",root.screwDirectLight,fine);
                lip(12.2*u,0.16,Math.PI/2-0.16,"#91c2cb",root.screwReflectedLight,fine);
                lip(10.2*u,0.20,Math.PI/2-0.20,"#91c2cb",root.screwReflectedLight,fine);
                c.beginPath(); c.moveTo(-arm,-half); c.lineTo(-half,-half); c.lineTo(-half,-arm);
                c.strokeStyle="#91c2cb"; c.lineWidth=fine; c.globalAlpha=root.screwDirectLight; c.stroke();
                c.beginPath(); c.moveTo(half,arm); c.lineTo(half,half); c.lineTo(arm,half);
                c.globalAlpha=root.screwReflectedLight; c.stroke(); c.globalAlpha=1;
                c.restore();
                // Fixed screen-space top-right catchlight; no external glow.
                c.save(); c.translate(x,y);
                lip(12.2*u,-0.92,-0.65,"#dcf3fa",root.screwCatchlight,Math.max(0.45,0.85*u));
                lip(10.1*u,-0.92,-0.65,"#b7dfe7",root.screwCatchlight/2.3,fine);
                c.beginPath(); c.moveTo(half,-arm); c.lineTo(half,-half); c.lineTo(arm,-half);
                c.strokeStyle="#a3d9df"; c.lineWidth=fine; c.globalAlpha=root.screwCatchlight/3; c.stroke();
                c.restore();
            }
        }
    }
}
