import QtQuick
import Quickshell
import Quickshell.Io
import "./widgets" as Widgets
import "./widgets/forest/ui2" as Review

// Actual ForestW PanelWindow, never an operator desktop or native model host.
ShellRoot {
    id: witness
    property int phase: 0
    property bool failed: false
    property bool small: false
    property bool compact: false
    property var parts: ({})
    property var joinedParent: null
    property int joinedCommits: 0
    property int joinedSteps: 0
    property int joinedPages: 0
    property var joinedRows: []
    property string joinedAlias: ""
    property string joinedLast: ""
    property bool joinedReopened: false
    property int joinedStart: 0
    property int negativeCase: 0
    property bool negativeTriggered: false
    property int reviewPhase: 0
    property var originalPreviewComponent: null
    property var firstReviewScope: null
    property var secondReviewScope: null
    readonly property var reviewPlan: [{category:"CONTINUITY",state:"PRESERVED"},
        {category:"CONTEXT",state:"REVIEW"},{category:"WORKSHOP",state:"AVAILABLE"},
        {category:"MODEL_FORM",state:"DORMANT"},{category:"REASONING",state:"UNKNOWN"}]
    property string dbStage: ""
    property int dbChecks: 0
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
    // Explicit test-only units, never an installed producer or permission.
    readonly property var firstRef: ({requestId: "a".repeat(32), viewKey: "b".repeat(32), generation: 1})
    readonly property var secondRef: ({requestId: "c".repeat(32), viewKey: "d".repeat(32), generation: 2})
    readonly property var thirdRef: ({requestId: "e".repeat(32), viewKey: "f".repeat(32), generation: 3})
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
    function openRuntime(item, ref) {
        // The test host supplies currentness independently of incoming units.
        item.runtimeTreeKey = forest.activeTree.sessionKey;
        item.runtimeCurrentCorrelation = ref;
        item.runtimeViewOpen = true;
        check(item.runtimeInitialized && item.runtimeEligible && item.openRuntimeLifetime(ref),
            "explicit fixture lifetime");
    }
    function statusGeometry(expected) {
        geometry(true);
        if (failed) return false;
        const item = parts.loader.item;
        const status = find(item, "publicFixtureStatus");
        const runtime = find(item, "publicFixtureRuntimeStatus");
        const feed = find(item, "publicFixtureFeed");
        const viewport = find(feed, "conversationViewport");
        check(status && runtime && feed && viewport, "missing actual status/viewport");
        if (failed) return false;
        check(item.runtimeStatusText === expected && runtime.visible === (expected !== ""),
            "actual operation label");
        check(expected ? runtime.height > 0 : runtime.height === 0, "status collapse/height");
        check(status.statusText === "HISTORY SNAPSHOT COMPLETE"
            && status.executionText === "PUBLIC FIXTURE // SEND / STOP LOCKED"
            && item.transcriptReady && feed.messages.length === 2
            && feed.messages[0].body === "What is a Tree?"
            && feed.messages[1].direction === "incoming", "history/transcript changed");
        check(!runtime.sendEnabled && !runtime.stopEnabled && !runtime.sourceAuthenticated
            && !runtime.permissionGranted && !runtime.productionAuthority
            && !runtime.modelExecutionPermitted, "status authority changed");
        check(runtime.y === status.height && runtime.width === item.width
            && feed.y === status.height + runtime.height
            && feed.height === item.height - feed.y && feed.height > 0
            && viewport.y === 0 && viewport.height === feed.height, "actual status/feed geometry");
        check(parts.pane.width >= 300 && parts.pane.height >= 160, "measured usable viewport");
        console.info("FOREST_HOST_STATUS_GEOMETRY " + parts.pane.width + "x" + parts.pane.height
            + " label=" + runtime.height + " feed=" + feed.height);
        return !failed;
    }
    function runtimePhase(n) {
        const item = parts.loader.item;
        switch (n) {
        case 0:
            if (!statusGeometry("")) return;
            check(item.runtimeCurrentCorrelation === null, "default correlation");
            item.receiveRuntimeUnit(unit(firstRef, 1, "REQUEST_PENDING"));
            check(item.runtimeState === "CLOSED", "incoming auto-open");
            openRuntime(item, firstRef);
            item.receiveRuntimeUnit(unit(firstRef, 1, "REQUEST_PENDING"));
            item.receiveRuntimeUnit(unit(firstRef, 2, "PREPARING"));
            item.receiveRuntimeUnit(unit(firstRef, 3, "GENERATING"));
            item.receiveRuntimeUnit(unit(firstRef, 4, "LOCAL_COMMIT_RECORDED"));
            break;
        case 1:
            if (!statusGeometry("LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED")) return;
            check(parts.input.text === "unsubmitted local draft", "active status changed draft");
            forest.selectedTreeIndex = 1;
            break;
        case 2:
            geometry(false);
            check(!parts.preview.interactive, "non-CHERRY retained status lifetime");
            forest.selectedTreeIndex = 0;
            break;
        case 3:
            geometry(false);
            check(parts.preview.interactive, "CHERRY gate unavailable");
            parts.preview.leftClicked(null);
            break;
        case 4:
            if (!statusGeometry("")) return;
            check(item.runtimeCurrentCorrelation === null, "replacement Loader retained old correlation");
            item.receiveRuntimeUnit(unit(firstRef, 4, "LOCAL_COMMIT_RECORDED"));
            item.receiveRuntimeUnit(withdraw(firstRef, 5));
            check(item.runtimeState === "CLOSED", "old callback reopened replacement");
            openRuntime(item, secondRef);
            item.receiveRuntimeUnit(unit(secondRef, 1, "REQUEST_PENDING"));
            item.receiveRuntimeUnit(withdraw(firstRef, 5));
            item.invalidateRuntimeLifetime(firstRef);
            check(!item.openRuntimeLifetime(firstRef), "stale open accepted");
            break;
        case 5:
            if (!statusGeometry("REQUEST PENDING")) return;
            item.runtimeCurrentCorrelation = null;
            check(item.runtimeState === "CLOSED", "independent currentness loss not cleared");
            item.receiveRuntimeUnit(unit(secondRef, 2, "PREPARING"));
            break;
        case 6:
            if (!statusGeometry("")) return;
            openRuntime(item, thirdRef);
            item.receiveRuntimeUnit(unit(thirdRef, 1, "REQUEST_PENDING"));
            check(item.runtimeStatusText === "REQUEST PENDING", "fresh lifetime did not paint");
            forest.menuOpen = false;
            break;
        case 7:
            check(!parts.loader.active && parts.loader.item === null, "closed active host retained fixture");
            check(parts.input.text === "", "closed host retained draft");
            break;
        default: check(false, "unexpected runtime phase");
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
    Component { id: parentType; ParentProcess {} }
    function startJoined() {
        const item = parts.loader.item;
        if (!item || !parts.loader.visible) { check(false,"joined loader"); finish(); return; }
        const p = parentType.createObject(witness,{trial:"9".repeat(32),
            fixtureDirectory:Quickshell.shellPath("privateJoined"),originalOwner:item,
            originalLoader:parts.loader,joined:true,acceptOffer:true});
        if (!p) { check(false,"joined create"); finish(); return; }
        p.observedOwner = Qt.binding(function() { return parts.loader.item; });
        p.eligible = Qt.binding(function() { return forest.menuOpen && forest.visible
            && parts.loader.active && parts.loader.visible && forest.activeTree.sessionKey==="CHERRY"; });
        joinedParent=p;
        p.actionFinished.connect(function(code) {
            joinedLast=code;
            joinedDrive.restart();
        });
        p.finished.connect(function() {
            check(p.reaped && !p.running && !p.failure && p.closeResult
                && p.outcome==="ABORTED_LOCAL" && p.wire.snapshot().ended
                && joinedCommits===2 && joinedPages===4 && joinedReopened && dbChecks===3
                && !item.historyScopeActive && item.runtimeState==="CLOSED","joined terminal");
            if (failed) { finish(); return; }
            console.info("FOREST_HOST_JOINED_PASS");
            joinedParent=null;
            p.destroy();
            startNegative(1);
        });
        if (!p.start()) { check(false,"joined start"); finish(); }
    }
    function driveJoined() {
        const p=joinedParent, item=parts.loader.item;
        if (!p || failed) return;
        const feed=find(item,"publicFixtureFeed");
        let ok=false;
        if (joinedLast==="READY") ok=item.connectedHistoryMode && feed.messages.length===0 && p.request("NEXT");
        else if (joinedLast==="TURN_STARTED") {
            joinedSteps=1;
            ok=feed.messages.length===0 && p.request("STEP");
        } else if (joinedLast==="ACTIVE") {
            if (p.turnsStarted===3 && joinedSteps===4)
                ok=item.runtimeStatusText==="GENERATING" && p.request("STOP");
            else { joinedSteps++; ok=joinedSteps<=5 && p.request("STEP"); }
        } else if (joinedLast==="COMMITTED_LOCAL") {
            joinedCommits++;
            ok=item.runtimeStatusText==="LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED"
                && feed.messages.length===0 && (joinedCommits===1?p.request("NEXT"):p.request("HISTORY_ATTACH"));
        } else if (joinedLast==="HISTORY_ATTACHED") {
            ok=item.historyScopeActive && feed.messages.length===0 && p.historyScope.revision===4
                && p.request("HISTORY_PAGE",("0000000000000000000000000000000"+(joinedPages+1)),2);
        } else if (joinedLast==="PAGE_READY") {
            joinedPages++;
            if (joinedPages%2===1) {
                ok=item.fixtureState==="PARTIAL" && feed.messages.length===2
                    && p.request("HISTORY_PAGE",("0000000000000000000000000000000"+(joinedPages+1)),2);
            } else if (joinedPages===2) {
                joinedAlias=p.sessionAlias;
                joinedRows=feed.messages.map(x=>x.turnId);
                ok=item.fixtureState==="COMPLETE" && feed.messages.length===4
                    && waitForDb("BEFORE");
            } else {
                ok=item.fixtureState==="COMPLETE" && feed.messages.length===4
                    && p.sessionAlias===joinedAlias
                    && feed.messages.every((x,i)=>x.turnId===joinedRows[i])
                    && waitForDb("AFTER");
            }
        } else if (joinedLast==="JOURNAL_REOPENED") {
            joinedReopened=true;
            ok=p.turnsStarted===2 && !p.request("REOPEN") && p.request("HISTORY_ATTACH");
        } else if (joinedLast==="STOP_OBSERVED")
            ok=item.runtimeStatusText==="STOP REQUESTED // OUTCOME PENDING"
                && p.outcome!=="ABORTED_LOCAL" && feed.messages.length===0 && p.request("STEP");
        else if (joinedLast==="ABORTED_LOCAL")
            ok=p.phase==="BLOCKED" && p.outcome==="ABORTED_LOCAL"
                && item.runtimeStatusText==="LOCAL ABORT RECORDED // DELIVERY UNCONFIRMED"
                && feed.messages.length===0 && !p.request("NEXT") && waitForDb("ABORT");
            if (ok) console.info("FOREST_HOST_TYPED_ABORT_PASS");
        else if (joinedLast==="CLOSED") return;
        check(ok,"joined action "+joinedLast);
        if (failed) p.hold("JOINED_HARNESS");
    }
    // Private CI-only gate, not a Runtime frame or production authorization.
    // The external harness observes the still-open journal independently.
    FileView {
        id: dbAck
        path: Quickshell.shellPath("db-observer-ack")
        blockLoading: false
        printErrors: false
    }
    function waitForDb(stage) {
        if (dbStage!=="" || !joinedParent.live() || joinedParent.pending) return false;
        dbStage=stage;
        console.info("FOREST_HOST_DB_STAGE "+stage);
        dbPoll.start();
        return true;
    }
    Timer {
        id: dbPoll
        interval: 75
        repeat: true
        onTriggered: {
            const p=witness.joinedParent;
            if (!p || !p.live() || p.pending || witness.failed) {
                stop(); witness.check(false,"DB gate expired");
                if (p) p.hold("DB_GATE");
                return;
            }
            if (!dbAck.loaded || dbAck.text()!==witness.dbStage) {
                dbAck.reload(); return;
            }
            stop();
            const stage=witness.dbStage;
            witness.dbStage="";
            witness.dbChecks++;
            const feed=witness.find(witness.parts.loader.item,"publicFixtureFeed");
            const ok=stage==="BEFORE" ? p.request("REOPEN") && feed.messages.length===0
                : stage==="AFTER" ? p.request("NEXT") && feed.messages.length===0
                : stage==="ABORT" && p.request("CLOSE");
            witness.check(ok,"DB gate action");
            if (!ok) p.hold("DB_GATE");
        }
    }
    // Actual original Loader consumer, not an alternate parser or fixture.
    // The independent harness changes scope or Tree synchronously on offer.
    function startNegative(n) {
        negativeCase=n;
        negativeTriggered=false;
        forest.menuOpen=false;
        negativeMount.restart();
    }
    Timer {
        id: negativeMount
        interval: 350
        onTriggered: {
            forest.selectedTreeIndex=0;
            forest.menuOpen=true;
            negativeOpen.restart();
        }
    }
    Timer {
        id: negativeOpen
        interval: 350
        onTriggered: {
            parts.preview.leftClicked(null);
            negativeConnect.restart();
        }
    }
    Timer {
        id: negativeConnect
        interval: 350
        onTriggered: {
            const item=parts.loader.item;
            if (!item || !parts.loader.visible) { check(false,"negative loader"); finish(); return; }
            const p=parentType.createObject(witness,{trial:String(negativeCase+6).repeat(32),
                fixtureDirectory:Quickshell.shellPath("privateNegative"+negativeCase),
                originalOwner:item,originalLoader:parts.loader,joined:true,acceptOffer:true});
            if (!p) { check(false,"negative create"); finish(); return; }
            p.observedOwner=Qt.binding(function(){return parts.loader.item;});
            p.eligible=Qt.binding(function(){return forest.menuOpen && forest.visible
                && parts.loader.active && parts.loader.visible && forest.activeTree.sessionKey==="CHERRY";});
            joinedParent=p;
            item.historyCurrentScopeChanged.connect(function(){
                if (negativeTriggered || !item.historyCurrentScope) return;
                negativeTriggered=true;
                if (negativeCase===1) item.historyCurrentScope=null;
                else forest.selectedTreeIndex=1;
            });
            p.actionFinished.connect(function(code){
                if (code==="READY") negativeDrive.restart();
                else if (code!=="REFUSED") { check(false,"unexpected negative result"); p.hold("NEGATIVE"); }
            });
            p.finished.connect(function(){
                let ok=negativeTriggered && p.reaped && !p.running && p.action===2
                    && p.positiveHistoryAcks===0 && p.historyScope===null && !p.historyConfirmed;
                if (negativeCase===1)
                    ok=ok && p.negativeHistoryAcks===1 && p.refusedResult && !p.failure
                        && p.wire.snapshot().ended && !item.historyScopeActive;
                else ok=ok && p.negativeHistoryAcks===0 && p.failure==="OWNER_LOST"
                    && parts.loader.item===null;
                check(ok,"negative history acceptance "+negativeCase);
                if (failed) { finish(); return; }
                console.info("FOREST_HOST_HISTORY_NEGATIVE_PASS "+negativeCase);
                joinedParent=null;
                p.destroy();
                if (negativeCase===1) startNegative(2);
                else startReviewPlacement();
            });
            if (!p.start()) { check(false,"negative start"); finish(); }
        }
    }
    Timer {
        id: negativeDrive
        interval: 30
        onTriggered: {
            if (!joinedParent.request("HISTORY_ATTACH")) {
                check(false,"negative attach");
                joinedParent.hold("NEGATIVE");
            }
        }
    }
    // CI-only placement rehearsal: borrow the actual existing preview Loader
    // while it is inactive. No installed button, second panel, or host query.
    Component { id: reviewType; Review.PublicRestorationReview {} }
    function startReviewPlacement() {
        forest.menuOpen=false;
        reviewPhase=0;
        reviewTimer.start();
    }
    function reviewScope(n) {
        return {treeKey:"CHERRY",taskAlias:"a".repeat(32),viewKey:String(n).repeat(32),planRevision:1};
    }
    function reviewGeometry(item) {
        const a=parts;
        const body=find(item,"restorationReviewBody");
        const dismiss=find(item,"restorationReviewDismiss");
        const label=find(item,"restorationReviewSynthetic");
        const locked=find(item,"restorationReviewLocked");
        check(a.loader.active && a.loader.visible && a.loader.item===item
            && item.width===a.pane.width && item.height===a.pane.height
            && item.width>=300 && item.height>=160 && !a.empty.visible
            && a.pane.y>=a.heading.y+a.heading.height
            && a.pane.y+a.pane.height<=a.prompt.y
            && a.pane.x+a.pane.width<=a.rail.x,"review viewport");
        check(body && dismiss && label && locked && body.visible
            && dismiss.activeFocusOnTab && label.text==="SYNTHETIC // NO LIVE SEASON OR AVAILABILITY"
            && locked.text==="READ ONLY // RESTORATION LOCKED"
            && locked.y+locked.height<=body.height,"review layout/focus eligibility");
        check(!item.restorationEnabled && !item.sendEnabled && !item.stopEnabled
            && !item.sourceAuthenticated && !item.permissionGranted
            && !item.productionAuthority && !item.modelExecutionPermitted
            && !forest.chatHostTrusted && !a.send.enabledAction && !a.voice.backendReady,
            "review authority unchanged");
        return !failed;
    }
    function reviewStep(n) {
        const a=parts;
        if (n===0) {
            check(!a.loader.active && a.loader.item===null,"review default closed");
            originalPreviewComponent=a.loader.sourceComponent;
            a.loader.sourceComponent=reviewType;
            forest.selectedTreeIndex=0;
            forest.menuOpen=true;
        } else if (n===1) {
            check(a.preview.interactive && !a.loader.active,"review explicit entry");
            a.input.text="review-local draft";
            a.preview.leftClicked(null);
        } else if (n===2) {
            const item=a.loader.item;
            check(item && item.reviewState==="CLOSED" && item.reviewRows.length===0,
                "review initial state");
            if (failed) return;
            firstReviewScope=reviewScope(1);
            item.syntheticOwner=true;
            item.ownerScope=firstReviewScope;
            check(item.openReview(firstReviewScope) && item.receiveReview(firstReviewScope,reviewPlan)
                && item.reviewRows.length===5 && reviewGeometry(item),"review explicit scoped rows");
            const dismiss=find(item,"restorationReviewDismiss");
            if (dismiss) dismiss.forceActiveFocus();
            check(a.input.text==="review-local draft","review draft preserved");
        } else if (n===3) {
            const item=a.loader.item;
            check(item && item.dismissReview(firstReviewScope) && item.reviewRows.length===0
                && item.reviewState==="CLOSED","review dismiss state");
        } else if (n===4) {
            const item=a.loader.item;
            const dismiss=find(item,"restorationReviewDismiss");
            const body=find(item,"restorationReviewBody");
            check(item && item.reviewState==="CLOSED" && item.reviewRows.length===0
                && dismiss && body && !body.visible && !dismiss.activeFocusOnTab
                && !dismiss.activeFocus && !dismiss.focus,
                "review dismissed tab eligibility");
            if (failed) return;
            a.preview.leftClicked(null);
            a.input.forceActiveFocus(); // local host focus restoration request, not physical keyboard input
        } else if (n===5) {
            check(!a.loader.active && a.loader.item===null && a.empty.visible,"review unloaded");
            check(a.input.focus && a.input.text==="review-local draft","review return focus request/draft");
            a.preview.leftClicked(null);
        } else if (n===6) {
            const item=a.loader.item;
            check(item && item.reviewState==="CLOSED" && item.reviewRows.length===0,
                "review replacement empty");
            if (failed) return;
            secondReviewScope=reviewScope(2);
            item.syntheticOwner=true;
            item.ownerScope=secondReviewScope;
            check(item.openReview(secondReviewScope) && item.receiveReview(secondReviewScope,reviewPlan)
                && !item.receiveReview(firstReviewScope,reviewPlan)
                && !item.dismissReview(firstReviewScope) && reviewGeometry(item),
                "review stale scope isolated");
            forest.selectedTreeIndex=1;
        } else if (n===7) {
            check(!a.loader.active && a.loader.item===null,"review tree loss unload");
            a.loader.sourceComponent=originalPreviewComponent;
            forest.selectedTreeIndex=0;
        } else if (n===8) {
            check(a.preview.interactive && !a.loader.active && a.input.text==="review-local draft",
                "review return to original preview");
            a.preview.leftClicked(null);
        } else if (n===9) {
            geometry(true);
            check(a.input.text==="review-local draft","original preview/draft restored");
            forest.menuOpen=false;
        } else if (n===10) {
            check(!a.loader.active && a.loader.item===null && a.input.text==="","review close");
        }
    }
    Timer {
        id: reviewTimer
        interval: 350
        repeat: true
        onTriggered: {
            const n=reviewPhase++;
            reviewStep(n);
            if (failed) { stop(); finish(); return; }
            console.info("FOREST_HOST_REVIEW_PHASE_PASS "+n);
            if (n===10) {
                stop();
                console.info("FOREST_HOST_REVIEW_PLACEMENT_PASS");
                finish();
            }
        }
    }
    Timer { id: joinedDrive; interval: 30; onTriggered: witness.driveJoined() }
    Timer { id: joinedMount; interval: 350; repeat:true
        onTriggered: {
            if (witness.joinedStart===0) {
                witness.joinedStart++;
                witness.parts.preview.leftClicked(null);
            } else {
                stop();
                witness.startJoined();
            }
        }
    }
    Timer {
        id: timer
        interval: 350
        running: true
        repeat: true
        onTriggered: {
            if (witness.failed) { stop(); Qt.quit(); return; }
            const n = witness.phase++;
            const runtimeStart = witness.compact ? 2 : 10;
            if (!witness.small && n >= runtimeStart) {
                witness.runtimePhase(n - runtimeStart);
                witness.completePhase(n);
                if (n === runtimeStart + 7) {
                    if (witness.failed) witness.finish();
                    else if (witness.compact) { stop(); witness.startReviewPlacement(); }
                    else {
                        stop();
                        forest.menuOpen=true;
                        joinedMount.start();
                    }
                }
                return;
            }
            switch (n) {
            case 0:
                if (!witness.capture()) return;
                witness.check(forest.screen !== null, "native screen unavailable");
                if (witness.failed) return;
                witness.small = forest.screen.width < 600;
                witness.compact = !witness.small && forest.screen.width < 930;
                witness.check(witness.small
                    ? forest.screen.width === 420 && forest.screen.height === 340
                    : witness.compact
                        ? forest.screen.width === 770 && forest.screen.height === 450
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
                witness.check(witness.compact
                    ? forest.frameWidth < 930 && forest.frameHeight < 610
                    : forest.frameWidth === 930 && forest.frameHeight === 610, "default/clamped stage");
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
                forest.chassisLevel = 0;
                parts.input.text = "unsubmitted local draft";
                parts.preview.leftClicked(null);
                break;
            default:
                witness.check(false, "unexpected phase");
            }
            witness.completePhase(n);
        }
    }
}
