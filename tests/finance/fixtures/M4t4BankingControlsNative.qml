import QtQuick
import QtQuick.Window
import Quickshell
import "widgets" as Widgets

// Native visual components, disposable CI only. Invoke the real button
// signals, not a simulated backend or physical mouse/keyboard automation.
ShellRoot {
    id: root
    property int stage: 0
    property string sealedId: ""
    readonly property string password: "fictional M4t4 passphrase only"
    Window {
        width: 1000
        height: 720
        visible: true
        color: "#1B0623"
        Widgets.FinanceBankingBackupControlsCandidate {
            id: backup
            width: 460
            height: implicitHeight
            x: 10
            y: 10
            active: true
            storeReady: true
            dirty: false
            localSaved: true
            savedRevision: 1
        }
        Widgets.FinanceBankingPortableControlsCandidate {
            id: portable
            width: 460
            height: implicitHeight
            x: 510
            y: 10
            active: true
            storeReady: true
            dirty: false
            localSaved: true
            savedRevision: 1
        }
    }
    function check(ok,label) {
        if(!ok){console.error("M4T4_NATIVE_FAIL "+label+" stage="+stage);Qt.quit();}
        return ok;
    }
    function find(item,predicate) {
        if(predicate(item))return item;
        const children=item.children||[];
        for(let i=0;i<children.length;i++){
            const result=find(children[i],predicate);
            if(result)return result;
        }
        return null;
    }
    function click(panel,label) {
        const button=find(panel,function(x){return x.label===label&&typeof x.leftClicked==="function";});
        if(!check(button!==null&&button.available&&button.visible,"button "+label))return false;
        button.leftClicked(null);
        return true;
    }
    function input(limit) {
        return find(portable,function(x){return x.maximumLength===limit&&typeof x.text==="string";});
    }
    Timer {
        interval: 100
        repeat: true
        running: true
        onTriggered: {
            const secret=root.input(1025), file=root.input(53);
            if(!root.check(secret!==null&&file!==null,"native input fields"))return;
            switch(root.stage){
            case 0:
                if(!root.check(!backup.available&&!portable.available&&!backup.refresh()&&!portable.confirm("export"),"default disabled"))return;
                backup.reviewEnabled=true;portable.reviewEnabled=true;
                if(!root.check(secret.echoMode===TextInput.Password,"masked input"))return;
                if(!root.click(backup,"REFRESH BACKUPS"))return;
                root.stage++;return;
            case 1:
                if(!backup.rowsLoaded)return;
                if(!root.check(backup.rows.length===0,"empty list"))return;
                if(!root.click(backup,"CREATE SAVED BACKUP"))return;
                if(!root.check(backup.armed!==null,"first click arms only"))return;
                backup.dirty=true;
                if(!root.check(backup.armed===null&&backup.createRequest()===null,"dirty cancels confirmation"))return;
                backup.dirty=false;
                if(!root.click(backup,"CREATE SAVED BACKUP")||!root.click(backup,"CANCEL CONFIRMATION"))return;
                if(!root.check(backup.armed===null,"cancelled"))return;
                if(!root.click(backup,"CREATE SAVED BACKUP")||!root.click(backup,"CONFIRM CREATE BACKUP"))return;
                root.stage++;return;
            case 2:
                if(backup.notice!=="BACKUP CREATED // REFRESH LIST")return;
                if(!root.check(!backup.rowsLoaded,"refresh required after write"))return;
                if(!root.click(backup,"REFRESH BACKUPS"))return;
                root.stage++;return;
            case 3:
                if(!backup.rowsLoaded)return;
                if(!root.check(backup.rows.length===1&&backup.rows[0].sourceRevision===1&&backup.rows[0].accountCount===1,"actual backup metadata"))return;
                const row=backup.rows[0];
                if(!root.click(backup,row.createdUtc+" // R1 // 1 ACC // 0 ENTRIES"))return;
                if(!root.check(backup.selectedId===row.backupId,"row selected"))return;
                if(!root.click(backup,"DELETE SELECTED BACKUP")||!root.click(backup,"CANCEL CONFIRMATION"))return;
                if(!root.check(backup.rows.length===1&&backup.armed===null,"delete cancellation"))return;
                if(!root.click(backup,"DELETE SELECTED BACKUP")||!root.click(backup,"CONFIRM DELETE BACKUP"))return;
                root.stage++;return;
            case 4:
                if(backup.notice!=="BACKUP DELETED // REFRESH LIST")return;
                if(!root.click(backup,"REFRESH BACKUPS"))return;
                root.stage++;return;
            case 5:
                if(!backup.rowsLoaded)return;
                if(!root.check(backup.rows.length===0,"confirmed delete"))return;
                secret.text=root.password;
                if(!root.click(portable,"EXPORT SAVED MANUAL LEDGER"))return;
                if(!root.check(portable.armed!==null,"export armed"))return;
                portable.savedRevision=2;
                if(!root.check(secret.text===""&&portable.armed===null,"revision clears secret and arm"))return;
                portable.savedRevision=1;
                secret.text=root.password;
                if(!root.click(portable,"EXPORT SAVED MANUAL LEDGER")||!root.click(portable,"CANCEL / CLEAR PASSPHRASE"))return;
                if(!root.check(secret.text===""&&portable.armed===null,"explicit secret cancellation"))return;
                secret.text=root.password;
                if(!root.click(portable,"EXPORT SAVED MANUAL LEDGER")||!root.click(portable,"CONFIRM EXPORT"))return;
                if(!root.check(secret.text===""&&portable.armed===null,"submission clears secret"))return;
                root.stage++;return;
            case 6:
                if(portable.receipt===null)return;
                if(!root.check(portable.receipt.action==="export"&&portable.receipt.sourceRevision===1,"export receipt"))return;
                root.sealedId=portable.receipt.portableId;
                file.text=root.sealedId;
                secret.text="incorrect fictional passphrase";
                if(!root.click(portable,"AUTHENTICATE / PREVIEW SEALED FILE")||!root.click(portable,"CONFIRM PREVIEW"))return;
                root.stage++;return;
            case 7:
                if(portable.notice!=="RESULT NOT CONFIRMED // INSPECT FILES BEFORE RETRY")return;
                if(!root.check(portable.receipt===null&&secret.text==="","wrong password refused"))return;
                secret.text=root.password;
                if(!root.click(portable,"AUTHENTICATE / PREVIEW SEALED FILE")||!root.click(portable,"CONFIRM PREVIEW"))return;
                root.stage++;return;
            case 8:
                if(portable.receipt===null)return;
                if(!root.check(portable.receipt.action==="preview"&&portable.receipt.portableId===root.sealedId
                    &&portable.receipt.accountCount===1&&portable.receipt.entryCount===0
                    &&portable.receipt.ciphertextAuthenticated&&!portable.receipt.originAuthenticated,"actual authenticated preview"))return;
                secret.text=root.password;
                portable.active=false;
                if(!root.check(secret.text===""&&portable.receipt===null&&portable.armed===null,"context clears sensitive input"))return;
                console.log("M4T4_NATIVE_PASS");Qt.quit();return;
            }
        }
    }
    Timer {
        interval: 45000
        running: true
        repeat: false
        onTriggered: {console.error("M4T4_NATIVE_FAIL watchdog stage="+root.stage+" backup="+backup.notice+" portable="+portable.notice);Qt.quit();}
    }
    Component.onCompleted: Quickshell.watchFiles=false
}
