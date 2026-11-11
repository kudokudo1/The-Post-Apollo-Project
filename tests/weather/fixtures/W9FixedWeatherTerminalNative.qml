import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W9 // Disposable native Quickshell test. No live providers/desktop writes.
// Check the actual original SKY renderer and all four fixed-sized views.
ShellRoot {
    id: root
    property int ticks: 0
    property int phase: 0
    property bool finished: false
    readonly property var pages: ["now","hourly","daily","twilight"]
    function fail(reason) {
        if(finished)return;
        finished=true;
        console.error("W9_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    QtObject {
        id: sampleWeather
        property bool ready: true
        property bool loading: false
        property bool forecastReady: true
        property bool aqiReady: true
        property bool aqiLoading: false
        property double tempF: 57
        property double feelsLikeF: 55
        property double humidity: 56
        property double windMph: 7
        property string windDirection: "W"
        property string condition: "Clear"
        property int weatherCode: 0
        property double aqi: 60
        property string aqiLabel: "MODERATE"
        property double pressureHpa: 1015
        property double visibilityMiles: 6.8
        property double cloudCover: 20
        property double precipMm: 0
        property double uvIndex: 0
        property double latitude: 38.9
        property double longitude: -77.0
        property string observationTime: "2026-11-10 21:30"
        property string localObservationDateTime: "2026-11-10 21:30"
        property double localObservationAnchorMs: 1794364200000
        property int airQualityUtcOffsetMinutes: -300
        property var hourlyForecast: [
            {timeLabel:"10 PM",date:"2026-11-10",time:"22:00",
             tempF:55,condition:"Clear",weatherCode:0,chanceRain:5},
            {timeLabel:"11 PM",date:"2026-11-10",time:"23:00",
             tempF:54,condition:"Clear",weatherCode:0,chanceRain:5},
            {timeLabel:"12 AM",date:"2026-11-11",time:"00:00",
             tempF:52,condition:"Cloudy",weatherCode:2,chanceRain:8},
            {timeLabel:"01 AM",date:"2026-11-11",time:"01:00",
             tempF:51,condition:"Cloudy",weatherCode:3,chanceRain:12},
            {timeLabel:"02 AM",date:"2026-11-11",time:"02:00",
             tempF:49,condition:"Rain",weatherCode:61,chanceRain:50},
            {timeLabel:"03 AM",date:"2026-11-11",time:"03:00",
             tempF:48,condition:"Rain",weatherCode:61,chanceRain:60}
        ]
        property var dailyForecast: [
            {date:"2026-11-10",maxTempF:64,minTempF:45,
             weatherCode:0,condition:"Clear",chanceRain:5,
             sunrise:"6:44 AM",sunset:"5:04 PM"},
            {date:"2026-11-11",maxTempF:61,minTempF:46,
             weatherCode:3,condition:"Cloudy",chanceRain:30,
             sunrise:"6:45 AM",sunset:"5:03 PM"},
            {date:"2026-11-12",maxTempF:62,minTempF:49,
             weatherCode:61,condition:"Rain",chanceRain:70,
             sunrise:"6:46 AM",sunset:"5:02 PM"}
        ]
    }
    Window {
        id: window
        visible: true
        width: 520
        height: 300
        color: "black"
        Weather.StationWeatherSubjectPane {
            id: weather
            anchors.fill: parent
            subjectRoute: "weather/conditions/current"
            weatherService: sampleWeather
            runtimeNowMs: 1794364200000
        }
    }
    Timer {
        interval: 250
        repeat: true
        running: !root.finished
        onTriggered: {
            root.ticks++;
            if(root.ticks>35) return root.fail("TIMEOUT");
            const host=weather.activePanelLoader.item;
            if(!host || !host.renderer || !host.viewport || !host.pageRail) {
                if(root.ticks>12)return root.fail("COMBINED_HOST_MISSING");
                return;
            }
            const sky=host.renderer;
            const target=root.pages[root.phase];
            if(host.focus !== target) host.focus=target;
            if(sky.weatherFocus!==target)return;
            if(!host.pageRail.visible || host.pageRail.height!==26
                    || sky.visualScroll.interactive)
                return root.fail("SCROLLING_OR_PAGE_RAIL // "+target);
            if(sky.visualScroll.contentY!==0)
                return root.fail("SCROLL_OFFSET_LEAK // "+target);
            const drawnWidth=sky.width*sky.scale;
            const drawnHeight=sky.focusedContentHeight*sky.scale;
            if(!isFinite(drawnHeight)||drawnHeight<=0
                ||drawnHeight>host.viewport.height+1
                ||drawnWidth>host.viewport.width+1)
                return root.fail("CLIPPED_"+target+" // "
                    +drawnWidth+"x"+drawnHeight+" in "
                    +host.viewport.width+"x"+host.viewport.height);
            if(root.phase===1 && sky.hourlyForecast.length!==6)
                return root.fail("HOURLY_MODEL_LOST");
            if(root.phase===2 && sky.dailyForecast.length!==3)
                return root.fail("DAILY_MODEL_LOST");
            root.phase++;
            if(root.phase===root.pages.length) {
                root.finished=true;
                console.log("W9_NATIVE_PASS // FIXED_WEATHER_FOUR_PAGES_520X300_NO_SCROLL");
                Qt.quit();
            }
        }
    }
}
