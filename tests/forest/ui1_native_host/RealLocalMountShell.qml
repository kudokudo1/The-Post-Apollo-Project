import QtQuick
import Quickshell
import "./widgets" as Widgets

// Hosted control-only interface witness. No real provider or native admission.
ShellRoot {
    id: test
    property int phase: 0
    property int ticks: 0
    property bool failed: false
    readonly property string draft: "  Reply with READY.  "
    function check(ok, reason) {
        if (!ok) { failed = true; console.error("FOREST_HOST_FAIL // " + reason); }
    }
    function find(item,name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const result = find(child,name);
            if (result) return result;
        }
        return null;
    }
    QtObject {
        id: heldHost
        property bool ready: true
        property double epoch: 0
        property int submits: 0
        function observe(v) { epoch = v === null ? 0 : v; return true; }
        function submit(model, prompt, e) {
            test.check(model === "fixture:local" && prompt === test.draft && e === epoch,
                "held host received exact original input");
            submits++; return "HELD";
        }
        function attach(c) { test.check(false,"held host must not attach"); return false; }
        function stop(c) { return false; }
        function withdraw(c) { return false; }
    }
    QtObject {
        id: controlHost
        property bool ready: true
        property double epoch: 0
        property int attaches: 0
        property int stops: 0
        property int withdrawals: 0
        property var correlation: ({token:"test-control-only"})
        function observe(v) { epoch = v === null ? 0 : v; return true; }
        function submit(model,prompt,e) {
            test.check(model === "fixture:local" && prompt === test.draft && e === epoch,
                "accepted control host received exact original input");
            return {accepted:true,correlation:correlation};
        }
        function attach(c) {
            const f = test.find(forest.contentItem,"forestRealLocalFeed");
            test.check(c === correlation && f && f.messages.length === 1
                && f.messages[0].body === test.draft,"feed attaches before ACK");
            attaches++; return true;
        }
        function stop(c) { stops++; return c === correlation; }
        function withdraw(c) { withdrawals++; return c === correlation; }
    }
    Widgets.ForestW { id: forest; menuOpen: true }
    Timer {
        interval: 250
        running: true
        repeat: true
        onTriggered: {
            const input = test.find(forest.contentItem,"forestPromptInput");
            const send = test.find(forest.contentItem,"forestSendButton");
            const loader = test.find(forest.contentItem,"forestPublicPreviewLoader");
            test.check(input && send && loader,"actual mounted composer");
            if (++test.ticks > 80) test.check(false,"bounded test deadline");
            if (test.failed) { stop(); Qt.quit(); return; }
            switch (test.phase) {
            case 0:
                test.check(!send.enabledAction && !forest.chatHostTrusted,"default held");
                forest.modelPopupOpen = true;
                test.phase++;
                break;
            case 1:
                if (!forest.equipLocalModel("small","fixture:local")) break;
                forest.chooseModelForm("SMALL");
                forest.modelPopupOpen = false;
                test.check(forest.selectedLocalModel === "fixture:local","disposable inventory selected");
                forest.localRequestHost = heldHost;
                input.text = test.draft;
                test.phase++;
                break;
            case 2:
                if (!send.enabledAction) break;
                test.check(loader.item && test.find(loader.item,"forestRealLocalFeed"),
                    "same existing Loader mounts real feed");
                send.primaryRequested();
                test.check(heldHost.submits === 1 && input.text === test.draft
                    && forest.localRequestState.status === "HELD" && !send.enabledAction,
                    "held result preserves draft and locks retry");
                forest.localRequestHost = controlHost;
                test.phase++;
                break;
            case 3:
                if (!send.enabledAction) break;
                send.primaryRequested();
                test.check(controlHost.attaches === 1 && input.text === ""
                    && send.askLabel === "STOP" && !forest.chatHostTrusted,
                    "original acceptance attaches and changes composer action");
                test.check(forest.receiveLocalSnapshot(controlHost.epoch,controlHost.correlation,
                    {sequence:1,status:"PREPARED",text:"",local_outcome:"UNKNOWN_HOLD",
                     provisional:false,native_admitted:false}),"prepared status only");
                send.primaryRequested();
                test.check(controlHost.stops === 1 && !send.enabledAction
                    && forest.localRequestState.status === "STOP_REQUESTED","original STOP invoked");
                test.check(!forest.receiveLocalSnapshot(controlHost.epoch,{},{}),"foreign correlation refused");
                test.check(forest.receiveLocalSnapshot(controlHost.epoch,controlHost.correlation,
                    {sequence:2,status:"UNKNOWN_HOLD",text:"",local_outcome:"ABORTED_LOCAL",
                     provisional:false,native_admitted:false}),"original terminal accepted");
                forest.menuOpen = false;
                test.phase++;
                break;
            case 4:
                test.check(!loader.active && !send.enabledAction && controlHost.withdrawals === 1,
                    "close withdraws original and removes feed");
                if (!test.failed) console.info("FOREST_REAL_LOCAL_MOUNT_PASS");
                stop(); Qt.quit();
                break;
            }
            if (test.failed) { stop(); Qt.quit(); }
        }
    }
}
