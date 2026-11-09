import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// C44 // Disposable offscreen top-frame geometry witness across all five
// COSMOS landing families. Only one page is mounted at once; no live host,
// authenticated provider, local store or persistent update is touched.
ShellRoot {
    id: root
    property int caseIndex: 0
    property int ticks: 0
    property int verified: 0
    property bool done: false
    readonly property var cases: [
        ["cosmos-c44-mode-title","cosmos-c44-mode-tabs",
         "cosmos-c44-mode-divider","cosmos-c44-mode-stage"],
        ["cosmos-c9-moon-free-header","cosmos-c18-moon-fullwidth-mode-rail",
         "cosmos-c23-moon-overview-divider","cosmos-c9-moon-hero-row"],
        ["cosmos-c44-moon-year-header","cosmos-c11-moon-year-mode-rail",
         "cosmos-c23-moon-year-divider","cosmos-c11-moon-year-wheel"],
        ["cosmos-c44-space-title","cosmos-c42-space-view-modes",
         "cosmos-c44-space-divider","cosmos-c42-space-metrics"],
        ["cosmos-c44-overview-title","cosmos-c44-overview-mode-rail",
         "cosmos-c44-overview-divider","cosmos-c44-overview-stage"]
    ]
    function find(item,name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        const children=item.children || [];
        for(let i=0;i<children.length;i++) {
            const f=find(children[i],name);
            if(f)return f;
        }
        return null;
    }
    function findAll(item,name) {
        if (!item) return [];
        let result=item.objectName===name ? [item] : [];
        const children=item.children || [];
        for(let i=0;i<children.length;i++)
            result=result.concat(findAll(children[i],name));
        return result;
    }
    function buttons(item,index) {
        if (index===0) return findAll(item,"cosmos-c44-mode-button");
        if (index===1) return [
            find(item,"cosmos-c18-moon-observation-tab"),
            find(item,"cosmos-c11-open-moon-year")
        ];
        if (index===2) return [
            find(item,"cosmos-c11-back-to-moon"),
            find(item,"cosmos-c17-moon-wheel-tab")
        ];
        if (index===3) return findAll(item,"cosmos-c44-space-button");
        return findAll(item,"cosmos-c44-overview-button");
    }
    function fail(what){
        if(done)return;
        done=true;
        console.error("C44_NATIVE_FAIL // "+what+" CASE "+caseIndex);
        Qt.quit();
    }
    function closeTo(actual,expected) {
        return isFinite(actual) && Math.abs(actual-expected)<0.15;
    }
    QtObject {
        id: fakeWeather
        property var latitude: ""
        property var longitude: ""
        property var dailyForecast: []
        property var hourlyForecast: []
        property bool forecastReady: false
        property bool aqiReady: false
        property bool aqiLoading: false
        property int airQualityUtcOffsetMinutes: -300
        property bool ready: false
        property bool loading: false
        property string localObservationDateTime: ""
        property real localObservationAnchorMs: 0
    }
    QtObject {
        id: fakeSpace
        property bool ready: false
        property bool loading: false
        property bool kpReady: false
        property bool kpLoading: false
        property real kp: 0
        property string kpLabel: ""
        property string kpErrorText: ""
        property var kpLastUpdated: null
        property string kpTime: ""
        property bool usingPersistentKpCache: false
        property var kpHistory: []
        property var kpHistorySummary: ({})
        property bool solarWindReady: false
        property bool solarWindLoading: false
        property real solarWindSpeed: 0
        property string solarWindErrorText: ""
        property var solarWindLastUpdated: null
        property string solarWindTime: ""
        property bool usingPersistentSolarWindCache: false
        property bool magneticFieldReady: false
        property bool magneticFieldLoading: false
        property real magneticFieldBt: 0
        property real magneticFieldBz: 0
        property string magneticFieldErrorText: ""
        property var magneticFieldLastUpdated: null
        property string magneticFieldTime: ""
        property bool usingPersistentMagneticFieldCache: false
        property bool solarFluxReady: false
        property bool solarFluxLoading: false
        property real solarFlux: 0
        property string solarFluxErrorText: ""
        property var solarFluxLastUpdated: null
        property string solarFluxTime: ""
        property bool usingPersistentSolarFluxCache: false
        property string kpText: "--"
        property string solarWindText: "--"
        property string bzText: "--"
        property string bzLabel: ""
        property string solarFluxText: "--"
    }
    Window {
        id: fixtureWindow
        visible: true
        width: 520
        height: 340
        color: "black"
        Loader {
            id: panelLoader
            anchors.fill: parent
            sourceComponent: root.caseIndex===0 ? modeCase
                : root.caseIndex===1 ? moonCase
                : root.caseIndex===2 ? yearCase
                : root.caseIndex===3 ? spaceCase : overviewCase
        }
    }
    Component {
        id: modeCase
        Weather.StationCosmosModesPane {
            subjectRoute:"cosmos/planets-stars/celestial-fix"
            weatherService:fakeWeather
            spaceService:fakeSpace
            runtimeNowMs:Date.UTC(2026,10,9,8,30)
        }
    }
    Component {
        id: moonCase
        Weather.StationCosmosMoonCompactPane {
            weatherService:fakeWeather
            spaceService:fakeSpace
            runtimeNowMs:Date.UTC(2026,10,9,8,30)
        }
    }
    Component {
        id: yearCase
        Weather.StationCosmosAnnualWheelPane {
            subject:"moon"
            weatherService:fakeWeather
            runtimeNowMs:Date.UTC(2026,10,9,8,30)
        }
    }
    Component {
        id: spaceCase
        Weather.StationCosmosSpaceWeatherHubPane {
            spaceService:fakeSpace
            weatherService:fakeWeather
            runtimeNowMs:Date.UTC(2026,10,9,8,30)
            activateLiveFeeds:false
        }
    }
    Component {
        id: overviewCase
        Weather.StationCosmosOverviewPane {
            spaceService:fakeSpace
            weatherService:fakeWeather
            runtimeNowMs:Date.UTC(2026,10,9,8,30)
        }
    }
    Timer {
        interval:120
        running:!root.done
        repeat:true
        onTriggered:{
            root.ticks++;
            if(root.ticks>90) return root.fail("TIMEOUT");
            if(!panelLoader.item || panelLoader.status!==Loader.Ready)return;
            const panel=panelLoader.item;
            const c=root.cases[root.caseIndex];
            const title=root.find(panel,c[0]);
            const tabs=root.find(panel,c[1]);
            const rule=root.find(panel,c[2]);
            const body=root.find(panel,c[3]);
            if(!title || !tabs || !rule || !body)return;
            const a=title.mapToItem(panel,0,0);
            const b=tabs.mapToItem(panel,0,0);
            const d=rule.mapToItem(panel,0,0);
            const f=body.mapToItem(panel,0,0);
            if(!root.closeTo(a.x,6)||!root.closeTo(a.y,6)
                ||!root.closeTo(title.width,508)
                ||!root.closeTo(title.height,18)
                ||!root.closeTo(b.x,6)||!root.closeTo(b.y,28)
                ||!root.closeTo(tabs.width,508)
                ||!root.closeTo(tabs.height,27)
                ||!root.closeTo(d.x,6)||!root.closeTo(d.y,60)
                ||!root.closeTo(rule.width,508)
                ||!root.closeTo(rule.height,2)
                ||!root.closeTo(f.x,6)||!root.closeTo(f.y,65)
                ||!root.closeTo(body.width,508)
                ||body.height<=0)
                return root.fail("HEADER_GEOMETRY_MISMATCH: "+
                    [a.x,a.y,title.width,title.height,
                     b.x,b.y,tabs.width,tabs.height,
                     d.x,d.y,rule.width,rule.height,
                     f.x,f.y,body.width,body.height].join(","));
            // Check each actual clickable button, not just the row
            // container. This catches asymmetric padding and leftover
            // old hardcoded widths in individual panels.
            const buttons=root.buttons(panel,root.caseIndex);
            const count=root.caseIndex===4 ? 3 : 2;
            const expected=(508-(count-1)*4)/count;
            if(buttons.length!==count)
                return root.fail("WRONG_TOP_BUTTON_COUNT");
            for(let i=0;i<count;i++){
                const button=buttons[i];
                if(!button)return root.fail("MISSING_TOP_BUTTON_"+i);
                const loc=button.mapToItem(panel,0,0);
                if(!root.closeTo(loc.x,6+i*(expected+4))
                    ||!root.closeTo(loc.y,28)
                    ||!root.closeTo(button.width,expected)
                    ||!root.closeTo(button.height,27))
                    return root.fail("UNEQUAL_TOP_BUTTON_"+i+": "+
                        [loc.x,loc.y,button.width,button.height].join(","));
            }
            root.verified++;
            if(root.verified===root.cases.length){
                root.done=true;
                console.log("C44_NATIVE_PASS // ALL_FIVE_COSMOS_FRAMES_6_18_27_2_65");
                Qt.quit();
                return;
            }
            root.caseIndex++;
        }
    }
}
