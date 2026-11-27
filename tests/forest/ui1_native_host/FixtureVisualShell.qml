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
                witness.check(loader.active && loader.item && loader.item.transcriptReady
                    && input.text === "local fixture draft" && !send.enabledAction,
                    "fixture displays existing sample without submitting draft");
                forest.menuOpen = false;
                break;
            case 2:
                witness.check(!loader.active && loader.item === null && input.text === "",
                    "fixture close unloads and clears draft");
                if (!witness.failed) console.info("FOREST_FIXTURE_VISUAL_PASS");
                stop(); Qt.quit();
                break;
            }
            if (witness.failed) { stop(); Qt.quit(); }
        }
    }
}
