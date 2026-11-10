import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// M4 // Synthetic-only saved-strip geometry. Never opens station,
// bookmarks, network or MPD. Tests ten compact squares per half width.
ShellRoot {
    id: root
    property bool done:false
    property int ticks:0
    property int phase:0
    property var saved: {
        const result=[];
        for(let i=0;i<10;i++)result.push({title:"F"+(i+1)});
        return result;
    }
    property var recent: {
        const result=[];
        for(let i=0;i<8;i++)result.push({title:"R"+(i+1)});
        return result;
    }
    function find(item,name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        for(const child of (item.children||[])) {
            const match=find(child,name);
            if(match)return match;
        }
        return null;
    }
    function count(item,name) {
        if(!item)return 0;
        let result=item.objectName===name?1:0;
        for(const child of (item.children||[]))
            result+=count(child,name);
        return result;
    }
    function fail(msg) {
        if(done)return;
        done=true;
        console.error("M4_NATIVE_FAIL // "+msg);
        Qt.quit();
    }

    Window {
        width:520
        height:110
        visible:true
        color:"black"
        Weather.StationRadioSavedStrips {
            id:strips
            x:8
            y:2
            width:504
            compactDocked:root.phase<2
            favoriteItems:root.saved
            recentItems:root.recent
            canRecall:true
        }
    }
    Timer {
        running:!root.done
        repeat:true
        interval:180
        onTriggered: {
            root.ticks++;
            if(root.ticks>25)return root.fail("TIMEOUT");
            const row=find(strips,"media-m4-pinned-saved-pair");
            const f=find(strips,"media-m4-docked-favorites-scroll");
            const r=find(strips,"media-m4-docked-recents-scroll");
            const first=find(strips,"media-m4-docked-favorite-tile");
            const firstRecent=find(strips,"media-m4-docked-recent-tile");
            if(!row||!f||!r||!first||!firstRecent)return;
            if(root.phase===0) {
                if(strips.height!==28||!row.visible
                    ||count(strips,"media-m4-docked-favorite-tile")!==10
                    ||count(strips,"media-m4-docked-recent-tile")!==8
                    ||Math.abs(first.width-first.height)>0.1
                    ||Math.abs(firstRecent.width-firstRecent.height)>0.1
                    ||f.contentWidth>f.width+1
                    ||r.contentWidth>r.width+1
                    ||f.y!==r.y)
                    return root.fail("COMPACT_TEN_ACROSS_SQUARE_LAYOUT");
                root.saved=root.saved.concat([{title:"F11"},{title:"F12"}]);
                root.phase=1;return;
            }
            if(root.phase===1) {
                if(count(strips,"media-m4-docked-favorite-tile")!==12
                    ||f.contentWidth<=f.width
                    ||!f.interactive)
                    return root.fail("COMPACT_HORIZ_OVERFLOW");
                root.phase=2;return;
            }
            if(root.phase===2) {
                if(strips.height!==88 ||row.visible
                    ||!find(strips,"media-m2-favorite-scroll")
                    ||!find(strips,"media-m2-recent-scroll"))
                    return root.fail("NORMAL_RADIO_LAYOUT_CHANGED");
                root.done=true;
                console.log("M4_NATIVE_PASS // DENSE_PINNED_SQUARE_SAVED_ROWS");
                Qt.quit();
            }
        }
    }
}
