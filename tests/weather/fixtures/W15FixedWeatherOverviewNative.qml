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
             tempF:60,condition:"Thunderstorm",weatherCode:95,chanceRain:40}
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
        const snap=overview.overviewSnapshotItem;
        const autoCards=overview.overviewRelevantItem;
        if(!scroll || !content || !summary || !snap || !autoCards)
            return "ONE_PAGE_ITEMS_MISSING";
        if(scroll.interactive || scroll.contentHeight>scroll.height+1
           || Math.abs(scroll.contentY)>1)
            return "STILL_PANNING";
        if(summary.height!==158)
            return "WEATHER_SUMMARY_CHANGED";
        if(!snap.visible || !autoCards.visible)
            return "CARD_GROUPS_NOT_BOTH_VISIBLE";
        if(content.implicitHeight>scroll.height+1)
            return "ONE_PAGE_CLIPPED "+content.implicitHeight
                +" > "+scroll.height;
        if(snap.height<55 || autoCards.height<55)
            return "CARDS_TOO_SMALL "+snap.height+"/"+autoCards.height;
        if(summary.glyph(95,"Thunderstorm")!=="⚡︎")
            return "THUNDERBOLT_CODEPOINT_WRONG";
        for(const group of [snap,autoCards]) {
            for(let i=0;i<group.children.length;i++) {
                const c=group.children[i];
                if(!c || !c.overviewDense || !c.contentItem)continue;
                const contentHeight=c.contentItem.childrenRect.height;
                if(contentHeight>c.contentItem.height+2)
                    return "DENSE_CARD_TEXT_OVERFLOW "+contentHeight
                       +" / "+c.contentItem.height;
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
                        if(image && image.saveToFile("/tmp/weather-w16-overview-compact.png"))
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
                        if(image && image.saveToFile("/tmp/weather-w16-overview-wide.png"))
                            console.log("W16_OVERVIEW_WIDE_CAPTURED");
                    },Qt.size(1040,600));
                    return;
                }
                root.finished=true;
                console.log("W16_OVERVIEW_NATIVE_PASS // BOTH_CARD_GROUPS_NO_PAN_440_520");
                Qt.quit();
            }
        }
    }
}
