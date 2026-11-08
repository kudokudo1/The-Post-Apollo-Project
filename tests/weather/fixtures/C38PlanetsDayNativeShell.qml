import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather
import "widgets/weather/StationCosmosPlanetEventPolicy.js" as Events

// C38 // Disposable offscreen fixture. Five source-backed dated lanes;
// no network, remote USNO activation or local desktop modifications.
ShellRoot {
    id: root
    property bool done: false
    function fail(why) {
        if(done) return;
        done=true;
        console.error("C38_NATIVE_FAIL // "+why);
        Qt.quit();
    }
    Window {
        visible: true
        width: 520
        height: 315
        color: "black"
        Weather.StationCosmosPlanetsDayPane {
            id: eventsPane
            anchors.fill: parent
            civilDate: "2026-11-08"
            sourceReady: true
            sourceStatus: "SOURCE RECEIVED"
            datedRows: Events.clockRows([
                {name:"MERCURY",date:"2026-11-08",status:"NORMAL",
                 rise:"06:14",riseAzimuth:88,
                 transit:"12:43",transitAltitude:45,transitHemisphere:"S",
                 set:"19:21",setAzimuth:274},
                {name:"SATURN",date:"2026-11-08",status:"NORMAL",
                 rise:"03:40",riseAzimuth:93,
                 transit:"10:00",transitAltitude:39,transitHemisphere:"N",
                 set:"17:30",setAzimuth:272}
            ],"2026-11-08")
        }
    }
    Timer {
        interval: 350
        running: !root.done
        repeat: false
        onTriggered: {
            if(eventsPane.rows.length!==5)
                return root.fail("EXPECTED_FIVE_PLANET_ROWS");
            if(eventsPane.events.length!==6)
                return root.fail("USNO_EVENTS_NOT_READY");
            eventsPane.pickPlanet("MERCURY");
            eventsPane.pickKind("rise");
            if(eventsPane.events.length!==1)
                return root.fail("PLANET_EVENT_FILTER_FAILED");
            eventsPane.setWindow(6,720);
            if(eventsPane.viewSpan!==360)
                return root.fail("ZOOM_PRESET_FAILED");
            eventsPane.step(1);
            if(!eventsPane.inspectedEvent
                || eventsPane.inspectedEvent.planet!=="MERCURY")
                return root.fail("EVENT_INSPECTOR_FAILED");
            if(!Events.inWindow(eventsPane.inspectedEvent.minute,
                eventsPane.viewStartMinute,eventsPane.viewSpan))
                return root.fail("FOCUSED_EVENT_HIDDEN");
            eventsPane.pickKind("transit");
            if(eventsPane.events.length!==1)
                return root.fail("TRANSIT_FILTER_FAILED");
            eventsPane.setWindow(24,720);
            if(eventsPane.viewSpan!==1440)
                return root.fail("FULL_DAY_RESTORE_FAILED");
            root.done=true;
            console.log("C38_NATIVE_PASS // FIVE_DATED_LANES_ZOOM_FILTER_INSPECT");
            Qt.quit();
        }
    }
}
