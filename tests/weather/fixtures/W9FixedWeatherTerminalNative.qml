import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W14 // Native Quickshell test of the visual hierarchy, real forecast
// record counts, contextual timestamps, padded rail and preserved TWILIGHT.
ShellRoot {
    id: root
    property int ticks: 0
    property int phase: 0
    property bool finished: false
    readonly property var pages: ["weather","twilight"]
    function fail(reason) {
        if(finished)return;
        finished=true;
        console.error("W14_NATIVE_FAIL // "+reason);
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
    // W14 // Capture the actual offscreen Quickshell arrangement for
    // operator visual review. The capture is diagnostic, never production.
    property bool previewRequested: false
    Timer {
        interval: 250
        repeat: true
        running: !root.finished
        onTriggered: {
            root.ticks++;
            if(root.ticks>40)return root.fail("TIMEOUT");
            const host=weather.activePanelLoader.item;
            if(!host || !host.renderer || !host.viewport
                || !host.pageRail || !host.combinedPanel || !host.solarVisual) {
                if(root.ticks>12)return root.fail("COMBINED_HOST_MISSING");
                return;
            }
            const sky=host.renderer;
            const combined=host.combinedPanel;
            const solar=host.solarVisual;
            if(!host.pageRail.visible || host.pageRail.height!==24
               || !host.modeHeader || host.modeHeader.height!==18
               || host.pageRail.y <= host.modeHeader.height
               || sky.visualScroll.interactive)
                return root.fail("HEADER_SPACING_OR_SCROLL");
            if(sky.visualScroll.contentY!==0)
                return root.fail("SCROLL_OFFSET_LEAK");
            if(root.phase===0) {
                if(host.activeInstrument!=="weather")
                    return root.fail("COMBINED_NOT_DEFAULT");
                if(!combined.visible || sky.visible)
                    return root.fail("WEATHER_NOT_VISIBLE");
                if(combined.hourRepeater.count!==6
                   || combined.dayCardsRepeater.count!==3
                   || sky.hourlyForecast.length!==6
                   || sky.dailyForecast.length!==3)
                    return root.fail("ORIGINAL_FORECAST_ROWS_LOST");

                const bottom=combined.footerItem.mapToItem(
                    combined,0,combined.footerItem.height).y;
                if(bottom>combined.height+1 ||
                   bottom<combined.height-16)
                    return root.fail("INSTRUMENT_DECK_OVERFLOW // "+bottom);

                if(combined.currentItem.height<65 ||
                   combined.hourlyItem.height<77 ||
                   combined.dailyItem.height<30)
                    return root.fail("INSUFFICIENT_INSTRUMENT_HEIGHT // "
                      +combined.currentItem.height+" / "
                      +combined.hourlyItem.height+" / "
                      +combined.dailyItem.height);
                if(combined.currentItem.mainGlyph.width<54 ||
                   combined.currentItem.mainTemperature.font.pixelSize<36 ||
                   combined.currentItem.weatherMeters.count!==4)
                    return root.fail("HERO_WEATHER_INSTRUMENT_TOO_SMALL");
                for(const idx of [0,1,2]) {
                    const m=combined.currentItem.weatherMeters.itemAt(idx);
                    if(!m || !m.meter.visible || m.meter.height<5)
                        return root.fail("CURRENT_METER_MISSING_"+idx);
                }
                const hour=combined.hourRepeater.itemAt(0);
                if(!hour || !hour.glyph || !hour.rainMeter ||
                   !hour.timeItem.text.includes("11/10") ||
                   hour.glyph.width<22 || hour.rainMeter.height<4)
                    return root.fail("FORECAST_HOUR_CONTEXT_OR_SYMBOL");
                const dailyBottom=combined.dailyItem.mapToItem(
                    combined,0,combined.dailyItem.height).y;
                if(dailyBottom>combined.height)
                    return root.fail("DAILY_STRIP_OVERFLOW");

                if(!root.previewRequested) {
                    root.previewRequested=true;
                    window.contentItem.grabToImage(function(image) {
                        if(image && image.saveToFile(
                                "/tmp/weather-w14-visual-preview.png"))
                            console.log("W14_PREVIEW_CAPTURED");
                    },Qt.size(1040,600));
                    return;
                }

                host.activeInstrument="twilight";
                root.phase=1;
                return;
            }
            if(root.phase===1) {
                if(host.activeInstrument!=="twilight" || sky.visible)
                    return;
                if(sky.weatherFocus!=="twilight")
                    return root.fail("TWILIGHT_ROUTE");
                const grid=host.twilightGrid;
                const graph=host.solarGraphViewport;
                if(!grid || !graph || !grid.visible || !graph.visible
                   || grid.x!==0 || grid.y!==0)
                    return root.fail("TWILIGHT_FULL_GRID_MISSING");
                if(Math.abs(grid.width-host.viewport.width)>1
                   || Math.abs(graph.width-host.viewport.width)>1
                   || Math.abs(solar.width-graph.width)>1
                   || Math.abs(solar.height-graph.height)>1)
                    return root.fail("TWILIGHT_INSET_GRAPH");
                const graphBottom=graph.mapToItem(
                    host.viewport,0,graph.height).y;
                if(Math.abs(graphBottom-host.viewport.height)>2
                   || Math.abs(graph.y-grid.height)>2)
                    return root.fail("TWILIGHT_BANDS_NOT_FILLING // "
                        +graphBottom+" / "+host.viewport.height);
                if(!solar.showSun || solar.showMoon
                   || !solar.fullBleedSolar || solar.scale!==1
                   || solar.solarCanvasItem.width<graph.width*0.80
                   || solar.solarCanvasItem.height<40)
                    return root.fail("SOLAR_CURVE_NOT_FULL_BLEED // "
                        +solar.solarCanvasItem.width+"x"
                        +solar.solarCanvasItem.height);
                host.activeInstrument="weather";
                sampleWeather.forecastReady=false;
                root.phase=2;
                return;
            }
            if(root.phase===2) {
                if(combined.hourlyRows.length!==0
                   || combined.dailyRows.length!==0)
                    return root.fail("STALE_FORECAST_PRESENT");
                root.finished=true;
                console.log("W14_NATIVE_PASS // LINE_GLYPH_TERMINAL_AND_PADDED_RAIL_520X300");
                Qt.quit();
            }
        }
    }
}
