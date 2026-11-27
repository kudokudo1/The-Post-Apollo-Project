import QtQuick
import Quickshell
import "./widgets" as Widgets

// Explicit visual-only host, not the normal shell or an operator launcher.
ShellRoot {
    id: witness
    property int phase: 0
    property bool failed: false
    function check(ok, reason) {
        if (!ok) {
            failed = true;
            console.error("FOREST_HOST_FAIL // " + reason);
        }
    }
    function find(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        if (item.children) {
            for (let i = 0; i < item.children.length; ++i) {
                const found = find(item.children[i], name);
                if (found) return found;
            }
        }
        return null;
    }
    Widgets.ForestW { id: forest; fixtureOnly: true; menuOpen: true }
    Timer {
        interval: 350
        repeat: true
        running: true
        onTriggered: {
            const input = witness.find(forest.contentItem, "forestPromptInput");
            const send = witness.find(forest.contentItem, "forestSendButton");
            const preview = witness.find(forest.contentItem, "forestPublicPreviewButton");
            const loader = witness.find(forest.contentItem, "forestPublicPreviewLoader");
            witness.check(input && send && preview && loader, "fixture uses actual ForestW controls");
            if (witness.failed) { stop(); Qt.quit(); return; }
            switch (witness.phase++) {
            case 0:
                witness.check(forest.fixtureOnly && !forest.chatHostTrusted && !forest.voiceHostTrusted
                    && !send.enabledAction && preview.label === "SAMPLE" && !loader.active,
                    "fixture explicit sample and real SEND locked");
                forest.modelPopupOpen = true;
                witness.check(!forest.refreshLocalModelEvidence() && !forest.saveModelPreferences(),
                    "fixture root refuses inventory and preference IO");
                forest.chooseModelForm("BIG");
                witness.check(forest.selectedModelForm === "BIG", "fixture local preference");
                forest.modelPopupOpen = false;
                input.text = "local fixture draft";
                preview.leftClicked(null);
                break;
            case 1:
                witness.check(loader.active && loader.item && loader.item.demoState === "READY"
                    && input.text === "local fixture draft" && send.enabledAction
                    && send.askLabel === "TEST" && !forest.chatHostTrusted,
                    "fixture opens current fixed demo and preserves draft");
                send.primaryRequested();
                witness.check(loader.item.demoState === "STREAMING" && send.askLabel === "STOP",
                    "actual composer TEST event starts fixed stream");
                break;
            case 2:
                witness.check(loader.item.demoState === "STREAMING" && send.enabledAction,
                    "actual composer STOP available");
                send.primaryRequested();
                witness.check(loader.item.demoState === "STOPPED" && !send.enabledAction,
                    "actual composer STOP event retires stream");
                send.primaryRequested();
                witness.check(loader.item.demoState === "STOPPED", "stopped view refuses repeat");
                break;
            case 3:
                witness.check(loader.item.demoState === "STOPPED", "late timer cannot restart STOP");
                preview.leftClicked(null);
                witness.check(!loader.active && !send.enabledAction,
                    "sample close withdraws old view");
                preview.leftClicked(null);
                break;
            case 4:
                witness.check(loader.item && loader.item.demoState === "READY" && send.enabledAction,
                    "explicit reopen creates a fresh view");
                send.primaryRequested();
                break;
            case 5:
            case 6:
            case 7:
            case 8:
                break;
            case 9:
                witness.check(loader.item.demoState === "COMPLETE" && !send.enabledAction
                    && input.text === "local fixture draft", "fixed reply complete, draft unchanged");
                const feed = witness.find(loader.item, "publicFixtureFeed");
                witness.check(feed && feed.messages.length === 2
                    && feed.messages[0].body === "Reply with READY.",
                    "existing feed received fixed public prompt only");
                forest.menuOpen = false;
                break;
            case 10:
                witness.check(!loader.active && loader.item === null && input.text === ""
                    && !send.enabledAction, "fixture close unloads and clears draft");
                if (!witness.failed) console.info("FOREST_FIXTURE_VISUAL_PASS");
                stop(); Qt.quit();
                break;
            }
            if (witness.failed) { stop(); Qt.quit(); }
        }
    }
}
