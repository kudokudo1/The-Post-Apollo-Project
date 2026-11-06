import QtQuick
import "../../components"
import "StationMagickAgrippaCorrespondencePolicy.js" as Agrippa
import "StationMagickGrimoireAtlasPolicy.js" as Index

// M6f // Real reference-library route: one labelled primary source,
// searchable original terms and a nonexclusive association overlap graph.
// A reference index is NOT a complete grimoire, reading or personal journal.
Rectangle {
    id: atlas
    color: Colors.black
    clip: true
    property string query: ""
    property string category: "all"
    property string focusPlanet: ""
    property int pageIndex: 0
    readonly property int rowsPerPage: 4
    readonly property var corpus: Index.build(
        Agrippa.PLANETS,Agrippa.CATEGORIES,Agrippa.SOURCE,
        query,category,focusPlanet)
    readonly property var pageRows: Index.page(corpus,pageIndex,rowsPerPage)
    readonly property int numberOfPages: Index.pages(corpus,rowsPerPage)

    onCorpusChanged: {
        pageIndex=0;
        network.requestPaint();
    }
    onFocusPlanetChanged: network.requestPaint()
    onWidthChanged: network.requestPaint()
    onHeightChanged: network.requestPaint()

    function clearFilters() {
        category="all";
        focusPlanet="";
        searchInput.text="";
        pageIndex=0;
    }
    function planetColor(name) {
        if(name==="sun")return Colors.yellow;
        if(name==="venus")return Colors.magenta;
        if(name==="mars")return Colors.orange;
        if(name==="jupiter")return Colors.blue;
        if(name==="moon"||name==="mercury")return Colors.cyan;
        return Colors.white;
    }
    function movePlanet(delta) {
        const bodies=Agrippa.PLANETS;
        let n=bodies.findIndex(function(b){return b.id===atlas.focusPlanet;});
        if(n<0)n=0;
        atlas.focusPlanet=bodies[(n+delta+bodies.length)%bodies.length].id;
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4
        Row {
            width: parent.width
            height: 22
            spacing: 6
            GohuText {
                width: Math.max(20,parent.width-78)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                color: Colors.magenta
                font.pixelSize: 12
                text: "GRIMOIRE // SOURCE ATLAS"
                elide: Text.ElideRight
            }
            ActionButton {
                width: 70
                height: 22
                label: "RESET"
                labelPixelSize: 9
                accentColor: Colors.yellow
                onClicked: atlas.clearFilters()
            }
        }
        QuietText {
            width: parent.width
            height: 17
            font.pixelSize: 9
            color: Colors.yellow
            elide: Text.ElideRight
            text: "AGRIPPA // 1651 ENGLISH // BOOK I, CH. XXIII–XXIX"
        }
        Rectangle {
            width: parent.width
            height: 26
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true
            TextInput {
                id: searchInput
                anchors.fill: parent
                anchors.margins: 5
                color: Colors.white
                font.family: "monospace"
                font.pixelSize: 11
                selectionColor: Colors.magenta
                selectByMouse: true
                maximumLength: 80
                onTextChanged: atlas.query=text
            }
            QuietText {
                anchors.fill: parent
                anchors.margins: 5
                font.pixelSize: 11
                color: Colors.cyan
                text: "FIND A METAL / STONE / PLANT..."
                visible: searchInput.text.length===0
                enabled: false
                verticalAlignment: Text.AlignVCenter
            }
        }
        Row {
            id: categoryRow
            width: parent.width
            height: 23
            spacing: 4
            Repeater {
                model: [
                    {id:"all",label:"ALL"},
                    {id:"metals",label:"METALS"},
                    {id:"stones",label:"STONES"},
                    {id:"plants",label:"PLANTS"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(32,(categoryRow.width-12)/4)
                    height: 23
                    label: modelData.label
                    labelPixelSize: 9
                    contentPadding: 1
                    selected: atlas.category===modelData.id
                    accentColor: selected ? Colors.magenta : Colors.cyan
                    onClicked: atlas.category=modelData.id
                }
            }
        }
        Canvas {
            id: network
            width: parent.width
            height: Math.max(130,Math.min(248,atlas.height-325))
            onPaint: {
                const ctx=getContext("2d");
                ctx.clearRect(0,0,width,height);
                if(!atlas.corpus.ready)return;
                const g=Index.geometry(width,height);
                if(!g)return;
                ctx.save();
                ctx.font="9px monospace";
                ctx.textAlign="center";
                // Links exist only when two planets share an IDENTICAL
                // source term in the SAME historical category.
                for(let i=0;i<atlas.corpus.links.length;i++){
                    const edge=atlas.corpus.links[i];
                    const a=Index.nodePoint(edge.fromIndex,width,height);
                    const b=Index.nodePoint(edge.toIndex,width,height);
                    if(!a||!b)continue;
                    const active=atlas.focusPlanet==="" ||
                        edge.from===atlas.focusPlanet ||
                        edge.to===atlas.focusPlanet;
                    ctx.strokeStyle=String(Colors.magenta);
                    ctx.globalAlpha=(active?0.33:0.08)+
                        Math.min(0.45,edge.count*0.13);
                    ctx.lineWidth=Math.min(3.2,0.7+edge.count*0.6);
                    ctx.beginPath();
                    ctx.moveTo(a.x,a.y);
                    ctx.lineTo(b.x,b.y);
                    ctx.stroke();
                }
                for(let i=0;i<atlas.corpus.nodes.length;i++){
                    const node=atlas.corpus.nodes[i];
                    const p=Index.nodePoint(i,width,height);
                    if(!p)continue;
                    const selected=node.id===atlas.focusPlanet;
                    const highlighted=atlas.focusPlanet==="" || selected;
                    ctx.globalAlpha=highlighted?1:0.65;
                    ctx.fillStyle=String(Colors.dark);
                    ctx.beginPath();
                    ctx.arc(p.x,p.y,selected?16:13,0,Math.PI*2);
                    ctx.fill();
                    ctx.strokeStyle=String(atlas.planetColor(node.id));
                    ctx.lineWidth=selected?2.8:1.5;
                    ctx.stroke();
                    ctx.font="9px monospace";
                    ctx.fillStyle=String(selected?Colors.yellow:Colors.white);
                    ctx.fillText(node.id.slice(0,3).toUpperCase(),p.x,p.y+3,24);
                }
                ctx.globalAlpha=1;
                ctx.font="10px monospace";
                ctx.fillStyle=String(Colors.yellow);
                ctx.fillText(atlas.focusPlanet===""
                    ? "SHARED TERMS" : atlas.focusPlanet.toUpperCase(),
                    g.cx,g.cy-7,Math.max(30,g.radius*1.2));
                ctx.fillStyle=String(Colors.cyan);
                ctx.font="9px monospace";
                ctx.fillText(atlas.corpus.overlaps+" LINKS",
                    g.cx,g.cy+8,Math.max(30,g.radius*1.2));
                ctx.restore();
            }
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                cursorShape: Qt.PointingHandCursor
                onClicked: function(mouse) {
                    const node=Index.pickNode(atlas.corpus,
                        network.width,network.height,mouse.x,mouse.y);
                    if(node!=="")atlas.focusPlanet=
                        atlas.focusPlanet===node?"":node;
                }
                onWheel: function(wheel){
                    if(atlas.corpus.ready)
                        atlas.movePlanet(wheel.angleDelta.y>0?-1:1);
                    wheel.accepted=true;
                }
            }
        }
        Row {
            width: parent.width
            height: 18
            spacing: 8
            QuietText {
                width: Math.max(20,parent.width*0.56)
                height: parent.height
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideRight
                text: atlas.corpus.ready
                    ? atlas.corpus.visible+" / "+atlas.corpus.total+
                      " ENTRIES // "+atlas.corpus.overlaps+" LINKS"
                    : atlas.corpus.reason
            }
            QuietText {
                width: Math.max(18,parent.width*0.44-8)
                height: parent.height
                font.pixelSize: 9
                color: Colors.orange
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
                text: atlas.focusPlanet===""
                    ? "ALL PLANETS" : atlas.focusPlanet.toUpperCase()
            }
        }
        Repeater {
            model: atlas.pageRows
            delegate: Rectangle {
                required property var modelData
                width: parent.width
                height: 27
                color: Colors.dark
                border.width: 1
                border.color: modelData.planet===atlas.focusPlanet
                    ? Colors.magenta : Colors.blue
                clip: true
                Row {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 7
                    GohuText {
                        width: 67
                        font.pixelSize: 10
                        color: atlas.planetColor(modelData.planet)
                        text: modelData.planet.toUpperCase()
                        elide: Text.ElideRight
                    }
                    QuietText {
                        width: Math.max(18,parent.width-140)
                        font.pixelSize: 10
                        text: modelData.term.toUpperCase()+
                              " / "+modelData.category.toUpperCase()
                        elide: Text.ElideRight
                    }
                    QuietText {
                        width: 56
                        font.pixelSize: 9
                        color: Colors.yellow
                        text: "CH. "+modelData.chapter
                        horizontalAlignment: Text.AlignRight
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: atlas.focusPlanet=modelData.planet
                }
            }
        }
        Row {
            width: parent.width
            height: 21
            spacing: 4
            ActionButton {
                width: 65
                height: 20
                label: "◀ PAGE"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: atlas.pageIndex>0
                onClicked: atlas.pageIndex=Math.max(0,atlas.pageIndex-1)
            }
            QuietText {
                width: Math.max(20,parent.width-134)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 9
                color: Colors.white
                text: atlas.numberOfPages>0
                    ? "PAGE "+(atlas.pageIndex+1)+"/"+atlas.numberOfPages
                    : "NO MATCHING SOURCE TERMS"
                elide: Text.ElideRight
            }
            ActionButton {
                width: 65
                height: 20
                label: "PAGE ▶"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: atlas.pageIndex+1<atlas.numberOfPages
                onClicked: atlas.pageIndex=Math.min(
                    atlas.numberOfPages-1,atlas.pageIndex+1)
            }
        }
        QuietText {
            width: parent.width
            height: 16
            color: Colors.magenta
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "ONE CORPUS // AGRIPPA BOOK I // NOT A COMPLETE GRIMOIRE"
        }
        QuietText {
            width: parent.width
            height: 16
            color: Colors.orange
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "HISTORICAL ATTRIBUTIONS / NO MEDICAL OR CAUSAL CLAIMS"
        }
    }
}
