import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// E6: disposable offscreen two-zone EARTH witness. The original StationDiscovery
// is shown with stationOpen=false: no collector makes network calls.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
    property string openedTopic: ""
    property var fakeWeather: ({
        aqiReady:true,aqi:26,aqiLabel:"GOOD",pm25:4.8,pm10:7.4,
        pollenAvailable:true,alderPollen:0,birchPollen:2,grassPollen:5,
        mugwortPollen:0,olivePollen:1,ragweedPollen:3,
        tempF:"87",humidity:"62",usingPersistentAqiCache:false
    })
    property var fakeRiver: ({
        configured:true,ready:true,usingPersistentCache:false,
        gauge:{lid:"TEST1",name:"Synthetic Nearby Gauge",observedPrimary:2.2,
            forecastPrimary:2.8,primaryUnits:"ft",distanceKm:8.4,
            observedCategory:{label:"NO FLOODING"}}
    })
    property var fakeNws: ({
        configured:true,ready:true,usingPersistentCache:false,
        alertList:[{event:"Heat Advisory",severity:"Moderate"}]
    })
    property var fakeSeismic: ({
        ready:true,events:[{magnitude:3.8},{magnitude:2.6}]
    })
    function find(item,name) {
        if(!item) return null;
        if(item.objectName===name) return item;
        const children=item.children || [];
        for(let i=0;i<children.length;i++) {
            const child=find(children[i],name);
            if(child)return child;
        }
        return null;
    }
    function count(item,name) {
        if(!item)return 0;
        let result=item.objectName===name ? 1 : 0;
        for(const child of (item.children||[]))result+=count(child,name);
        return result;
    }
    function fail(reason) {
        if(done)return;
        done=true;
        console.error("E6_NATIVE_FAIL // "+reason);
        Qt.quit();
    }

    Window {
        id: win
        visible:true
        width:520
        height:300
        color:"black"
        Item {
            id: stage
            anchors.fill:parent
            Weather.StationDiscovery {
                id: map
                width:parent.width
                height:Math.floor(parent.height/2)
                domain:"map"
                stationOpen:false
                earthMapOnly:true
                earthMapRoute:"earth/overview"
                earthPinnedMap:true
                earthOverviewMode:true
            }
            Weather.StationEarthOverviewPane {
                id: summary
                anchors.top:map.bottom
                anchors.left:parent.left
                anchors.right:parent.right
                anchors.bottom:parent.bottom
                weatherService:root.fakeWeather
                riverSource:root.fakeRiver
                nwsAlertSource:root.fakeNws
                seismicSource:root.fakeSeismic
                onOpenTopicRequested: function(topicId) {
                    root.openedTopic=topicId;
                }
            }
        }
    }
    Timer {
        interval:150
        repeat:true
        running:!root.done
        onTriggered: {
            root.ticks++;
            if(root.ticks>45)return root.fail("TIMEOUT");
            const host=find(map,"earth-e2-pinned-map-host");
            const plot=find(map,"earth-e2-single-map-plot");
            const filters=find(map,"earth-e2-pinned-filters");
            const deck=find(map,"earth-e3-pinned-map-controls");
            const scroll=find(map,"earth-e2-event-scroll");
            const cards=find(summary,"earth-e6-summary-cards");
            const prev=find(summary,"earth-e6-prev");
            const next=find(summary,"earth-e6-next");
            const open=find(summary,"earth-e6-open-topic");
            if(!host||!plot||!filters||!deck||!scroll||!cards
                    ||!prev||!next||!open)return;
            if(!host.visible || !plot.visible || plot.parent!==host
                    || Math.abs(host.height-map.height)>8
                    || Math.abs(map.height-stage.height/2)>1
                    || filters.visible || deck.visible || scroll.visible
                    || count(map,"earth-e2-single-map-plot")!==1
                    || count(summary,"earth-e6-metric")!==4
                    || cards.height<30
                    || cards.y+cards.height>summary.height-18)
                return root.fail("HALF_MAP_OR_COMPACT_SUMMARY_BOUNDS");
            if(root.phase===0) {
                if(summary.currentTopic.id!=="water"
                    || summary.summary.cards[1].value!=="2.20 ft")
                    return root.fail("WATER_CARD_MISMATCH");
                next.clicked(null);
                root.phase=1; return;
            }
            if(root.phase===1) {
                if(summary.currentTopic.id!=="pollen"
                    || summary.summary.cards[3].detail!=="GRASS")
                    return root.fail("POLLEN_ARROW_MISMATCH");
                next.clicked(null);
                root.phase=2; return;
            }
            if(root.phase===2) {
                if(summary.currentTopic.id!=="environment"
                    || summary.summary.cards[0].value!=="1")
                    return root.fail("ENVIRONMENT_ARROW_MISMATCH");
                next.clicked(null);
                root.phase=3; return;
            }
            if(root.phase===3) {
                if(summary.currentTopic.id!=="water")
                    return root.fail("FORWARD_ARROW_NO_WRAP");
                prev.clicked(null);
                root.phase=4; return;
            }
            if(root.phase===4) {
                if(summary.currentTopic.id!=="environment")
                    return root.fail("BACKWARD_ARROW_NO_WRAP");
                open.clicked(null);
                root.phase=5; return;
            }
            if(root.phase===5) {
                if(root.openedTopic!=="environment")
                    return root.fail("DETAIL_LINK_MISMATCH");
                root.done=true;
                console.log("E6_NATIVE_PASS // HALF_MAP_THREE_TOPIC_ARROWS_NO_DUPLICATE_MAP");
                Qt.quit();
            }
        }
    }
}
