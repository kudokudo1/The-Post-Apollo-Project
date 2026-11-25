import QtQuick
import Quickshell
import "./widgets" as Widgets

// Actual ForestW PanelWindow, never an operator desktop or native model host.
ShellRoot {
    id: witness
    property int phase: 0
    property bool failed: false
    property bool small: false
    property var parts: ({})
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
    function capture() {
        const names = {
            chat: "forestChatPane", heading: "forestChatHeading",
            preview: "forestPublicPreviewButton", pane: "forestSessionPreview",
            loader: "forestPublicPreviewLoader", empty: "forestEmptySessionPlaceholder",
            rail: "forestReasoningRail", coffee: "forestReasoningCoffee",
            prompt: "forestPromptRow", input: "forestPromptInput",
            send: "forestSendButton", voice: "forestVoiceButton", model: "forestModelPopup"
        };
        const result = {};
        for (const key in names) {
            result[key] = find(forest.contentItem, names[key]);
            if (!result[key]) check(false, "missing actual host item " + names[key]);
        }
        parts = result;
        return !failed;
    }
    function geometry(active) {
        const a = parts;
        check(a.pane.y >= a.heading.y + a.heading.height, "heading overlap");
        check(a.pane.y + a.pane.height <= a.prompt.y, "prompt overlap");
        check(a.pane.x + a.pane.width <= a.rail.x, "reasoning rail overlap");
        check(a.preview.x >= a.heading.x + a.heading.width, "preview button overlaps heading");
        check(a.loader.width === a.pane.width && a.loader.height === a.pane.height, "loader bounds");
        check(a.loader.active === active && a.loader.visible === active, "loader state");
        check(a.empty.visible !== active, "placeholder state");
        check(!forest.chatHostTrusted && !forest.voiceHostTrusted
            && forest.activeChatSessions.length === 0 && !a.send.enabledAction
            && !a.voice.backendReady, "host or action unexpectedly unlocked");
        if (active) {
            check(a.loader.status === Loader.Ready && a.loader.item !== null, "fixture not loaded");
            const feed = find(a.loader.item, "publicFixtureFeed");
            const list = feed ? find(feed, "conversationMessages") : null;
            check(feed && list && list.count === 2 && !feed.showHeader
                && !feed.showComposer && !feed.sendEnabled, "public transcript contract");
        } else {
            check(a.loader.item === null, "inactive fixture retained");
        }
    }
    // Emit only after the actual assertions and changes in a phase complete.
    function completePhase(n) {
        if (failed) { timer.stop(); Qt.quit(); return; }
        console.info("FOREST_HOST_PHASE_PASS " + n);
    }
    function finish() {
        if (!failed) console.info("FOREST_HOST_NATIVE_PASS");
        timer.stop();
        Qt.quit();
    }
    Widgets.ForestW { id: forest }
    Timer {
        id: timer
        interval: 350
        running: true
        repeat: true
        onTriggered: {
            if (witness.failed) { stop(); Qt.quit(); return; }
            const n = witness.phase++;
            switch (n) {
            case 0:
                if (!witness.capture()) return;
                witness.check(forest.screen !== null, "native screen unavailable");
                if (witness.failed) return;
                witness.small = forest.screen.width < 600;
                witness.check(witness.small
                    ? forest.screen.width === 420 && forest.screen.height === 340
                    : forest.screen.width === 1366 && forest.screen.height === 900,
                    "unexpected private output dimensions");
                witness.check(!forest.menuOpen && !parts.loader.active, "default-off");
                forest.menuOpen = true;
                break;
            case 1:
                witness.geometry(false);
                if (witness.small) {
                    witness.check(!parts.preview.interactive, "small viewport eligible");
                    parts.preview.leftClicked(null); // direct signal, not a physical pointer event
                    break;
                }
                witness.check(forest.frameWidth === 930 && forest.frameHeight === 610, "default stage");
                witness.check(parts.preview.interactive, "normal viewport ineligible");
                parts.input.text = "unsubmitted local draft";
                parts.preview.leftClicked(null);
                break;
            case 2:
                if (witness.small) {
                    witness.geometry(false);
                    witness.completePhase(n);
                    witness.finish();
                    return;
                }
                witness.geometry(true);
                witness.check(parts.input.text === "unsubmitted local draft", "preview changed draft");
                parts.coffee.leftClicked(null);
                forest.chassisLevel = 1;
                break;
            case 3:
                witness.geometry(true);
                witness.check(forest.reasoningRailExpanded && forest.frameHeight === 790, "taller/coffee");
                forest.chassisLevel = 3;
                forest.modelPopupOpen = true;
                break;
            case 4:
                witness.geometry(true);
                witness.check(forest.frameWidth > 930 && parts.model.visible, "full stage/model popup");
                forest.modelPopupOpen = false;
                forest.selectedTreeIndex = 1;
                break;
            case 5:
                witness.geometry(false);
                witness.check(!parts.preview.interactive, "non-CHERRY eligible");
                parts.preview.leftClicked(null);
                forest.selectedTreeIndex = 0;
                break;
            case 6:
                witness.geometry(false);
                parts.preview.leftClicked(null);
                break;
            case 7:
                witness.geometry(true);
                forest.menuOpen = false;
                break;
            case 8:
                witness.check(!parts.loader.active && parts.loader.item === null, "closed host retained fixture");
                witness.check(parts.input.text === "", "closed host retained draft");
                forest.menuOpen = true;
                break;
            case 9:
                witness.geometry(false);
                witness.check(parts.preview.interactive, "preview unavailable after explicit reopen");
                witness.completePhase(n);
                witness.finish();
                return;
            default:
                witness.check(false, "unexpected phase");
            }
            witness.completePhase(n);
        }
    }
}
