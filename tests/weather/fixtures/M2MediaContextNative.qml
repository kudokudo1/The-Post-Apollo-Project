import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather
import "widgets/weather/StationSubjectHeaderGeometry.js" as Geometry

// M2 // One isolated real RADIO/NEWS/SERVICES fixture. No actual radio
// search/play, weather fetch, disk writes or live desktop activation.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
    property int lastPreset: -1
    property string lastNews: ""
    property string lastService: ""
    property string lastRoute: ""
    property var favoriteSamples: {
        const a=[];
        for(let i=0;i<10;i++)a.push({title:"F"+(i+1)});
        return a;
    }
    property var recentSamples: {
        const a=[];
        for(let i=0;i<8;i++)a.push({title:"R"+(i+1)});
        return a;
    }
    function find(item,name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        for(const child of (item.children||[])) {
            const x=find(child,name);
            if(x)return x;
        }
        return null;
    }
    function count(item,name) {
        if(!item)return 0;
        let n=item.objectName===name ? 1 : 0;
        for(const child of (item.children||[]))n+=count(child,name);
        return n;
    }
    function fail(text) {
        if(done)return;
        done=true;
        console.error("M2_NATIVE_FAIL // "+text);
        Qt.quit();
    }

    Window {
        visible: true
        width: 520
        height: 620
        color: "black"
        Item {
            id: frame
            anchors.fill: parent

            Weather.StationMediaHeader {
                id: header
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                subjectRoute: root.phase<3 ? "media/radio/full"
                    : root.phase===3 ? "media/news/full"
                    : root.phase===4 ? "media/services/health"
                    : "media/creators/saved"
                radioPresets: radio.presets
                radioPresetIndex: 0
                radioCanOperate: true
                newsSection: news.effectiveSection
                servicesMode: services.viewMode
                radioStatus: "STOPPED"
                onRadioPresetRequested: function(i) {root.lastPreset=i;}
                onNewsSectionRequested: function(section) {
                    root.lastNews=section;
                    news.selectSection(section);
                }
                onServicesModeRequested: function(mode) {
                    root.lastService=mode;
                    services.viewMode=mode;
                }
                onRouteRequested: function(path) { root.lastRoute=path; }
            }
            Weather.StationRadio {
                id: radio
                anchors.top: header.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 360
                visible: root.phase<3
                stationOpen: false
                subjectRoute: "media/radio/full"
                embeddedHeader: true
            }
            Weather.StationNewsHub {
                id: news
                anchors.top: header.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 360
                visible: root.phase===3
                stationOpen: false
                subjectRoute: "media/news/full"
                embeddedHeader: true
            }
            Weather.StationMediaServicesPane {
                id: services
                anchors.top: header.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 360
                visible: root.phase===4
                embeddedHeader: true
            }
            Weather.StationRadioSavedStrips {
                id: sample
                anchors.top: parent.top
                anchors.topMargin: 465
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                favoriteItems: root.favoriteSamples
                recentItems: root.recentSamples
                canRecall: true
            }
        }
    }
    Timer {
        running: !root.done
        interval: 180
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>35)return root.fail("TIMEOUT");
            const rail=find(header,"media-m1-c44-mode-rail");
            const title=find(header,"media-m1-c44-title");
            const divider=find(header,"media-m1-c44-divider");
            const saved=find(radio,"media-m2-radio-fixed-saved");
            const scroll=find(radio,"media-m1-radio-directory-scroll");
            const search=find(radio,"media-m1-radio-search-fixed");
            const footer=find(radio,"media-m1-radio-transport-fixed");
            const favorites=find(sample,"media-m2-favorite-scroll");
            const recents=find(sample,"media-m2-recent-scroll");
            if(!rail||!title||!divider||!saved||!scroll||!search
                ||!footer||!favorites||!recents)return;
            if(header.height!==Geometry.contentTop()
                ||Math.abs(title.y-Geometry.titleTop())>1
                ||Math.abs(rail.y-Geometry.tabsTop())>1
                ||Math.abs(divider.y-Geometry.ruleTop())>1)
                return root.fail("C44_HEADER");
            if(root.phase===0) {
                if(!String(title.text).includes("RADIO // NEWS FIRST")
                    ||count(header,"media-m2-mode-news")!==1
                    ||count(header,"media-m2-mode-talk")!==1
                    ||count(header,"media-m2-mode-public")!==1
                    ||count(header,"media-m2-mode-weather")!==1
                    ||count(header,"media-m2-mode-us-radio")!==1
                    ||count(header,"media-m2-mode-all-radio")!==1
                    ||!saved.visible ||saved.height!==88
                    ||search.height>54 ||scroll.y<saved.y+saved.height
                    ||scroll.y+scroll.height>footer.y+1
                    ||scroll.height<20)
                    return root.fail("RADIO_FILTERS_SAVED_PINNED_BOUNDS"
                        +" // search="+search.height
                        +" saved="+saved.height
                        +" scroll="+scroll.height
                        +" footer="+footer.height);
                const talk=find(header,"media-m2-mode-talk");
                talk.clicked(null);
                root.phase=1;return;
            }
            if(root.phase===1) {
                if(root.lastPreset!==1)return root.fail("TALK_PRESET_SIGNAL");
                if(count(sample,"media-m2-favorite-tile")!==10
                    ||count(sample,"media-m2-recent-tile")!==8
                    ||favorites.contentWidth>favorites.width+1
                    ||recents.contentWidth>recents.width+1)
                    return root.fail("TEN_ACROSS_SQUARE_STRIPS");
                scroll.contentY=Math.max(0,scroll.contentHeight-scroll.height);
                root.phase=2;return;
            }
            if(root.phase===2) {
                if(search.y!==2 ||scroll.y<saved.y+saved.height
                    ||Math.abs(footer.y+footer.height-radio.height+3)>1)
                    return root.fail("SCROLL_MOVED_FIXED_REGIONS");
                root.favoriteSamples=root.favoriteSamples.concat(
                    [{title:"F11"},{title:"F12"}]);
                root.phase=3;return;
            }
            if(root.phase===3) {
                const congress=find(header,"media-m2-mode-congress");
                if(!congress ||count(sample,"media-m2-favorite-tile")!==12
                    ||favorites.contentWidth<=favorites.width
                    ||!String(title.text).includes("NEWS //"))
                    return root.fail("NEWS_TABS_OR_HORIZONTAL_OVERFLOW");
                congress.clicked(null);
                root.phase=4;return;
            }
            if(root.phase===4) {
                const sources=find(header,"media-m2-mode-sources");
                if(root.lastNews!=="CONGRESS"||news.section!=="CONGRESS"
                    ||!sources)return root.fail("NEWS_DELEGATION");
                sources.clicked(null);
                root.phase=5;return;
            }
            if(root.phase===5) {
                const radioButton=find(header,"media-m2-mode-radio");
                if(root.lastService!=="sources"||services.viewMode!=="sources"
                    ||!radioButton)return root.fail("SERVICES_DELEGATION");
                radioButton.clicked(null);
                root.phase=6;return;
            }
            if(root.phase===6) {
                if(root.lastRoute!=="media/radio/full")
                    return root.fail("CREATORS_FALLBACK_NAVIGATION");
                root.done=true;
                console.log("M2_NATIVE_PASS // CONTEXTUAL_RAILS_PINNED_TEN_ACROSS_RADIO_SQUARES");
                Qt.quit();
            }
        }
    }
}
