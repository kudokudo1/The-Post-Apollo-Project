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
    readonly property var historyA: ({treeKey:"CHERRY", generation:1, sessionId:"1".repeat(32),
        revision:2, viewKey:"2".repeat(32)})
    readonly property var historyB: ({treeKey:"CHERRY", generation:2, sessionId:"1".repeat(32),
        revision:2, viewKey:"3".repeat(32)})
    readonly property string pageOne: "4".repeat(32)
    readonly property string pageTwo: "5".repeat(32)
    readonly property string pageThree: "6".repeat(32)
    function historyPage(ref,rid,ordinal,complete) {
        return {schema:"postapollo.forest.public-history-display.v1",requestId:rid,
            treeKey:ref.treeKey,generation:ref.generation,sessionId:ref.sessionId,revision:ref.revision,
            messages:[{turn_id:(ordinal===1?"7":"8").repeat(32),ordinal:ordinal,
                role:ordinal===1?"user":"assistant",text:ordinal===1?"Public first question":"Public committed reply"}],
            complete:complete};
    }
    function verifyConnected(count,state) {
        const item=preview.item, feed=child(item,"publicFixtureFeed");
        check(item && feed && item.connectedHistoryMode && feed.messages.length===count,
            "connected history row count");
        check(item.fixtureState===state, "connected history state "+item.fixtureState);
        check(!feed.sendEnabled && !feed.showComposer && !feed.richMessageActions,
            "connected execution gate");
        check(!feed.messages.some(row=>row.body==="What is a Tree?"), "literal history leaked");
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
                preview.active=true;
                break;
            case 9:
                verifyLoaded();
                check(preview.item.beginConnectedHistory(), "explicit connected mode");
                verifyConnected(0,"CLOSED");
                preview.item.historyCurrentScope=historyA;
                check(preview.item.attachHistoryScope(historyA), "attach accepted history");
                verifyConnected(0,"CLOSED");
                check(preview.item.openHistoryPage(historyA,pageOne,1), "first request");
                check(preview.item.historyPendingRequest.after===0, "first cursor");
                check(preview.item.receiveHistoryPage(historyA,historyPage(historyA,pageOne,1,false)), "partial page");
                break;
            case 10:
                verifyConnected(1,"PARTIAL");
                check(preview.item.historyNextAfter===1, "next cursor");
                check(preview.item.nextHistoryPage(historyA,pageTwo,1), "next request");
                check(preview.item.receiveHistoryPage(historyA,historyPage(historyA,pageTwo,2,true)), "complete page");
                break;
            case 11:
                verifyConnected(2,"COMPLETE");
                preview.item.historyCurrentScope=historyB;
                verifyConnected(0,"CLOSED");
                check(preview.item.attachHistoryScope(historyB), "new history scope");
                check(preview.item.openHistoryPage(historyB,pageThree,1), "new request");
                check(!preview.item.receiveHistoryPage(historyA,historyPage(historyA,pageTwo,2,true)), "old page");
                preview.item.refuseHistoryScope(historyA);
                check(!preview.item.attachHistoryScope(historyA), "old attachment");
                verifyConnected(0,"PENDING");
                check(preview.item.receiveHistoryPage(historyB,historyPage(historyB,pageThree,1,false)), "new partial");
                break;
            case 12:
                verifyConnected(1,"PARTIAL");
                preview.item.refuseHistoryScope(historyB);
                verifyConnected(0,"UNAVAILABLE");
                check(!preview.item.openHistoryPage(historyB,"9".repeat(32),1), "refused scope reopened");
                preview.item.historyCurrentScope=null;
                verifyConnected(0,"CLOSED");
                preview.item.historyCurrentScope=historyB;
                check(!preview.item.attachHistoryScope(historyB), "reused view accepted");
                verifyConnected(0,"CLOSED");
                preview.active=false;
                break;
            case 13:
                check(preview.item===null, "connected fixture survived unload");
                break;
            default:
                check(false, "unexpected phase");
            }
            if (witness.failed) {
                stop(); Qt.quit(); return;
            }
            console.info("UI2_PREVIEW_PHASE_PASS " + p);
            if (p === 13) {
                console.info("UI2_PREVIEW_NATIVE_PASS");
                stop(); Qt.quit();
            }
        }
    }
}
