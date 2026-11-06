import QtQuick
import "../../components"
import "StationMagickTarotDeckPolicy.js" as Deck

// M6g // ORIGINAL Post-Apollo fallback illustration, not Kim Krans art.
// Optional artwork is a user-provided read-only LOCAL file; never network.
Rectangle {
    id: face
    property var card: null
    property bool reversed: false
    property string localArtworkDirectory: ""
    property string positionLabel: ""
    readonly property bool hasCard: card !== null && card !== undefined
    // M6j // Only existing deck IDs and explicitly supplied local files.
    // Try common camera image formats; never make a web request.
    readonly property var artworkCandidates: hasCard
        ? Deck.localArtworkCandidates(localArtworkDirectory,card.id) : []
    property int artworkCandidateIndex: 0
    readonly property string localSource:
        artworkCandidateIndex<artworkCandidates.length
        ? artworkCandidates[artworkCandidateIndex] : ""
    readonly property bool hasLocalArt:
        art.status===Image.Ready && localSource!==""
    readonly property string artworkStatus: !hasCard
        ? "NO CARD" : artworkCandidates.length===0
        ? "NO CARD IMAGES INSTALLED"
        : hasLocalArt ? "PRIVATE LOCAL ART READY"
        : art.status===Image.Loading ? "LOADING LOCAL IMAGE"
        : art.status===Image.Error &&
          artworkCandidateIndex===artworkCandidates.length-1
        ? "IMAGE MISSING // CHECK CARD FILE"
        : "CHECKING LOCAL CARD PHOTO"
    onArtworkCandidatesChanged: artworkCandidateIndex=0
    color: Colors.black
    border.width: 1
    border.color: hasCard ? Colors.magenta : Colors.blue
    clip: true
    radius: 3
    onCardChanged: decorativeCanvas.requestPaint()
    onWidthChanged: decorativeCanvas.requestPaint()
    onHeightChanged: decorativeCanvas.requestPaint()

    Canvas {
        id: decorativeCanvas
        anchors.fill: parent
        visible: !face.hasLocalArt
        onPaint: {
            const ctx=getContext("2d"),w=width,h=height;
            ctx.clearRect(0,0,w,h);
            const cx=w/2,cy=h*0.43;
            const radius=Math.max(11,Math.min(w*0.37,h*0.32));
            ctx.save();
            ctx.strokeStyle=String(Colors.blue);
            ctx.globalAlpha=0.5;
            ctx.lineWidth=1;
            for(let i=0;i<3;i++){
                ctx.beginPath();
                ctx.arc(cx,cy,radius*(0.45+0.22*i),0,Math.PI*2);
                ctx.stroke();
            }
            ctx.strokeStyle=String(Colors.cyan);
            ctx.globalAlpha=0.83;
            const rotate=face.hasCard?face.card.index*0.618:0;
            for(let i=0;i<7;i++){
                const angle=rotate+(i/7)*Math.PI*2;
                ctx.beginPath();
                ctx.moveTo(cx+radius*0.2*Math.cos(angle),
                           cy+radius*0.2*Math.sin(angle));
                ctx.lineTo(cx+radius*0.92*Math.cos(angle),
                           cy+radius*0.92*Math.sin(angle));
                ctx.stroke();
            }
            ctx.globalAlpha=0.95;
            ctx.fillStyle=String(Colors.yellow);
            ctx.font="bold "+Math.round(Math.max(12,Math.min(24,w*0.14)))+
                     "px monospace";
            ctx.textAlign="center";
            ctx.textBaseline="middle";
            // Number-only placeholders looked like real deck artwork.
            // A labelled original fallback avoids that confusion.
            ctx.font="bold "+Math.round(Math.max(8,Math.min(15,w*0.095)))+
                     "px monospace";
            ctx.fillText("NO PHOTO",cx,cy,
                         Math.max(20,w*0.65));
            ctx.restore();
        }
    }
    Image {
        id: art
        anchors.fill: parent
        anchors.margins: 3
        source: face.localSource
        asynchronous: true
        cache: false
        fillMode: Image.PreserveAspectFit
        visible: face.hasLocalArt
        onStatusChanged: {
            if(status===Image.Error &&
               face.artworkCandidateIndex+1<face.artworkCandidates.length)
                face.artworkCandidateIndex++;
        }
        transform: Rotation {
            origin.x: art.width/2
            origin.y: art.height/2
            angle: face.reversed ? 180 : 0
        }
    }
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        // M6i // Readable labels at both five-card and focus sizes.
        height: Math.max(51,Math.min(64,parent.height*0.29))
        color: Colors.dark
        border.color: Colors.blue
        border.width: 1
        Column {
            anchors.fill: parent
            anchors.margins: 3
            spacing: 2
            QuietText {
                width: parent.width
                height: 14
                font.pixelSize: 10
                color: Colors.cyan
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: face.positionLabel
                      || (face.hasCard ? face.card.family.toUpperCase()
                                      : "NOT DRAWN")
            }
            GohuText {
                width: parent.width
                height: 18
                font.pixelSize: 11
                color: Colors.white
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: face.hasCard ? face.card.title.toUpperCase()
                                   : "PLACEHOLDER"
            }
            QuietText {
                width: parent.width
                height: 13
                font.pixelSize: 9
                color: face.reversed ? Colors.orange : Colors.yellow
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: face.reversed ? "REVERSED"
                        : face.hasLocalArt ? "LOCAL PHOTO"
                        : "PHOTO NOT LOADED"
            }
        }
    }
}
