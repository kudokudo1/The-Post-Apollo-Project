import QtQuick
import QtQuick.Window
import Quickshell
import "./widgets/forest/ui2" as UI2
import "ActualReplay.js" as Actual

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
    readonly property var emptyHistory: ({treeKey:"CHERRY",generation:3,
        sessionId:"1".repeat(32),revision:0,viewKey:"a".repeat(32)})
    readonly property var reopenedHistory: ({treeKey:"CHERRY",generation:4,
        sessionId:"1".repeat(32),revision:2,viewKey:"b".repeat(32)})
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
    // Actual child records, captured and independently correlated before this
    // native replay. This is not a live Process-to-Loader connection.
    property var actualRows: null
    property var hiddenOriginal: null
    function actualUnits(units) {
        for (const u of units) preview.item.receiveRuntimeUnit(u);
    }
    function actualPage(scope, entry, next=false) {
        const item=preview.item;
        check(next ? item.nextHistoryPage(scope,entry.requestId,2)
            : item.openHistoryPage(scope,entry.requestId,2), "actual explicit page");
        const req=item.historyPendingRequest;
        check(req && req.requestId===entry.requestId && req.after===entry.after,
            "actual independent request pin");
        check(item.receiveHistoryPage(scope,entry.frame), "actual page delivery");
        check(item.historyPendingRequest===null,"actual request remains pending");
        // Compare every delivered row to the actual independently pinned PAGE.
        // The public fixture prompt may have the same text as the literal sample.
        const rows=actualFeed().messages;
        check(rows.length===entry.after+entry.frame.messages.length,"actual accumulated row count");
        for (let i=0;i<entry.frame.messages.length;i++) {
            const expected=entry.frame.messages[i], actual=rows[entry.after+i];
            check(actual && /^[0-9a-f]{32}$/.test(expected.turn_id)
                && actual.turnId===expected.turn_id && actual.ordinal===expected.ordinal
                && actual.direction===(expected.role==="user"?"outgoing":"incoming")
                && actual.body===expected.text, "actual projected row identity/content");
        }
    }
    function actualAttach(scope) {
        preview.item.historyCurrentScope=scope;
        check(preview.item.attachHistoryScope(scope),"actual attach");
    }
    function actualRetire() {
        preview.item.historyCurrentScope=null;
        preview.item.runtimeCurrentCorrelation=null;
        preview.item.runtimeViewOpen=false;
    }
    function actualFeed() { return child(preview.item,"publicFixtureFeed"); }
    function verifyConnected(count,state) {
        const item=preview.item, feed=child(item,"publicFixtureFeed");
        check(item && feed && item.connectedHistoryMode && feed.messages.length===count,
            "connected history row count");
        check(item.fixtureState===state, "connected history state "+item.fixtureState);
        check(!feed.sendEnabled && !feed.showComposer && !feed.richMessageActions,
            "connected execution gate");
        // Literal sample identity, not its question wording, identifies fallback.
        check(!feed.messages.some(row=>row.turnId==="public-turn-1"
            || row.turnId==="public-turn-2"
            || row.body==="Public sample: a Tree is a Forest agent identity."),
            "literal history leaked");
    }
    function verifyConnectedStatus(label) {
        const item=preview.item, runtime=child(item,"publicFixtureRuntimeStatus");
        const historyStatus=child(item,"publicFixtureStatus"), feed=child(item,"publicFixtureFeed");
        check(item && item.visible && !item.transcriptReady && runtime && historyStatus && feed,
            "connected view depends on literal transcript");
        if (!item || !runtime || !historyStatus || !feed) return;
        check(item.runtimeStatusText===label && runtime.visible===(label!==""),
            "connected operation label");
        check(!runtime.sendEnabled && !runtime.stopEnabled && !runtime.sourceAuthenticated
            && !runtime.permissionGranted && !runtime.productionAuthority && !runtime.modelExecutionPermitted,
            "connected operation authority");
        check(feed.height>0 && feed.y===historyStatus.height+runtime.height
            && feed.height===item.height-historyStatus.height-runtime.height,
            "connected status geometry");
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
    function reviewScope(n,rev=1) {
        return {treeKey:"CHERRY",taskAlias:"f".repeat(32),
            viewKey:n.toString(16).padStart(32,"0"),planRevision:rev};
    }
    function fixedReviewRows() {
        return [{category:"CONTINUITY",state:"PRESERVED"},
            {category:"CONTEXT",state:"REVIEW"},{category:"WORKSHOP",state:"AVAILABLE"},
            {category:"MODEL_FORM",state:"DORMANT"},{category:"REASONING",state:"UNKNOWN"}];
    }
    function verifyReview(state,count) {
        const item=review.item;
        check(item && item.reviewState===state && item.reviewRows.length===count,
            "review state or rows "+state);
        if (!item) return;
        const body=child(item,"restorationReviewBody");
        check(body && body.visible===(state!=="CLOSED"),"review body visibility");
        check(!item.sourceAuthenticated && !item.permissionGranted && !item.productionAuthority
            && !item.modelExecutionPermitted && !item.restorationEnabled && !item.sendEnabled
            && !item.stopEnabled, "review authority changed");
        check(preview.item===null, "conversation and review coexist");
        if (state==="DISPLAYING") {
            check(item.reviewRows.every((r,i)=>r.category===fixedReviewRows()[i].category
                && r.state===fixedReviewRows()[i].state),"fixed review ordering");
            check(body.implicitHeight<=body.height,"review exceeds viewport");
            const badge=child(body,"restorationReviewSynthetic"), locked=child(body,"restorationReviewLocked");
            check(badge && locked && badge.text==="SYNTHETIC // NO LIVE SEASON OR AVAILABILITY"
                && locked.text==="READ ONLY // RESTORATION LOCKED" && !badge.truncated && !locked.truncated,
                "missing synthetic/locked labels");
        }
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
        Loader {
            id: review
            anchors.fill: parent
            active: false
            sourceComponent: UI2.PublicRestorationReview {}
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
                scene.width=480;
                scene.height=240;
                preview.active=true;
                break;
            case 14:
                verifyLoaded();
                check(preview.item.beginConnectedHistory(), "fresh connected mode");
                preview.item.historyCurrentScope=emptyHistory;
                check(preview.item.attachHistoryScope(emptyHistory), "empty revision attach");
                check(preview.item.openHistoryPage(emptyHistory,pageOne,2), "empty revision request");
                check(preview.item.receiveHistoryPage(emptyHistory,{
                    schema:"postapollo.forest.public-history-display.v1", requestId:pageOne,
                    treeKey:emptyHistory.treeKey,generation:emptyHistory.generation,
                    sessionId:emptyHistory.sessionId,revision:0,messages:[],complete:true
                }), "empty complete snapshot");
                verifyConnected(0,"COMPLETE");
                check(preview.item.historyNextAfter===null && !preview.item.nextHistoryPage(emptyHistory,pageTwo,2),
                    "empty completed snapshot offered continuation");
                // Owner retires old history before NEXT, not in response to status.
                preview.item.historyCurrentScope=null;
                openRuntime(firstRef);
                preview.item.receiveRuntimeUnit(unit(firstRef,1,"REQUEST_PENDING"));
                scene.width=300;
                scene.height=160;
                break;
            case 15:
                verifyConnected(0,"CLOSED");
                verifyConnectedStatus("REQUEST PENDING");
                preview.item.receiveRuntimeUnit(unit(firstRef,2,"PREPARING"));
                preview.item.receiveRuntimeUnit(unit(firstRef,3,"GENERATING"));
                preview.item.receiveRuntimeUnit(unit(firstRef,4,"LOCAL_COMMIT_RECORDED"));
                break;
            case 16:
                verifyConnected(0,"CLOSED");
                verifyConnectedStatus("LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED");
                // Explicit history attachment/page, not implicit commit refresh.
                preview.item.historyCurrentScope=reopenedHistory;
                check(preview.item.attachHistoryScope(reopenedHistory), "committed scope attach");
                check(preview.item.openHistoryPage(reopenedHistory,pageTwo,1), "committed first page");
                check(preview.item.receiveHistoryPage(reopenedHistory,
                    historyPage(reopenedHistory,pageTwo,1,false)), "committed partial");
                break;
            case 17:
                verifyConnected(1,"PARTIAL");
                verifyConnectedStatus("LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED");
                preview.item.invalidateRuntimeLifetime(firstRef);
                verifyConnected(1,"PARTIAL");
                verifyConnectedStatus("");
                check(preview.item.nextHistoryPage(reopenedHistory,pageThree,1), "continuation after status clear");
                check(preview.item.receiveHistoryPage(reopenedHistory,
                    historyPage(reopenedHistory,pageThree,2,true)), "committed complete");
                openRuntime(secondRef);
                preview.item.receiveRuntimeUnit(unit(secondRef,1,"REQUEST_PENDING"));
                break;
            case 18:
                verifyConnected(2,"COMPLETE");
                verifyConnectedStatus("REQUEST PENDING");
                preview.item.receiveRuntimeUnit(unit(secondRef,2,"PREPARING"));
                preview.item.receiveRuntimeUnit(unit(secondRef,3,"GENERATING"));
                preview.item.receiveRuntimeUnit(unit(secondRef,4,"STOP_REQUESTED"));
                preview.item.refuseHistoryScope(reopenedHistory);
                break;
            case 19:
                verifyConnected(0,"UNAVAILABLE");
                verifyConnectedStatus("STOP REQUESTED // OUTCOME PENDING");
                preview.item.receiveRuntimeUnit(unit(secondRef,5,"UNKNOWN_HOLD"));
                preview.item.historyCurrentScope=null;
                break;
            case 20:
                verifyConnected(0,"CLOSED");
                verifyConnectedStatus("UNKNOWN HOLD // NO AUTOMATIC RETRY");
                check(!preview.item.beginConnectedHistory(), "connected mode reopened");
                preview.item.runtimeCurrentCorrelation=null;
                verifyConnectedStatus("");
                preview.active=false;
                break;
            case 21:
                check(preview.item===null, "joined presentation survived unload");
                scene.width=480;
                scene.height=240;
                review.active=true;
                break;
            case 22: {
                verifyReview("CLOSED",0);
                const item=review.item, a=reviewScope(1);
                item.ownerScope=a;
                check(!item.openReview(a),"open without synthetic owner");
                item.syntheticOwner=true;
                check(!item.receiveReview(a,fixedReviewRows()),"unsolicited review");
                check(item.openReview(a),"explicit review open");
                verifyReview("PENDING",0);
                check(item.receiveReview(a,fixedReviewRows()),"review plan accepted");
                break;
            }
            case 23:
                verifyReview("DISPLAYING",5);
                scene.width=300;
                scene.height=160;
                break;
            case 24: {
                verifyReview("DISPLAYING",5);
                const item=review.item, a=reviewScope(1), b=reviewScope(2,2);
                item.ownerScope=b;
                verifyReview("CLOSED",0);
                check(item.openReview(b),"replacement review");
                check(!item.receiveReview(a,fixedReviewRows()) && !item.refuseReview(a)
                    && !item.dismissReview(a) && !item.openReview(a),"stale scope accepted");
                verifyReview("PENDING",0);
                check(item.receiveReview(b,fixedReviewRows()),"replacement plan");
                break;
            }
            case 25: {
                verifyReview("DISPLAYING",5);
                const item=review.item, b=reviewScope(2,2);
                check(!item.receiveReview(b,fixedReviewRows()),"duplicate plan accepted");
                verifyReview("UNAVAILABLE",0);
                check(!item.openReview(b),"refused view reused");
                const wrongPlans=[
                    fixedReviewRows().slice(0,4),
                    fixedReviewRows().concat([{category:"EXTRA",state:"UNKNOWN"}]),
                    [fixedReviewRows()[0],...fixedReviewRows().slice(0,4)],
                    fixedReviewRows().slice().reverse(),
                    fixedReviewRows().map((r,i)=>i===1?{category:r.category,state:"ACTIVE"}:r),
                    fixedReviewRows().map((r,i)=>i===1?{category:r.category,state:r.state,text:"not public"}:r)
                ];
                for(let i=0;i<wrongPlans.length;i++){
                    const ref=reviewScope(3+i,3+i);
                    item.ownerScope=ref;
                    check(item.openReview(ref),"invalid plan test open");
                    check(!item.receiveReview(ref,wrongPlans[i]),"invalid plan accepted");
                    verifyReview("UNAVAILABLE",0);
                    check(!item.receiveReview(ref,fixedReviewRows()),"invalid lifetime recovered");
                }
                break;
            }
            case 26: {
                const item=review.item, ref=reviewScope(10,10);
                item.ownerScope=ref;
                check(item.openReview(ref)&&item.receiveReview(ref,fixedReviewRows()),"dismiss setup");
                check(item.dismissReview(ref),"explicit dismiss");
                verifyReview("CLOSED",0);
                check(!item.openReview(ref)&&!item.receiveReview(ref,fixedReviewRows()),"dismiss replay");
                const next=reviewScope(11,11);
                item.ownerScope=next;
                check(item.openReview(next)&&item.receiveReview(next,fixedReviewRows()),"scope loss setup");
                item.syntheticOwner=false;
                verifyReview("CLOSED",0);
                item.syntheticOwner=true;
                check(!item.openReview(next),"scope restored old view");
                verifyReview("CLOSED",0);
                break;
            }
            case 27: {
                const item=review.item, ref=reviewScope(12,12);
                item.ownerScope=ref;
                check(item.openReview(ref)&&item.receiveReview(ref,fixedReviewRows()),"viewport loss setup");
                scene.width=299;
                break;
            }
            case 28:
                verifyReview("CLOSED",0);
                scene.width=300;
                break;
            case 29: {
                verifyReview("CLOSED",0);
                const item=review.item;
                check(!item.openReview(reviewScope(12,12)), "viewport loss replay");
                const ref=reviewScope(13,13);
                item.ownerScope=ref;
                check(item.openReview(ref)&&item.receiveReview(ref,fixedReviewRows()),"owner null setup");
                item.ownerScope=null;
                verifyReview("CLOSED",0);
                review.active=false;
                break;
            }
            case 30:
                check(review.item===null && preview.item===null, "review survived unload");
                break;
            case 31:
                preview.active=true;
                break;
            case 32: {
                const d=Actual.replay;
                verifyLoaded();
                check(preview.item.beginConnectedHistory(),"actual connected mode");
                openRuntime(d.a);
                actualUnits(d.unitsA);
                verifyConnected(0,"CLOSED");
                verifyConnectedStatus("LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED");
                actualAttach(d.h1);
                actualPage(d.h1,d.first);
                verifyConnected(2,"COMPLETE");
                check(actualFeed().messages[0].body==="What is a Tree?"
                    && actualFeed().messages[0].turnId!== "public-turn-1",
                    "shared prompt must retain actual public alias");
                break;
            }
            case 33: {
                const d=Actual.replay;
                actualRetire();
                verifyConnected(0,"CLOSED");
                openRuntime(d.b);
                actualUnits(d.unitsB);
                verifyConnectedStatus("LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED");
                verifyConnected(0,"CLOSED");
                actualAttach(d.h2);
                actualPage(d.h2,d.second[0]);
                verifyConnected(2,"PARTIAL");
                check(preview.item.historyNextAfter===2,"actual next cursor");
                break;
            }
            case 34: {
                const d=Actual.replay;
                actualPage(d.h2,d.second[1],true);
                verifyConnected(4,"COMPLETE");
                actualRows=JSON.stringify(actualFeed().messages);
                check(actualFeed().messages.filter(r=>r.direction==="incoming").length===2,
                    "actual two replies");
                actualRetire();
                verifyConnected(0,"CLOSED");
                verifyConnectedStatus("");
                break;
            }
            case 35: {
                const d=Actual.replay;
                check(d.h3.sessionId===d.h2.sessionId && d.h3.viewKey!==d.h2.viewKey,
                    "actual reopen scope");
                actualAttach(d.h3);
                actualPage(d.h3,d.reopened[0]);
                verifyConnected(2,"PARTIAL");
                check(!preview.item.receiveHistoryPage(d.h2,d.second[1].frame),"old page accepted");
                preview.item.refuseHistoryScope(d.h2);
                verifyConnected(2,"PARTIAL");
                actualPage(d.h3,d.reopened[1],true);
                verifyConnected(4,"COMPLETE");
                check(JSON.stringify(actualFeed().messages)===actualRows,"reopen rows changed");
                break;
            }
            case 36: {
                const d=Actual.replay;
                actualRetire();
                openRuntime(d.c);
                actualUnits(d.unitsC);
                verifyConnectedStatus("GENERATING");
                preview.item.receiveRuntimeUnit(d.unitsB[0]);
                preview.item.invalidateRuntimeLifetime(d.b);
                verifyConnectedStatus("GENERATING");
                verifyConnected(0,"CLOSED");
                actualUnits(d.stop);
                verifyConnectedStatus("STOP REQUESTED // OUTCOME PENDING");
                break;
            }
            case 37: {
                const d=Actual.replay;
                actualUnits(d.abort);
                verifyConnected(0,"CLOSED");
                check(preview.item.runtimeStatusText!=="LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED",
                    "aborted third turn painted as commit");
                const seq=d.unitsC.concat(d.stop,d.abort).slice(-1)[0].sequence;
                check(!preview.item.recordRuntimeLocalAbort(d.b,d.abortCode,seq),
                    "stale abort accepted");
                check(preview.item.recordRuntimeLocalAbort(d.c,d.abortCode,seq),
                    "actual typed abort refused");
                verifyConnectedStatus("LOCAL ABORT RECORDED // DELIVERY UNCONFIRMED");
                check(actualFeed().messages.length===0,"provisional reply");
                preview.active=false;
                break;
            }
            case 38:
                check(preview.item===null,"actual old Loader survived");
                preview.active=true;
                break;
            case 39: {
                const d=Actual.replay;
                verifyLoaded();
                check(preview.item.beginConnectedHistory(),"new Loader connected mode");
                preview.item.receiveRuntimeUnit(d.unitsC[0]);
                check(!preview.item.recordRuntimeLocalAbort(d.c,d.abortCode,4),"old abort opened replacement");
                check(!preview.item.receiveHistoryPage(d.h3,d.reopened[0].frame),"old page opened replacement");
                verifyConnected(0,"CLOSED");
                verifyConnectedStatus("");
                preview.active=false;
                break;
            }
            case 40:
                check(preview.item===null,"actual replay Loader survived");
                break;
            case 41:
                preview.active=true;
                break;
            case 42: {
                const d=Actual.replay;
                hiddenOriginal=preview.item;
                verifyLoaded();
                check(hiddenOriginal.beginConnectedHistory(),"visibility connected mode");
                openRuntime(d.b);
                actualUnits(d.unitsB);
                actualAttach(d.h2);
                actualPage(d.h2,d.second[0]);
                verifyConnected(2,"PARTIAL");
                check(hiddenOriginal.nextHistoryPage(d.h2,d.second[1].requestId,2),
                    "visibility pending continuation");
                verifyConnected(2,"PENDING");
                verifyConnectedStatus("LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED");
                preview.visible=false;
                break;
            }
            case 43: {
                const d=Actual.replay, item=preview.item;
                check(item===hiddenOriginal && !item.visible,"original hidden, not unloaded");
                check(!item.historyScopeActive && item.historyPendingRequest===null
                    && actualFeed().messages.length===0 && item.runtimeState==="CLOSED"
                    && item.runtimeStatusText==="","hidden original retains presentation");
                check(!item.receiveHistoryPage(d.h2,d.second[1].frame),"hidden page accepted");
                item.receiveRuntimeUnit(d.unitsB[0]);
                preview.visible=true;
                break;
            }
            case 44: {
                const d=Actual.replay, item=preview.item;
                check(item===hiddenOriginal && item.visible,"original re-shown");
                verifyConnected(0,"CLOSED");
                verifyConnectedStatus("");
                check(!item.attachHistoryScope(d.h2),"retired history view reopened");
                check(!item.openRuntimeLifetime(d.b),"retired status view reopened");
                check(!item.receiveHistoryPage(d.h2,d.second[1].frame),"retired page accepted");
                check(actualFeed().messages.length===0 && item.runtimeStatusText==="",
                    "retired data revived");
                actualRetire();
                actualAttach(d.h3);
                actualPage(d.h3,d.reopened[0]);
                verifyConnected(2,"PARTIAL");
                check(!item.receiveHistoryPage(d.h2,d.second[1].frame),"old page reached fresh scope");
                actualPage(d.h3,d.reopened[1],true);
                verifyConnected(4,"COMPLETE");
                break;
            }
            case 45: {
                const d=Actual.replay;
                actualRetire();
                openRuntime(d.c);
                actualUnits(d.unitsC);
                actualUnits(d.stop);
                actualUnits(d.abort);
                const seq=d.unitsC.concat(d.stop,d.abort).slice(-1)[0].sequence;
                check(preview.item.recordRuntimeLocalAbort(d.c,d.abortCode,seq),
                    "visibility typed abort setup");
                verifyConnectedStatus("LOCAL ABORT RECORDED // DELIVERY UNCONFIRMED");
                preview.visible=false;
                break;
            }
            case 46: {
                const d=Actual.replay,item=preview.item;
                check(item===hiddenOriginal && !item.visible && item.runtimeState==="CLOSED"
                    && item.runtimeStatusText==="","hidden abort survives");
                const seq=d.unitsC.concat(d.stop,d.abort).slice(-1)[0].sequence;
                check(!item.recordRuntimeLocalAbort(d.c,d.abortCode,seq),"hidden abort accepted");
                preview.visible=true;
                break;
            }
            case 47: {
                const d=Actual.replay,item=preview.item;
                check(item===hiddenOriginal && item.visible,"abort original re-shown");
                verifyConnected(0,"CLOSED");
                verifyConnectedStatus("");
                const seq=d.unitsC.concat(d.stop,d.abort).slice(-1)[0].sequence;
                check(!item.recordRuntimeLocalAbort(d.c,d.abortCode,seq),"old abort revived");
                check(!item.openRuntimeLifetime(d.c),"old terminal lifetime reopened");
                verifyConnectedStatus("");
                preview.active=false;
                hiddenOriginal=null;
                break;
            }
            case 48:
                check(preview.item===null,"visibility original survived unload");
                break;
            default:
                check(false, "unexpected phase");
            }
            if (witness.failed) {
                stop(); Qt.quit(); return;
            }
            console.info("UI2_PREVIEW_PHASE_PASS " + p);
            if (p === 48) {
                console.info("UI2_PREVIEW_NATIVE_PASS");
                stop(); Qt.quit();
            }
        }
    }
}
