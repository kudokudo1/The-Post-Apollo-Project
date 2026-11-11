import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W6 // Offscreen station console visual smoke with synthetic data only.
// No StationHome/Discovery/NewsHub services or host resources are mounted.
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property real headerY: -1
    property real cardsY: -1
    property real reportY: -1

    function rows(group, number) {
        const results=[];
        for(let i=0;i<number;i++) results.push({
            id: group+"-"+i,
            label: group.toUpperCase()+" / "+(i+1),
            transport: i%4===0 ? "LOADING" : "READY",
            availability: i%4===0 ? "READING" : i%3===0 ? "CACHE_FRESH" : "LIVE",
            receivedAgeMinutes: i+1,
            observationAgeMinutes: i+2,
            ageBand:"FRESH", mode:"NORMAL_POLL", cadenceMs:900000,
            retention:"MEMORY_LAST_GOOD",expireMs:21600000,
            detail:"SYNTHETIC OBSERVATION"
        });
        return results;
    }
    function directory(number) {
        const results=[];
        for(let i=0;i<number;i++) results.push({
            id:"directory-"+i,name:"SOURCE "+(i+1),
            state:"NOT MOUNTED ON SERVICES",
            owner:"ORIGINAL OWNER",detail:"ON REQUEST"
        });
        return results;
    }
    function homeMetrics() {
        const result=[];
        const names=["WEATHER","AQI","KP","WIND","IMF","SOLAR"];
        for(let i=0;i<6;i++) result.push({
            label:names[i],value:i%2===0 ? "LIVE":"CACHE",
            color:"#55cfca",detail:"PROVIDER "+i,footer:"LAST SUCCESS "+i+"m"
        });
        return result;
    }
    function find(item,name) {
        if(!item) return null;
        if(item.objectName===name) return item;
        for(const c of item.children || []) {
            const x=find(c,name); if(x) return x;
        }
        if(item.contentItem) {
            const x=find(item.contentItem,name); if(x) return x;
        }
        if(item.item) {
            const x=find(item.item,name); if(x) return x;
        }
        return null;
    }
    function fail(message) {
        if(done)return;
        done=true;console.error("W6_NATIVE_FAIL // "+message);Qt.quit();
    }
    Window {
        width: 520
        height: 300
        color: "black"
        visible: true
        Weather.StationServicesConsole {
            id: stationConsole
            anchors.fill: parent
            familyLabel: root.phase===0 ? "EARTH" : root.phase===1 ? "HOME":"MEDIA"
            statusScope: familyLabel
            embeddedHeader: root.phase===2
            homeCards: root.phase===1
            runtimeRows: root.phase===2 ? [] : root.rows(familyLabel,10)
            directoryRows: root.phase===1 ? [] : root.directory(root.phase===2 ? 9 : 3)
            customCards: root.phase===1 ? root.homeMetrics() : []
        }
    }
    Timer {
        interval: 200
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if(root.ticks>40) return root.fail("TIMEOUT");
            const top=root.find(stationConsole,"services-console-fixed-header");
            const cards=root.find(console,"services-console-summary-cards");
            const dossier=root.find(console,"services-console-detail-scroll");
            const report=root.find(console,"services-console-selected-report");
            const directory=root.find(console,"services-console-directory-heading");
            if(!top || !cards || !dossier || !report || !directory) {
                if(root.ticks>10) return root.fail("CONSOLE_NODES H="+!!top+" C="+!!cards+" S="+!!dossier+" R="+!!report+" D="+!!directory);
                return;
            }
            if(String(stationConsole.color).toLowerCase()==="#ffffff")
                return root.fail("WHITE_BACKGROUND");
            if(cards.height !== (root.phase===1 ? 99 : 65))
                return root.fail("COMPACT_CARD_HEIGHT");
            if(dossier.height<15 || dossier.contentHeight<=dossier.height)
                return root.fail("DETAIL_SCROLL_NOT_AVAILABLE");
            if(root.headerY<0) {
                root.headerY=top.y;root.cardsY=cards.y;root.reportY=report.y;
                dossier.contentY=25;
                return;
            }
            if(dossier.contentY<=0 || top.y!==root.headerY
                || cards.y!==root.cardsY || report.y!==root.reportY)
                return root.fail("PINNED_SURFACES_MOVED");
            if(root.phase===2) {
                root.done=true;
                console.log("W6_NATIVE_PASS // EARTH_HOME_MEDIA_CANONICAL_SERVICES_520X300");
                Qt.quit();
                return;
            }
            root.phase++;
            root.headerY=-1;root.cardsY=-1;root.reportY=-1;
        }
    }
}
