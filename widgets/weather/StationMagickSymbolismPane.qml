import QtQuick
import "../../components"
import "StationMagickAgrippaCorrespondencePolicy.js" as Agrippa
import "StationMagickSymbolismPolicy.js" as Symbols

// M7a // One attributed historical symbolism lens, not a universal oracle.
Rectangle {
    id: symbolism
    color: Colors.black
    clip: true
    property string category: "all"
    property string query: ""
    property string chosenTerm: ""
    property string chosenCategory: ""
    readonly property var sourceModel: Symbols.build(
        Agrippa.PLANETS,Agrippa.CATEGORIES,Agrippa.SOURCE,category,query)
    readonly property var matches: Symbols.associated(
        sourceModel,chosenTerm,chosenCategory)
    onCategoryChanged: {chosenTerm="";chosenCategory="";}
    onQueryChanged: {chosenTerm="";chosenCategory="";}
    onMatchesChanged: network.requestPaint()

    function ink(id) {
        if(id==="sun")return Colors.yellow;
        if(id==="mars")return Colors.orange;
        if(id==="venus")return Colors.magenta;
        if(id==="jupiter")return Colors.blue;
        return Colors.cyan;
    }
    function choosePlanet(id) {
        if(!sourceModel.ready)return;
        for(let i=0;i<sourceModel.rows.length;i++){
            const row=sourceModel.rows[i];
            if(row.planet===id){
                chosenTerm=row.term;
                chosenCategory=row.category;
                return;
            }
        }
    }
    Column {
        anchors.fill: parent
        anchors.margins: 7
        spacing: 5
        GohuText {
            width: parent.width
            height: 23
            color: Colors.magenta
            font.pixelSize: 12
            elide: Text.ElideRight
            text: "SYMBOLISM // SOURCE COMPARISON"
        }
        QuietText {
            width: parent.width
            height: 18
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "AGRIPPA BOOK I, 1651 // ONE HISTORICAL EDITION"
        }
        Rectangle {
            width: parent.width
            height: 27
            color: Colors.dark
            border.color: Colors.cyan
            border.width: 1
            TextInput {
                id: symbolSearch
                anchors.fill: parent
                anchors.margins: 5
                font.family: "monospace"
                font.pixelSize: 11
                color: Colors.white
                maximumLength: 80
                selectByMouse: true
                onTextChanged: symbolism.query=text
            }
            QuietText {
                anchors.fill: parent
                anchors.margins: 5
                visible: symbolSearch.text.length===0
                enabled: false
                color: Colors.cyan
                text: "SEARCH HISTORICAL METALS / STONES / PLANTS"
                font.pixelSize: 9
                verticalAlignment: Text.AlignVCenter
            }
        }
        Row {
            id: cats
            width: parent.width
            height: 25
            spacing: 3
            Repeater {
                model: [
                    {id:"all",label:"ALL"},
                    {id:"metals",label:"METALS"},
                    {id:"stones",label:"STONES"},
                    {id:"plants",label:"PLANTS"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(30,(cats.width-9)/4)
                    height: 24
                    labelPixelSize: 9
                    label: modelData.label
                    selected: symbolism.category===modelData.id
                    accentColor: selected?Colors.magenta:Colors.cyan
                    onClicked: symbolism.category=modelData.id
                }
            }
        }
        Canvas {
            id: network
            width: parent.width
            height: Math.min(215,Math.max(138,symbolism.height-300))
            onPaint: {
                const ctx=getContext("2d");
                ctx.clearRect(0,0,width,height);
                const ps=Agrippa.PLANETS;
                ctx.save();
                for(let i=0;i<ps.length;i++){
                    const p=Symbols.place(i,width,height);
                    if(!p)continue;
                    const active=symbolism.matches.some(function(r){
                        return r.planet===ps[i].id;});
                    ctx.fillStyle=String(Colors.dark);
                    ctx.strokeStyle=String(active?Colors.magenta:
                                            symbolism.ink(ps[i].id));
                    ctx.lineWidth=active?3:1.3;
                    ctx.globalAlpha=active?1:0.55;
                    ctx.beginPath();ctx.arc(p.x,p.y,15,0,2*Math.PI);
                    ctx.fill();ctx.stroke();
                    ctx.fillStyle=String(Colors.white);
                    ctx.textAlign="center";ctx.font="9px monospace";
                    ctx.fillText(ps[i].label.slice(0,3),p.x,p.y+3,27);
                }
                ctx.globalAlpha=1;
                ctx.textAlign="center";
                ctx.font="10px monospace";
                ctx.fillStyle=String(Colors.yellow);
                ctx.fillText(symbolism.chosenTerm?
                    symbolism.chosenTerm.toUpperCase():"SELECT A TERM",
                    width/2,height/2-5,width*0.39);
                ctx.font="9px monospace";ctx.fillStyle=String(Colors.cyan);
                ctx.fillText(symbolism.matches.length+" SOURCE MATCHES",
                    width/2,height/2+10,width*0.39);
                ctx.restore();
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: function(mouse){
                    for(let i=0;i<Agrippa.PLANETS.length;i++)
                        if(Symbols.hit(i,network.width,network.height,
                                       mouse.x,mouse.y)){
                            symbolism.choosePlanet(Agrippa.PLANETS[i].id);
                            break;
                        }
                }
            }
        }
        QuietText {
            width: parent.width
            height: 17
            color: Colors.cyan
            font.pixelSize: 9
            elide: Text.ElideRight
            text: symbolism.sourceModel.ready
                ? symbolism.sourceModel.count+
                  " SOURCE RECORDS // SELECT TERM FOR LINKS"
                : symbolism.sourceModel.reason
        }
        Column {
            width: parent.width
            spacing: 3
            Repeater {
                model: symbolism.sourceModel.ready
                    ? symbolism.sourceModel.terms.slice(0,5):[]
                delegate: ActionButton {
                    required property var modelData
                    width: parent.width
                    height: 22
                    labelPixelSize: 9
                    label: modelData.term.toUpperCase()+" / "+
                           modelData.category.toUpperCase()
                    selected: symbolism.chosenTerm===modelData.term &&
                              symbolism.chosenCategory===modelData.category
                    accentColor: selected?Colors.magenta:Colors.cyan
                    onClicked: {
                        symbolism.chosenTerm=modelData.term;
                        symbolism.chosenCategory=modelData.category;
                    }
                }
            }
        }
        QuietText {
            width: parent.width
            height: 19
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: symbolism.matches.length>0
                ? symbolism.matches.map(function(x){
                    return x.planet.toUpperCase()+" CH."+x.chapter;}).join(" // ")
                : "NO TERM SELECTED // NO IMPLIED SHARED MEANING"
        }
        QuietText {
            width: parent.width
            height: 16
            color: Colors.orange
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "TRADITION-SPECIFIC REFERENCES // NOT CAUSAL FACTS"
        }
    }
}
