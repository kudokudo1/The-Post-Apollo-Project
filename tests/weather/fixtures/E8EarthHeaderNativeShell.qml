import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather
import "widgets/weather/StationSubjectHeaderGeometry.js" as Geometry

// E8 // No live Weather Station is touched. One original StationDiscovery
// is mounted in an isolated software-rendered offscreen Quickshell test.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
    property string openedTopic: ""
    property string requestedRoute: ""
    property var fakeWeather: ({
        aqiReady:true,aqi:26,aqiLabel:"GOOD",pm25:4.8,pm10:7.4,
        pollenAvailable:true,alderPollen:0,birchPollen:2,grassPollen:5,
        mugwortPollen:0,olivePollen:1,ragweedPollen:3,
        tempF:"87",humidity:"62"
    })
    property var fakeRiver: ({configured:true,ready:true,
        gauge:{lid:"TEST1",name:"Synthetic Gauge",observedPrimary:2.2,
            forecastPrimary:2.8,primaryUnits:"ft",distanceKm:8.4,
            observedCategory:{label:"NO FLOODING"}}})
    property var fakeNws: ({configured:true,ready:true,
        alertList:[{event:"Heat Advisory",severity:"Moderate"}]})
    property var fakeSeismic: ({ready:true,events:[{magnitude:3.8}]})

    function find(item,name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        for(const child of (item.children||[])) {
            const found=find(child,name);
            if(found)return found;
        }
        return null;
    }
    function count(item,name) {
        if(!item)return 0;
        let n=item.objectName===name ? 1 : 0;
        for(const child of (item.children||[]))n+=count(child,name);
        return n;
    }
    function fail(reason) {
        if(done)return;
        done=true;
        console.error("E8_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    Window {
        id: window
        visible:true
        width:520
        height:300
        color:"black"
        Item {
            id: frame
            anchors.fill:parent
            Weather.StationEarthMapHeader {
                id: header
                subjectRoute:"earth/overview"
                anchors.top:parent.top
                anchors.left:parent.left
                anchors.right:parent.right
                onOpenTopicRequested: function(topicId) {
                    root.openedTopic=topicId;
                }
                onRouteRequested: function(path) {
                    root.requestedRoute=path;
                }
            }
            Weather.StationDiscovery {
                id: map
                anchors.top:header.bottom
                anchors.left:parent.left
                anchors.right:parent.right
                height:Math.floor((frame.height-Geometry.contentTop())/2)
                domain:"map"
                stationOpen:false
                earthMapOnly:true
                earthMapRoute:"earth/overview"
                earthPinnedMap:true
                earthOverviewMode:true
            }
            Weather.StationEarthOverviewPane {
                id: summary
                embeddedHeader:true
                anchors.top:map.bottom
                anchors.left:parent.left
                anchors.right:parent.right
                anchors.bottom:parent.bottom
                weatherService:root.fakeWeather
                riverSource:root.fakeRiver
                nwsAlertSource:root.fakeNws
                seismicSource:root.fakeSeismic
            }
        }
    }
    Timer {
        running:!root.done
        interval:180
        repeat:true
        onTriggered: {
            root.ticks++;
            if(root.ticks>35)return root.fail("TIMEOUT");
            const title=find(header,"earth-e8-c44-title");
            const rail=find(header,"earth-e8-c44-mode-rail");
            const divider=find(header,"earth-e8-c44-divider");
            const water=find(header,"earth-e8-full-water");
            const pollen=find(header,"earth-e8-full-pollen");
            const environment=find(header,"earth-e8-full-environment");
            const summaryCards=find(summary,"earth-e6-summary-cards");
            const arrows=find(summary,"earth-e6-overview-arrows");
            const oldRail=find(summary,"earth-e7-overview-main-rail");
            const oldDivider=find(summary,"earth-e7-overview-divider");
            const host=find(map,"earth-e2-pinned-map-host");
            const plot=find(map,"earth-e2-single-map-plot");
            if(!title||!rail||!divider
                ||(root.phase<4 && (!water||!pollen||!environment))
                ||!summaryCards||!arrows||!oldRail||!oldDivider
                ||!host||!plot) {
                if(root.ticks>8) {
                    const missing=[
                        ["title",title],["rail",rail],["divider",divider],
                        ["water",water],["pollen",pollen],
                        ["environment",environment],["cards",summaryCards],
                        ["arrows",arrows],["oldRail",oldRail],
                        ["oldDivider",oldDivider],["host",host],["plot",plot]
                    ].filter(function(pair){return !pair[1];})
                     .map(function(pair){return pair[0];}).join(",");
                    const childNames=rail && rail.children
                        ?rail.children.map(function(ch){
                            return String(ch.objectName||"") + ":"
                                +String(ch.label||"");
                        }).join("|"):"--";
                    return root.fail("MISSING_NODES // "+missing
                        +" // topic="+String(header.overviewMode)
                        +" // model="+String(header.tabs.length)
                        +" // buttons="+childNames);
                }
                return;
            }
            if(header.height!==Geometry.contentTop()
                || Math.abs(title.y-Geometry.titleTop())>1
                || Math.abs(rail.y-Geometry.tabsTop())>1
                || Math.abs(divider.y-Geometry.ruleTop())>1
                || Math.abs(map.y-Geometry.contentTop())>1
                || Math.abs(map.height-(frame.height-header.height)/2)>1
                || Math.abs(summary.y-map.y-map.height)>1
                || Math.abs(summary.height-(frame.height-header.height)/2)>2
                || oldRail.visible || oldDivider.visible
                || oldRail.height!==0 || oldDivider.height!==0
                || arrows.y>4 || summaryCards.height<35
                || summaryCards.y+summaryCards.height>summary.height
                || count(map,"earth-e2-single-map-plot")!==1
                || count(summary,"earth-e7-microchart")!==4)
                return root.fail("C44_HEADER_OR_EMBEDDED_CONTENT_GEOMETRY");
            if(root.phase===0) {
                water.clicked(null);
                root.phase=1;
                return;
            }
            if(root.phase===1) {
                if(root.openedTopic!=="water")
                    return root.fail("WATER_TOP_BUTTON_ROUTE");
                pollen.clicked(null);
                root.phase=2;
                return;
            }
            if(root.phase===2) {
                if(root.openedTopic!=="pollen")
                    return root.fail("POLLEN_TOP_BUTTON_ROUTE");
                environment.clicked(null);
                root.phase=3;
                return;
            }
            if(root.phase===3) {
                if(root.openedTopic!=="environment")
                    return root.fail("ENVIRONMENT_TOP_BUTTON_ROUTE");
                header.subjectRoute="earth/maps/events";
                root.phase=4;
                return;
            }
            if(root.phase===4) {
                const events=find(header,"earth-e8-map-events");
                const full=find(header,"earth-e8-map-full");
                if(!events||!full)return;
                full.clicked(null);
                root.phase=5;
                return;
            }
            if(root.phase===5) {
                if(root.requestedRoute!=="earth/maps/full")
                    return root.fail("MAP_TOP_ROUTE");
                root.done=true;
                console.log("E8_NATIVE_PASS // C44_ALL_EARTH_TOP_RAIL_NO_LOWER_DUPLICATE");
                Qt.quit();
            }
        }
    }
}
