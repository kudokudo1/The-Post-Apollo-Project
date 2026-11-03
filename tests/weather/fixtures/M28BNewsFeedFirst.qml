import QtQuick
import Quickshell
import "widgets/weather"

// M28-B uses the real StationDiscovery NEWS renderer and a synthetic local
// provider to verify that HEADLINES appear before analytics, a real pointer
// opens the article inspector, and TRENDS/STORIES remain independent routes.
ShellRoot {
    id: root
    property bool done: false
    property int ticks: 0
    property string phase: "init"
    FloatingWindow {
        id: window
        title: "M28B-NEWS-FEED-FIRST"
        visible: true
        implicitWidth: 800
        implicitHeight: 720

        StationDiscovery {
            id: news
            anchors.fill: parent
            domain: "news"
            stationOpen: true
            newsSubjectRoute: "media/news/reports"
        }
    }
    function find(item,fn) {
        if(!item)return null;
        if(fn(item))return item;
        if(!item.children)return null;
        for(let i=0;i<item.children.length;i++) {
            const found=find(item.children[i],fn);
            if(found)return found;
        }
        return null;
    }
    function card(){
        return find(news,function(item){
            return item.modelData && item.modelData.title
                 === "M28B SYNTHETIC WEATHER REPORT"
                 && item.height >= 85;
        });
    }
    function divider(name) {
        return find(news,function(item){
            return item.title !== undefined && String(item.title).indexOf(name)===0;
        });
    }
    function scroll(){
        return find(news,function(item){
            return item.contentY !== undefined && item.contentHeight !== undefined
                   && item.contentHeight > item.height && item.height>500;
        });
    }
    function fail(reason){
        if(done)return;
        done=true;
        console.error("M28B_FAIL // "+reason+" phase="+phase);
    }
    Timer {
        interval: 70
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if(root.ticks===1||root.ticks%55===0)
                console.log("M28B_TICK // "+root.phase+
                            " rows="+news.visibleRows.length);
            if(root.phase==="init"){
                // Allow first-polish Qt Quick Column/Repeater layout to settle.
                if(root.ticks < 4 || news.visibleRows.length!==2)return;
                const feed=root.divider("NEWS HEADLINES // CURRENT FILTERED BATCH");
                const trend=root.divider("REPORTING TREND // CURRENT FILTERED BATCH");
                const stories=root.divider("STORY FAMILIES // CONSERVATIVE TITLE TOKENS");
                const row=root.card(),s=root.scroll();
                if(!feed||!row||!s){root.fail("HEADLINES_MISSING");return;}
                if(trend&&trend.visible){root.fail("TREND_BURIED_HEADLINES");return;}
                if(stories&&stories.visible){root.fail("STORIES_BURIED_HEADLINES");return;}
                const a=feed.mapToItem(s,0,0);
                const b=row.mapToItem(s,0,0);
                console.log("M28B_ORDER // feedY="+a.y+" cardY="+b.y
                            +" scrollY="+s.contentY
                            +" feedVisible="+feed.visible+" cardVisible="+row.visible);
                if(!(a.y < b.y)){root.fail("HEADLINE_ORDER_WRONG");return;}
                const p=row.mapToItem(s,row.width/2,row.height/2);
                s.contentY=Math.max(0,Math.min(s.contentHeight-s.height,
                                           s.contentY+p.y-380));
                root.phase="ready";
            }else if(root.phase==="ready"){
                const row=root.card();
                if(!row||!row.visible)return;
                const p=row.mapToItem(window.contentItem,
                                      row.width/2,row.height/2);
                if(p.x<2||p.y<2||p.x>=window.width-2||p.y>=window.height-2)return;
                console.log("M28B_NEWS_CARD_READY // x="+Math.round(p.x)
                            +" y="+Math.round(p.y));
                root.phase="clicked";
            }else if(root.phase==="clicked"){
                if(!news.viewerOpen)return;
                if(!news.selectedNews
                   ||news.selectedNews.title!=="M28B SYNTHETIC WEATHER REPORT"){
                    root.fail("WRONG_NEWS_INSPECTOR");return;
                }
                console.log("M28B_PASS // NATIVE_HEADLINE_CARD_OPENS_VIEWER");
                news.closeViewer();
                news.newsSubjectRoute="media/news/trends";
                root.phase="trends";
            }else if(root.phase==="trends"){
                const trend=root.divider("REPORTING TREND // CURRENT FILTERED BATCH");
                if(!trend||!trend.visible)return;
                if(root.card()){root.fail("TREND_ROUTE_HAS_REPORT_CARDS");return;}
                console.log("M28B_PASS // TRENDS_IN_DEDICATED_SUBJECT_ROUTE");
                news.newsSubjectRoute="media/news/stories";
                root.phase="stories";
            }else if(root.phase==="stories"){
                const stories=root.divider("STORY FAMILIES // CONSERVATIVE TITLE TOKENS");
                if(!stories||!stories.visible)return;
                if(root.card()){root.fail("STORY_ROUTE_HAS_REPORT_CARDS");return;}
                root.done=true;
                console.log("M28B_PASS // REAL_NEWS_FEED_FIRST_WITH_INDEPENDENT_ANALYTICS");
            }
        }
    }
    Timer {
        interval: 18000
        repeat: false
        running: !root.done
        onTriggered: root.fail("TIMEOUT")
    }
    Timer {
        interval: 250
        repeat: false
        running: root.done
        onTriggered: Qt.quit()
    }
}
