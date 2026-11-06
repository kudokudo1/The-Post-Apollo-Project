import QtQuick
import "../../components"
import "StationMagickTarotDeckPolicy.js" as Deck
import "StationMagickTarotPhysicalPolicy.js" as Physical

// M6g // Symbolic deck workspace. No actual copyrighted illustrations,
// guidebook readings, journal storage, network, additional provider or
// claim of cryptographically secure random draws.
Rectangle {
    id: tarot
    color: Colors.black
    clip: true

    property string viewMode: "draw"
    property string spreadId: "three"
    property bool reversals: false
    // M6h // Physical-card transcription or digital pseudorandom deal.
    property string drawMethod: "digital"
    property bool manualReversed: false
    property string manualMessage: ""
    property var reading: ({ready:false,cards:[]})
    property string lastError: ""
    property string localArtworkDirectory: "" // Session-only; no stored path
    property string catalogGroup: "all"
    property int catalogPage: 0
    property string previewId: ""
    readonly property var catalogEntries: Deck.catalog(catalogGroup)
    readonly property int catalogPageSize: 8
    readonly property int catalogPages: Math.ceil(
        catalogEntries.length/catalogPageSize)
    readonly property var visibleCatalog: catalogEntries.slice(
        catalogPage*catalogPageSize,
        (catalogPage+1)*catalogPageSize)
    readonly property var inspectedCard: Deck.cardById(previewId) &&
        catalogEntries.some(function(c){return c.id===previewId;})
        ? Deck.cardById(previewId)
        : catalogEntries.length
        ? catalogEntries[Math.min(catalogEntries.length-1,
              Math.max(0,catalogPage*catalogPageSize))] : null

    onCatalogGroupChanged: {
        catalogPage=0;
        previewId="";
    }
    onCatalogPageChanged: previewId=""
    onSpreadIdChanged: {
        reading=drawMethod==="physical"
            ? Physical.start(Deck.SPREADS,Deck.DECK.id,spreadId)
            : ({ready:false,cards:[]});
        manualMessage="";
        lastError="";
    }

    function setDrawMethod(method) {
        if(method!=="digital" && method!=="physical")return;
        if(drawMethod===method)return;
        drawMethod=method;
        reading=method==="physical"
            ? Physical.start(Deck.SPREADS,Deck.DECK.id,spreadId)
            : ({ready:false,cards:[]});
        manualReversed=false;
        manualMessage="";
        lastError="";
    }
    function addPhysicalCard() {
        if(drawMethod!=="physical" || !inspectedCard)return;
        const result=Physical.add(Deck.SPREADS,Deck.CARDS,reading,
                                  inspectedCard.id,manualReversed);
        if(!result.ok) {
            manualMessage=result.reason;
            return;
        }
        reading=result.state;
        manualMessage=result.state.complete?"PHYSICAL SPREAD COMPLETE"
            :"ENTER "+result.state.nextPosition;
        manualReversed=false;
        if(result.state.complete)viewMode="draw";
    }
    function undoPhysicalCard() {
        if(drawMethod!=="physical")return;
        const result=Physical.undo(Deck.SPREADS,Deck.CARDS,reading);
        if(result.ok) {
            reading=result.state;
            manualMessage="UNDID LAST CARD";
        }else manualMessage=result.reason;
    }
    function drawCards() {
        if(drawMethod!=="digital")return;
        // Math.random is a PRNG supplied by the existing Qt JS runtime.
        // Never claim a cryptographic RNG or guaranteed future prediction.
        const result=Deck.draw(spreadId,Math.random,reversals);
        reading=result;
        lastError=result.ready?"":result.reason;
    }
    function setPage(delta) {
        catalogPage=Math.max(0,Math.min(catalogPages-1,catalogPage+delta));
    }

    Column {
        anchors.fill: parent
        anchors.margins: 7
        spacing: 5

        Row {
            width: parent.width
            height: 24
            spacing: 4
            GohuText {
                width: Math.max(40,parent.width-147)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 12
                color: Colors.magenta
                text: "TAROT // THE WILD UNKNOWN"
                elide: Text.ElideRight
            }
            ActionButton {
                width: 68
                height: 24
                label: "DRAW"
                selected: tarot.viewMode==="draw"
                labelPixelSize: 10
                accentColor: Colors.magenta
                onClicked: tarot.viewMode="draw"
            }
            ActionButton {
                width: 71
                height: 24
                label: "INDEX"
                selected: tarot.viewMode==="catalog"
                labelPixelSize: 10
                accentColor: Colors.cyan
                onClicked: tarot.viewMode="catalog"
            }
        }

        QuietText {
            width: parent.width
            height: 15
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "78 CARD IDENTITIES // KIM KRANS // ART NOT DISTRIBUTED"
        }

        // M6h // Either the desktop deals, or the operator transcribes
        // cards already drawn from the physical deck. No camera or scanner.
        Row {
            id: drawMethodRow
            width: parent.width
            height: 25
            spacing: 5
            ActionButton {
                width: Math.max(90,(parent.width-8)/2)
                height: 24
                label: "DIGITAL SHUFFLE"
                labelPixelSize: 9
                selected: tarot.drawMethod==="digital"
                accentColor: selected ? Colors.magenta : Colors.cyan
                onClicked: tarot.setDrawMethod("digital")
            }
            ActionButton {
                width: Math.max(90,(parent.width-8)/2)
                height: 24
                label: "MY PHYSICAL CARDS"
                labelPixelSize: 9
                selected: tarot.drawMethod==="physical"
                accentColor: selected ? Colors.magenta : Colors.cyan
                onClicked: tarot.setDrawMethod("physical")
            }
        }

        Row {
            id: folderRow
            width: parent.width
            height: 28
            spacing: 5
            QuietText {
                width: 92
                height: parent.height
                font.pixelSize: 9
                verticalAlignment: Text.AlignVCenter
                color: Colors.cyan
                text: "LOCAL ART DIR"
            }
            Rectangle {
                width: Math.max(60,parent.width-97)
                height: 26
                color: Colors.dark
                border.width: 1
                border.color: Deck.localArtworkUrl(
                    tarot.localArtworkDirectory,"major-the-fool")!==""
                    ? Colors.green : Colors.blue
                clip: true
                TextInput {
                    id: artworkFolderInput
                    anchors.fill: parent
                    anchors.margins: 5
                    font.family: "monospace"
                    font.pixelSize: 10
                    color: Colors.white
                    selectionColor: Colors.magenta
                    selectByMouse: true
                    maximumLength: 1024
                    onTextChanged: tarot.localArtworkDirectory=text
                }
                QuietText {
                    anchors.fill: parent
                    anchors.margins: 5
                    verticalAlignment: Text.AlignVCenter
                    enabled: false
                    visible: artworkFolderInput.text.length===0
                    color: Colors.cyan
                    font.pixelSize: 9
                    text: "OPTIONAL ABSOLUTE LOCAL FOLDER / NO UPLOAD"
                    elide: Text.ElideRight
                }
            }
        }

        // The drawing view is intentionally centered on cards, not
        // interpretive prose copied from the copyrighted guidebook.
        Column {
            id: drawView
            width: parent.width
            spacing: 5
            visible: tarot.viewMode==="draw"

            Row {
                width: parent.width
                height: 25
                spacing: 4
                Repeater {
                    model: [
                        {id:"one",label:"SINGLE"},
                        {id:"three",label:"THREE"},
                        {id:"five",label:"FIVE"}
                    ]
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(55,(drawView.width-92-3*4)/3)
                        height: 24
                        labelPixelSize: 9
                        contentPadding: 1
                        label: modelData.label
                        selected: tarot.spreadId===modelData.id
                        accentColor: selected?Colors.magenta:Colors.cyan
                        onClicked: tarot.spreadId=modelData.id
                    }
                }
                ActionButton {
                    width: 87
                    height: 24
                    label: tarot.reversals?"REVERSE ON":"REVERSE OFF"
                    visible: tarot.drawMethod==="digital"
                    labelPixelSize: 8
                    accentColor: tarot.reversals?Colors.magenta:Colors.blue
                    selected: tarot.reversals
                    onClicked: tarot.reversals=!tarot.reversals
                }
            }

            Row {
                width: parent.width
                height: 28
                spacing: 5
                ActionButton {
                    width: 98
                    height: 27
                    label: tarot.drawMethod==="physical"
                        ? "CHOOSE CARD" : "SHUFFLE + DRAW"
                    labelPixelSize: 9
                    accentColor: Colors.magenta
                    onClicked: {
                        if(tarot.drawMethod==="physical")
                            tarot.viewMode="catalog";
                        else tarot.drawCards();
                    }
                }
                ActionButton {
                    width: 60
                    height: 27
                    label: "CLEAR"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    onClicked: {
                        tarot.reading=tarot.drawMethod==="physical"
                            ? Physical.start(Deck.SPREADS,Deck.DECK.id,
                                             tarot.spreadId)
                            : ({ready:false,cards:[]});
                        tarot.manualMessage="";
                        tarot.lastError="";
                    }
                }
                QuietText {
                    width: Math.max(20,parent.width-168)
                    height: 27
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    color: Colors.yellow
                    text: tarot.drawMethod==="physical"
                        ? (tarot.reading.ready
                           ? tarot.reading.count+"/"+tarot.reading.total+
                             " ENTERED // "+
                             (tarot.reading.complete?"COMPLETE":
                              tarot.reading.nextPosition)
                           : "CHOOSE SPREAD") :
                        tarot.reading.ready
                        ? tarot.reading.count+" UNIQUE CARDS // NEW SHUFFLE"
                        : tarot.lastError!=="" ? tarot.lastError
                        : "READY // PSEUDORANDOM IN THIS SESSION"
                }
            }

            Flow {
                id: cardFlow
                width: parent.width
                spacing: 5
                // At five cards the third item wraps, keeping each card
                // legible rather than presenting five tiny thumbnails.
                readonly property int targetColumns:
                    tarot.spreadId==="one"?1:
                    tarot.spreadId==="three"?3:3
                readonly property real slotWidth:
                    tarot.spreadId==="one"?
                    Math.min(220,Math.max(100,width*0.46)):
                    Math.max(72,(width-10)/targetColumns)
                Repeater {
                    model: tarot.reading.ready ? tarot.reading.cards : []
                    delegate: Column {
                        required property var modelData
                        width: cardFlow.slotWidth
                        spacing: 3
                        StationMagickTarotCard {
                            width: parent.width
                            height: tarot.spreadId==="one"?224
                                : tarot.spreadId==="five"?126:175
                            card: modelData
                            positionLabel: modelData.position
                            reversed: modelData.reversed
                            localArtworkDirectory: tarot.localArtworkDirectory
                        }
                    }
                }
                QuietText {
                    visible: !tarot.reading.ready ||
                             !tarot.reading.cards ||
                             tarot.reading.cards.length===0
                    width: parent.width
                    height: 133
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                    color: Colors.cyan
                    font.pixelSize: 11
                    text: tarot.drawMethod==="physical"
                        ? "HOLD YOUR REAL DECK // CHOOSE CARDS IN INDEX"
                        : "SELECT SPREAD // SHUFFLE + DRAW"
                }
            }

            Row {
                width: parent.width
                height: tarot.drawMethod==="physical"?24:0
                visible: tarot.drawMethod==="physical"
                spacing: 5
                ActionButton {
                    width: 83
                    height: 23
                    label: "UNDO LAST"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    available: tarot.reading.ready &&
                               tarot.reading.count>0
                    onClicked: tarot.undoPhysicalCard()
                }
                QuietText {
                    width: Math.max(15,parent.width-88)
                    height: 23
                    verticalAlignment: Text.AlignVCenter
                    color: Colors.yellow
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    text: tarot.manualMessage ||
                        "NO STORAGE // CARDS ENTERED BY YOU"
                }
            }
            QuietText {
                width: parent.width
                height: 20
                color: Colors.orange
                font.pixelSize: 9
                elide: Text.ElideRight
                text: "SYMBOLIC POSITIONS / NO GUIDEBOOK QUOTES OR PREDICTIONS"
            }
        }

        // Catalog: every one of the 78 named Wild Unknown cards is available,
        // without reproducing the artist's guidebook or illustrations.
        Column {
            id: browseView
            width: parent.width
            spacing: 5
            visible: tarot.viewMode==="catalog"

            Row {
                width: parent.width
                height: 23
                spacing: 3
                Repeater {
                    model: [
                        {id:"all",label:"ALL"},
                        {id:"major",label:"MAJOR"},
                        {id:"wands",label:"WANDS"},
                        {id:"cups",label:"CUPS"},
                        {id:"swords",label:"SWORDS"},
                        {id:"pentacles",label:"PENT."}
                    ]
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(35,(browseView.width-15)/6)
                        height: 22
                        label: modelData.label
                        labelPixelSize: 8
                        contentPadding: 1
                        selected: tarot.catalogGroup===modelData.id
                        accentColor: selected?Colors.magenta:Colors.cyan
                        onClicked: tarot.catalogGroup=modelData.id
                    }
                }
            }
            Row {
                width: parent.width
                height: 247
                spacing: 7
                StationMagickTarotCard {
                    width: Math.max(105,Math.min(175,parent.width*0.36))
                    height: 240
                    card: tarot.inspectedCard
                    localArtworkDirectory: tarot.localArtworkDirectory
                    positionLabel: "CATALOG // NO DRAW"
                }
                Column {
                    width: Math.max(50,parent.width-
                        Math.max(105,Math.min(175,parent.width*0.36))-7)
                    spacing: 3
                    Repeater {
                        model: tarot.visibleCatalog
                        delegate: ActionButton {
                            required property var modelData
                            width: parent.width
                            height: 26
                            label: (modelData.index+1)+
                                " // "+modelData.title.toUpperCase()
                            labelPixelSize: 9
                            accentColor: modelData.id===
                                (tarot.inspectedCard?
                                 tarot.inspectedCard.id:"")
                                ? Colors.magenta:Colors.cyan
                            onClicked: {
                                // Choose a catalogue page/preview by
                                // clicking its original card index.
                                tarot.previewId=modelData.id;
                            }
                        }
                    }
                }
            }
            Row {
                width: parent.width
                height: 24
                spacing: 6
                ActionButton {
                    width: 75
                    height: 23
                    label: "◀ PREV"
                    labelPixelSize: 9
                    available: tarot.catalogPage>0
                    accentColor: Colors.cyan
                    onClicked: tarot.setPage(-1)
                }
                QuietText {
                    width: Math.max(20,parent.width-160)
                    height: 24
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: 9
                    color: Colors.yellow
                    text: "PAGE "+(tarot.catalogPage+1)+"/"+
                          tarot.catalogPages+" // "+tarot.catalogEntries.length
                          +" CARDS"
                }
                ActionButton {
                    width: 75
                    height: 23
                    label: "NEXT ▶"
                    labelPixelSize: 9
                    available: tarot.catalogPage+1<tarot.catalogPages
                    accentColor: Colors.cyan
                    onClicked: tarot.setPage(1)
                }
            }
        }

        QuietText {
            width: parent.width
            height: 16
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "LOCAL FILES: major-the-fool.png / wands-daughter.png / ... "
        }
        QuietText {
            width: parent.width
            height: 15
            color: Colors.orange
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "PRIVATE READ-ONLY ART // NO BUNDLED IMAGES, NO SAVED READINGS"
        }
    }
}
