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
    property bool showGlow: true
    property bool showValue: true
    property bool showSetValue: true
    property color accentColor: Colors.orange
    property color structuralColor: Colors.cyan
    property real faceDiameter: 116
    property real fraction: 1
    property real rotationDegrees: 360*boundedFraction
    property bool flash: false
    property string valueText: "0"
    property string valueUnit: ""
    property string setText: ""
    property real scaleMinimum: 0
    property real scaleMaximum: 5
    readonly property string resolvedArmStyle: ["tapered","industrial","capsule"].includes(armStyle) ? armStyle : "tapered"
    readonly property real boundedFraction: Number.isFinite(fraction) ? Math.max(0,Math.min(1,fraction)) : 0
    readonly property real boundedArmReach: Number.isFinite(armReach) ? Math.max(65,Math.min(95,armReach)) : 95
    readonly property int litSegments: Math.ceil(30*boundedFraction)
    readonly property color liveColor: flash ? Colors.white : accentColor
    implicitWidth: faceDiameter + (showChassis ? 2*Math.max(0,Math.min(40,chassisClearance)) : 0)
    implicitHeight: implicitWidth
    width: implicitWidth
    height: implicitHeight

    InstrumentChassis {
        anchors.centerIn: parent
        visible: root.showChassis
        faceDiameter: root.faceDiameter
        clearance: root.chassisClearance
        chassisStyle: root.chassisStyle
        showScrews: root.showScrews
        structuralColor: root.structuralColor
    }

    Item {
        id: face
        objectName: "selectorStopwatchFace"
        anchors.centerIn: parent
        width: 216; height: 216
        scale: Math.min(root.faceDiameter,root.width,root.height)/216
        Canvas {
            id: gauge
            objectName: "automotiveGauge"
            anchors.fill: parent
            property bool hasPainted: false
            onPainted: hasPainted = true
            onAvailableChanged: if (available) requestPaint()
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
                c.reset(); c.clearRect(0,0,width,height); c.translate(108,108);
                function ring(r,fill,stroke,w) {
                    c.beginPath(); c.arc(0,0,r,0,tau);
                    if(fill) {c.fillStyle=fill;c.fill();}
                    if(stroke) {c.strokeStyle=stroke;c.lineWidth=w;c.stroke();}
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
                    if(root.gaugeStyle==="dualRail") for(let i=0;i<30;i++){
                        c.save();c.rotate(i*tau/30);c.fillStyle="#09060e";c.fillRect(-1,-102,2,16);c.restore();
                    }
                } else {
                    const teeth=root.gaugeStyle==="radialTeeth", n=teeth?60:30;
                    for(let i=0;i<n;i++) {
                        c.save();c.rotate(i*tau/n);
                        c.fillStyle=i<Math.ceil(f*n)?root.liveColor:"#39283f";
                        const w=teeth?(i%5===0?5:2.8):12;
                        c.fillRect(-w/2,-100,w,teeth?(i%5===0?17:10):15);
                        c.restore();
                    }
                }
                ring(82,null,root.structuralColor,1);
                ring(79,null,"#78858a",0.8);
                ring(70,"#120c19",root.accentColor,0.8);
                c.globalAlpha=0.45;ring(63,null,root.accentColor,0.8);c.globalAlpha=1;
                if(root.scaleStyle!=="none") for(let i=0;i<60;i++){
                    c.save();c.rotate(i*tau/60);c.fillStyle=i%5===0?Colors.white:root.accentColor;
                    c.globalAlpha=i%5===0?0.9:0.45;c.fillRect(-0.6,-77,1.2,i%5===0?7:3);c.restore();
                }
                if(root.scaleStyle==="numbers" || root.scaleStyle==="sparse"){
                    const n=root.scaleStyle==="sparse"?3:5;
                    c.fillStyle=Colors.white;c.font="11px monospace";c.textAlign="center";c.textBaseline="middle";
                    for(let i=0;i<n;i++){
                        const a=i*tau/n;
                        c.fillText(String(Number((root.scaleMinimum+(root.scaleMaximum-root.scaleMinimum)*i/n).toFixed(2))),55*Math.sin(a),-55*Math.cos(a));
                    }
                }
            }
        }
        // Recessed readout layers MUST precede the rotating arm.
        Rectangle {
            visible: root.showValue
            x: 64; y: 57; width: 88; height: 31
            color: "#33263d"; border.color: "#514354"
            Rectangle {
                anchors.fill: parent; anchors.margins: 3
                color: "#07040b"; border.color: root.accentColor
                GohuText {
                    objectName: "selectorStopwatchCenter"
                    anchors.verticalCenter: parent.verticalCenter
                    x: 2
                    text: root.valueText
                    color: root.liveColor
                    font.pixelSize: text.length>4?18:29
                    width: parent.width-(root.valueUnit!==""?24:4)
                    horizontalAlignment: Text.AlignHCenter
                    fontSizeMode: Text.Fit
                    minimumPixelSize: 12
                }
                GohuText {
                    anchors.right: parent.right; anchors.rightMargin: 2
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.valueUnit!==""
                    text: root.valueUnit; color: Colors.white; font.pixelSize: 10
                }
            }
        }
        Rectangle {
            visible: root.showSetValue && root.setText!==""
            x: 66; y: 140; width: 84; height: 23
            color: "#09060e"; border.color: root.structuralColor
            GohuText {
                anchors.centerIn: parent
                width: parent.width-4
                horizontalAlignment: Text.AlignHCenter
                text: root.setText
                textFormat: Text.RichText
                color: root.accentColor
                font.pixelSize: 12
                fontSizeMode: Text.Fit
                minimumPixelSize: 8
                elide: Text.ElideRight
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
                onAvailableChanged: if(available) requestPaint()
                Connections {
                    target: root
                    function onArmStyleChanged() {arm.requestPaint()}
                    function onBoundedArmReachChanged() {arm.requestPaint()}
                    function onLiveColorChanged() {arm.requestPaint()}
                }
                onPaint: {
                    const c=getContext("2d"), r=root.boundedArmReach-1;
                    c.reset();c.clearRect(0,0,width,height);c.translate(108,108);
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
                    body(0);c.fillStyle="#d4dfe3";c.fill();c.strokeStyle="#97a6ad";c.lineWidth=1;c.stroke();
                    c.fillStyle="#30323c";
                    if(tapered) {
                        c.beginPath();c.moveTo(0,-r+9);c.lineTo(5,-r+21);c.lineTo(8,-35);c.lineTo(-8,-35);c.lineTo(-5,-r+21);c.closePath();c.fill();
                        c.beginPath();c.moveTo(0,-r+15);c.lineTo(3,-r+23);c.lineTo(5,-39);c.lineTo(-5,-39);c.lineTo(-3,-r+23);c.closePath();c.fillStyle=root.liveColor;c.fill();
                    } else {
                        c.fillRect(-half+4,-tip+6,2*half-8,tip-39);
                        c.fillStyle=root.liveColor;c.fillRect(-half+7,-tip+9,2*half-14,tip-45);
                    }
                    c.strokeStyle="#78858a";c.lineWidth=2;
                    for(const y of [-27,-21,-15]){c.beginPath();c.moveTo(-7,y);c.lineTo(7,y);c.stroke();}
                }
            }
        }
        Rectangle {
            anchors.centerIn: parent; width:34; height:34; radius:17
            color:"#78858a";border.color:"#b2c0c4"
            Rectangle {
                anchors.centerIn:parent; width:24;height:24;radius:12
                color:"#241a29";border.color:"#d4dfe3"
                Rectangle {anchors.centerIn:parent;width:14;height:14;radius:7;color:"#09060e";border.color:root.accentColor;border.width:2}
            }
        }
    }
}
