import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import "../../components"
import "../../services/git" as GitMap
import "../../services/git/GitMapViewportPolicy.js" as Policy

// One bounded viewport for recent data and indexed history.
// The Flickable is the sole scroll position owner after explicit activation.
Rectangle {
    id: root
    color: Colors.dark
    border.color: Colors.cyan
    border.width: 1
    readonly property int rowHeight: 24
    property alias requestsEnabled: bridge.requestsEnabled
    property bool indexedActive: true
    property bool externalSelection: false
    property var recentTopology: null
    property string recentRepo: ""
    property string titleText: "BRANCH MAP"
    property real recentY: 0
    // Recent data is an explicitly bounded adapter, not a second renderer.
    readonly property var recentPage: recentRows(recentTopology, recentRepo,
        recentTopology ? recentTopology.topologyRevision : -1)
    readonly property var recentState: ({
        total: recentPage.rows.length, maxLane: recentPage.maxLane,
        rowHeight: root.rowHeight, viewportHeight: Math.max(1,flick ? flick.height : 1),
        y: recentY, snapshot: "recent:" + recentRepo,
        epoch: recentTopology ? recentTopology.topologyRevision : 0,
        shallow: false, cache: {0: recentPage}, errors: {}
    })
    readonly property var mapState: indexedActive ? bridge.state : recentState
    function recentRows(service, repo, revision) {
        const result = {start:0, frontier:[], rows:[], maxLane:0};
        if (!service || !repo || service.repoPath !== repo || service.repoRoot !== repo || service.refreshing) return result;
        const ordinals = {};
        for (let i=0; i<Math.min(48,service.commitCount); ++i) {
            const row=service.commitAt(i);
            if (!row || !Policy.sha(String(row.sha)) || !Policy.integer(row.lane,0,511)) break;
            const entry={ordinal:i,sha:String(row.sha),lane:row.lane,
                subject:String(row.subject || ""),refsText:String(row.refsText || ""),
                isHead:row.isHead===true || String(row.sha)===String(service.headFull || ""),
                parentText:String(row.parents || ""),parents:[]};
            result.rows.push(entry);
            ordinals[entry.sha]=entry;
            result.maxLane=Math.max(result.maxLane,entry.lane);
        }
        for (const row of result.rows) {
            for (const sha of row.parentText.trim().split(/\s+/)) {
                const parent=ordinals[sha];
                if (parent && parent.ordinal>row.ordinal)
                    row.parents.push({sha:sha,ordinal:parent.ordinal,lane:parent.lane});
            }
        }
        return result;
    }
    function decoration(record) {
        if (!record) return {isHead:false,refsText:""};
        if (!indexedActive) return record;
        // Match by exact SHA only. Historical index does not store refs.
        const found=recentPage.rows.find(r=>r.sha===record.sha);
        return found || {isHead:false,refsText:""};
    }
    onRecentRepoChanged: {
        recentY=0;
        if (!indexedActive && flick) flick.contentY=0;
        if (!externalSelection) selectedSha="";
    }
    onIndexedActiveChanged: {
        if (!flick || !graph) return;
        applyingGeometry=true;
        flick.cancelFlick();
        flick.contentY=mapState ? Policy.clamp(mapState,mapState.y) : 0;
        applyingGeometry=false;
        graph.requestPaint();
    }
    onRecentPageChanged: {
        if (!indexedActive && recentState && flick && graph) {
            recentY=Policy.clamp(recentState,recentY);
            flick.contentY=recentY;
            graph.requestPaint();
        }
    }
    readonly property real scrollPosition: flick.contentY
    readonly property real scrollExtent: flick.contentHeight
    readonly property int renderedRows: rows.count
    readonly property int graphSurfaceHeight: graph.height
    // Expose the real interaction targets for the disposable input fixture.
    property alias scrollRail: rail
    property alias scrollViewport: flick
    readonly property string bottomStatus: mapState ? Policy.bottomState(mapState) : "NO INDEX"
    readonly property bool bridgeFaulted: indexedActive && bridge.faulted
    readonly property int activePageStart: bridge.activeRequest ? bridge.activeRequest.start : -1
    property bool applyingGeometry: false
    property string selectedSha: ""
    signal commitSelected(string sha)

    function activate(directory, manifest, anchor) {
        applyingGeometry = true;
        const ok = bridge.activate(directory,manifest,rowHeight,Math.max(1,flick.height),anchor);
        if (ok) {
            flick.cancelFlick();
            if (indexedActive) flick.contentY = bridge.state.y;
            if (!externalSelection) selectedSha = "";
        }
        applyingGeometry = false;
        return ok;
    }
    function scrollTo(y) {
        if (!mapState || !Number.isFinite(y)) return;
        flick.cancelFlick();
        flick.contentY = Policy.clamp(mapState,y);
    }
    function rowAt(ordinal) { return mapState ? Policy.rowAt(mapState,ordinal) : null; }
    function rowStatus(ordinal) {
        if (!mapState) return "NO INDEX";
        const status = Policy.rowState(mapState,ordinal);
        return bridgeFaulted && status === "LOADING" ? "UNAVAILABLE" : status;
    }
    function retry(ordinal) { if (indexedActive) bridge.retry(ordinal); }
    function choose(ordinal) {
        const row = rowAt(ordinal);
        if (!row) return false;
        if (!externalSelection) selectedSha = row.sha;
        commitSelected(row.sha);
        return true;
    }

    GitMap.GitMapPageBridge { id: bridge }

    function currentAnchor() { return mapState ? Policy.anchorOf(mapState) : null; }

    function nodeGlyph(record) {
        const d=decoration(record);
        return d.isHead || d.refsText ? "★" : "✧";
    }

    GohuText {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8
        height: 24
        text: root.mapState ? root.titleText + " // " + root.mapState.total + (root.indexedActive ? " LOCAL COMMITS" : " AVAILABLE COMMITS") + (graph.laneX(root.mapState.maxLane) >= graph.width-14 ? " // LANES CLIPPED" : "") : root.titleText + " // NO INDEX"
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
        contentHeight: root.mapState ? Policy.extent(root.mapState) : height
        onContentYChanged: {
            if (root.applyingGeometry || !root.mapState) return;
            if (root.indexedActive) bridge.scroll(contentY);
            else root.recentY=Policy.clamp(root.mapState,contentY);
        }
        onHeightChanged: {
            if (!root.mapState || height < 1) return;
            root.applyingGeometry = true;
            if (root.indexedActive) { bridge.resize(height); contentY = bridge.state.y; }
            else { root.recentY=Policy.clamp(root.recentState,root.recentY); contentY=root.recentY; }
            root.applyingGeometry = false;
        }

        // The canvas never grows to match the full logical content height.
        Canvas {
            id: graph
            x: 0
            y: flick.contentY
            width: Math.min(190, Math.max(0,flick.width/3), 34+22*Math.min(7,root.mapState ? root.mapState.maxLane+1 : 1))
            height: flick.height
            onYChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            Connections {
                target: bridge
                function onStateChanged() { graph.requestPaint(); }
            }
            function laneX(lane) { return 14 + lane * 22; }
            function laneColor(lane) {
                return [Colors.orange,Colors.cyan,Colors.magenta,Colors.blue,Colors.green,Colors.red][lane%6];
            }
            onPaint: {
                const ctx = getContext("2d");
                ctx.clearRect(0,0,width,height);
                const s = root.mapState;
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
                        if (visible) {
                            ctx.lineWidth=1.35;
                            ctx.lineJoin="miter";
                            ctx.lineCap="butt";
                            ctx.globalAlpha=0.90;
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
                                // Strict orthogonal routing: no diagonal or rounded corner.
                                const elbow=y+root.rowHeight*0.75;
                                ctx.lineTo(laneX(row.lane),elbow);
                                ctx.lineTo(laneX(edge.lane),elbow);
                                ctx.lineTo(laneX(edge.lane),y+root.rowHeight);ctx.stroke();
                            }
                            frontier[edge.sha]=edge.lane;
                        }

                    }
                }
                ctx.globalAlpha=1.0;
            }
        }

        // Fixed-size pool relative to the first visible ordinal. It does not
        // allocate one delegate per commit or use variable row heights.
        Repeater {
            id: rows
            model: root.mapState ? Math.min(root.mapState.total,Math.ceil(flick.height/root.rowHeight)+1) : 0
            delegate: Item {
                id: rowItem
                required property int index
                readonly property int ordinal: root.mapState ? Policy.visibleRange(root.mapState).first+index : -1
                readonly property var record: root.rowAt(ordinal)
                readonly property string status: root.rowStatus(ordinal)
                visible: root.mapState !== null && ordinal<root.mapState.total
                x: 0
                y: ordinal*root.rowHeight
                width: flick.width
                height: root.rowHeight
                readonly property var decoration: root.decoration(record)
                readonly property bool selected: !!record && root.selectedSha===record.sha
                Item {
                    width: graph.width
                    height: parent.height
                    // The outer viewport clips the graph, not each 24px halo.
                    visible: rowItem.record !== null && graph.laneX(rowItem.record.lane)<width-14
                    Rectangle {
                        width: rowItem.decoration.isHead || rowItem.decoration.refsText ? 10 : 8
                        height: width
                        radius: width/2
                        x: graph.laneX(rowItem.record ? rowItem.record.lane : 0)-width/2
                        anchors.verticalCenter: parent.verticalCenter
                        color: Colors.dark
                    }
                    NotoText {
                        width: 20; height: parent.height
                        x: graph.laneX(rowItem.record ? rowItem.record.lane : 0)-width/2
                        text: root.nodeGlyph(rowItem.record)
                        font.pixelSize: rowItem.decoration.isHead ? 15 : 13
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: Colors.orange
                        visible: rowItem.selected
                        layer.enabled: visible
                        layer.effect: DropShadow {
                            radius: 15; samples: 25; opacity: 1.0
                            color: Colors.orange; transparentBorder: true
                        }
                    }
                    // Separate the halo from the full-opacity foreground. The
                    // effect opacity must never dim the commit's actual glyph.
                    NotoText {
                        id: halo
                        width: star.width; height: star.height
                        x: star.x
                        text: star.text
                        font.pixelSize: star.font.pixelSize
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: star.color
                        layer.enabled: visible && parent.visible
                        layer.effect: DropShadow {
                            radius: 8
                            samples: 17
                            spread: 0.28
                            opacity: 0.9
                            color: halo.color
                            transparentBorder: true
                        }
                    }
                    NotoText {
                        id: star
                        objectName: "gitMapCommitStar"
                        z: 3
                        width: 20; height: parent.height
                        x: graph.laneX(rowItem.record ? rowItem.record.lane : 0)-width/2
                        text: root.nodeGlyph(rowItem.record)
                        font.pixelSize: rowItem.decoration.isHead ? 15 : 13
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: Qt.lighter(rowItem.decoration.isHead ? Colors.yellow : graph.laneColor(rowItem.record ? rowItem.record.lane : 0), 1.30)
                        opacity: 1.0
                        layer.enabled: false
                    }
                }
                Row {
                    x: graph.width
                    width: Math.max(0,parent.width-x)
                    height: parent.height
                    spacing: 4
                    GohuText {
                        id: hash
                        anchors.verticalCenter: parent.verticalCenter
                        visible: !!rowItem.record
                        text: rowItem.record ? rowItem.record.sha.slice(0,8) : ""
                        font.pixelSize: 9
                        color: Colors.orange
                    }
                    GohuText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0,parent.width-(hash.visible ? hash.implicitWidth+parent.spacing : 0))
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                        font.pixelSize: 11
                        color: rowItem.record ? (rowItem.selected || rowItem.decoration.isHead ? Colors.yellow : Colors.cyan) : Colors.orange
                        text: rowItem.record ? (rowItem.decoration.refsText ? rowItem.decoration.refsText+" // " : "// ")+rowItem.record.subject
                            : rowItem.status==="UNAVAILABLE" ? (root.bridgeFaulted ? "READER UNAVAILABLE" : "UNAVAILABLE // TAP TO RETRY") : "LOADING COMMIT "+(rowItem.ordinal+1)
                    }
                }
                TapHandler {
                    property int pressedOrdinal: -1
                    property string pressedSha: ""
                    property string pressedSnapshot: ""
                    property int pressedEpoch: -1
                    onPressedChanged: if (pressed) {
                        pressedOrdinal = rowItem.ordinal;
                        pressedSha = rowItem.record ? rowItem.record.sha : "";
                        pressedSnapshot = root.mapState ? root.mapState.snapshot : "";
                        pressedEpoch = root.mapState ? root.mapState.epoch : -1;
                    }
                    onTapped: {
                        if (!root.mapState || pressedSnapshot !== root.mapState.snapshot
                                || pressedEpoch !== root.mapState.epoch
                                || pressedOrdinal !== rowItem.ordinal) return;
                        if (rowItem.record && pressedSha === rowItem.record.sha)
                            root.choose(rowItem.ordinal);
                        else if (!pressedSha && rowItem.status==="UNAVAILABLE" && !root.bridgeFaulted)
                            root.retry(rowItem.ordinal);
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
        protectHandleDragFromAncestor: true
    }
    GohuText {
        id: footer
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8
        height: 24
        text: root.bridgeFaulted ? "PAGE READER UNAVAILABLE // REOPEN REQUIRED" :
            root.mapState ? (root.mapState.total ? Policy.visibleRange(root.mapState).first+1 : 0)+" / "+root.mapState.total+" // "+(root.indexedActive ? root.bottomStatus : "AVAILABLE HISTORY // CHECK OR BUILD INDEX") : "NO INDEX"
        textFormat: Text.PlainText
        color: Colors.orange
        font.pixelSize: 10
        elide: Text.ElideRight
    }
}
