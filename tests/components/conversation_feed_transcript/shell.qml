import QtQuick
import QtQuick.Window
import Quickshell
import "./components" as Shared

// Real shared QML, fixed public messages, no adapters or transport.
ShellRoot {
    id: witness
    property int sent: 0
    property string lastText: ""
    property bool failed: false
    property int phase: 0
    property real initialTailHeight: 0
    property real earlierY: 0
    property var originalTail: null
    readonly property string firstBody: "Public response growing in the same row. ".repeat(45)
    readonly property string secondBody: firstBody + "Additional public response. ".repeat(45)
    Component.onCompleted: console.info("FEED_TRANSCRIPT_FIXTURE_STARTED")
    function check(ok, why) {
        if (!ok) {
            failed = true;
            console.error("FEED_TRANSCRIPT_FAIL // " + why);
        }
    }
    function geometry(headerVisible, composerVisible, y, h) {
        check(header.visible === headerVisible, "header visibility");
        check(composer.visible === composerVisible, "composer visibility");
        check(viewport.y === y && viewport.height === h, "viewport " + viewport.y + "/" + viewport.height + " expected " + y + "/" + h);
        check(viewport.width === feed.width, "viewport width");
        check(list.visible && list.count === 2, "messages retained");
    }
    function child(name) {
        for (let i = 0; i < feed.children.length; ++i) {
            if (feed.children[i].objectName === name)
                return feed.children[i];
        }
        return null;
    }
    readonly property var header: child("conversationHeader")
    readonly property var composer: child("conversationComposer")
    readonly property var viewport: child("conversationViewport")
    readonly property var list: child("conversationMessages")
    readonly property var sendError: child("conversationSendError")
    readonly property var input: {
        if (composer) {
            for (let i = 0; i < composer.children.length; ++i) {
                if (composer.children[i].objectName === "conversationInput")
                    return composer.children[i];
            }
        }
        return null;
    }

    Window {
        id: scene
        width: 480
        height: 360
        visible: true
        Shared.ConversationFeed {
            id: feed
            anchors.fill: parent
            conversation: ({id: "public-a", displayNameInProfile: "Public sample"})
            messages: [{direction: "outgoing", body: "Hello"}, {direction: "incoming", body: "Public answer"}]
            onSendRequested: function(conversationId, text) {
                witness.sent++;
                witness.lastText = text;
                witness.check(conversationId === "public-a", "wrong send destination");
            }
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: true
        onTriggered: {
            if (witness.failed) { stop(); Qt.quit(); return; }
            if (!header || !composer || !viewport || !list || !input || !sendError) {
                check(false, "missing production items");
                return;
            }
            const currentPhase = witness.phase++;
            switch (currentPhase) {
            case 0:
                check(feed.showHeader && feed.showComposer, "default opt-ins changed");
                geometry(true, true, 60, 230);
                input.text = "ordinary send";
                feed.trySend();
                check(sent === 1 && lastText === "ordinary send", "default send changed");
                feed.sendSuccessSerial++;
                check(input.text === "", "ordinary acknowledgement");
                input.text = "retained draft";
                feed.trySend();
                check(sent === 2, "second default send");
                input.text = "edited after send";
                feed.showHeader = false;
                break;
            case 1:
                geometry(false, true, 0, 290);
                feed.focusMessageInput(); // queued before mode switch
                feed.showComposer = false;
                feed.sendError = "public fixture test error";
                break;
            case 2:
                geometry(false, false, 0, 360);
                check(!input.enabled && !input.activeFocus && !input.focus, "hidden composer acquired focus");
                check(!sendError.visible, "hidden send error leaked into viewport");
                feed.trySend();
                feed.focusMessageInput();
                feed.sendSuccessSerial++;
                check(sent === 2, "hidden composer dispatched");
                check(input.text === "edited after send", "ack erased edited draft");
                check(!input.activeFocus && !input.focus, "hidden acknowledgement focused input");
                feed.scopeId = "other-public-scope";
                check(input.text === "", "scope draft leaked");
                feed.scopeId = "";
                check(input.text === "edited after send", "scope draft lost");
                feed.showHeader = true;
                scene.height = 240;
                break;
            case 3:
                geometry(true, false, 60, 180);
                feed.showHeader = false;
                break;
            case 4:
                geometry(false, false, 0, 240);
                feed.showHeader = true;
                feed.showComposer = true;
                feed.sendError = "";
                break;
            case 5:
                geometry(true, true, 60, 110);
                check(input.text === "edited after send", "restored composer lost draft");
                feed.discordMode = true;
                break;
            case 6:
                check(!header.visible && !composer.visible && !list.visible, "discord external mode changed");
                feed.discordMode = false;
                break;
            case 7:
                geometry(true, true, 60, 110);
                check(!feed.streamingTailEnabled
                    && !feed.updateStreamingTail(feed.effectiveScope, "not opted in"),
                    "default feed behavior changed");
                break;
            case 8:
                feed.showHeader = false;
                feed.showComposer = false;
                feed.sendEnabled = false;
                feed.streamingTailEnabled = true;
                scene.width = 300;
                scene.height = 160;
                feed.messages = [
                    {direction: "outgoing", body: "Earlier public text."},
                    {direction: "incoming", body: "Public response"}
                ];
                // The array replacement and window resize settle before the
                // next phase. Establish a real baseline before measuring growth.
                break;
            case 9:
                list.forceLayout();
                list.positionViewAtEnd();
                list.forceLayout();
                check(feed.streamingTailEligible && list.count === 2 && list.atYEnd,
                    "streaming baseline not at end");
                originalTail = list.itemAtIndex(1);
                if (!originalTail) { check(false, "missing tail delegate"); break; }
                initialTailHeight = originalTail.height;
                check(feed.updateStreamingTail(feed.effectiveScope, firstBody),
                    "valid tail update refused");
                check(list.count === 2 && feed.messages[1].body === "Public response",
                    "stable message model changed");
                break;
            case 10:
                check(list.count === 2 && list.itemAtIndex(1) === originalTail,
                    "tail row recreated");
                check(originalTail && originalTail.renderedBody === firstBody
                    && originalTail.height > initialTailHeight && list.atYEnd,
                    "tail did not grow and follow bottom");
                list.positionViewAtBeginning();
                break;
            case 11:
                check(!list.atYEnd, "earlier reading position missing");
                earlierY = list.contentY;
                check(feed.updateStreamingTail(feed.effectiveScope, secondBody),
                    "second tail update refused");
                break;
            case 12:
                check(!list.atYEnd && Math.abs(list.contentY - earlierY) <= 2
                    && list.count === 2, "reader pulled away from earlier text");
                check(!feed.updateStreamingTail("wrong-scope", "stale")
                    && !feed.updateStreamingTail(feed.effectiveScope, "é".repeat(8001)),
                    "invalid scope or oversized UTF8 accepted");
                list.positionViewAtEnd();
                break;
            case 13:
                check(list.itemAtIndex(1) && list.itemAtIndex(1).renderedBody === secondBody,
                    "newest snapshot missing on return");
                feed.scopeId = "new-public-scope";
                check(!feed.updateStreamingTail("default:public-a", "late"),
                    "old scope accepted");
                check(!feed._streamingTailActive, "scope change retained live body");
                check(feed.updateStreamingTail(feed.effectiveScope, "new public text"),
                    "new scope update refused");
                feed.streamingTailEnabled = false;
                check(!feed._streamingTailActive && feed._streamingTailBody === "",
                    "disable retained live body");
                check(sent === 2, "streaming dispatched a message");
                break;
            default:
                check(false, "unexpected test phase " + currentPhase);
            }
            // Emit a witness only AFTER this phase's assertions completed.
            // No pass on early Qt.quit, exception or failed check.
            if (witness.failed) {
                stop();
                Qt.quit();
                return;
            }
            console.info("FEED_TRANSCRIPT_PHASE_PASS " + currentPhase);
            if (currentPhase === 13) {
                console.info("FEED_TRANSCRIPT_NATIVE_PASS");
                stop();
                Qt.quit();
            }
        }
    }
}
