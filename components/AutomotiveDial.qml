import QtQuick

// Passive automotive instrument; caller owns time, values, and interaction.
// Design radius 108; arm envelope <=95, including its border.
Item {
    id: root
    property string armStyle: "tapered"
    property real armReach: 95
    property string gaugeStyle: "segmented"
    property string scaleStyle: "ticks"
    property string chassisStyle: "square"
    property real chassisClearance: 10
    property bool showChassis: true
    property bool showScrews: true
    property color screwColor: "#40899b"
    property bool showGlow: true
    property bool showValue: true
    property bool showSetValue: true
    // Caller may provide an unobstructed external value/unit readout.
    property bool externalUnitReadout: false
    property color accentColor: Colors.orange
    property color structuralColor: Colors.cyan
    property real faceDiameter: 116
    property real fraction: 1
    property real rotationDegrees: 360*boundedFraction
    property bool flash: false
    property string valueText: "0"
    property string valueUnit: ""
    property string setText: ""
    property string compactSetText: setText
    property real scaleMinimum: 0
    property real scaleMaximum: 5
    readonly property string resolvedArmStyle: ["tapered","industrial","capsule"].includes(armStyle) ? armStyle : "tapered"
    readonly property real boundedFraction: Number.isFinite(fraction) ? Math.max(0,Math.min(1,fraction)) : 0
    readonly property real boundedArmReach: Number.isFinite(armReach) ? Math.max(65,Math.min(95,armReach)) : 95
    readonly property int litSegments: Math.ceil(segmentCount*boundedFraction)
    readonly property real actualFaceDiameter: Math.max(0,Math.min(faceDiameter,Math.min(width,height)-(showChassis?2*Math.max(0,Math.min(40,chassisClearance)):0)))
    readonly property real faceUnit: actualFaceDiameter/216
    readonly property real insetRadius: Math.max(0,70*faceUnit-1)
    readonly property real minimumSegmentGap: 2
    // Width is computed from the actual chamfer vertices, not a rectangle
    // percentage. Both readout frames fit inside the innermost visible ring.
    function insetWindow(lower) {
        const u=faceUnit, r=insetRadius;
        const inner=Math.ceil(Math.max(4,17*u)+1);
        const available=Math.max(0,r-inner-1);
        const h=Math.max(0,Math.floor(Math.min(available,lower?Math.max(12,actualFaceDiameter*0.12):Math.max(12,actualFaceDiameter*0.17))));
        const outer=inner+h;
        const cut=Math.min(Math.floor(h/3),Math.max(2,Math.round(h*0.18)));
        const chord=y=>Math.sqrt(Math.max(0,r*r-y*y));
        const half=Math.max(0,Math.min(chord(outer)+cut,chord(outer-cut))-0.5);
        const w=Math.max(0,2*Math.floor(half));
        return {width:w,height:h,cut:cut,y:actualFaceDiameter/2+(lower?inner:-outer)};
    }
    readonly property var upperGeometry: insetWindow(false)
    readonly property var lowerGeometry: insetWindow(true)
    function insetWindowFits(g) {
        if(g.width<=0||g.height<=0)return false;
        const half=g.width/2, outer=Math.max(Math.abs(g.y-actualFaceDiameter/2),Math.abs(g.y+g.height-actualFaceDiameter/2));
        return Math.hypot(half-g.cut,outer)<=insetRadius+0.01
            && Math.hypot(half,outer-g.cut)<=insetRadius+0.01;
    }
    readonly property string detailTier: actualFaceDiameter>=150?"large":actualFaceDiameter>=105?"medium":actualFaceDiameter>=72?"small":"compact"
    readonly property int segmentCount: detailTier==="large"?30:detailTier==="medium"?24:detailTier==="small"?18:12
    readonly property int tickCount: detailTier==="large"?60:detailTier==="medium"?30:12
    readonly property int teethCount: detailTier==="large"?60:detailTier==="medium"?40:detailTier==="small"?24:12
    readonly property int valuePixelSize: Math.max(12,Math.round(actualFaceDiameter*0.18))
    readonly property int unitPixelSize: Math.max(9,Math.round(actualFaceDiameter*0.085))
    readonly property color liveColor: flash ? Colors.white : accentColor
    implicitWidth: faceDiameter + (showChassis ? 2*Math.max(0,Math.min(40,chassisClearance)) : 0)
    implicitHeight: implicitWidth
    width: implicitWidth
    height: implicitHeight

    InstrumentChassis {
        anchors.centerIn: parent
        visible: root.showChassis
        faceDiameter: root.actualFaceDiameter
        clearance: root.chassisClearance
        chassisStyle: root.chassisStyle
        showScrews: root.showScrews
        screwColor: root.screwColor
        structuralColor: root.structuralColor
    }

    Item {
        id: face
        objectName: "selectorStopwatchFace"
        anchors.centerIn: parent
        width: root.actualFaceDiameter; height: width
        visible: width>0
        Canvas {
            id: gauge
            objectName: "automotiveGauge"
            anchors.fill: parent
            property bool hasPainted: false
            onPainted: hasPainted = true
            onAvailableChanged: if (available) requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            Connections {
                target: root
                function onBoundedFractionChanged() { gauge.requestPaint() }
                function onLiveColorChanged() { gauge.requestPaint() }
                function onAccentColorChanged() { gauge.requestPaint() }
                function onStructuralColorChanged() { gauge.requestPaint() }
                function onGaugeStyleChanged() { gauge.requestPaint() }
                function onScaleStyleChanged() { gauge.requestPaint() }
                function onScaleMinimumChanged() { gauge.requestPaint() }
                function onScaleMaximumChanged() { gauge.requestPaint() }
                function onShowGlowChanged() { gauge.requestPaint() }
            }
            onPaint: {
                const c=getContext("2d"), tau=2*Math.PI, f=root.boundedFraction;
                c.reset(); c.clearRect(0,0,width,height);
                if(width<=0)return;
                const u=width/216;
                c.translate(width/2,height/2); c.scale(u,u);
                function ring(r,fill,stroke,w) {
                    c.beginPath(); c.arc(0,0,r,0,tau);
                    if(fill) {c.fillStyle=fill;c.fill();}
                    if(stroke) {c.strokeStyle=stroke;c.lineWidth=Math.max(w,0.85/u);c.stroke();}
                }
                function arc(r,w,color,amount) {
                    if(amount<=0)return;
                    c.beginPath(); c.arc(0,0,r,-Math.PI/2,-Math.PI/2+tau*amount);
                    c.strokeStyle=color;c.lineWidth=w;c.stroke();
                }
                ring(107,"#09060e","#78858a",1);
                if(root.showGlow) {
                    c.globalAlpha=0.1; ring(104,null,root.accentColor,6); c.globalAlpha=1;
                }
                ring(103,null,root.accentColor,1.5);
                if(root.gaugeStyle==="continuous" || root.gaugeStyle==="dualRail") {
                    const rails=root.gaugeStyle==="dualRail" ? [89,99] : [93];
                    for(const r of rails) {
                        const w=root.gaugeStyle==="dualRail" ? 5 : 14;
                        arc(r,w,"#39283f",1); arc(r,w,root.liveColor,f);
                    }
                    if(root.gaugeStyle==="dualRail") for(let i=0;i<root.segmentCount;i++){
                        c.save();c.rotate(i*tau/root.segmentCount);c.fillStyle="#09060e";const gap=Math.max(2,1/u);c.fillRect(-gap/2,-102,gap,16);c.restore();
                    }
                } else {
                    const teeth=root.gaugeStyle==="radialTeeth", n=teeth?root.teethCount:root.segmentCount;
                    for(let i=0;i<n;i++) {
                        c.save();c.rotate(i*tau/n);
                        c.fillStyle=i<Math.ceil(f*n)?root.liveColor:"#39283f";
                        const major=i%Math.max(1,Math.floor(n/12))===0;
                        if(teeth) {
                            const w=Math.max(major?5:2.8,1.1/u);
                            c.fillRect(-w/2,-100,w,major?17:10);
                        } else {
                            // True annular sectors with a constant actual-pixel
                            // gap at BOTH the inner and outer edges.
                            const pitch=tau/n, outer=100, inner=85;
                            const go=Math.min(pitch*0.40,root.minimumSegmentGap/(outer*u))/2;
                            const gi=Math.min(pitch*0.40,root.minimumSegmentGap/(inner*u))/2;
                            const mid=-Math.PI/2;
                            c.beginPath();
                            c.arc(0,0,outer,mid-pitch/2+go,mid+pitch/2-go);
                            c.arc(0,0,inner,mid+pitch/2-gi,mid-pitch/2+gi,true);
                            c.closePath();c.fill();
                        }
                        c.restore();
                    }
                }
                ring(82,null,root.structuralColor,1);
                if(root.detailTier==="large" || root.detailTier==="medium") ring(79,null,"#78858a",0.8);
                ring(70,"#120c19",root.accentColor,0.8);
                // Radius 70 is the clear mechanical/display boundary.
                if(root.scaleStyle!=="none") for(let i=0;i<root.tickCount;i++){
                    const major=root.tickCount<=12 || i%Math.max(1,Math.floor(root.tickCount/12))===0;
                    const tickWidth=Math.max(major?2:1.2,(major?1.25:0.8)/u);
                    c.save();c.rotate(i*tau/root.tickCount);c.fillStyle=major?Colors.white:root.accentColor;
                    c.globalAlpha=major?1:0.75;c.fillRect(-tickWidth/2,-79,tickWidth,major?8:4);c.restore();
                }
                if(root.scaleStyle==="numbers" || root.scaleStyle==="sparse"){
                    const n=root.scaleStyle==="sparse"||root.detailTier==="small"||root.detailTier==="compact"?3:5;
                    c.fillStyle=Colors.white;c.font=Math.max(12,9/u)+"px monospace";c.textAlign="center";c.textBaseline="middle";
                    for(let i=0;i<n;i++){
                        const a=i*tau/n;
                        c.fillText(String(Number((root.scaleMinimum+(root.scaleMaximum-root.scaleMinimum)*i/n).toFixed(2))),55*Math.sin(a),-55*Math.cos(a));
                    }
                }
            }
        }
        // The two plates are positioned using the circle chord at each
        // chamfer vertex. The arm intentionally remains in front of both.
        Item {
            id: valueWindow
            objectName: "automotiveValueWindow"
            visible: root.showValue && root.insetWindowFits(root.upperGeometry)
            width: root.upperGeometry.width
            height: root.upperGeometry.height
            anchors.horizontalCenter: parent.horizontalCenter
            y: root.upperGeometry.y
            readonly property bool inlineUnit: root.valueUnit!=="" &&
                width>=unitMeasure.advanceWidth+Math.max(22,root.valuePixelSize*1.1)+5
            readonly property bool stackedUnit: root.valueUnit!=="" && !inlineUnit && !root.externalUnitReadout
            readonly property real unitWidth: inlineUnit ? Math.ceil(unitMeasure.advanceWidth)+2 : 0
            readonly property real unitHeight: stackedUnit ? Math.min(height/2,root.unitPixelSize+2) : 0
            TextMetrics {
                id: unitMeasure
                font.family: unitLabel.font.family
                font.pixelSize: root.unitPixelSize
                text: root.valueUnit
            }
            Canvas {
                id: valueFrame
                anchors.fill: parent
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onAvailableChanged: if(available) requestPaint()
                Connections {target: root; function onAccentColorChanged(){valueFrame.requestPaint()}}
                onPaint: {
                    const c=getContext("2d"); c.reset();c.clearRect(0,0,width,height);
                    function cut(m,k,fill,stroke){
                        const x=m,y=m,b=width-m,d=height-m;
                        if(b-x<=2*k || d-y<=2*k)return;
                        c.beginPath();c.moveTo(x+k,y);c.lineTo(b-k,y);c.lineTo(b,y+k);
                        c.lineTo(b,d-k);c.lineTo(b-k,d);c.lineTo(x+k,d);c.lineTo(x,d-k);c.lineTo(x,y+k);c.closePath();
                        c.fillStyle=fill;c.fill();c.strokeStyle=stroke;c.lineWidth=1;c.stroke();
                    }
                    cut(0.5,root.upperGeometry.cut,"#33263d","#78858a");
                    cut(1.5,Math.max(1,root.upperGeometry.cut-1),"#07040b",root.accentColor);
                }
            }
            GohuText {
                id: valueLabel
                objectName: "selectorStopwatchCenter"
                x: 2; y: 1
                width: Math.max(0,parent.width-4-parent.unitWidth)
                height: Math.max(0,parent.height-2-parent.unitHeight)
                text: root.valueText
                color: root.liveColor
                font.pixelSize: root.valuePixelSize
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                fontSizeMode: Text.Fit
                minimumPixelSize: 9
                clip: true
            }
            GohuText {
                id: unitLabel
                objectName: "automotiveValueUnit"
                visible: parent.inlineUnit || parent.stackedUnit
                x: parent.inlineUnit ? parent.width-parent.unitWidth-1 : 2
                y: parent.inlineUnit ? 1 : parent.height-parent.unitHeight-1
                width: parent.inlineUnit ? parent.unitWidth : Math.max(0,parent.width-4)
                height: parent.inlineUnit ? Math.max(0,parent.height-2) : parent.unitHeight
                text: root.valueUnit; color: Colors.white; font.pixelSize: root.unitPixelSize
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                fontSizeMode: Text.Fit
                minimumPixelSize: 8
                clip: true
            }
        }
        Item {
            id: setWindow
            objectName: "automotiveSetWindow"
            visible: root.showSetValue && root.setText!=="" && root.insetWindowFits(root.lowerGeometry)
            width: root.lowerGeometry.width
            height: root.lowerGeometry.height
            anchors.horizontalCenter: parent.horizontalCenter
            y: root.lowerGeometry.y
            Canvas {
                id: setFrame
                anchors.fill: parent
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onAvailableChanged: if(available) requestPaint()
                Connections {target:root; function onStructuralColorChanged(){setFrame.requestPaint()}}
                onPaint: {
                    const c=getContext("2d"),k=root.lowerGeometry.cut,b=width-0.5,d=height-0.5;
                    c.reset();c.clearRect(0,0,width,height);
                    c.beginPath();c.moveTo(k+0.5,0.5);c.lineTo(b-k,0.5);c.lineTo(b,k+0.5);c.lineTo(b,d-k);c.lineTo(b-k,d);c.lineTo(k+0.5,d);c.lineTo(0.5,d-k);c.lineTo(0.5,k+0.5);c.closePath();
                    c.fillStyle="#09060e";c.fill();c.strokeStyle=root.structuralColor;c.lineWidth=1;c.stroke();
                }
            }
            GohuText {
                objectName: "automotiveSetText"
                anchors.fill: parent; anchors.leftMargin: 2; anchors.rightMargin: 2
                anchors.topMargin: 1; anchors.bottomMargin: 1
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                text: root.detailTier==="small"||root.detailTier==="compact" ? root.compactSetText : root.setText
                textFormat: Text.RichText; color: root.accentColor
                font.pixelSize: Math.max(9,Math.round(face.width*0.09))
                fontSizeMode: Text.Fit; minimumPixelSize: 8
                elide: Text.ElideRight
                clip: true
            }
        }
        Item {
            objectName: "selectorStopwatchHand"
            anchors.fill: parent
            rotation: root.rotationDegrees
            Canvas {
                id: arm
                objectName: "automotiveArm"
                anchors.fill: parent
                property bool hasPainted: false
                onPainted: hasPainted = true
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onAvailableChanged: if(available) requestPaint()
                Connections {
                    target: root
                    function onArmStyleChanged() {arm.requestPaint()}
                    function onBoundedArmReachChanged() {arm.requestPaint()}
                    function onLiveColorChanged() {arm.requestPaint()}
                }
                onPaint: {
                    const c=getContext("2d");
                    c.reset();c.clearRect(0,0,width,height);
                    if(width<=0)return;
                    const u=width/216;
                    const r=Math.max(1,root.boundedArmReach-Math.max(2,0.4/u+1));
                    c.translate(width/2,height/2);c.scale(u,u);
                    const tapered=root.resolvedArmStyle==="tapered";
                    const half=root.resolvedArmStyle==="industrial"?14:11;
                    const tip=Math.sqrt(r*r-half*half);
                    function body(offset) {
                        c.beginPath();
                        if(tapered) {
                            c.moveTo(-14,0+offset);c.lineTo(-7,-r+12+offset);
                            c.quadraticCurveTo(0,-r-12+offset,7,-r+12+offset);c.lineTo(14,0+offset);c.closePath();
                        } else {
                            const k=root.resolvedArmStyle==="industrial"?3:half;
                            c.moveTo(-half,-tip+k+offset);c.quadraticCurveTo(-half,-tip+offset,-half+k,-tip+offset);
                            c.lineTo(half-k,-tip+offset);c.quadraticCurveTo(half,-tip+offset,half,-tip+k+offset);
                            c.lineTo(half,offset);c.lineTo(-half,offset);c.closePath();
                        }
                    }
                    body(3);c.fillStyle="#647178";c.fill();
                    body(0);c.fillStyle="#d4dfe3";c.fill();c.strokeStyle="#97a6ad";c.lineWidth=Math.max(1,0.8/u);c.stroke();
                    c.fillStyle="#30323c";
                    if(tapered) {
                        c.beginPath();c.moveTo(0,-r+9);c.lineTo(5,-r+21);c.lineTo(8,-35);c.lineTo(-8,-35);c.lineTo(-5,-r+21);c.closePath();c.fill();
                        c.beginPath();c.moveTo(0,-r+15);c.lineTo(3,-r+23);c.lineTo(5,-39);c.lineTo(-5,-39);c.lineTo(-3,-r+23);c.closePath();c.fillStyle=root.liveColor;c.fill();
                    } else {
                        c.fillRect(-half+4,-tip+6,2*half-8,tip-39);
                        c.fillStyle=root.liveColor;c.fillRect(-half+7,-tip+9,2*half-14,tip-45);
                    }
                    c.strokeStyle="#78858a";c.lineWidth=2;
                    for(const y of (root.detailTier==="large"||root.detailTier==="medium"?[-27,-21,-15]:[-22])){c.beginPath();c.moveTo(-7,y);c.lineTo(7,y);c.stroke();}
                }
            }
        }
        Rectangle {
            anchors.centerIn: parent; width:Math.max(8,34*root.faceUnit); height:width; radius:width/2
            color:"#78858a";border.color:"#b2c0c4"
            Rectangle {
                anchors.centerIn:parent; width:parent.width*0.70;height:width;radius:width/2
                color:"#241a29";border.color:"#d4dfe3"
                Rectangle {anchors.centerIn:parent;width:parent.width*0.58;height:width;radius:width/2;color:"#09060e";border.color:root.accentColor;border.width:2}
            }
        }
    }
}
