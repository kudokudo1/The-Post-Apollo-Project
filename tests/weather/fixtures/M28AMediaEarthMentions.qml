import QtQuick
import Quickshell
import "widgets/weather"

// M28-A: one real SUBJECTS navigator, a synthetic MEDIA article-location
// handoff, the real EARTH StationDiscovery map and native pointer inspector.
// No real source request and no event/dossier save.
ShellRoot {
    id: root
    property bool activate: false
    property bool done: false
    property string phase: "boot"
    property int ticks: 0
    readonly property var packet: ({
        "articleTitle": "SYNTHETIC M28A LOCATION ARTICLE",
        "articleUrl": "https://example.invalid/M28A",
        "articleSource": "TEST ONLY",
        "semantics": "MENTIONED LOCATIONS, NOT VERIFIED EVENT LOCATIONS",
        "matchMethod": "GDELT GKG TEST",
        "locations": [
            {"id":"M28A-NEWS","name":"SYNTHETIC M28A PLACE",
             "latitude":23,"longitude":35,"typeLabel":"LOCATION",
             "mentionCount":2,"firstOffset":5,"featureId":"SYNTHETIC"}
        ]
    })

    FloatingWindow {
        id: window
        visible: true
        title: "M28A-MEDIA-EARTH"
        implicitWidth: 1400
        implicitHeight: 1080

        StationSubjectNavigator {
            id: navigator
            anchors.fill: parent
            visible: root.activate
            currentPath: "media/news/locations"
        }
    }

    function find(item,predicate) {
        if(!item) return null;
        if(predicate(item)) return item;
        if(!item.children) return null;
        for(let i=0;i<item.children.length;i++) {
            let child=find(item.children[i],predicate);
            if(child) return child;
        }
        return null;
    }
    function map() {
        return find(navigator,function(item){
            return item.mapNewsMentionRows !== undefined &&
                   item.selectedMapNewsMention !== undefined;
        });
    }
    function marker() {
        const m=map();
        return find(m,function(item){
            return item.modelData !== undefined &&
                item.modelData && item.modelData.id === "M28A-NEWS" &&
                item.projected !== undefined && item.width === 18;
        });
    }
    function scroll() {
        return find(map(),function(item){
            return item.contentY !== undefined &&
                   item.contentHeight !== undefined &&
                   item.height > 500 && item.contentHeight > item.height;
        });
    }
    function button(label) {
        return find(map(),function(item){
            return item.label === label && item.available !== undefined;
        });
    }
    function position(item,desiredY) {
        if(!item) return false;
        const s=scroll();
        if(!s) return false;
        const p=item.mapToItem(s,item.width/2,item.height/2);
        s.contentY=Math.max(0,Math.min(s.contentHeight-s.height,
                           s.contentY+p.y-desiredY));
        return true;
    }
    function announce(item,kind) {
        if(!item || !item.visible) return false;
        const p=item.mapToItem(window.contentItem,item.width/2,item.height/2);
        if(!isFinite(p.x)||!isFinite(p.y)||p.x<2||p.y<2||
           p.x>=window.width-2||p.y>=window.height-2)
            return false;
        console.log("M28A_"+kind+"_READY // x="+Math.round(p.x)
                    +" y="+Math.round(p.y));
        return true;
    }
    function fail(why) {
        if(done)return;
        done=true;
        console.error("M28A_FAIL // "+why+" phase="+phase+
                      " path="+navigator.currentPath);
    }
    Timer {
        interval: 70
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if(root.ticks===1||root.ticks%60===0)
                console.log("M28A_TICK // phase="+root.phase
                       +" path="+navigator.currentPath
                       +" map="+!!root.map());
            if(root.phase==="boot") {
                if(!navigator.showNewsMentionsOnEarth(root.packet)){
                    root.fail("MEDIA_LOCATION_NOT_ACCEPTED");return;
                }
                root.activate=true;
                root.phase="map";
            } else if(root.phase==="map") {
                const m=root.map();
                if(!m || m.mapNewsMentionRows.length!==1)return;
                if(navigator.currentPath!=="earth/maps/overview"
                    || navigator.indexOpen || m.earthMapOnly!==true
                    || m.newsMentionOverlay.articleTitle!==
                       "SYNTHETIC M28A LOCATION ARTICLE") {
                    root.fail("WRONG_SUBJECT_ROUTE_OR_OVERLAY");return;
                }
                if(!root.position(root.marker(),420))return;
                root.phase="markerPos";
            } else if(root.phase==="markerPos") {
                if(root.announce(root.marker(),"MARKER"))
                    root.phase="markerClicked";
            } else if(root.phase==="markerClicked") {
                const m=root.map();
                if(!m||!m.selectedMapNewsMention)return;
                if(m.selectedMapNewsMention.id!=="M28A-NEWS"
                   || m.selectedContextSourceId!==""
                   || !m.newsMentionInspectorOpen) {
                    root.fail("NEWS_MENTION_MISCLASSIFIED_AS_EVENT");return;
                }
                console.log("M28A_PASS // NATIVE_NEWS_MARKER_INSPECTED_NOT_EVENT");
                if(!root.position(root.button("CLEAR NEWS"),400))return;
                root.phase="clearPos";
            } else if(root.phase==="clearPos") {
                if(root.announce(root.button("CLEAR NEWS"),"CLEAR"))
                    root.phase="clearClicked";
            } else if(root.phase==="clearClicked") {
                const m=root.map();
                if(!m || navigator.newsMentionOverlay!==null)return;
                if(m.mapNewsMentionRows.length!==0
                    || m.selectedMapNewsMention!==null
                    || navigator.currentPath!=="earth/maps/overview") {
                    root.fail("CLEAR_LEFT_STALE_CONTEXT");return;
                }
                root.done=true;
                console.log("M28A_PASS // SUBJECT_NATIVE_MEDIA_TO_EARTH_NO_CLASSIC");
            }
        }
    }
    Timer {
        interval: 20000
        running: !root.done
        repeat: false
        onTriggered: root.fail("TIMEOUT")
    }
    Timer {
        interval: 300
        running: root.done
        repeat: false
        onTriggered: Qt.quit()
    }
}
