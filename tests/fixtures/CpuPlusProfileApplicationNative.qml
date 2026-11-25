import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/cpuplus"
import "widgets/cpuplus/CpuPlusProfileCatalog.js" as Catalog

// Isolated native preview test. No privileged backend or subprocess is invoked.
ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_MEMORY_UI_SMOKE")==="CI_DISPOSABLE_ONLY"
    property int ticks: 0
    property int phase: 0
    property int intents: 0
    property bool failed: false
    function find(item,name){
        if(item.objectName===name)return item;
        for(const child of item.children||[]){
            const result=find(child,name);
            if(result)return result;
        }
        return null;
    }
    function check(ok,message){
        if(!ok){failed=true;console.error("CPU_PROFILE_APPLICATION_NATIVE_FAIL // "+message);Qt.quit();}
        return ok;
    }
    Window {
        id: win
        width: 220
        height: 620
        visible: smoke.armed
        Flickable {
            anchors.fill: parent
            contentHeight: prof.implicitHeight
            clip: true
            CpuPlusProfilePane {
                id: prof
                width: parent.width
                selectedProfile: "CUSTOM"
                customDraft: Catalog.capture(Catalog.capture(Catalog.empty(),"capacityGiB",24),"swappiness",150)
                actualKiB: 16777216
                actualSwappiness: 60
                capacityTarget: 32
                policyTarget: 80
                observationReady: true
                operationBusy: false
                onDraftCapture: key=>smoke.intents++
                onDraftCleared: smoke.intents++
                onCatalogLoadRequested: smoke.intents++
                onCatalogSaveRequested: name=>smoke.intents++
                onSavedDraftRequested: name=>smoke.intents++
                onCatalogChangeRequested: request=>smoke.intents++
            }
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: smoke.armed&&!smoke.failed
        onTriggered: {
            if(++smoke.ticks>40){smoke.check(false,"timeout");return;}
            const toggle=smoke.find(prof,"cpuplusProfileApplicationPreview");
            const locked=smoke.find(prof,"cpuplusProfileApplyLocked");
            if(!toggle||!locked)return;
            if(smoke.phase===0){
                if(!smoke.check(toggle.available&&!prof.applicationExpanded&&!locked.visible,"initial collapsed preview"))return;
                toggle.leftClicked(null);
                smoke.phase=1;return;
            }
            if(smoke.phase===1){
                if(!smoke.check(prof.applicationExpanded&&locked.visible&&!locked.available&&!prof.applicationPlan.canApply
                    &&prof.applicationPlan.rows.length===2
                    &&prof.applicationPlan.rows[0].assessment==="INCREASE CANDIDATE","expanded locked preview"))return;
                if(!smoke.check(locked.width>0&&locked.width<=win.width,"narrow control geometry"))return;
                locked.leftClicked(null);
                if(!smoke.check(smoke.intents===0&&prof.capacityTarget===32&&prof.policyTarget===80
                    &&prof.customDraft.capacityGiB===24&&prof.customDraft.swappiness===150,"no mutation or intent"))return;
                prof.observationReady=false;
                smoke.phase=2;return;
            }
            if(smoke.phase===2){
                if(!smoke.check(prof.applicationPlan.rows[0].assessment==="OBSERVATION REQUIRED"
                    &&!locked.available,"unavailable observation remains locked"))return;
                prof.operationBusy=true;
                smoke.phase=3;return;
            }
            if(smoke.phase===3){
                if(!smoke.check(prof.applicationPlan.status==="OPERATION BUSY // HOLD"&&!locked.available,"busy remains locked"))return;
                prof.selectedProfile="GAMING";
                smoke.phase=4;return;
            }
            if(smoke.phase===4){
                if(!smoke.check(prof.applicationPlan===null&&!prof.applicationExpanded&&!toggle.available&&!locked.visible
                    &&smoke.intents===0,"preset invalidates preview without intent"))return;
                console.log("CPU_PROFILE_APPLICATION_NATIVE_PASS // narrow preview, locked apply, stale and busy, preset isolation");
                Qt.quit();
            }
        }
    }
    Component.onCompleted: if(!armed)Qt.quit()
}
