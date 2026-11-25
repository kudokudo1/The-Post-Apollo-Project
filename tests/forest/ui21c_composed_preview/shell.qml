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
    // Explicit public test input, not a producer/transport or live execution.
    readonly property var firstRef: ({requestId: "a".repeat(32), viewKey: "b".repeat(32), generation: 1})
    readonly property var secondRef: ({requestId: "c".repeat(32), viewKey: "d".repeat(32), generation: 2})
    function unit(ref, seq, name) {
        return {requestId: ref.requestId, viewKey: ref.viewKey, generation: ref.generation,
            sequence: seq, kind: "STATUS", statusPacket: {
                schema: "postapollo.forest.public-runtime-status.v1", status: name,
                sourceAuthenticated: false, permissionGranted: false,
                productionAuthority: false, modelExecutionPermitted: false, safeActions: []}};
    }
    function withdraw(ref, seq) {
        return {requestId: ref.requestId, viewKey: ref.viewKey, generation: ref.generation,
            sequence: seq, kind: "WITHDRAW", statusPacket: null};
    }
    function openRuntime(ref) {
        const item = preview.item;
        item.runtimeTreeKey = "CHERRY";
        item.runtimeCurrentCorrelation = ref;
        item.runtimeViewOpen = true;
        check(item.runtimeInitialized && item.runtimeEligible && item.openRuntimeLifetime(ref),
            "explicit runtime lifetime");
    }
    function verifyLoaded(expectedLabel = "") {
        const item = preview.item;
        const status = child(item, "publicFixtureStatus");
        const feed = child(item, "publicFixtureFeed");
        const runtime = child(item, "publicFixtureRuntimeStatus");
        check(item && status && feed && runtime, "missing composed production objects");
        if (!item || !status || !feed || !runtime) return;
        check(item.runtimeStatusText === expectedLabel && runtime.visible === (expectedLabel !== ""),
            "unexpected operation label");
        check(!runtime.sendEnabled && !runtime.stopEnabled && !runtime.sourceAuthenticated
            && !runtime.permissionGranted && !runtime.productionAuthority && !runtime.modelExecutionPermitted,
            "operation authority changed");
        check(expectedLabel ? runtime.height > 0 : runtime.height === 0, "status height");
        check(runtime.y === status.height && runtime.width === item.width, "operation label geometry");
        check(item.fixtureReady, "fixed session validation failed");
        check(item.transcriptReady && status.statusText === "HISTORY SNAPSHOT COMPLETE",
            "history status " + item.fixtureState + "/" + item.fixtureReason + "/" + status.statusText);
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
        check(status.height > 0 && feed.y === status.height + runtime.height
            && feed.height === item.height - status.height - runtime.height && feed.height > 0
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
                // No event may auto-open the disconnected fixture.
                preview.item.receiveRuntimeUnit(unit(firstRef, 1, "REQUEST_PENDING"));
                check(preview.item.runtimeState === "CLOSED", "incoming auto-open");
                openRuntime(firstRef);
                preview.item.receiveRuntimeUnit(unit(firstRef, 1, "REQUEST_PENDING"));
                scene.width = 300;
                scene.height = 160;
                break;
            case 2:
                verifyLoaded("REQUEST PENDING");
                preview.item.receiveRuntimeUnit(unit(firstRef, 2, "PREPARING"));
                preview.item.receiveRuntimeUnit(unit(firstRef, 3, "GENERATING"));
                preview.item.receiveRuntimeUnit(unit(firstRef, 4, "LOCAL_COMMIT_RECORDED"));
                break;
            case 3:
                verifyLoaded("LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED");
                openRuntime(secondRef);
                preview.item.receiveRuntimeUnit(unit(secondRef, 1, "REQUEST_PENDING"));
                preview.item.receiveRuntimeUnit(withdraw(firstRef, 5));
                preview.item.invalidateRuntimeLifetime(firstRef);
                check(!preview.item.openRuntimeLifetime(firstRef), "stale open accepted");
                break;
            case 4:
                verifyLoaded("REQUEST PENDING");
                preview.item.runtimeTreeKey = "MAPLE";
                check(preview.item.runtimeState === "CLOSED", "Tree loss not cleared");
                preview.item.runtimeTreeKey = "CHERRY";
                preview.item.receiveRuntimeUnit(unit(secondRef, 2, "PREPARING"));
                break;
            case 5:
                verifyLoaded();
                preview.active = false;
                break;
            case 6:
                check(preview.item === null, "fixture not destroyed");
                preview.active = true;
                break;
            case 7:
                verifyLoaded();
                check(preview.item.runtimeCurrentCorrelation === null, "old lifetime retained");
                preview.item.receiveRuntimeUnit(unit(secondRef, 2, "PREPARING"));
                preview.item.receiveRuntimeUnit(withdraw(secondRef, 2));
                verifyLoaded();
                preview.active = false;
                break;
            case 8:
                check(preview.item === null, "fixture survived unload");
                break;
            default:
                check(false, "unexpected phase");
            }
            if (witness.failed) {
                stop(); Qt.quit(); return;
            }
            console.info("UI2_PREVIEW_PHASE_PASS " + p);
            if (p === 8) {
                console.info("UI2_PREVIEW_NATIVE_PASS");
                stop(); Qt.quit();
            }
        }
    }
}
