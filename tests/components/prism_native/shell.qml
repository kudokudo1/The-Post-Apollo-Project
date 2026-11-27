import QtQuick
import QtQuick.Window
import Quickshell
import "./components" as Ui

// Disposable native rendering probe. No operator desktop or compositor access.
ShellRoot {
    id: witness
    property bool failed: false
    property real glowDuration: -1
    property int openPaintCount: -1
    function descendant(item, wanted) {
        if (!item) return null;
        if (item.objectName === wanted) return item;
        const children=item.children || [];
        for (let i=0;i<children.length;i++) {
            const found=descendant(children[i],wanted);
            if (found) return found;
        }
        return null;
    }
    Window {
        id: preview
        width: 300
        height: 240
        visible: true
        color: "#000000"
        Ui.PrismButton {
            id: prism
            x: 40
            y: 40
            width: 50
            height: 50
        }
        Item {
            id: spectrumWitness
            x: 130
            y: 20
            width: 150
            height: 200
            Rectangle {
                anchors.fill: parent
                color: "#000000"
            }
            Rectangle {
                anchors.fill: parent
                anchors.margins: 12
                color: "#16051F"
                border.width: 1
                border.color: "#DCF3FA"
                Ui.PrismBorderGlow { anchors.fill: parent }
                Ui.PrismTextGlow { labelItem: testLabel }
                Ui.GohuText {
                    id: testLabel
                    anchors.centerIn: parent
                    width: parent.width - 16
                    height: 26
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    color: "#ffffff"
                    font.pixelSize: 13
                    font.bold: true
                    text: "PRISM TEST"
                    elide: Text.ElideRight
                }
            }
        }
    }
    Timer {
        interval: 2000
        running: true
        repeat: false
        onTriggered: {
            const canvas=witness.descendant(prism,"prismArtwork");
            console.info("PRISM_NATIVE_BUTTON",prism.width,prism.height,prism.contentItem.width,prism.contentItem.height);
            if (!canvas) {
                console.error("PRISM_NATIVE_FAIL canvas missing");
                Qt.quit(); return;
            }
            console.info("PRISM_NATIVE_CANVAS",canvas.width,canvas.height,canvas.available,canvas.visible,canvas.opacity);
            const ctx=canvas.getContext("2d");
            if (!ctx) {
                console.error("PRISM_NATIVE_FAIL context missing");
                Qt.quit(); return;
            }
            const center=ctx.getImageData(Math.floor(canvas.width/2),Math.floor(canvas.height/2),1,1).data;
            console.info("PRISM_NATIVE_CENTER",center[0],center[1],center[2],center[3]);
            if (!center || center[3]<64)
                console.error("PRISM_NATIVE_FAIL canvas center unpainted");
            else
                console.info("PRISM_NATIVE_CANVAS_PAINTED");
            console.info("PRISM_NATIVE_PAINT_MS",canvas.lastPaintDurationMs);
            const glow=witness.descendant(prism,"prismGlowArtwork");
            if (!glow || glow.lastPaintDurationMs<0 || !glow.getContext("2d")
                    || glow.opacity<0.10 || glow.opacity>0.20
                    || prism.activeBorderWidth!==1
                    || prism.idleBorderWidth!==1 || prism.hoverBorderWidth!==1
                    || prism.pressedBorderWidth!==1 || prism.selectedBorderWidth!==1
                    || prism.keyboardSelectedBorderWidth!==1) {
                console.error("PRISM_NATIVE_FAIL fixed border or cached glow setup");
                Qt.quit(); return;
            }
            witness.glowDuration=glow.lastPaintDurationMs;
            prism.grabToImage(function(result) {
                if (!result.saveToFile("/tmp/prism-render-idle.png")) {
                    console.error("PRISM_NATIVE_FAIL idle snapshot");
                    Qt.quit(); return;
                }
                prism.selected=true;
                selectionCheck.start();
            });
        }
    }
    Timer {
        id: selectionCheck
        interval: 450
        repeat: false
        onTriggered: {
            const glow=witness.descendant(prism,"prismGlowArtwork");
            const openArt=witness.descendant(prism,"prismOpenArtwork");
            if (!glow || !prism.selected || prism.activeBorderWidth!==1
                    || glow.opacity!==0 || glow.lastPaintDurationMs!==witness.glowDuration
                    || !Qt.colorEqual(prism.fillColor, Ui.Colors.yellow)
                    || !Qt.colorEqual(prism.activeBorderColor, Ui.Colors.magenta)
                    || !openArt || openArt.lastPaintDurationMs<0
                    || !prism.openArtworkPrepared) {
                console.error("PRISM_NATIVE_FAIL selected palette or cached artwork");
                Qt.quit(); return;
            }
            console.info("PRISM_NATIVE_OPEN_PALETTE",prism.fillColor,prism.activeBorderColor,openArt.lastPaintDurationMs);
            witness.openPaintCount=openArt.paintCount;
            prism.grabToImage(function(result) {
                console.info("PRISM_NATIVE_COMPOSITE",result.saveToFile("/tmp/prism-render-composite.png"));
                spectrumWitness.grabToImage(function(spectrumResult) {
                    if (!spectrumResult.saveToFile("/tmp/prism-render-spectrum.png"))
                        console.error("PRISM_NATIVE_FAIL spectrum snapshot");
                    prism.selected=false;
                    closedCheck.start();
                });
            });
        }
    }
    Timer {
        id: closedCheck
        interval: 150
        onTriggered: {
            if (!Qt.colorEqual(prism.fillColor, Ui.Colors.black)
                    || !Qt.colorEqual(prism.activeBorderColor, Ui.Colors.white)
                    || !witness.descendant(prism,"prismOpenArtwork")) {
                console.error("PRISM_NATIVE_FAIL closed palette or lost cache");
                Qt.quit(); return;
            }
            prism.selected=true;
            reopenedCheck.start();
        }
    }
    Timer {
        id: reopenedCheck
        interval: 150
        onTriggered: {
            const openArt=witness.descendant(prism,"prismOpenArtwork");
            if (!openArt || openArt.paintCount!==witness.openPaintCount)
                console.error("PRISM_NATIVE_FAIL open state repaint");
            console.info("PRISM_NATIVE_DONE");
            Qt.quit();
        }
    }
    Timer {
        interval: 6000
        running: true
        onTriggered: {
            console.error("PRISM_NATIVE_FAIL timeout");
            Qt.quit();
        }
    }
}
