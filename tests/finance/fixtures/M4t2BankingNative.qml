import QtQuick
import Quickshell
import "services/finance" as Finance

// Disposable shell root, never loaded by the production shell.
ShellRoot {
    id: root
    property int stage: 0
    property string oldGeneration: ""
    property var fictional: ({mode:"manual",accounts:[{id:"acct-1",providerId:"chime",
        productId:"chime-checking",nickname:"Fictional account",openingCents:10000,
        origin:"manual"}],entries:[],nextId:2})
    Finance.FinanceBankingRevisionBridgeCandidate { id: a; reviewEnabled: true }
    Finance.FinanceBankingRevisionBridgeCandidate { id: b; reviewEnabled: true }
    Finance.FinanceBankingRevisionBridgeCandidate { id: c; reviewEnabled: true }
    Finance.FinanceBankingRevisionBridgeCandidate { id: d; reviewEnabled: true }
    function check(ok,label) {
        if(!ok){console.error("M4T2_NATIVE_FAIL "+label+" stage="+stage);Qt.quit();}
        return ok;
    }
    Timer {
        interval: 50
        repeat: true
        running: true
        onTriggered: {
            switch(root.stage){
            case 0:
                if(!root.check(a.phase==="idle"&&!a.childRunning,"dormant"))return;
                if(!root.check(a.start()&&b.start(),"explicit launch"))return;
                root.stage++;return;
            case 1:
                if(!a.ready||!b.ready)return;
                if(!root.check(a.document.revision===0&&b.document.revision===0&&a.generation!==b.generation,"fresh generations"))return;
                root.oldGeneration=a.generation;
                if(!root.check(!a.request("save",b.generation,0,root.fictional,true),"wrong generation"))return;
                if(!root.check(!a.request("save",a.generation,0,root.fictional,false),"explicit confirmation"))return;
                if(!root.check(a.request("save",a.generation,0,root.fictional,true),"save request"))return;
                if(!root.check(!a.request("refresh",a.generation,0,null,false),"one flight"))return;
                root.stage++;return;
            case 2:
                if(!a.ready)return;
                if(!root.check(a.document.revision===1&&a.document.session.accounts[0].openingCents===10000,"confirmed save"))return;
                if(!root.check(b.request("refresh",b.generation,0,null,false),"stale refresh launched"))return;
                root.stage++;return;
            case 3:
                if(b.phase!=="failed"||b.childRunning)return;
                if(!root.check(b.document===null&&b.generation===""&&!b.start(),"stale client retired"))return;
                if(!root.check(a.request("close",a.generation,1,null,false),"close requested"))return;
                root.stage++;return;
            case 4:
                if(a.phase!=="closed"||a.childRunning)return;
                if(!root.check(a.document===null&&a.generation===""&&!a.start(),"closed generation retired"))return;
                if(!root.check(c.start()&&d.start(),"new clients"))return;
                root.stage++;return;
            case 5:
                if(!c.ready||!d.ready)return;
                if(!root.check(c.document.revision===1&&c.generation!==root.oldGeneration,"fresh disk load"))return;
                if(!root.check(!c.request("clear",root.oldGeneration,1,null,true),"retired token rejected"))return;
                d.reviewEnabled=false;
                if(!root.check(d.phase==="failed"&&d.document===null&&!d.ready,"disable invalidates"))return;
                if(!root.check(c.request("clear",c.generation,1,null,true),"clear requested"))return;
                root.stage++;return;
            case 6:
                if(!c.ready||d.childRunning)return;
                if(!root.check(c.document.revision===2&&c.document.session.mode==="empty","confirmed clear"))return;
                if(!root.check(c.request("close",c.generation,2,null,false),"final close"))return;
                root.stage++;return;
            case 7:
                if(c.phase!=="closed"||c.childRunning)return;
                console.log("M4T2_NATIVE_PASS");
                Qt.quit();return;
            }
        }
    }
    Timer {
        interval: 45000
        running: true
        repeat: false
        onTriggered: {console.error("M4T2_NATIVE_FAIL watchdog stage="+root.stage+" "+a.phase+" "+b.phase+" "+c.phase+" "+d.phase);Qt.quit();}
    }
    Component.onCompleted: Quickshell.watchFiles=false
}
