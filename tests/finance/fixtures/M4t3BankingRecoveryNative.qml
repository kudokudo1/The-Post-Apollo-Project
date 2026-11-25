import QtQuick
import Quickshell
import Quickshell.Io
import "services/finance" as Finance

// CI fixture only: real client bridge plus independently executed recovery.
ShellRoot {
    id: root
    property int stage: 0
    property string retired: ""
    property string driverStage: ""
    property bool driverMarker: false
    property bool driverDone: false
    property var original: ({
        mode:"manual", accounts:[
            {id:"acct-1",providerId:"chime",productId:"chime-checking",nickname:"Fictional checking",openingCents:10000,origin:"manual"},
            {id:"acct-2",providerId:"cashapp",productId:"cash-balance",nickname:"Fictional wallet",openingCents:5000,origin:"manual"}
        ], entries:[
            {id:"entry-3",accountId:"acct-1",amountCents:-1200,date:"2026-01-01",description:"Fictional transfer",origin:"manual",transferId:"transfer-5",transferSide:"out"},
            {id:"entry-4",accountId:"acct-2",amountCents:1200,date:"2026-01-01",description:"Fictional transfer",origin:"manual",transferId:"transfer-5",transferSide:"in"}
        ], nextId:6
    })
    Finance.FinanceBankingRevisionBridgeCandidate { id: a; reviewEnabled: true }
    Finance.FinanceBankingRevisionBridgeCandidate { id: b; reviewEnabled: true }
    Finance.FinanceBankingRevisionBridgeCandidate { id: c; reviewEnabled: true }
    Finance.FinanceBankingRevisionBridgeCandidate { id: d; reviewEnabled: true }
    function check(ok,label) {
        if(!ok){console.error("M4T3_NATIVE_FAIL "+label+" stage="+stage);Qt.quit();}
        return ok;
    }
    function launch(action) {
        if(!check(!driver.running,"driver overlap"))return;
        driverStage=action;driverDone=false;driverMarker=false;
        driver.exec({command:["/usr/bin/python3","-B",Quickshell.shellPath("scripts/finance/m4t3_recovery_driver.py"),action]});
    }
    function matches(client,revision) {
        return client.ready&&client.document.revision===revision&&client.equal(client.document.session,original);
    }
    Process {
        id: driver
        stdout: SplitParser {
            onRead: function(line) {
                if(root.check(!root.driverMarker&&line==="M4T3_DRIVER_PASS "+root.driverStage,"driver receipt"))
                    root.driverMarker=true;
            }
        }
        stderr: SplitParser {
            onRead: function(line) { root.check(false,"driver stderr"); }
        }
        onExited: function(code,status) {
            Qt.callLater(function(){
                if(root.check(code===0&&root.driverMarker,"driver exit"))root.driverDone=true;
            });
        }
    }
    Timer {
        interval: 50
        repeat: true
        running: true
        onTriggered: {
            switch(root.stage){
            case 0:
                if(!root.check(a.start(),"first client start"))return;
                root.stage++;return;
            case 1:
                if(!a.ready)return;
                if(!root.check(a.document.revision===2&&a.document.session.accounts[0].openingCents===20000,"changed ledger"))return;
                root.retired=a.generation;
                root.launch("busy");root.stage++;return;
            case 2:
                if(!root.driverDone)return;
                if(!root.check(a.ready&&a.request("close",a.generation,2,null,false),"close before recovery"))return;
                root.stage++;return;
            case 3:
                if(a.phase!=="closed"||a.childRunning)return;
                if(!root.check(a.document===null&&a.generation==="","old client invalidated"))return;
                root.launch("restore");root.stage++;return;
            case 4:
                if(!root.driverDone)return;
                if(!root.check(b.start(),"restored client launch"))return;
                root.stage++;return;
            case 5:
                if(!b.ready)return;
                if(!root.check(root.matches(b,3)&&b.generation!==root.retired,"restore exact ledger"))return;
                if(!root.check(!b.request("clear",root.retired,3,null,true),"old generation denied"))return;
                if(!root.check(b.request("clear",b.generation,3,null,true),"explicit clear"))return;
                root.stage++;return;
            case 6:
                if(!b.ready)return;
                if(!root.check(b.document.revision===4&&b.document.session.mode==="empty","empty destination"))return;
                if(!root.check(b.request("close",b.generation,4,null,false),"close import destination"))return;
                root.stage++;return;
            case 7:
                if(b.phase!=="closed"||b.childRunning)return;
                root.launch("import");root.stage++;return;
            case 8:
                if(!root.driverDone)return;
                if(!root.check(c.start(),"imported client launch"))return;
                root.stage++;return;
            case 9:
                if(!c.ready)return;
                if(!root.check(root.matches(c,5),"encrypted import exact ledger"))return;
                if(!root.check(c.request("close",c.generation,5,null,false),"close before damaged recovery"))return;
                root.stage++;return;
            case 10:
                if(c.phase!=="closed"||c.childRunning)return;
                root.launch("recover");root.stage++;return;
            case 11:
                if(!root.driverDone)return;
                if(!root.check(d.start(),"recovered client launch"))return;
                root.stage++;return;
            case 12:
                if(!d.ready)return;
                if(!root.check(root.matches(d,6),"damaged primary recovery exact ledger"))return;
                if(!root.check(d.request("close",d.generation,6,null,false),"final close"))return;
                root.stage++;return;
            case 13:
                if(d.phase!=="closed"||d.childRunning)return;
                if(!root.check(!a.childRunning&&!b.childRunning&&!c.childRunning&&!driver.running,"all processes exited"))return;
                console.log("M4T3_NATIVE_PASS");Qt.quit();return;
            }
        }
    }
    Timer {
        interval: 90000
        running: true
        repeat: false
        onTriggered: {console.error("M4T3_NATIVE_FAIL watchdog stage="+root.stage);Qt.quit();}
    }
    Component.onCompleted: Quickshell.watchFiles=false
}
