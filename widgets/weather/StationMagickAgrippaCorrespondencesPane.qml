import QtQuick
import "../../components"
import "StationMagickAgrippaCorrespondencePolicy.js" as Agrippa

// M6e // Source-labelled historical reference. No new providers, journal,
// health/ritual advice, physical claims or modification of the LENSES route.
Rectangle {
    id: catalogue
    color: Colors.black
    clip: true

    signal backRequested()
    property string viewMode: "wheel"
    property string selectedPlanet: "saturn"
    property string selectedCategory: "metals"
    readonly property var selectedRow: Agrippa.find(selectedPlanet)
    readonly property var selectedEntry:
        Agrippa.entry(selectedPlanet,selectedCategory)
    readonly property string citation:
        "AGRIPPA // 1651 ENGLISH // BOOK I, CH. "+
        (selectedRow ? selectedRow.chapter : "--")

    function ink(id) {
        if(id==="sun")return Colors.yellow;
        if(id==="mars")return Colors.orange;
        if(id==="venus")return Colors.magenta;
        if(id==="jupiter")return Colors.blue;
        if(id==="mercury")return Colors.cyan;
        if(id==="moon")return Colors.cyan;
        return Colors.white;
    }
    function choose(hit){
        if(!hit)return;
        catalogue.selectedPlanet=hit.planet;
        catalogue.selectedCategory=hit.category;
    }
    function selectNeighbor(delta){
        const rows=Agrippa.PLANETS;
        let found=rows.findIndex(function(p){return p.id===selectedPlanet;});
        if(found<0)found=0;
        selectedPlanet=rows[(found+delta+rows.length)%rows.length].id;
    }

    onSelectedPlanetChanged: diagram.requestPaint()
    onSelectedCategoryChanged: diagram.requestPaint()
    onViewModeChanged: diagram.requestPaint()
    onWidthChanged: diagram.requestPaint()
    onHeightChanged: diagram.requestPaint()

    Column {
        anchors.fill: parent
        anchors.margins: 7
        spacing: 5

        Row {
            width: parent.width
            height: 24
            spacing: 5
            ActionButton {
                width: 56
                height: 23
                label: "BACK"
                labelPixelSize: 9
                accentColor: Colors.magenta
                onClicked: catalogue.backRequested()
            }
            GohuText {
                width: Math.max(15,parent.width-56-7-124-10)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "AGRIPPA // PLANETARY ATTRIBUTIONS"
                elide: Text.ElideRight
                font.pixelSize: 11
                color: Colors.magenta
            }
            ActionButton {
                width: 59
                height: 23
                label: "WHEEL"
                labelPixelSize: 9
                selected: catalogue.viewMode==="wheel"
                accentColor: Colors.cyan
                onClicked: catalogue.viewMode="wheel"
            }
            ActionButton {
                width: 60
                height: 23
                label: "MATRIX"
                labelPixelSize: 9
                selected: catalogue.viewMode==="matrix"
                accentColor: Colors.cyan
                onClicked: catalogue.viewMode="matrix"
            }
        }
        QuietText {
            width: parent.width
            height: 16
            font.pixelSize: 9
            color: Colors.yellow
            text: "SOURCE // AGRIPPA, BOOK I XXIII–XXIX // HISTORICAL, NONEXCLUSIVE"
            elide: Text.ElideRight
        }
        Canvas {
            id: diagram
            width: parent.width
            height: Math.max(158,Math.min(370,catalogue.height-161))
            onPaint: {
                const ctx=getContext("2d");
                ctx.clearRect(0,0,width,height);
                ctx.save();
                ctx.font="9px monospace";
                if(catalogue.viewMode==="wheel"){
                    const g=Agrippa.wheel(width,height);
                    if(!g){ctx.restore();return;}
                    const count=Agrippa.PLANETS.length;
                    for(let i=0;i<count;i++){
                        const planet=Agrippa.PLANETS[i];
                        const color=String(catalogue.ink(planet.id));
                        for(let j=0;j<Agrippa.CATEGORIES.length;j++){
                            const cat=Agrippa.CATEGORIES[j].id;
                            const selected=planet.id===catalogue.selectedPlanet
                                && cat===catalogue.selectedCategory;
                            const r=g.inner+g.band*(j+0.5);
                            const begin=-Math.PI/2+Math.PI*2*i/count+0.022;
                            const end=-Math.PI/2+Math.PI*2*(i+1)/count-0.022;
                            ctx.beginPath();
                            ctx.arc(g.cx,g.cy,r,begin,end);
                            ctx.strokeStyle=color;
                            ctx.lineWidth=g.band*(selected?0.94:0.79);
                            ctx.globalAlpha=selected?1:0.25+0.13*j;
                            ctx.stroke();
                            if(selected){
                                ctx.beginPath();
                                ctx.arc(g.cx,g.cy,r,begin,end);
                                ctx.strokeStyle=String(Colors.magenta);
                                ctx.lineWidth=1.4;
                                ctx.globalAlpha=1;
                                ctx.stroke();
                            }
                        }
                        const angle=-Math.PI/2+Math.PI*2*(i+0.5)/count;
                        const radius=g.outer+17;
                        ctx.fillStyle=color;
                        ctx.globalAlpha=planet.id===catalogue.selectedPlanet?1:0.75;
                        ctx.textAlign="center";
                        ctx.font="9px monospace";
                        ctx.fillText(planet.label.slice(0,4),
                            g.cx+radius*Math.cos(angle),
                            g.cy+radius*Math.sin(angle),38);
                    }
                    ctx.globalAlpha=1;
                    ctx.font="bold 11px monospace";
                    ctx.fillStyle=String(catalogue.ink(catalogue.selectedPlanet));
                    ctx.textAlign="center";
                    ctx.fillText(catalogue.selectedPlanet.toUpperCase(),
                                 g.cx,g.cy-8,Math.max(20,g.inner*1.8));
                    ctx.font="9px monospace";
                    ctx.fillStyle=String(Colors.white);
                    ctx.fillText(catalogue.selectedCategory.toUpperCase(),
                                 g.cx,g.cy+8,Math.max(20,g.inner*1.9));
                }else{
                    const left=85,top=22,right=width-3,bottom=height-6;
                    const cellW=(right-left)/Agrippa.CATEGORIES.length;
                    const cellH=(bottom-top)/Agrippa.PLANETS.length;
                    ctx.textAlign="center";
                    ctx.font="9px monospace";
                    for(let col=0;col<Agrippa.CATEGORIES.length;col++){
                        ctx.globalAlpha=1;
                        ctx.fillStyle=String(Colors.yellow);
                        ctx.fillText(Agrippa.CATEGORIES[col].label,
                            left+(col+0.5)*cellW,12,cellW-4);
                    }
                    for(let row=0;row<Agrippa.PLANETS.length;row++){
                        const planet=Agrippa.PLANETS[row];
                        const cy=top+(row+0.5)*cellH;
                        ctx.globalAlpha=1;
                        ctx.textAlign="left";
                        ctx.fillStyle=String(catalogue.ink(planet.id));
                        ctx.fillText(planet.label,3,cy+3,left-8);
                        for(let col=0;col<Agrippa.CATEGORIES.length;col++){
                            const category=Agrippa.CATEGORIES[col].id;
                            const x=left+col*cellW,y=top+row*cellH;
                            const chosen=planet.id===catalogue.selectedPlanet &&
                                category===catalogue.selectedCategory;
                            ctx.fillStyle=String(chosen?Colors.magenta:Colors.blue);
                            ctx.globalAlpha=chosen?0.4:row%2?0.14:0.22;
                            ctx.fillRect(x+1,y+1,Math.max(1,cellW-2),
                                         Math.max(1,cellH-2));
                            ctx.globalAlpha=1;
                            ctx.textAlign="center";
                            ctx.font="9px monospace";
                            ctx.fillStyle=String(chosen?Colors.yellow:Colors.white);
                            ctx.fillText(planet[category][0].toUpperCase(),
                                x+cellW/2,cy+3,cellW-8);
                            if(chosen){
                                ctx.strokeStyle=String(Colors.magenta);
                                ctx.lineWidth=1.2;
                                ctx.strokeRect(x+1,y+1,
                                    Math.max(1,cellW-2),Math.max(1,cellH-2));
                            }
                        }
                    }
                }
                ctx.restore();
            }
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                cursorShape: Qt.PointingHandCursor
                onClicked: function(mouse){
                    const hit=catalogue.viewMode==="wheel"
                        ? Agrippa.pickWheel(diagram.width,diagram.height,
                                           mouse.x,mouse.y)
                        : Agrippa.matrixCell(diagram.width,diagram.height,
                                            mouse.x,mouse.y);
                    catalogue.choose(hit);
                }
                onWheel: function(wheel){
                    catalogue.selectNeighbor(wheel.angleDelta.y>0?-1:1);
                    wheel.accepted=true;
                }
            }
        }
        Row {
            width: parent.width
            height: 22
            spacing: 5
            ActionButton {
                width: 65
                height: 21
                label: "◀ BODY"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onClicked: catalogue.selectNeighbor(-1)
            }
            GohuText {
                width: Math.max(15,parent.width-135)
                height: 21
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 11
                color: Colors.yellow
                text: catalogue.selectedPlanet.toUpperCase()
                    +" // "+catalogue.selectedCategory.toUpperCase()
                elide: Text.ElideRight
            }
            ActionButton {
                width: 65
                height: 21
                label: "BODY ▶"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onClicked: catalogue.selectNeighbor(1)
            }
        }
        QuietText {
            width: parent.width
            height: 17
            font.pixelSize: 10
            color: Colors.white
            elide: Text.ElideRight
            text: catalogue.selectedEntry
                ? catalogue.selectedEntry.values.join("  /  ").toUpperCase()
                : "NO SOURCE ENTRY"
        }
        QuietText {
            width: parent.width
            height: 16
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight
            text: catalogue.citation
        }
        QuietText {
            width: parent.width
            height: 16
            font.pixelSize: 9
            color: Colors.orange
            elide: Text.ElideRight
            text: "HISTORICAL ATTRIBUTIONS // NOT MEDICAL OR CAUSAL CLAIMS"
        }
        QuietText {
            width: parent.width
            height: 15
            font.pixelSize: 9
            color: Colors.yellow
            elide: Text.ElideRight
            text: "MULTIPLE PLANETS MAY SHARE TERMS // METALS FOR REFERENCE ONLY"
        }
    }
}
