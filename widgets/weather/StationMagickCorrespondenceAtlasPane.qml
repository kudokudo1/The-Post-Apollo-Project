import QtQuick
import "../../components"
import "StationMagickAgrippaCorrespondencePolicy.js" as Agrippa
import "StationMagickSymbolismPolicy.js" as Symbols
import "StationMagickWheelViewportPolicy.js" as Viewport

// M8a // Illustrated-style index of already sourced historical relationships.
// Each term comes from Agrippa Book I 1651; the lines are coincidences
// within this edition, NOT empirical or cross-tradition causal claims.
Rectangle {
    id: atlas
    color: Colors.black
    clip: true
    signal networkRequested()
    property string planetId: "sun"
    property string categoryId: "plants"
    property string chosenTerm: ""
    readonly property var planet: Agrippa.find(planetId)
    readonly property var record: Agrippa.entry(planetId,categoryId)
    readonly property var term: record && record.values.length>0
        ? (record.values.indexOf(chosenTerm)>=0?chosenTerm:record.values[0]) : ""
    readonly property var sharedPlanets: Agrippa.shared(term,categoryId)
    property real zoom: 1.25
    property real panX: 0
    property real panY: 0
    readonly property real radius: Viewport.fitRadius(graph.width,graph.height)
    function ink(id) {
        if(id==="sun")return Colors.yellow;
        if(id==="venus")return Colors.magenta;
        if(id==="mars")return Colors.orange;
        if(id==="jupiter")return Colors.blue;
        return Colors.cyan;
    }
    function fit(){zoom=1;panX=0;panY=0;}
    function zoomAt(factor,x,y) {
        const v=Viewport.zoomAt(zoom,panX,panY,factor,x,y,
              graph.width,graph.height,radius);
        if(!v)return;
        zoom=v.zoom;panX=v.panX;panY=v.panY;
    }
    function drag(dx,dy) {
        const p=Viewport.boundedPan(panX+dx,panY+dy,radius,zoom);
        panX=p.x;panY=p.y;
    }
    onPlanetIdChanged: { chosenTerm="";graph.requestPaint(); }
    onCategoryIdChanged: { chosenTerm="";graph.requestPaint(); }
    onTermChanged:graph.requestPaint()
    onZoomChanged:graph.requestPaint()
    onPanXChanged:graph.requestPaint()
    onPanYChanged:graph.requestPaint()
    onSharedPlanetsChanged:graph.requestPaint()

    Row {
        id: titleRow
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.top:parent.top
        height:25;spacing:4
        GohuText {
            width:Math.max(20,parent.width-68)
            height:24
            font.pixelSize:12;color:Colors.magenta
            text:"SYMBOLISM // CORRESPONDENCE ATLAS"
            elide:Text.ElideRight
        }
        ActionButton {
            width:64;height:24;label:"NETWORK"
            labelPixelSize:8
            accentColor:Colors.cyan
            onClicked:atlas.networkRequested()
        }
    }
    Row {
        id: planets
        anchors.top:titleRow.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        height:26;spacing:3
        Repeater {
            model:Agrippa.PLANETS
            delegate:ActionButton {
                required property var modelData
                width:Math.max(20,(planets.width-6*planets.spacing)/7)
                height:25
                label:modelData.label.slice(0,3)
                labelPixelSize:8
                contentPadding:1
                selected:atlas.planetId===modelData.id
                accentColor:selected?Colors.magenta:atlas.ink(modelData.id)
                onClicked:atlas.planetId=modelData.id
            }
        }
    }
    Row {
        id: categoryRow
        anchors.top:planets.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        height:25;spacing:3
        Repeater {
            model:Agrippa.CATEGORIES
            delegate:ActionButton {
                required property var modelData
                width:Math.max(20,(categoryRow.width-6)/3)
                height:24
                label:modelData.label
                labelPixelSize:8
                selected:atlas.categoryId===modelData.id
                accentColor:selected?Colors.magenta:Colors.cyan
                onClicked:atlas.categoryId=modelData.id
            }
        }
    }
    Canvas {
        id: graph
        anchors.top:categoryRow.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.bottom:details.top
        anchors.bottomMargin:2
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint: {
            const ctx=getContext("2d");
            ctx.clearRect(0,0,width,height);
            ctx.save();
            ctx.translate(width/2+atlas.panX,height/2+atlas.panY);
            ctx.scale(atlas.zoom,atlas.zoom);
            const points=Agrippa.PLANETS.map(function(_,i){
                const p=Symbols.place(i,width,height);
                return p?{x:p.x-width/2,y:p.y-height/2}:null;
            });
            const selectedIndex=Agrippa.PLANETS.findIndex(function(p){
                return p.id===atlas.planetId;
            });
            const origin=points[selectedIndex];
            points.forEach(function(p,i){
                if(!p||!origin)return;
                const selected=atlas.sharedPlanets.indexOf(Agrippa.PLANETS[i].id)>=0;
                if(!selected&&i!==selectedIndex)return;
                ctx.beginPath();ctx.moveTo(origin.x,origin.y);
                ctx.lineTo(p.x,p.y);
                ctx.strokeStyle=String(i===selectedIndex?Colors.magenta:Colors.yellow);
                ctx.globalAlpha=i===selectedIndex?1:0.58;
                ctx.lineWidth=i===selectedIndex?1.8:1;ctx.stroke();
            });
            ctx.globalAlpha=1;
            points.forEach(function(p,i){
                if(!p)return;
                const source=Agrippa.PLANETS[i];
                const chosen=source.id===atlas.planetId;
                const shared=atlas.sharedPlanets.indexOf(source.id)>=0;
                ctx.fillStyle=String(Colors.dark);
                ctx.strokeStyle=String(chosen?Colors.magenta:atlas.ink(source.id));
                ctx.lineWidth=chosen?3:shared?2:1;
                ctx.globalAlpha=chosen||shared?1:0.45;
                ctx.beginPath();ctx.arc(p.x,p.y,17,0,2*Math.PI);
                ctx.fill();ctx.stroke();
                ctx.font="8px monospace";ctx.textAlign="center";
                ctx.fillStyle=String(Colors.white);
                ctx.fillText(source.label.slice(0,3),p.x,p.y+3,31);
            });
            ctx.globalAlpha=1;
            ctx.textAlign="center";
            ctx.fillStyle=String(Colors.yellow);ctx.font="bold 10px monospace";
            ctx.fillText(atlas.planet?atlas.planet.label:"NO SOURCE",0,-9,width*.40);
            ctx.fillStyle=String(Colors.cyan);ctx.font="9px monospace";
            ctx.fillText(atlas.term.toUpperCase(),0,9,width*.42);
            ctx.restore();
        }
        MouseArea {
            id:touch
            anchors.fill:parent
            cursorShape:pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor
            hoverEnabled:true
            property real sx:0
            property real sy:0
            property real lastX:0
            property real lastY:0
            property bool moved:false
            onPressed:function(mouse){sx=lastX=mouse.x;sy=lastY=mouse.y;moved=false;}
            onPositionChanged:function(mouse){
                if(!pressed)return;
                if(Math.hypot(mouse.x-sx,mouse.y-sy)>5)moved=true;
                if(moved)atlas.drag(mouse.x-lastX,mouse.y-lastY);
                lastX=mouse.x;lastY=mouse.y;
            }
            onWheel:function(wheel){
                if(wheel.angleDelta.y===0)return;
                atlas.zoomAt(wheel.angleDelta.y>0?1.2:1/1.2,wheel.x,wheel.y);
                wheel.accepted=true;
            }
            onDoubleClicked:atlas.fit()
            onClicked:function(mouse){
                if(moved)return;
                const p=Viewport.inversePoint(mouse.x,mouse.y,width,height,
                    atlas.panX,atlas.panY,atlas.zoom);
                if(!p)return;
                for(let i=0;i<Agrippa.PLANETS.length;i++)
                    if(Symbols.hit(i,width,height,p.x+width/2,p.y+height/2)){
                        atlas.planetId=Agrippa.PLANETS[i].id;return;
                    }
            }
        }
    }
    Column {
        id:details
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.bottom:parent.bottom
        height:implicitHeight
        spacing:3
        Row {
            id:terms
            width:parent.width;height:24;spacing:3
            Repeater {
                model:atlas.record?atlas.record.values:[]
                delegate:ActionButton {
                    required property var modelData
                    width:Math.max(36,(terms.width-
                        Math.max(0,(atlas.record?atlas.record.values.length:0)-1)
                        *terms.spacing)/Math.max(1,atlas.record?atlas.record.values.length:1))
                    height:23
                    label:modelData.toUpperCase()
                    labelPixelSize:8
                    selected:atlas.term===modelData
                    accentColor:selected?Colors.magenta:Colors.cyan
                    onClicked:atlas.chosenTerm=modelData
                }
            }
        }
        QuietText {
            width:parent.width;height:19
            color:Colors.yellow;font.pixelSize:9;elide:Text.ElideRight
            text:(atlas.planet?atlas.planet.label:"--")+
                " // "+atlas.categoryId.toUpperCase()+
                " // "+atlas.term.toUpperCase()+
                " // SOURCE LINKS "+atlas.sharedPlanets.join(", ").toUpperCase()
        }
        QuietText {
            width:parent.width;height:17
            font.pixelSize:9;color:Colors.cyan
            elide:Text.ElideRight
            text:atlas.record?"AGRIPPA BOOK I CH. "+atlas.record.chapter+
                " // 1651 ENGLISH EDITION":"SOURCE UNAVAILABLE"
        }
        QuietText {
            width:parent.width;height:15
            font.pixelSize:8;color:Colors.orange
            elide:Text.ElideRight
            text:"HISTORICAL TRADITION // NOT SCIENTIFIC OR MEDICAL PROPERTIES"
        }
    }
}
