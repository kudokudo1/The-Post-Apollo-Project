import QtQuick
import QtQuick.Window
import Quickshell
import "./components" as Ui

// Disposable native rendering probe. No operator desktop or compositor access.
ShellRoot {
    id: witness
    property bool failed: false
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
        width: 180
        height: 180
        visible: true
        color: "#000000"
        Ui.PrismButton {
            id: prism
            x: 40
            y: 40
            width: 50
            height: 50
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
            const saved=canvas.save("/tmp/prism-render-canvas.png");
            console.info("PRISM_NATIVE_CANVAS_SAVED",saved);
            prism.grabToImage(function(result) {
                console.info("PRISM_NATIVE_COMPOSITE",result.saveToFile("/tmp/prism-render-composite.png"));
                console.info("PRISM_NATIVE_DONE");
                Qt.quit();
            });
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
