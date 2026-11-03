import QtQuick
import Quickshell
import "widgets/weather"

// M28-C: actual TOOLS buttons are clicked with a native pointer. The
// fixture intercepts the request; never starts Kitty or sends Sway IPC.
ShellRoot {
    id: root
    property string route: "tools/terminal/consoles"
    property string phase: "newsSelect"
    property int signalsSeen: 0
    property bool finished: false
    property int ticks: 0

    FloatingWindow {
        id: window
        title: "M28C-TOOLS-TERMINAL-CONTROLS"
        visible: true
        implicitWidth: 1150
        implicitHeight: 850
        StationToolsSubjectPane {
            id: tools
            anchors.fill: parent
            subjectRoute: root.route
            onTerminalLaunchRequested: function(mode) {
                root.signalsSeen++;
                if (root.phase === "newsLaunch" && mode === "news"
                    && root.signalsSeen === 1) {
                    console.log("M28C_PASS // NEWS_CONTEXT_SIGNAL_NO_KITTY");
                    root.route = "tools/terminal/star-map";
                    root.phase = "starSelect";
                } else if (root.phase === "starLaunch"
                           && mode === "terminal"
                           && root.signalsSeen === 2) {
                    root.finished = true;
                    console.log("M28C_PASS // STAR_MAP_SIGNAL_NO_KITTY");
                } else {
                    root.fail("UNEXPECTED_MODE_OR_DUPLICATE_SIGNAL_" + mode);
                }
            }
        }
    }

    function find(item,predicate) {
        if (!item) return null;
        if (predicate(item)) return item;
        if (!item.children) return null;
        for (let i=0; i<item.children.length; i++) {
            const found = find(item.children[i],predicate);
            if (found) return found;
        }
        return null;
    }
    function modeButton(label) {
        return find(tools,function(item) {
            return item.labelText !== undefined
                && item.labelText === label && item.selected !== undefined;
        });
    }
    function actionButton(label) {
        return find(tools,function(item) {
            return item.label !== undefined && item.label === label
                && item.available !== undefined;
        });
    }
    function announce(item,name) {
        if (!item || !item.visible) return false;
        const point=item.mapToItem(window.contentItem,
                                  item.width/2,item.height/2);
        if (!isFinite(point.x)||!isFinite(point.y)
            ||point.x<=1||point.y<=1
            ||point.x>=window.width-1||point.y>=window.height-1)
            return false;
        console.log("M28C_" + name + "_READY // x="
                    + Math.round(point.x) + " y=" + Math.round(point.y));
        return true;
    }
    function fail(message) {
        if(finished) return;
        finished=true;
        console.error("M28C_FAIL // " + message + " phase=" + phase);
    }
    Timer {
        interval: 70
        repeat: true
        running: !root.finished
        onTriggered: {
            root.ticks++;
            if (root.ticks===1 || root.ticks%70===0)
                console.log("M28C_TICK // phase=" + root.phase
                    + " route=" + root.route);
            if (root.phase==="newsSelect") {
                if(root.announce(root.modeButton("NEWS"),"NEWS"))
                    root.phase="newsWait";
            } else if (root.phase==="newsWait") {
                if (tools.selectedConsoleMode!=="news") return;
                root.phase="newsReady";
            } else if(root.phase==="newsReady") {
                if(root.announce(root.actionButton(
                    "LAUNCH CONTEXT CONSOLE // NEWS"),"CONSOLE"))
                    root.phase="newsLaunch";
            } else if(root.phase==="starSelect") {
                if(root.announce(root.actionButton("LAUNCH STAR MAP"),"STAR"))
                    root.phase="starLaunch";
            }
        }
    }
    Timer {
        interval: 15000
        repeat: false
        running: !root.finished
        onTriggered: root.fail("TIMEOUT")
    }
    Timer {
        interval: 250
        repeat: false
        running: root.finished
        onTriggered: Qt.quit()
    }
}
