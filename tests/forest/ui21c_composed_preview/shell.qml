import QtQuick
import QtQuick.Window
import Quickshell
import "./widgets/forest/ui2" as UI2

ShellRoot {
    id: witness
    property int phase: 0
    property bool failed: false
    property int sent: 0
    Component.onCompleted: console.info("UI2_PREVIEW_STARTED")

    function check(ok, why) {
        if (!ok) {
            failed = true;
            console.error("UI2_PREVIEW_FAIL // " + why);
        }
    }
    function child(item, name) {
        if (!item) return null;
        for (let i = 0; i < item.children.length; ++i)
            if (item.children[i].objectName === name)
                return item.children[i];
        return null;
    }
    function verifyLoaded() {
        const item = preview.item;
        const status = child(item, "publicFixtureStatus");
        const feed = child(item, "publicFixtureFeed");
        check(item && status && feed, "missing composed production objects");
        if (!item || !status || !feed) return;
        check(item.fixtureReady, "fixed session validation failed");
        check(status.statusText === "HISTORY SNAPSHOT COMPLETE", "history status");
        check(status.executionText === "PUBLIC FIXTURE // SEND / STOP LOCKED", "execution label");
        check(!status.sendEnabled && !status.stopEnabled && !status.permissionGranted
            && !status.sourceAuthenticated, "status authority changed");
        check(!feed.showHeader && !feed.showComposer && !feed.sendEnabled
            && !feed.richMessageActions && feed.messageTextFormat === Text.PlainText,
            "transcript-only gates");
        check(feed.messages.length === 2
            && feed.messages[0].body === "What is a Tree?"
            && feed.messages[1].direction === "incoming", "validated transcript");
        const header = child(feed, "conversationHeader");
        const composer = child(feed, "conversationComposer");
        const viewport = child(feed, "conversationViewport");
        const list = child(feed, "conversationMessages");
        check(header && composer && viewport && list, "missing actual shared objects");
        if (!header || !composer || !viewport || !list) return;
        check(!header.visible && !composer.visible && list.visible && list.count === 2,
            "duplicate controls or missing messages");
        check(status.height > 0 && feed.y === status.height
            && feed.height === item.height - status.height && feed.height > 0
            && viewport.y === 0 && viewport.height === feed.height,
            "composed geometry");
        const input = child(composer, "conversationInput");
        check(input && !input.enabled && !input.activeFocus && !input.focus,
            "hidden composer input enabled or focused");
        if (!input) return;
        input.text = "must never dispatch";
        const before = witness.sent;
        const countSend = function() { witness.sent++; };
        feed.sendRequested.connect(countSend);
        feed.trySend();
        feed.focusMessageInput();
        feed.sendRequested.disconnect(countSend);
        check(witness.sent === before, "fixture dispatched a send");
        check(!input.activeFocus && !input.focus, "hidden input gained focus");
        input.text = "";
    }
    Window {
        id: scene
        width: 480
        height: 240
        visible: true
        Loader {
            id: preview
            anchors.fill: parent
            active: false
            sourceComponent: UI2.PublicConversationFixture {}
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: true
        onTriggered: {
            const p = witness.phase++;
            switch (p) {
            case 0:
                check(!preview.active && preview.item === null, "preview auto-open");
                preview.active = true;
                break;
            case 1:
                verifyLoaded();
                scene.width = 300;
                scene.height = 160;
                break;
            case 2:
                verifyLoaded();
                preview.active = false;
                break;
            case 3:
                check(preview.item === null, "fixture not destroyed");
                preview.active = true;
                break;
            case 4:
                verifyLoaded();
                preview.active = false;
                break;
            case 5:
                check(preview.item === null, "fixture survived unload");
                break;
            default:
                check(false, "unexpected phase");
            }
            if (witness.failed) {
                stop(); Qt.quit(); return;
            }
            console.info("UI2_PREVIEW_PHASE_PASS " + p);
            if (p === 5) {
                console.info("UI2_PREVIEW_NATIVE_PASS");
                stop(); Qt.quit();
            }
        }
    }
}
