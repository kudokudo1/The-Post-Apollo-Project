import QtQuick
import "../../components"
import "StationCosmosCelestialNetworkPolicy.js" as Network
import "StationMagickCelestialVisualPolicy.js" as Celestial

// V4a // A read-only diagram of SOURCE-VERIFIED geocentric apparent
// ecliptic longitude relationships at one M4 UTC sample.
// The radial coordinate is a graphic convention, not orbit distance.
Item {
    id: graph
    property var graphModel: null
    property var spatialPayload: null
    property int focusIndex: -1
    property string selectedBody: ""
    property bool neonEnabled: true
    property string selectedPairKey: ""
    // V4b internally linked views; existing M4 sample and focus stay shared.
    property string displayMode: "chords"
    property string hoverBody: ""
    property string hoverPairKey: ""
    readonly property var scene: Network.network(graphModel,focusIndex)
    readonly property var activePair: Network.edgeByKey(
        scene, selectedPairKey!=="" ? selectedPairKey
             : scene.ready && scene.edges.length ? scene.edges[0].key : "")
    readonly property var activeBody: Network.nodeByBody(
        scene, selectedBody)

    signal bodyPicked(string body)
    signal sampleScrubbed(int originIndex, real offsetPixels)
    signal zoomRequested(int direction)

    onSceneChanged: {
        hoverBody="";
        hoverPairKey="";
        sceneCanvas.requestPaint();
    }
    onActivePairChanged: sceneCanvas.requestPaint()
    onSelectedBodyChanged: sceneCanvas.requestPaint()
    onHoverBodyChanged: sceneCanvas.requestPaint()
    onHoverPairKeyChanged: sceneCanvas.requestPaint()

    function render(ctx) {
        const width=sceneCanvas.width,height=sceneCanvas.height;
        ctx.clearRect(0,0,width,height);
        const g=Network.layout(width,height);
        if(!g.ready)return;
        ctx.save();
        ctx.lineCap="round";

        for(let ring=1;ring<=3;ring++){
            ctx.beginPath();
            ctx.arc(g.cx,g.cy,g.r*ring/3,0,Math.PI*2);
            ctx.strokeStyle=String(Colors.cyan);
            ctx.lineWidth=ring===3?1.4:0.8;
            ctx.globalAlpha=ring===3?0.65:0.17;
            ctx.stroke();
        }
        // 0° is the upper ecliptic-longitude reference; 30° sector marks
        // are a coordinate grid, NOT traditional interpretive claims.
        for(let degree=0;degree<360;degree+=30){
            const a=degree*Math.PI/180;
            ctx.beginPath();
            ctx.moveTo(g.cx+Math.sin(a)*(g.r-5),
                       g.cy-Math.cos(a)*(g.r-5));
            ctx.lineTo(g.cx+Math.sin(a)*(g.r+2),
                       g.cy-Math.cos(a)*(g.r+2));
            ctx.strokeStyle=String(degree%90===0?Colors.yellow:Colors.blue);
            ctx.lineWidth=degree%90===0?1.5:0.9;
            ctx.globalAlpha=degree%90===0?0.95:0.55;
            ctx.stroke();
        }
        ctx.fillStyle=String(Colors.yellow);
        ctx.globalAlpha=0.85;
        ctx.font="9px monospace";
        ctx.textAlign="center";
        ctx.textBaseline="middle";
        for(const mark of [{v:0,s:"0°"},{v:90,s:"90°"},
                           {v:180,s:"180°"},{v:270,s:"270°"}]){
            const a=mark.v*Math.PI/180;
            ctx.fillText(mark.s,g.cx+Math.sin(a)*(g.r+14),
                         g.cy-Math.cos(a)*(g.r+14));
        }
        ctx.beginPath();
        ctx.arc(g.cx,g.cy,2.5,0,2*Math.PI);
        ctx.fillStyle=String(Colors.magenta);
        ctx.fill();
        if(!graph.scene.ready){
            ctx.fillStyle=String(Colors.orange);
            ctx.font="10px monospace";
            ctx.fillText("NO VERIFIED M4 SAMPLE",g.cx,g.cy+18);
            ctx.restore();
            return;
        }

        const nodeByName={};
        for(let j=0;j<graph.scene.nodes.length;j++)
            nodeByName[graph.scene.nodes[j].body]=graph.scene.nodes[j];
        // Source-derived lines are ecliptic longitude chords. They do not
        // represent physical distances or simultaneous sky angles.
        for(let e=0;e<graph.scene.edges.length;e++){
            const pair=graph.scene.edges[e];
            const from=nodeByName[pair.first],to=nodeByName[pair.second];
            const p=Network.position(from.longitude_deg,width,height);
            const q=Network.position(to.longitude_deg,width,height);
            if(!p||!q)continue;
            const chosen=graph.activePair && graph.activePair.key===pair.key
                || graph.hoverPairKey===pair.key;
            ctx.beginPath();
            ctx.moveTo(p.x,p.y);
            ctx.lineTo(q.x,q.y);
            ctx.strokeStyle=String(chosen?Colors.magenta:Colors.blue);
            ctx.lineWidth=chosen?2.8:1.3;
            ctx.globalAlpha=chosen?0.94:0.43;
            ctx.shadowColor=ctx.strokeStyle;
            ctx.shadowBlur=graph.neonEnabled && chosen?8:0;
            ctx.stroke();
            ctx.shadowBlur=0;
        }

        for(let k=0;k<graph.scene.nodes.length;k++){
            const node=graph.scene.nodes[k];
            const p=Network.position(node.longitude_deg,width,height);
            if(!p)continue;
            const chosen=graph.selectedBody===node.body
                || graph.hoverBody===node.body;
            ctx.beginPath();
            ctx.arc(p.x,p.y,chosen?7:5,0,Math.PI*2);
            ctx.globalAlpha=1;
            ctx.fillStyle=String(node.color);
            ctx.shadowColor=String(node.color);
            ctx.shadowBlur=graph.neonEnabled?(chosen?12:5):0;
            ctx.fill();
            ctx.shadowBlur=0;
            if(chosen){
                ctx.beginPath();
                ctx.arc(p.x,p.y,10,0,Math.PI*2);
                ctx.strokeStyle=String(Colors.yellow);
                ctx.lineWidth=1.2;
                ctx.stroke();
            }
            const label=Celestial.shortBodyName(node.body);
            ctx.font="9px monospace";
            ctx.fillStyle=String(node.color);
            ctx.textAlign=p.x>=g.cx?"left":"right";
            ctx.fillText(label,p.x+(p.x>=g.cx?10:-10),
                         Math.max(10,Math.min(height-10,p.y)));
        }
        ctx.restore();
    }

    Canvas {
        id: sceneCanvas
        anchors.fill: parent
        anchors.margins: 7
        antialiasing: true
        renderTarget: Canvas.Image
        visible: graph.displayMode === "chords"
        onPaint: graph.render(getContext("2d"))
    }

    MouseArea {
        id: hitArea
        anchors.fill: sceneCanvas
        enabled: graph.scene.ready && graph.displayMode === "chords"
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        preventStealing: true
        cursorShape: Qt.CrossCursor
        property real pressX: 0
        property int originIndex: -1
        property bool didDrag: false

        onPressed: function(mouse) {
            pressX=mouse.x;
            originIndex=graph.focusIndex;
            didDrag=false;
        }
        onPositionChanged: function(mouse) {
            if(pressed){
                const dx=mouse.x-pressX;
                if(Math.abs(dx)>5)didDrag=true;
                if(didDrag && originIndex>=0)
                    graph.sampleScrubbed(originIndex,dx);
                return;
            }
            graph.hoverBody=Network.bodyHit(
                graph.scene,mouse.x,mouse.y,width,height,11);
            graph.hoverPairKey=graph.hoverBody!==""?""
                :Network.edgeHit(graph.scene,mouse.x,mouse.y,
                                 width,height,6);
        }
        onClicked: function(mouse) {
            if(didDrag)return;
            const body=Network.bodyHit(
                graph.scene,mouse.x,mouse.y,width,height,13);
            if(body!==""){
                graph.bodyPicked(body);
                return;
            }
            const pair=Network.edgeHit(graph.scene,mouse.x,mouse.y,
                                       width,height,8);
            if(pair!=="")graph.selectedPairKey=pair;
        }
        // Retain the drag flag through onClicked; reset on next press.
        // Clearing it at onReleased would misinterpret a scrub as a click.
        onCanceled: didDrag=false
        onExited: {
            if(!pressed){graph.hoverBody="";graph.hoverPairKey="";}
        }
        onWheel: function(wheel) {
            if(wheel.angleDelta.y!==0){
                graph.zoomRequested(wheel.angleDelta.y>0?1:-1);
                wheel.accepted=true;
            }
        }
    }

    // V4b isolated depth projection. Keeps parent JPL model, source UTC
    // index and body selection; introduces no additional calculation owner.
    StationCosmosCelestialDepthPane {
        id: depthPane
        anchors.fill: sceneCanvas
        visible: graph.displayMode === "depth"
        graphModel: graph.graphModel
        verifiedScene: graph.scene
        focusIndex: graph.focusIndex
        selectedBody: graph.selectedBody
        neonEnabled: graph.neonEnabled
        onBodyPicked: function(body) { graph.bodyPicked(body); }
        onSampleScrubbed: function(originIndex,offsetPixels) {
            graph.sampleScrubbed(originIndex,offsetPixels);
        }
        onZoomRequested: function(direction) {
            graph.zoomRequested(direction);
        }
    }

    StationCosmosHeliocentricPane {
        id: heliocentricPane
        anchors.fill: sceneCanvas
        visible: graph.displayMode === "heliocentric"
        embedded: true
        visualData: graph.spatialPayload
        graphModel: graph.graphModel
        verifiedNetwork: graph.scene
        focusIndex: graph.focusIndex
        selectedBody: graph.selectedBody
        neonEnabled: graph.neonEnabled
        onBodyPicked: function(body) { graph.bodyPicked(body); }
        onSampleScrubbed: function(originIndex,offsetPixels) {
            graph.sampleScrubbed(originIndex,offsetPixels);
        }
    }

    Column {
        anchors.right: parent.right
        anchors.rightMargin: 5
        anchors.top: parent.top
        anchors.topMargin: 5
        width: Math.max(155,parent.width*0.29)
        spacing: 5
        GohuText {
            width: parent.width
            font.pixelSize: 11
            color: Colors.magenta
            text: graph.displayMode==="heliocentric" ? "JPL // HELIO"
                : graph.displayMode==="depth" ? "M4 // DEPTH" : "M4 // NETWORK"
            elide: Text.ElideRight
        }
        Row {
            id: depthModes
            width: parent.width
            height: 23
            spacing: 3
            ActionButton {
                width: Math.max(1,(depthModes.width-2*depthModes.spacing)/3)
                height: 22
                contentPadding: 0
                labelPixelSize: 9
                label: "CHORDS"
                selected: graph.displayMode==="chords"
                accentColor: Colors.magenta
                onClicked: graph.displayMode="chords"
            }
            ActionButton {
                width: Math.max(1,(depthModes.width-2*depthModes.spacing)/3)
                height: 22
                contentPadding: 0
                labelPixelSize: 9
                label: "DEPTH"
                selected: graph.displayMode==="depth"
                accentColor: Colors.cyan
                onClicked: graph.displayMode="depth"
            }
            ActionButton {
                width: Math.max(1,(depthModes.width-2*depthModes.spacing)/3)
                height: 22
                contentPadding: 0
                labelPixelSize: 9
                label: "HELIO"
                selected: graph.displayMode==="heliocentric"
                accentColor: Colors.yellow
                onClicked: graph.displayMode="heliocentric"
            }
        }
        QuietText {
            width: parent.width
            font.pixelSize: 9
            color: graph.scene.ready?Colors.cyan:Colors.orange
            elide: Text.ElideRight
            text: graph.displayMode==="heliocentric"
                ? heliocentricPane.scene.ready
                  ? heliocentricPane.scene.count+" TRUE SUN-RELATIVE VECTORS"
                  : "SUN-RELATIVE SOURCE UNAVAILABLE"
                : graph.scene.ready
                  ? graph.displayMode==="depth"
                    ? graph.scene.count+" APPARENT SOURCE RAYS"
                    : graph.scene.count+" BODIES // "+graph.scene.edges.length+" PAIRS"
                  : "SOURCE UNAVAILABLE"
        }
        QuietText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.yellow
            wrapMode: Text.WordWrap
            text: graph.scene.ready
                  ? Celestial.axisText(graph.scene.timeMs)
                    +" // "+graph.scene.source+" / "+graph.scene.hash
                  : graph.scene.reason
        }
        QuietText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.magenta
            wrapMode: Text.WordWrap
            text: graph.displayMode==="heliocentric"
                ? heliocentricPane.scene.ready
                  ? "SUN ORIGIN // "+heliocentricPane.scene.maxAu.toFixed(4)+" AU"
                  : heliocentricPane.scene.reason
                : graph.displayMode==="depth"
                  ? depthPane.depthScene.ready
                    ? "MAX RADIUS "+depthPane.depthScene.maxDistanceAu.toFixed(6)+" AU"
                    : depthPane.depthScene.reason
                  : Network.pairLabel(graph.activePair)
        }
        QuietText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.cyan
            wrapMode: Text.WordWrap
            text: graph.displayMode==="heliocentric"
                ? "GEOMETRIC // TRUE ECLIPTIC OF DATE"
                : graph.displayMode==="depth"
                  ? depthPane.depthScene.ready
                    ? "LAT / DISTANCE: "+depthPane.depthScene.count+" VERIFIED"
                    : "NO APPARENT DISTANCE"
                  : graph.activePair && graph.activePair.aspects.length
                    ? "M4 TAGS // "+graph.activePair.aspects.join(", ")
                    : "M4 ASPECT TAGS // NONE"
        }
        QuietText {
            width: parent.width
            visible: graph.displayMode==="depth"
            font.pixelSize: 9
            color: Colors.yellow
            wrapMode: Text.WordWrap
            text: depthPane.focusDetail
        }
        QuietText {
            width: parent.width
            visible: graph.displayMode==="heliocentric"
            font.pixelSize: 9
            color: Colors.yellow
            wrapMode: Text.WordWrap
            text: heliocentricPane.scene.ready
                ? "SAMPLED UTC "+heliocentricPane.scene.utc
                : "MISSING JPL XYZ // NO FALLBACK"
        }
        Repeater {
            model: graph.scene.ready?graph.scene.nodes:[]
            delegate: ActionButton {
                required property var modelData
                width: parent.width
                height: 20
                contentPadding: 0
                labelPixelSize: 9
                label: Celestial.shortBodyName(modelData.body)
                       +" "+(graph.displayMode==="heliocentric"
                             && heliocentricPane.scene.ready
                             ? heliocentricPane.scene.points.filter(
                                 function(p){return p.body===modelData.body;})
                                 .map(function(p){return p.distance_au.toFixed(4)+" AU";})[0]
                                 || "--"
                             : graph.displayMode==="depth"
                               && depthPane.depthScene.ready
                               ? depthPane.depthScene.points.filter(
                                   function(p){return p.body===modelData.body;})
                                   .map(function(p){return p.distance_au.toFixed(4)+" AU";})[0]
                                   || "--"
                               : modelData.longitude_deg.toFixed(2)+"°")
                accentColor: Colors.cyan
                selected: graph.selectedBody===modelData.body
                onClicked: graph.bodyPicked(modelData.body)
            }
        }
        QuietText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
            text: graph.displayMode==="heliocentric"
                  ? "GEOMETRIC HELIOCENTRIC XYZ AU"
                  : graph.displayMode==="depth"
                    ? "APPARENT ECLIPTIC // GEOCENTRIC AU"
                    : "GEOCENTRIC ECLIPTIC LONGITUDES"
        }
    }

    QuietText {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: 2
        width: Math.max(0,parent.width*0.72)
        font.pixelSize: 9
        color: Colors.orange
        elide: Text.ElideRight
        text: graph.displayMode==="heliocentric"
              ? "SUN-RELATIVE XYZ // NO INTERPOLATED ORBITS"
              : graph.displayMode==="depth"
                ? "APPARENT RAY DISTANCES // NO PHYSICAL ORBITS"
                : "NOT PHYSICAL ORBITS // DRAG TIME // WHEEL ZOOM TIME"
    }
}
