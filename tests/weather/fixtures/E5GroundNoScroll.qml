import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// E5 isolated native fit test. All provider data are local synthetic objects,
// no network request, file writer, or production Quickshell state is used.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
    property var fakeWeather: ({
        latitude: "38.90", longitude: "-76.80",
        tempF: "81", humidity: "61", windMph: "6",
        aqiReady: true, aqiLoading: false,
        aqi: 26, aqiLabel: "GOOD", pm25: 4.8, pm10: 7.4,
        ozone: 50, nitrogenDioxide: 8.5, carbonMonoxide: 167,
        dust: 0, ozoneAqi: 26, nitrogenDioxideAqi: 22,
        carbonMonoxideAqi: 12, airQualitySourceTime: "2026-11-09T14:00:00Z",
        pollenAvailable: true,
        alderPollen: 1, birchPollen: 2, grassPollen: 3,
        mugwortPollen: 4, olivePollen: 5, ragweedPollen: 6,
        airQualityForecastReady: true,
        airQualityForecast: [
            {label:"10 AM",aqi:26,pm25:4.8},
            {label:"12 PM",aqi:28,pm25:5.0},
            {label:"2 PM",aqi:29,pm25:5.2},
            {label:"4 PM",aqi:31,pm25:5.4},
            {label:"6 PM",aqi:33,pm25:5.6},
            {label:"8 PM",aqi:35,pm25:5.8}
        ]
    })
    property var fakeAlerts: ({
        configured:true, ready:true, loading:false, errorText:"",
        alertPoint:"38.90,-76.80", usingPersistentCache:false,
        alertList:[
            {event:"Heat Advisory",severity:"Moderate",urgency:"Expected",
             listingState:"CURRENT",headline:"Heat advisory sample",
             area:"Test county",certainty:"Likely",issuer:"NWS",
             effective:"2026-11-09T10:00:00Z",expires:"2026-11-10T00:00:00Z"},
            {event:"Red Flag Warning",severity:"Severe",urgency:"Immediate",
             listingState:"CURRENT",headline:"Red flag test",
             area:"Test county",certainty:"Likely",issuer:"NWS",
             effective:"2026-11-09T10:00:00Z",expires:"2026-11-10T00:00:00Z"},
            {event:"Wind Advisory",severity:"Moderate",urgency:"Expected",
             listingState:"CURRENT",headline:"Wind advisory sample",
             area:"Test county",certainty:"Likely",issuer:"NWS",
             effective:"2026-11-09T10:00:00Z",expires:"2026-11-10T00:00:00Z"},
            {event:"Fire Weather Watch",severity:"Moderate",urgency:"Future",
             listingState:"CURRENT",headline:"Fire weather sample",
             area:"Test county",certainty:"Likely",issuer:"NWS",
             effective:"2026-11-09T10:00:00Z",expires:"2026-11-10T00:00:00Z"}
        ]
    })
    property var fakeSeismic: ({
        ready:true, loading:false, failed:false, errorText:"",
        events: [
            {magnitude:4.2,utc:"09:00 UTC",place:"Synthetic event A",
             depthKm:12,latitude:38.8,longitude:-77.0},
            {magnitude:3.6,utc:"08:00 UTC",place:"Synthetic event B",
             depthKm:21,latitude:39.0,longitude:-76.0},
            {magnitude:3.0,utc:"07:00 UTC",place:"Synthetic event C",
             depthKm:7,latitude:40.0,longitude:-78.0}
        ]
    })
    property var fakeRiver: ({stageflowReady:false,ready:false,loading:false})
    property var fakeLightning: ({ready:false,loading:false,active:false})

    function find(item,name) {
        if (!item) return null;
        if (item.objectName===name) return item;
        const children=item.children||[];
        for(let i=0;i<children.length;i++) {
            const found=find(children[i],name);
            if(found)return found;
        }
        return null;
    }
    function fail(reason) {
        if(done)return;
        done=true;
        console.error("E5_NATIVE_FAIL // "+reason);
        Qt.quit();
    }

    Window {
        id: win
        visible: true
        width: 800
        height: 440
        color: "black"
        Weather.StationGround {
            id: ground
            anchors.fill: parent
            subjectRoute: root.phase===0
                ? "earth/ground/air-pollen" : "earth/ground/environment"
            weatherService: root.fakeWeather
            nwsAlertSource: root.fakeAlerts
            seismicSource: root.fakeSeismic
            riverSource: root.fakeRiver
            lightningSource: root.fakeLightning
        }
    }
    Timer {
        interval: 200
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if(root.ticks>30) return root.fail("TIMEOUT");
            const viewport=find(ground,"earth-e5-ground-viewport");
            const content=find(ground,"earth-e5-ground-content");
            if(!viewport || !content) return root.fail("GROUND_LAYOUT_MISSING");
            if(viewport.interactive || viewport.contentY>0.5
                || ground.requiredContentHeight>ground.height+1) {
                return root.fail((root.phase===0?"AIR_POLLEN":"ENVIRONMENT")
                    +"_OVERFLOW // required="+ground.requiredContentHeight
                    +" available="+ground.height
                    +" interactive="+viewport.interactive);
            }
            if(root.phase===0) {
                if(!ground.airQualityForecastReady
                    || ground.pollenSpecies.length!==6)
                    return root.fail("AIR_SOURCE_ROWS_MISSING");
                root.phase=1;
                return;
            }
            if(ground.officialAlerts.length!==4
                || ground.recentSeismicEvents.length!==3
                || ground.fireWeatherAlertRows.length<1)
                return root.fail("ENVIRONMENT_SOURCE_ROWS_MISSING");
            root.done=true;
            console.log("E5_NATIVE_PASS // BOTH_EARTH_GROUND_PAGES_FIT_WITHOUT_SCROLL");
            Qt.quit();
        }
    }
}
