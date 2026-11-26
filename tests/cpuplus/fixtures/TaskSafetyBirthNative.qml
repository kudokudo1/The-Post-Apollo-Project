import QtQuick
import Quickshell
import "services/system"

ShellRoot {
    id: root
    TaskSafety { id: safety }
    function check(ok,reason) {
        if (!ok) {
            console.error("TASK_SAFETY_BIRTH_FAIL // "+reason);
            return false;
        }
        return true;
    }
    Timer {
        interval: 100
        running: true
        repeat: false
        onTriggered: root.runChecks()
    }
    function runChecks() {
        if (Quickshell.env("POST_APOLLO_HUNTER_DISPOSABLE_CI") !== "1") {
            Qt.quit(); return;
        }
        const old={pid:3210,startTicks:100,comm:"sway",user:"synthetic"};
        const same={pid:3210,startTicks:100,comm:"sway",user:"synthetic"};
        const reused={pid:3210,startTicks:101,comm:"sway",user:"synthetic"};
        const unknown={pid:3210,startTicks:0,comm:"sway",user:"synthetic"};
        safety.toggleDangerStickyUnlock(old);
        if (!check(safety.dangerUnlockMode(same)==="sticky"
            && safety.dangerUnlockMode(reused)===""
            && safety.dangerUnlockMode(unknown)==="","master grant belongs to one birth")) {Qt.quit();return;}
        safety.toggleDangerUnlock(old);
        safety.toggleDangerActionUnlock(old,"freeze");
        if (!check(safety.dangerActionUnlockMode(same,"freeze")==="once"
            && safety.dangerActionUnlockMode(reused,"freeze")==="","one-shot grant belongs to one birth")) {Qt.quit();return;}
        safety.relockDangerAction(same,"freeze");
        safety.toggleDangerActionStickyUnlock(old,"kill");
        if (!check(safety.dangerActionUnlockMode(same,"kill")==="sticky"
            && safety.dangerActionUnlockMode(reused,"kill")===""
            && safety.dangerActionUnlockMode(unknown,"kill")==="","sticky action grant cannot transfer")) {Qt.quit();return;}
        safety.toggleDangerUnlock(unknown);
        safety.toggleDangerActionStickyUnlock(unknown,"kill");
        if (!check(!safety.dangerUnlocked(unknown)
            && !safety.dangerActionUnlocked(unknown,"kill"),"missing birth fails closed")) {Qt.quit();return;}
        console.log("TASK_SAFETY_BIRTH_PASS");
        Qt.quit();
    }
}
