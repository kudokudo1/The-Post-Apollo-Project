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
    readonly property string localSource: hasCard
        ? Deck.localArtworkUrl(localArtworkDirectory,card.id) : ""
    readonly property bool hasLocalArt:
        art.status===Image.Ready && localSource!==""
    color: Colors.black
    border.width: 1
    border.color: hasCard ? Colors.magenta : Colors.blue
    clip: true
    radius: 3

    Canvas {
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
            ctx.font="12px monospace";
            ctx.textAlign="center";
            ctx.textBaseline="middle";
            ctx.fillText(face.hasCard
                ? String(face.card.index+1).padStart(2,"0") : "78",
                cx,cy,Math.max(20,w*0.3));
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
        height: Math.max(35,Math.min(58,parent.height*0.28))
        color: Colors.dark
        border.color: Colors.blue
        border.width: 1
        Column {
            anchors.fill: parent
            anchors.margins: 3
            spacing: 2
            QuietText {
                width: parent.width
                height: 12
                font.pixelSize: 8
                color: Colors.cyan
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: face.positionLabel
                      || (face.hasCard ? face.card.family.toUpperCase()
                                      : "NOT DRAWN")
            }
            GohuText {
                width: parent.width
                height: 14
                font.pixelSize: 9
                color: Colors.white
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: face.hasCard ? face.card.title.toUpperCase()
                                   : "PLACEHOLDER"
            }
            QuietText {
                width: parent.width
                height: 11
                font.pixelSize: 8
                color: face.reversed ? Colors.orange : Colors.yellow
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: face.reversed ? "REVERSED"
                        : face.hasLocalArt ? "LOCAL ART" : "APOLLO ORIGINAL"
            }
        }
    }
}
