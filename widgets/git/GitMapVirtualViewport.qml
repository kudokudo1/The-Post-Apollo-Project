import QtQuick
import QtQuick.Controls
import "../../components"
import "../../services/git" as GitMap
import "../../services/git/GitMapViewportPolicy.js" as Policy

// Disposable candidate, not a replacement for existing BranchMap.
// The Flickable is the sole scroll position owner after explicit activation.
Rectangle {
    id: root
    color: Colors.dark
    border.color: Colors.cyan
    border.width: 1
    readonly property int rowHeight: 24
    readonly property var state: bridge.state
    readonly property real scrollPosition: flick.contentY
    readonly property real scrollExtent: flick.contentHeight
    readonly property int renderedRows: rows.count
    readonly property int graphSurfaceHeight: graph.height
    readonly property string bottomStatus: state ? Policy.bottomState(state) : "NO INDEX"
    readonly property bool bridgeFaulted: bridge.faulted
    property bool applyingGeometry: false
    property string selectedSha: ""
    signal commitSelected(string sha)

    function activate(directory, manifest, anchor) {
        applyingGeometry = true;
        const ok = bridge.activate(directory,manifest,rowHeight,Math.max(1,flick.height),anchor);
        if (ok) {
            flick.cancelFlick();
            flick.contentY = bridge.state.y;
            selectedSha = "";
        }
        applyingGeometry = false;
        return ok;
    }
    function scrollTo(y) {
        if (!state || !Number.isFinite(y)) return;
        flick.cancelFlick();
        flick.contentY = Policy.clamp(state,y);
    }
    function rowAt(ordinal) { return state ? Policy.rowAt(state,ordinal) : null; }
    function rowStatus(ordinal) { return state ? Policy.rowState(state,ordinal) : "NO INDEX"; }
    function retry(ordinal) { bridge.retry(ordinal); }
    function choose(ordinal) {
        const row = rowAt(ordinal);
        if (!row) return false;
        selectedSha = row.sha;
        commitSelected(row.sha);
        return true;
    }

    GitMap.GitMapPageBridge { id: bridge }

    Text {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8
        height: 24
        text: root.state ? "BRANCH MAP // " + root.state.total + " LOCAL COMMITS" : "BRANCH MAP // NO INDEX"
        color: Colors.magenta
        font.pixelSize: 12
        textFormat: Text.PlainText
        elide: Text.ElideRight
    }
    Flickable {
        id: flick
        anchors.top: header.bottom
        anchors.bottom: footer.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 8
        anchors.rightMargin: rail.reservedExtent + 12
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        contentWidth: width
        contentHeight: root.state ? Policy.extent(root.state) : height
        onContentYChanged: if (!root.applyingGeometry && root.state) bridge.scroll(contentY)
        onHeightChanged: {
            if (!root.state || height < 1) return;
            root.applyingGeometry = true;
            bridge.resize(height);
            contentY = bridge.state.y;
            root.applyingGeometry = false;
        }

        // The canvas never grows to match the full logical content height.
        Canvas {
            id: graph
            x: 0
            y: flick.contentY
            width: Math.min(170, Math.max(0,flick.width/3))
            height: flick.height
            onYChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            Connections {
                target: bridge
                function onStateChanged() { graph.requestPaint(); }
            }
            function laneX(lane) { return 10 + lane * 20; }
            function laneColor(lane) {
                return [Colors.orange,Colors.cyan,Colors.magenta,Colors.blue,Colors.green,Colors.red][lane%6];
            }
            onPaint: {
                const ctx = getContext("2d");
                ctx.clearRect(0,0,width,height);
                const s = root.state;
                if (!s) return;
                const range = Policy.visibleRange(s);
                // Reconstruct active frontier from each loaded page's exact
                // boundary; draw only visible row-height segments.
                const firstPage = Math.floor(range.first/128)*128;
                for (let start=firstPage; start<range.stop; start+=128) {
                    const page = s.cache[start];
                    if (!page) continue;
                    const frontier = {};
                    for (const f of page.frontier) frontier[f.sha]=f.lane;
                    for (const row of page.rows) {
                        if (row.ordinal>=range.stop) break;
                        const visible = row.ordinal>=range.first;
                        const y = row.ordinal*root.rowHeight-flick.contentY;
                        const middle = y+root.rowHeight/2;
                        const incoming = frontier[row.sha] !== undefined;
                        if (visible) {
                            ctx.lineWidth=1.3;
                            for (const key of Object.keys(frontier)) {
                                const lane=frontier[key], x=laneX(lane);
                                if (x>=width) continue;
                                ctx.strokeStyle=laneColor(lane);
                                ctx.beginPath();ctx.moveTo(x,y);
                                ctx.lineTo(x,key===row.sha?middle:y+root.rowHeight);ctx.stroke();
                            }
                        }
                        delete frontier[row.sha];
                        for (const edge of row.parents) {
                            if (visible) {
                                ctx.strokeStyle=laneColor(edge.lane);
                                ctx.beginPath();ctx.moveTo(laneX(row.lane),middle);
                                ctx.lineTo(laneX(edge.lane),y+root.rowHeight);ctx.stroke();
                            }
                            frontier[edge.sha]=edge.lane;
                        }
                        if (visible && laneX(row.lane)<width) {
                            ctx.fillStyle=laneColor(row.lane);
                            ctx.beginPath();ctx.arc(laneX(row.lane),middle,3.5,0,Math.PI*2);ctx.fill();
                        }
                    }
                }
            }
        }

        // Fixed-size pool relative to the first visible ordinal. It does not
        // allocate one delegate per commit or use variable row heights.
        Repeater {
            id: rows
            model: root.state ? Math.min(root.state.total,Math.ceil(flick.height/root.rowHeight)+1) : 0
            delegate: Item {
                id: rowItem
                required property int index
                readonly property int ordinal: root.state ? Policy.visibleRange(root.state).first+index : -1
                readonly property var record: root.rowAt(ordinal)
                readonly property string status: root.rowStatus(ordinal)
                visible: root.state !== null && ordinal<root.state.total
                x: graph.width
                y: ordinal*root.rowHeight
                width: Math.max(0,flick.width-x)
                height: root.rowHeight
                Text {
                    anchors.fill: parent
                    verticalAlignment: Text.AlignVCenter
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    font.pixelSize: 11
                    color: rowItem.record ? (root.selectedSha===rowItem.record.sha ? Colors.yellow : Colors.cyan) : Colors.orange
                    text: rowItem.record ? rowItem.record.sha.slice(0,8)+" // "+rowItem.record.subject
                        : rowItem.status==="UNAVAILABLE" ? "UNAVAILABLE // TAP TO RETRY" : "LOADING COMMIT "+(rowItem.ordinal+1)
                }
                TapHandler {
                    onTapped: {
                        if (rowItem.record) root.choose(rowItem.ordinal);
                        else if (rowItem.status==="UNAVAILABLE") root.retry(rowItem.ordinal);
                    }
                }
            }
        }
    }
    NeonScrollBar {
        id: rail
        flickable: flick
        geometryHost: root
        handleStyle: "star"
        visible: scrollable
    }
    Text {
        id: footer
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8
        height: 24
        text: root.bridgeFaulted ? "PAGE READER UNAVAILABLE // REOPEN REQUIRED" :
            root.state ? (Policy.visibleRange(root.state).first+1)+" / "+root.state.total+" // "+root.bottomStatus : "NO INDEX"
        textFormat: Text.PlainText
        color: Colors.orange
        font.pixelSize: 10
        elide: Text.ElideRight
    }
}
