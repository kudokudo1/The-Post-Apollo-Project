import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather
import "widgets/weather/StationCosmosPlanetEventPolicy.js" as Events

// Disposable QML fixture; synthetic source rows never reach production.
ShellRoot {
    id: root
    property bool done: false
    property bool showLight: false
    property int phase: 0
    property int ticks: 0
    property var rows: Events.clockRows([{
        name:"MERCURY",date:"2026-11-06",status:"NORMAL",
        rise:"06:15",transit:"12:00",set:"18:20",
        riseAzimuth:110,transitAltitude:60,transitHemisphere:"N",
        setAzimuth:250
    }],"2026-11-06")
    property var twilightData: ({
        available:true,astronomicalDawn:"04:45",
        nauticalDawn:"05:15",civilDawn:"05:45",solarNoon:"12:00",
        civilDusk:"18:30",nauticalDusk:"19:00",astronomicalDusk:"19:30",
        blueMorningStart:"05:25",blueMorningEnd:"05:45",
        goldenMorningStart:"06:00",goldenMorningEnd:"06:45",
        goldenEveningStart:"17:15",goldenEveningEnd:"18:00",
        blueEveningStart:"18:30",blueEveningEnd:"18:50"
    })
    property var astronomyData: ({
        sunrise:"06:20",sunset:"18:15",daylightLabel:"11H 55M"
    })
    Window {
        visible: true
        width: 510
        height: 335
        color: "black"
        Weather.StationCosmosClockCompactPane {
            id: clock
            visible: !root.showLight
            anchors.fill: parent
            clockRows: root.rows
            civilDate: "2026-11-06"
            sourceStatus: "SOURCE RECEIVED"
            sourcePrecision: "ONE MINUTE"
            azimuthReference: "TRUE NORTH"
        }
        Weather.StationCosmosLightDetailPane {
            id: light
            visible: root.showLight
            anchors.fill: parent
            twilight: root.twilightData
            astronomy: root.astronomyData
            sourceStatus: "CALIBRATED"
        }
    }
    function countNamed(item,name) {
        if(!item)return 0;
        var count=item.objectName===name?1:0;
        const children=item.children||[];
        for(let i=0;i<children.length;i++)
            count+=countNamed(children[i],name);
        return count;
    }
    function fail(text) {
        if(done)return;
        done=true;
        console.error("C6_CLOCK_LIGHT_FAIL // "+text);
        Qt.quit();
    }
    Timer {
        interval: 110
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>40)return root.fail("TIMEOUT");
            if(root.phase===0) {
                if(clock.renderedRowCount!==5
                    || countNamed(clock,"cosmos-c5-planet-event-marker")!==3)
                    return root.fail("PLANET_LANES_AND_MARKERS_MISSING");
                root.phase=1;
                clock.setWindow(12);
            } else if(root.phase===1) {
                if(clock.windowHours!==12 || clock.spanMinutes!==720)
                    return root.fail("CLOCK_ZOOM_BROKEN");
                clock.stepEvent(1);
                root.phase=2;
            } else if(root.phase===2) {
                if(!clock.inspecting || !clock.selectedEvent
                    || clock.eventFacts[2].value!=="06:15"
                    || countNamed(clock,"cosmos-c6-clock-fact")!==4)
                    return root.fail("CLOCK_EVENT_INSPECTOR_MISSING");
                clock.inspectPage=1;
                if(clock.eventFacts[5].value!=="110.0° TRUE N")
                    return root.fail("CLOCK_RISE_AZIMUTH_MISSING");
                clock.stepEvent(1);
                root.phase=3;
            } else if(root.phase===3) {
                if(!clock.selectedEvent
                    || clock.selectedEvent.kind!=="transit"
                    || clock.eventFacts[4].value!=="60.0° N")
                    return root.fail("CLOCK_TRANSIT_ALTITUDE_MISSING");
                root.showLight=true;
                root.phase=4;
            } else if(root.phase===4) {
                if(light.renderedFieldCount!==4
                    || light.metrics[1].value!=="05:15")
                    return root.fail("LIGHT_NAUTICAL_DAWN_MISSING");
                light.selectedMode="DUSK";
                root.phase=5;
            } else if(root.phase===5) {
                if(light.metrics[2].value!=="19:00"
                    || light.metrics[3].value!=="19:30")
                    return root.fail("LIGHT_NAUTICAL_ASTRONOMICAL_DUSK_MISSING");
                light.selectedMode="PHOTO";
                root.phase=6;
            } else if(root.phase===6) {
                if(light.metrics[0].value!=="05:25 → 05:45"
                    || light.metrics[3].value!=="18:30 → 18:50"
                    || countNamed(light,"cosmos-c6-light-field")!==4)
                    return root.fail("LIGHT_GOLDEN_BLUE_WINDOWS_MISSING");
                root.done=true;
                console.log("C6_CLOCK_LIGHT_PASS // USNO_ZOOM_EVENT_INSPECTOR FULL_TWILIGHT_FIELDS");
                Qt.quit();
            }
        }
    }
}
