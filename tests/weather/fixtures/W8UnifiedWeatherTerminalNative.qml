import QtQuick
import QtQml
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W8 // Native geometry test of one reusable WEATHER terminal at 520x300.
// All readings are synthetic. No network or weather provider is mounted.
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false
    function fail(reason) {
        if(done) return;
        done=true;
        console.error("W8_NATIVE_FAIL // "+reason);
        Qt.quit();
    }

    QtObject {
        id: observations
        property bool ready: true
        property bool forecastReady: true
        property bool aqiReady: true
        property double tempF: 57
        property string condition: "Clear"
        property double humidity: 56
        property double windMph: 7
        property string windDirection: "W"
        property double pressureHpa: 1015
        property double visibilityMiles: 6.8
        property double aqi: 60
        property double pm25: 10.2
        property var hourlyForecast: [
            {timeLabel:"09 PM",tempF:56,weatherCode:0,condition:"Clear",chanceRain:5},
            {timeLabel:"10 PM",tempF:53,weatherCode:3,condition:"Cloudy",chanceRain:15},
            {timeLabel:"11 PM",tempF:51,weatherCode:61,condition:"Rain",chanceRain:25}
        ]
        property var dailyForecast: [
            {date:"2026-11-10",maxTempF:64,minTempF:45,
             weatherCode:0,condition:"Clear",chanceRain:5},
            {date:"2026-11-11",maxTempF:61,minTempF:46,
             weatherCode:3,condition:"Cloudy",chanceRain:35},
            {date:"2026-11-12",maxTempF:62,minTempF:49,
             weatherCode:61,condition:"Rain",chanceRain:70}
        ]
    }

    Window {
        width: 520
        height: 300
        visible: true
        color: "black"
        Weather.StationWeatherTerminalSummary {
            id: weatherTerminal
            x: 4
            y: 4
            width: 512
            compact: root.phase !== 0
            weatherService: observations
        }
    }

    Timer {
        interval: 200
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if(root.ticks > 25) return root.fail("TIMEOUT");
            if(weatherTerminal.metrics.length!==4
                || weatherTerminal.hourlySamples.length!==3
                || weatherTerminal.dailySamples.length!==3)
                return root.fail("SYNTHETIC_OBSERVATION_NOT_RENDERED // "
                    +weatherTerminal.metrics.length+" / "
                    +weatherTerminal.hourlySamples.length+" / "
                    +weatherTerminal.dailySamples.length+" // READY "
                    +weatherTerminal.forecastReady);
            if(!weatherTerminal.currentMetricItem
                || !weatherTerminal.hourlyItem || !weatherTerminal.dailyItem)
                return root.fail("INSTRUMENT_GEOMETRY_MISSING");
            const dailyBottom=weatherTerminal.dailyItem.mapToItem(
                weatherTerminal,0,weatherTerminal.dailyItem.height).y;
            if(dailyBottom>weatherTerminal.height-1
                || dailyBottom<90)
                return root.fail("DAILY_INSTRUMENT_CLIPPED // "+dailyBottom);
            if(root.phase===0) {
                if(weatherTerminal.height!==164)
                    return root.fail("FULL_HEIGHT");
                root.phase=1;
                return;
            }
            if(root.phase===1) {
                if(weatherTerminal.height!==158)
                    return root.fail("OVERVIEW_HEIGHT");
                observations.forecastReady=false;
                root.phase=2;
                return;
            }
            if(weatherTerminal.hourlySamples.length!==0
                || weatherTerminal.dailySamples.length!==0)
                return root.fail("STALE_FORECAST_ON_UNREADY_SOURCE");
            root.done=true;
            console.log("W8_NATIVE_PASS // UNIFIED_TERMINAL_FULL_OVERVIEW_AND_NO_STALE_FORECAST");
            Qt.quit();
        }
    }
}
