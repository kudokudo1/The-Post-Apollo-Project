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
    property int dormantPhase: 0
    property int seasonPhase: 0
    property var seasonRows: []
    property bool catalogDismissed: false
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
    // S2a: identify the actual unchanged host rail without a shipping test ID.
    // Constrain discovery to siblings of the known chat pane; never select
    // a candidate by its expected width or position.
    function directTextCount(item, value) {
        let count = 0;
        for (const child of item.children) {
            if (typeof child.text === "string" && child.text === value) ++count;
        }
        return count;
    }
    function captureChatRail(result) {
        if (!result.chat || !result.chat.parent) {
            check(false, "missing actual rail parent");
            return;
        }
        const siblings = result.chat.parent.children;
        const rails = [], trees = [];
        const heading = "TREES // " + String(forest.treeSlots.length).padStart(2, "0");
        for (const item of siblings) {
            if (item !== result.chat && typeof item.hostConnected === "boolean"
                    && typeof item.treeKey === "string"
                    && Array.isArray(item.sessions) && Array.isArray(item.visibleSessions))
                rails.push(item);
            if (directTextCount(item, heading) === 1) trees.push(item);
        }
        check(rails.length === 1 && trees.length === 1, "ambiguous actual rail/tree");
        if (failed) return;
        result.chatRail = rails[0];
        result.treePane = trees[0];
        const headers = [];
        for (const child of result.chatRail.children) {
            if (directTextCount(child, forest.activeTree.name) === 1
                    && directTextCount(child, "COLONY UNAVAILABLE") === 1)
                headers.push(child);
        }
        check(headers.length === 1, "missing or ambiguous actual Colony header");
        if (!failed) result.chatRailHeader = headers[0];
    }
    function chatRailGeometry() {
        const a = parts, rail = a.chatRail, tree = a.treePane;
        const expected = forest.frameWidth >= 800 ? 184 : forest.frameWidth >= 680 ? 148 : 0;
        check(rail.parent === a.chat.parent && tree.parent === a.chat.parent
            && rail !== tree && rail !== a.chat && tree !== a.chat, "actual rail parent");
        check(rail.width === expected && rail.visible === (expected > 0),
            "actual rail width/visibility");
        check(tree.x === 0 && tree.width > 0 && tree.width === forest.sideWidth
            && rail.x === tree.x + tree.width && a.chat.x === rail.x + rail.width
            && a.chat.x + a.chat.width === a.chat.parent.width
            && tree.y === rail.y && rail.y === a.chat.y
            && tree.height === rail.height && rail.height === a.chat.height
            && a.chat.width > 0 && a.chat.height > 0, "actual Tree/rail/chat adjacency");
        check(a.pane.width > 0 && a.pane.height > 0 && a.prompt.width > 0
            && a.prompt.height > 0 && a.pane.x >= 0 && a.pane.y >= 0
            && a.pane.x + a.pane.width <= a.chat.width
            && a.pane.y + a.pane.height <= a.chat.height
            && a.prompt.x >= 0 && a.prompt.y >= 0
            && a.prompt.x + a.prompt.width <= a.chat.width
            && a.prompt.y + a.prompt.height <= a.chat.height, "rail workspace/prompt bounds");
        check(!rail.hostConnected && rail.sessions.length === 0
            && rail.visibleSessions.length === 0 && rail.treeKey === forest.activeTree.sessionKey
            && rail.treeName === forest.activeTree.name,
            "actual disconnected chat source state");
        unifiedRailPresentation();
    }
    // S4-U1: public presentation, not a Colony source or a native AT client.
    function unifiedRailPresentation() {
        const rail = parts.chatRail, header = parts.chatRailHeader;
        const name = header.children.filter(x => x.text === forest.activeTree.name);
        const status = header.children.filter(x => x.text === "COLONY UNAVAILABLE");
        const offline = rail.children.filter(x => x.text === "CHAT HOST OFFLINE");
        const inventory = rail.inventoryStatus === "REACHABLE"
            ? "OLLAMA // " + rail.discoveredModels + " FOUND"
            : rail.inventoryStatus === "CHECKING" ? "OLLAMA // SCANNING"
            : rail.inventoryStatus === "NOT_CHECKED" ? "OLLAMA // NOT SCANNED" : "OLLAMA // OFFLINE";
        const model = rail.selectedModel ? "MODEL // " + rail.selectedModel : "MODEL // NOT SELECTED";
        const strips = rail.children.filter(x => directTextCount(x, inventory) === 1
            && directTextCount(x, model) === 1);
        check(header.height === 55 && name.length === 1 && status.length === 1
            && offline.length === 1 && strips.length === 1 && strips[0].height === 56,
            "unified heading/status and independent B0");
        if (failed) return;
        check(name[0].textFormat === Text.PlainText && name[0].elide === Text.ElideRight
            && status[0].textFormat === Text.PlainText
            && offline[0].textFormat === Text.PlainText
            && directTextCount(header, "CHATS // 00") === 0,
            "unified plain labels without false count");
        const lists = rail.children.filter(x => typeof x.count === "number"
            && x.contentItem !== undefined && x.model !== undefined);
        check(lists.length === 1 && lists[0].count === 0
            && offline[0].visible === rail.visible,
            "unavailable chat, no fabricated member or session");
        if (failed) return;
        function inspect(item) {
            if (typeof item.text === "string")
                check(!/CHATS \/\/|NO ACTIVE CHATS|Clone [0-9]/.test(item.text),
                    "false count, empty state or member");
            if (!rail.visible)
                check(!item.visible && !item.enabled && !item.activeFocus,
                    "hidden rail descendant activation");
            for (const child of item.children || []) inspect(child);
        }
        check(rail.enabled === rail.visible && !rail.activeFocusOnTab
            && rail.Accessible.ignored === !rail.visible
            && name[0].Accessible.ignored === !rail.visible
            && status[0].Accessible.ignored === !rail.visible
            && offline[0].Accessible.ignored === !rail.visible,
            "unified rail accessibility properties");
        inspect(rail);
    }
    // S5 preparation: exercise actual disconnected Tree preferences only.
    // No fabricated room, addressee, membership or provider operation.
    function treePreferenceIsolation() {
        const a = parts, original = forest.selectedTreeIndex;
        const draft = a.input.text;
        const before = forest.selectedTreeReasoningSteps.slice();
        const equipment = JSON.stringify(forest.selectedTreeEquipment);
        const modelOpen = forest.modelPopupOpen;
        const railOpen = forest.reasoningRailExpanded;
        check(!modelOpen && !railOpen && !forest.chatHostTrusted,
            "S5 disconnected preference baseline");
        if (failed) return false;
        a.input.text = "local draft: Tree browsing must not submit";
        forest.selectedTreeIndex = 0;
        const first = (before[0] + 1) % 4;
        forest.chooseTreeReasoningStep(first);
        check(forest.selectedReasoningStep === first
            && forest.selectedTreeReasoningSteps.slice(1).join(",") === before.slice(1).join(","),
            "S5 local CHERRY reasoning isolation");
        geometry(false);
        forest.selectedTreeIndex = 1;
        check(forest.selectedReasoningStep === before[1]
            && forest.selectedEquipment === forest.selectedTreeEquipment[1],
            "S5 MAPLE browse preference target");
        const second = (before[1] + 2) % 4;
        forest.chooseTreeReasoningStep(second);
        check(forest.selectedTreeReasoningSteps[0] === first
            && forest.selectedReasoningStep === second
            && forest.selectedTreeReasoningSteps.slice(2).join(",") === before.slice(2).join(","),
            "S5 local MAPLE reasoning isolation");
        geometry(false);
        check(!forest.chooseModelForm("BIG") && !forest.clearLocalModel("small")
            && JSON.stringify(forest.selectedTreeEquipment) === equipment,
            "S5 hidden equipment controls refuse");
        forest.selectedTreeIndex = 0;
        check(forest.selectedReasoningStep === first
            && forest.selectedEquipment === forest.selectedTreeEquipment[0],
            "S5 original Tree preference retained");
        geometry(false);
        check(a.input.text === "local draft: Tree browsing must not submit"
            && !a.send.enabledAction && !a.voice.backendReady
            && forest.activeChatSessions.length === 0
            && !a.loader.active && a.loader.item === null,
            "S5 draft, disconnected send and preview isolation");
        // Restore in-memory preferences; never call SAVE or open a model popup.
        forest.selectedTreeReasoningSteps = before;
        forest.selectedTreeIndex = original;
        a.input.text = draft;
        geometry(false);
        return !failed;
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
        if (!failed) captureChatRail(result);
        parts = result;
        return !failed;
    }
    function geometry(active) {
        const a = parts;
        chatRailGeometry();
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
        else if (joinedLast==="ABORTED_LOCAL") {
            ok=p.phase==="BLOCKED" && p.outcome==="ABORTED_LOCAL"
                && item.runtimeStatusText==="LOCAL ABORT RECORDED // DELIVERY UNCONFIRMED"
                && feed.messages.length===0 && !p.request("NEXT") && waitForDb("ABORT");
            if (ok) console.info("FOREST_HOST_TYPED_ABORT_PASS");
        } else if (joinedLast==="CLOSED") return;
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
                dormantPhase=0;
                dormantTimer.start();
            }
        }
    }
    // R2 disposable actual host placement. Use the same inactive Loader,
    // never mount a second panel or authorize a real catalog.
    Component { id: dormantType; Review.PublicDormantTaskSelector {} }
    function dormantScope(n) {
        return {treeKey:"CHERRY",viewKey:(n===1?"b":"c").repeat(32),catalogRevision:n};
    }
    function dormantGeometry(item) {
        const a=parts, body=find(item,"dormantCatalogBody");
        check(a.loader.active && a.loader.visible && a.loader.item===item
            && item.width===a.pane.width && item.height===a.pane.height
            && item.width>=300 && item.height>=160 && !a.empty.visible
            && a.pane.y>=a.heading.y+a.heading.height
            && a.pane.y+a.pane.height<=a.prompt.y
            && a.pane.x+a.pane.width<=a.rail.x
            && body && body.visible && body.implicitHeight<=body.height
            && !item.restorationEnabled && !item.sendEnabled && !item.stopEnabled
            && !item.sourceAuthenticated && !item.permissionGranted
            && !item.productionAuthority && !item.modelExecutionPermitted
            && !forest.chatHostTrusted && !a.send.enabledAction && !a.voice.backendReady,
            "dormant viewport and locked authority");
        return !failed;
    }
    function dormantStep(n) {
        const a=parts, first=dormantScope(1), second=dormantScope(2);
        const rows=[{taskAlias:"a".repeat(32)},{taskAlias:"d".repeat(32)},{taskAlias:"e".repeat(32)}];
        const plan={treeKey:"CHERRY",taskAlias:rows[0].taskAlias,viewKey:"f".repeat(32),planRevision:7};
        const item=a.loader.item;
        if (n===0) {
            check(!a.loader.active && item===null && a.loader.sourceComponent===originalPreviewComponent,
                "dormant default closed");
            a.loader.sourceComponent=dormantType;
            forest.menuOpen=true;
        } else if (n===1) {
            check(a.preview.interactive && !a.loader.active,"dormant explicit entry");
            a.input.text="dormant-local draft";
            a.preview.leftClicked(null);
        } else if (n===2) {
            check(item && item.catalogState==="CLOSED" && item.reviewState==="CLOSED","dormant initial");
            if (failed) return;
            catalogDismissed=false;
            item.dismissed.connect(function(){catalogDismissed=true;});
            item.syntheticOwner=true;
            item.ownerScope=first;
            check(item.openCatalog(first) && item.receiveCatalog(first,rows)
                && item.catalogRows.length===3 && !item.selectedAlias && dormantGeometry(item),
                "dormant fixed list");
        } else if (n===3) {
            item.ownerPlanScope=plan;
            check(!item.openReview(first,plan) && item.selectTask(first,rows[0].taskAlias)
                && item.reviewState==="CLOSED","dormant explicit selection");
            const opener=find(item,"dormantOpenReview");
            check(opener && opener.activeFocusOnTab,"dormant opener focus");
            if (opener) opener.forceActiveFocus();
        } else if (n===4) {
            const opener=find(item,"dormantOpenReview"), body=find(item,"dormantCatalogBody");
            check(item.openReview(first,plan) && item.receivePlan(first,plan,reviewPlan)
                && item.catalogRows.length===0 && body && !body.visible
                && opener && !opener.focus && !opener.activeFocusOnTab
                && reviewGeometry(item),"dormant exclusive review");
            const dismiss=find(item,"restorationReviewDismiss");
            if (dismiss) dismiss.forceActiveFocus();
        } else if (n===5) {
            check(item.dismissPlan(first,plan) && item.reviewState==="CLOSED"
                && item.reviewRows.length===0,"dormant review dismiss");
        } else if (n===6) {
            const opener=find(item,"dormantOpenReview");
            check(item.catalogRows.length===3 && item.selectedAlias===rows[0].taskAlias
                && opener && opener.focus && opener.activeFocusOnTab && dormantGeometry(item),
                "dormant local focus return");
            check(item.dismissCatalog(first) && catalogDismissed && item.catalogState==="CLOSED"
                && !item.selectedAlias,"dormant catalog dismiss");
        } else if (n===7) {
            check(item.catalogState==="CLOSED" && !find(item,"dormantOpenReview").activeFocusOnTab
                && !find(item,"dormantCatalogDismiss").activeFocusOnTab,"dormant tab retirement");
            a.preview.leftClicked(null);
            a.input.forceActiveFocus();
        } else if (n===8) {
            check(!a.loader.active && item===null && a.empty.visible && a.input.focus
                && a.input.text==="dormant-local draft","dormant close to empty and focus request");
            a.preview.leftClicked(null);
        } else if (n===9) {
            check(item && item.catalogState==="CLOSED" && !item.selectedAlias,"dormant fresh replacement");
            if (failed) return;
            item.syntheticOwner=true;
            item.ownerScope=second;
            check(item.openCatalog(second) && item.receiveCatalog(second,rows)
                && !item.dismissCatalog(first) && !item.selectTask(first,rows[0].taskAlias)
                && !item.receivePlan(first,plan,reviewPlan) && dormantGeometry(item),"dormant stale isolation");
            forest.selectedTreeIndex=1;
        } else if (n===10) {
            check(!a.loader.active && item===null && a.empty.visible,"dormant Tree loss");
            a.loader.sourceComponent=originalPreviewComponent;
            forest.selectedTreeIndex=0;
        } else if (n===11) {
            check(a.preview.interactive && !a.loader.active && a.input.text==="dormant-local draft",
                "dormant no automatic conversation");
            a.preview.leftClicked(null);
        } else if (n===12) {
            geometry(true);
            check(a.input.text==="dormant-local draft","dormant original preview preserved");
            forest.menuOpen=false;
        } else if (n===13) {
            check(!a.loader.active && item===null && a.input.text==="","dormant menu close");
        }
    }
    Timer {
        id: dormantTimer
        interval: 350
        repeat: true
        onTriggered: {
            const n=dormantPhase++;
            dormantStep(n);
            if (failed) { stop(); finish(); return; }
            console.info("FOREST_HOST_DORMANT_PHASE_PASS "+n);
            if (n===13) {
                stop();
                console.info("FOREST_HOST_DORMANT_PLACEMENT_PASS");
                seasonPhase=0;
                seasonTimer.start();
            }
        }
    }
    // The actual source mounts UNKNOWN-only indicators. Fixed example scopes
    // are supplied exclusively here, then retired back to the source default.
    function treeLabel(item,textValue,size) {
        if (!item) return null;
        if (item.text===textValue && item.pixelSize===size
                && item.baseColor!==undefined && item.visibleGlyphWidth!==undefined) return item;
        if (item.children) {
            for (let i=0;i<item.children.length;i++) {
                const match=treeLabel(item.children[i],textValue,size);
                if (match) return match;
            }
        }
        return null;
    }
    function seasonRef(i,revision) {
        return {kind:"TREE",entityAlias:(i+1).toString(16).repeat(32),
            viewKey:(revision===1?"a":"b")+(i+1).toString(16).repeat(31),revision:revision};
    }
    function seasonGeometry() {
        const a=parts;
        check(seasonRows.length===forest.treeSlots.length && !a.loader.active
            && !forest.chatHostTrusted && !forest.voiceHostTrusted && forest.activeChatSessions.length===0
            && !a.send.enabledAction && !a.voice.backendReady,"season host remains locked");
        for (const entry of seasonRows) {
            const row=entry.row, name=entry.name, role=entry.role, title=name.parent, icon=entry.icon;
            check(row.height===59 && row.width===forest.sideWidth-18
                && row.interactive===entry.interactive && row.open===(entry.index===forest.selectedTreeIndex)
                && title.height===26 && title.width===row.width-18
                && name.x===32 && name.width>0 && name.width===title.width-52
                && icon.width===16 && icon.height===16 && icon.x===name.x+name.width+4
                && icon.x+icon.width===title.width && icon.y===5
                && role.width===row.width-18 && role.height===12
                && role.text===forest.treeSlots[entry.index].role
                && name.text===forest.treeSlots[entry.index].name
                && !icon.focus && !icon.activeFocusOnTab
                && !icon.sourceAuthenticated && !icon.permissionGranted
                && !icon.productionAuthority && !icon.restorationEnabled,
                "actual Tree row season geometry "+entry.index);
        }
    }
    function collectSeasonRows() {
        const entries=[];
        const original=forest.selectedTreeIndex;
        for (let i=0;i<forest.treeSlots.length;i++) {
            forest.selectedTreeIndex=i;
            unifiedRailPresentation();
            if (failed) return false;
            const row=forest.selectedTreeButton, slot=forest.treeSlots[i];
            const name=treeLabel(row,slot.name,12), role=treeLabel(row,slot.role,9);
            check(row && name && role && name.parent.height===26,"actual Tree row lookup "+i);
            if (failed) return false;
            const title=name.parent;
            const art=title.children.find(x=>x.width===26 && x.height===26 && x.source!==undefined);
            const icons=title.children.filter(x=>x.objectName==="forestTreeSeasonIndicator");
            const icon=icons[0];
            check(art && art.x===0 && name.x===32 && name.anchors.rightMargin===20,
                "actual Tree artwork and source reservation");
            check(icons.length===1 && icon && icon.season==="UNKNOWN"
                && icon.seasonLabel==="Season unknown" && !icon.syntheticOwner
                && icon.ownerScope===null && !icon.eligible,
                "actual Tree source unknown default");
            if (failed) return false;
            entries.push({index:i,row:row,name:name,role:role,art:art,icon:icon,interactive:row.interactive});
        }
        seasonRows=entries;
        forest.selectedTreeIndex=original;
        unifiedRailPresentation();
        seasonGeometry();
        return !failed;
    }
    function seasonStep(n) {
        if (n===0) {
            check(!forest.menuOpen && !parts.loader.active,"season default host closed");
            forest.menuOpen=true;
        } else if (n===1) {
            if (!collectSeasonRows()) return;
            forest.selectedTreeIndex=0;
        } else if (n===2) {
            seasonGeometry();
            for (const entry of seasonRows) {
                check(entry.art.width===26 && entry.art.height===26 && entry.art.x===0,
                    "actual Tree artwork retained");
                const ref=seasonRef(entry.index,1);
                entry.icon.syntheticOwner=true;
                entry.icon.ownerScope=ref;
                check(entry.icon.receive(ref,["SUMMER","WINTER","SPRING","FALL","UNKNOWN"][entry.index]),
                    "CI only independent fixed public season");
            }
        } else if (n===3) {
            const entries=seasonRows;
            check(entries.map(e=>e.icon.season).join(",")==="SUMMER,WINTER,SPRING,FALL,UNKNOWN",
                "actual Tree independent status");
            entries[1].row.leftClicked(null);
            check(forest.selectedTreeIndex===1,"actual Tree selection retained");
            check(!entries[0].icon.receive(seasonRef(1,1),"WINTER")
                && entries[0].icon.season==="SUMMER","other Tree stale isolated");
            seasonGeometry();
        } else if (n===4) {
            // Independently retire the original example before loss/replacement.
            const icon=seasonRows[0].icon;
            icon.ownerScope=null;
            icon.syntheticOwner=false;
            check(icon.season==="UNKNOWN" && !icon.receive(seasonRef(0,1),"WINTER")
                && seasonRows[1].icon.season==="WINTER","original retirement only");
            icon.syntheticOwner=true;
            icon.ownerScope=seasonRef(0,2);
            check(!icon.receive(seasonRef(0,1),"WINTER")
                && icon.receive(seasonRef(0,2),"FALL"),"fresh example scope");
        } else if (n===5) {
            for (const entry of seasonRows) {
                entry.icon.ownerScope=null;
                entry.icon.syntheticOwner=false;
            }
            forest.menuOpen=false;
        } else if (n===6) {
            check(seasonRows.every(e=>e.icon.season==="UNKNOWN" &&
                !e.icon.receive(seasonRef(e.index,1),"WINTER")),"closed original scope retired");
            forest.menuOpen=true;
        } else if (n===7) {
            seasonGeometry();
            check(seasonRows.every(e=>e.icon.season==="UNKNOWN"),"reopen no automatic season");
        } else if (n===8) {
            seasonGeometry();
            for (const entry of seasonRows)
                check(entry.icon===find(entry.name.parent,"forestTreeSeasonIndicator")
                    && entry.icon.season==="UNKNOWN" && !entry.icon.syntheticOwner
                    && entry.icon.ownerScope===null && !entry.icon.eligible
                    && entry.name.anchors.rightMargin===20 && entry.art.width===26,
                    "actual source UNKNOWN and reserved geometry restored");
            seasonRows=[];
            forest.selectedTreeIndex=0;
            forest.menuOpen=false;
        }
    }
    Timer {
        id: seasonTimer
        interval: 350
        repeat: true
        onTriggered: {
            const n=seasonPhase++;
            seasonStep(n);
            if (failed) { stop(); finish(); return; }
            console.info("FOREST_HOST_SEASON_PHASE_PASS "+n);
            if (n===8) {
                stop();
                console.info("FOREST_HOST_SEASON_PLACEMENT_PASS");
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
                if (witness.failed) return;
                // One measured baseline per private output, independent of
                // the existing phase counters. Geometry also runs on resizes.
                console.info("FOREST_HOST_CHAT_RAIL_BASELINE_PASS " + forest.frameWidth
                    + " " + parts.chatRail.width + " " + (parts.chatRail.visible ? 1 : 0));
                if (!witness.collectSeasonRows()) return;
                witness.seasonRows=[];
                console.info("FOREST_HOST_UNIFIED_RAIL_PASS " + parts.chatRail.width);
                console.info("FOREST_HOST_SEASON_SOURCE_DEFAULT_PASS");
                if (!witness.treePreferenceIsolation()) return;
                console.info("FOREST_HOST_TREE_PREFERENCE_ISOLATION_PASS " + parts.chatRail.width);
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
