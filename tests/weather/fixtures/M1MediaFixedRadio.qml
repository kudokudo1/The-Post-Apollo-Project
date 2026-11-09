import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather
import "widgets/weather/StationSubjectHeaderGeometry.js" as Geometry

// M1 // Disposable Quickshell native witness. Radio controller is NOT
// activated: no MPD commands, directory network search, or saved-file writes.
ShellRoot {
    id: root
    property bool done:false
    property int phase:0
    property int ticks:0
    property string requestedRoute:""
    function find(item,name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        for(const child of (item.children||[])) {
            const match=find(child,name);
            if(match)return match;
        }
        return null;
    }
    function fail(reason) {
        if(done)return;
        done=true;
        console.error("M1_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    Window {
        visible:true
        width:520
        height:410
        color:"black"
        Item {
            id:frame
            anchors.fill:parent
            Weather.StationMediaHeader {
                id:header
                anchors.top:parent.top
                anchors.left:parent.left
                anchors.right:parent.right
                subjectRoute: root.phase<3 ? "media/radio/full"
                    : root.phase===3 ? "media/news/full"
                    : "media/services/health"
                onRouteRequested: function(path){root.requestedRoute=path;}
            }
            Weather.StationRadio {
                id:radio
                visible:root.phase<3
                anchors.top:header.bottom
                anchors.left:parent.left
                anchors.right:parent.right
                anchors.bottom:parent.bottom
                stationOpen:false
                subjectRoute:root.phase===2?"media/overview":"media/radio/full"
            }
            Weather.StationNewsHub {
                id:news
                visible:root.phase===3
                anchors.top:header.bottom
                anchors.left:parent.left
                anchors.right:parent.right
                anchors.bottom:parent.bottom
                stationOpen:false
                embeddedHeader:true
                subjectRoute:"media/news/full"
            }
            Weather.StationMediaServicesPane {
                id:services
                visible:root.phase>=4
                anchors.top:header.bottom
                anchors.left:parent.left
                anchors.right:parent.right
                anchors.bottom:parent.bottom
            }
        }
    }
    Timer {
        interval:180
        running:!root.done
        repeat:true
        onTriggered:{
            root.ticks++;
            if(root.ticks>35)return root.fail("TIMEOUT");
            const title=find(header,"media-m1-c44-title");
            const rail=find(header,"media-m1-c44-mode-rail");
            const divider=find(header,"media-m1-c44-divider");
            const search=find(radio,"media-m1-radio-search-fixed");
            const list=find(radio,"media-m1-radio-directory-scroll");
            const footer=find(radio,"media-m1-radio-transport-fixed");
            const preset=find(radio,"media-m1-radio-preset-rail");
            const query=find(radio,"media-m1-radio-query-rail");
            const transport=find(radio,"media-m1-radio-transport-row");
            if(!title||!rail||!divider||!search||!list
                ||!footer||!preset||!query||!transport)return;
            if(Math.abs(title.y-Geometry.titleTop())>1
                ||Math.abs(rail.y-Geometry.tabsTop())>1
                ||Math.abs(divider.y-Geometry.ruleTop())>1
                ||Math.abs(radio.y-Geometry.contentTop())>1
                ||Math.abs(header.height-Geometry.contentTop())>1)
                return root.fail("C44_HEADER_BOUNDS");
            if(root.phase<2) {
                if(!search.visible || !footer.visible
                    || search.height<45 || footer.height<40
                    || Math.abs(search.y-2)>1
                    || Math.abs(footer.y+footer.height-radio.height+3)>1
                    || list.y < search.y+search.height
                    || list.y+list.height>footer.y
                    || list.height<=15
                    || transport.children.length!==7
                    || preset.children.length<6)
                    return root.fail("RADIO_PINNED_SEARCH_LIST_TRANSPORT_BOUNDS"
                        +" // search="+search.height
                        +" list="+list.height+" footer="+footer.height
                        +" controls="+transport.children.length);
                if(root.phase===0) {
                    list.contentY=Math.max(0,list.contentHeight-list.height);
                    root.phase=1;return;
                }
                if(Math.abs(search.y-2)>1
                    ||Math.abs(footer.y+footer.height-radio.height+3)>1)
                    return root.fail("SCROLL_SHIFTED_FIXED_CONTROLS");
                root.phase=2;return;
            }
            if(root.phase===2) {
                if(search.visible || footer.visible
                    || list.height<radio.height-10)
                    return root.fail("OVERVIEW_COMPACT_SCROLL");
                root.phase=3;return;
            }
            if(root.phase===3) {
                const old=find(news,"media-m1-legacy-news-title");
                if(!old||old.visible)
                    return root.fail("DUPLICATE_SCROLLING_NEWS_HEADING");
                root.phase=4;return;
            }
            if(root.phase===4) {
                const dash=find(services,"media-m1-services");
                if(!dash || !services.visible || !header.sections.length)
                    return root.fail("SERVICES_NOT_MOUNTED");
                root.done=true;
                console.log("M1_NATIVE_PASS // RADIO_PINNED_CONTROLS_MEDIA_NEWS_HEADERS_SERVICES");
                Qt.quit();
            }
        }
    }
}
