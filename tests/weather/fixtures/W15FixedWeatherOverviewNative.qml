import QtQuick
import QtQml
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W16 // Synthetic-only native test of one continuous WEATHER OVERVIEW.
// Both Snapshot and Auto rows must fit at 440x275 AND 520x300 without panning.
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool finished: false
    property bool capturedCompact: false
    property bool capturedWide: false
    property bool capturedTall: false
    function fail(message) {
        if(finished)return;
        finished=true;
        console.error("W16_OVERVIEW_NATIVE_FAIL // "+message);
        Qt.quit();
    }
    QtObject {
        id: observation
        property bool ready: true
        property bool loading: false
        property bool forecastReady: true
        property bool aqiReady: true
        property double tempF: 57
        property double feelsLikeF: 53
        property string condition: "Clear"
        property int weatherCode: 0
        property double humidity: 56
        property double windMph: 7
        property string windDirection: "W"
        property double aqi: 60
        property string aqiLabel: "MODERATE"
        property double pm25: 10.2
        property double pressureHpa: 1015
        property double visibilityMiles: 6.8
        property double uvIndex: 0
        property var hourlyForecast: [
            {date:"2026-11-11",time:"900",timeLabel:"9 AM",
             tempF:56,condition:"Clear",weatherCode:0,chanceRain:5},
            {date:"2026-11-11",time:"1200",timeLabel:"12 PM",
             tempF:58,condition:"Cloudy",weatherCode:3,chanceRain:15},
            {date:"2026-11-11",time:"1500",timeLabel:"3 PM",
             tempF:60,condition:"Thunderstorm",weatherCode:95,chanceRain:40},
            {date:"2026-11-11",time:"1800",timeLabel:"6 PM",
             tempF:58,condition:"Cloudy",weatherCode:3,chanceRain:35},
            {date:"2026-11-11",time:"2100",timeLabel:"9 PM",
             tempF:54,condition:"Rain",weatherCode:61,chanceRain:20},
            {date:"2026-11-12",time:"0000",timeLabel:"12 AM",
             tempF:49,condition:"Clear",weatherCode:0,chanceRain:0}
        ]
        property var dailyForecast: [
            {date:"2026-11-11",maxTempF:64,minTempF:45,
             weatherCode:0,condition:"Clear",chanceRain:5},
            {date:"2026-11-12",maxTempF:61,minTempF:46,
             weatherCode:3,condition:"Cloudy",chanceRain:35},
            {date:"2026-11-13",maxTempF:62,minTempF:49,
             weatherCode:95,condition:"Thunderstorm",chanceRain:70}
        ]
    }
    Window {
        id: window
        width: 440
        height: 275
        visible: true
        color: "black"
        Weather.StationHome {
            id: overview
            anchors.fill: parent
            subjectRoute: "weather/overview"
            weatherService: observation
            runtimeNowMs: 1794397200000
        }
    }
    function checkFit() {
        const scroll=overview.overviewViewportItem;
        const content=overview.overviewContentItem;
        const summary=overview.overviewSummaryItem;
        const rail=overview.overviewRailItem;
        const snap=overview.overviewSnapshotItem;
        const autoCards=overview.overviewRelevantItem;
        if(!scroll || !content || !summary || !rail || !snap || !autoCards)
            return "ONE_PAGE_ITEMS_MISSING";
        if(scroll.interactive || scroll.contentHeight>scroll.height+1
           || Math.abs(scroll.contentY)>1)
            return "STILL_PANNING";
        if(summary.height<150 || !summary.compactInstrument ||
           summary.compactInstrument.currentMeters.count!==4 ||
           summary.compactInstrument.hourRepeater.count!==6 ||
           summary.compactInstrument.dayRepeater.count!==3)
            return "WEATHER_MIRROR_DATA_LOST";
        if(summary.compactInstrument.hourlyStrip.height<40
           || summary.compactInstrument.dailyStrip.height<24)
            return "WEATHER_MIRROR_INSTRUMENTS_SHRUNK";

        if(!snap.visible || !autoCards.visible)
            return "CARD_GROUPS_NOT_BOTH_VISIBLE";
        if(content.implicitHeight>scroll.height+1)
            return "ONE_PAGE_CLIPPED "+content.implicitHeight
                +" > "+scroll.height;
        if(snap.height<(window.height<286 ? 46 : 55)
           || autoCards.height<(window.height<286 ? 46 : 55))
            return "CARDS_TOO_SMALL "+snap.height+"/"+autoCards.height;
        if(snap.height>60 || autoCards.height>60)
            return "OVERSIZED_EMPTY_CARDS "+snap.height+"/"+autoCards.height;
        if(rail.height!==31 || rail.buttonRepeater.count!==3
           || rail.width<content.width-1)
            return "W21_OVERVIEW_RAIL_MISSING";
        for(let i=0;i<3;i++) {
            const button=rail.buttonRepeater.itemAt(i);
            if(!button || button.width<rail.width/3-6
                || button.height!==25)
                return "W21_RAIL_BUTTON_NOT_FULL_WIDTH_"+i;
        }
        if(Math.abs(summary.height+rail.height+snap.height
                    +autoCards.height-scroll.height)>2)
            return "OVERVIEW_HEIGHT_BUDGET_LOST";
        if(window.height>=500 && (summary.height<330 ||
           summary.compactInstrument.mainGlyph.width<80 ||
           summary.compactInstrument.hourlyStrip.height<120))
            return "TALL_WEATHER_INSTRUMENT_STILL_TINY";
        if(window.height>=500) {
            const instrument=summary.compactInstrument;
            if(snap.height>60 || autoCards.height>60)
                return "W20_LOWER_CARDS_NOT_REDUCED";
            if(instrument.currentStrip.height<130 ||
               instrument.currentStrip.height>134)
                return "W20_NOW_BAND_CHANGED "+instrument.currentStrip.height;
            if(instrument.dailyStrip.height<50 ||
               instrument.dailyStrip.height>53)
                return "W20_THREE_DAY_CHANGED "+instrument.dailyStrip.height;
            if(instrument.hourlyStrip.height<120 ||
               instrument.hourlyStrip.height<instrument.dailyStrip.height*2.3)
                return "W20_SIX_PERIOD_FORECAST_TOO_SMALL";
        }
        if(summary.glyph(95,"Thunderstorm")!=="⚡︎")
            return "THUNDERBOLT_CODEPOINT_WRONG";
        // W19 // Rain meters are a data reading between temperature
        // and percentage, for every hourly AND daily forecast item.
        const instrument=summary.compactInstrument;
        function barBetween(item,label) {
            if(!item || !item.rainMeter || !item.temperatureItem || !item.chanceItem)
                return label+"_REQUIRED_ITEMS_MISSING";
            const tempBottom=item.temperatureItem.mapToItem(
                item,0,item.temperatureItem.height).y;
            const meterTop=item.rainMeter.mapToItem(item,0,0).y;
            const meterBottom=item.rainMeter.mapToItem(
                item,0,item.rainMeter.height).y;
            const chanceTop=item.chanceItem.mapToItem(item,0,0).y;
            if(item.rainMeter.height<5 || tempBottom>meterTop+1
               || meterBottom>chanceTop+1)
                return label+"_RAIN_METER_ORDER "+tempBottom+"/"
                    +meterTop+"/"+meterBottom+"/"+chanceTop;
            return "";
        }
        for(let i=0;i<6;i++) {
            const problem=barBetween(instrument.hourRepeater.itemAt(i),
                                     "HOUR_"+i);
            if(problem!=="")return problem;
        }
        for(let i=0;i<3;i++) {
            const problem=barBetween(instrument.dayRepeater.itemAt(i),
                                     "DAY_"+i);
            if(problem!=="")return problem;
        }
        if(window.height>=500) {
            if(instrument.mainGlyph.width<95)
                return "NOW_HERO_ARTWORK_NOT_ENLARGED";
            for(let i=0;i<3;i++) {
                const metric=instrument.currentMeters.itemAt(i);
                const valueBottom=metric.readoutRow.mapToItem(
                    metric,0,metric.readoutRow.height).y;
                if(metric.meter.height<6 || metric.meter.y<valueBottom-1
                   || metric.height-metric.meter.y-metric.meter.height<5)
                    return "TOP_METERS_NOT_CENTERED_"+i;
            }
        }
        for(const group of [snap,autoCards]) {
            for(let i=0;i<group.children.length;i++) {
                const c=group.children[i];
                if(!c || !c.overviewDense || !c.contentItem)continue;
                const contentHeight=c.contentItem.childrenRect.height;
                if(contentHeight>c.contentItem.height+2)
                    return "DENSE_CARD_TEXT_OVERFLOW "+contentHeight
                       +" / "+c.contentItem.height;
                // W20 // Reduced support rows intentionally have 1px
                // spacing at 68px. Their actual text bounds are checked
                // immediately above; old W18 >=2px spacing was tied to 88px.
                // W21 // Small supporting rows can use zero spare spacing;
                // the bounds check above still rejects actual text clipping.
                if(window.height>=500 && c.height>66
                   && c.contentItem.spacing<1)
                    return "TALL_CARD_TEXT_STILL_TINY";
            }
        }
        return "";
    }
    Timer {
        interval: 250
        running: !root.finished
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>40)return root.fail("TIMEOUT");
            if(!overview.overviewSummaryItem ||
               !overview.overviewViewportItem)return;
            const error=root.checkFit();
            if(error!=="")return root.fail(error);
            if(root.phase===0) {
                if(!root.capturedCompact) {
                    root.capturedCompact=true;
                    window.contentItem.grabToImage(function(image) {
                        if(image && image.saveToFile("/tmp/weather-w17-overview-compact.png"))
                            console.log("W16_OVERVIEW_COMPACT_CAPTURED");
                    },Qt.size(880,550));
                    return;
                }
                window.width=520;
                window.height=300;
                root.phase=1;
                return;
            }
            if(root.phase===1) {
                if(window.width!==520 || overview.overviewSnapshotItem.width<500)
                    return root.fail("LARGE_VIEW_NOT_RESIZED");
                if(!root.capturedWide) {
                    root.capturedWide=true;
                    window.contentItem.grabToImage(function(image) {
                        if(image && image.saveToFile("/tmp/weather-w17-overview-wide.png"))
                            console.log("W16_OVERVIEW_WIDE_CAPTURED");
                    },Qt.size(1040,600));
                    return;
                }
                window.height=500;
                root.phase=2;
                return;
            }
            if(root.phase===2) {
                if(window.height!==500 || overview.overviewSnapshotItem.width<500)
                    return root.fail("TALL_VIEW_NOT_RESIZED");
                if(!root.capturedTall) {
                    root.capturedTall=true;
                    window.contentItem.grabToImage(function(image) {
                        if(image && image.saveToFile("/tmp/weather-w18-overview-tall.png"))
                            console.log("W18_OVERVIEW_TALL_CAPTURED");
                    },Qt.size(1040,1000));
                    return;
                }
                root.finished=true;
                console.log("W16_OVERVIEW_NATIVE_PASS // BOTH_CARD_GROUPS_NO_PAN_440_520");
                console.log("W18_OVERVIEW_NATIVE_PASS // TALL_VIEW_NO_EMPTY_PANELS");
                Qt.quit();
            }
        }
    }
}
