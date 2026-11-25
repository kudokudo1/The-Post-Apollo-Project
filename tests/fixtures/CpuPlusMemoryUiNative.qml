import QtQuick
import QtQuick.Window
import Quickshell
import qs.services.memory
import qs.services.diagnostics
import "widgets/cpuplus"
import "widgets/cpuplus/CpuPlusQueueConsumer.js" as Consumer
import "widgets/cpuplus/CpuPlusQueuePresentation.js" as QueueView
import "services/memory/MemoryQueueSessionHost.js" as Host

// Unmounted, isolated native test only. Runner copies the actual UI and uses
// a recording operation singleton instead of any privileged backend.
ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_MEMORY_UI_SMOKE") === "CI_DISPOSABLE_ONLY"
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property int intentCount: 0
    property int readCount: 0
    property var lastIntent: null
    property var comparisonDraft: null
    // Inert external owner: verify the actual actuator passes the same
    // instance through its Loader without launching or retiring it.
    QtObject {
        id: externalSession
        property string phase: "IDLE"
        property int generation: 0
        property int storageGeneration: -1
        property bool startupLocked: true
        property bool canExecute: false
        property var recoveryContext: null
        property var reviewContext: null
        property var dispositionContext: null
        property var retentionSelection: null
        property int opens: 0
        property int closes: 0
        function active() { return false; }
        function open() { if(phase!=="IDLE")return false; opens++;phase="LOADING";return true; }
        function close() { closes++;return false; }
    }

    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const found = find(child, name);
            if (found) return found;
        }
        return null;
    }
    function check(ok, message) {
        if (!ok) {
            console.error("CPU_MEMORY_UI_NATIVE_FAIL // " + message);
            done = true;
            Qt.quit();
        }
        return ok;
    }
    Window {
        id: win
        visible: smoke.armed
        width: 320
        height: 620
        color: "#1B0623"
        Loader {
            id: scene
            anchors.fill: parent
            active: smoke.armed
            sourceComponent: Item {
            CpuPlusMemoryActuatorPane {
                id: pane
                anchors.fill: parent
            }
            function testStep() {
                const rail = smoke.find(pane, "cpuplusMemoryMenuRail");
                const footer = smoke.find(pane, "cpuplusMemoryFooter");
                const scroll = smoke.find(pane, "cpuplusMemoryScroll");
                const slider = smoke.find(pane, "cpuplusCapacitySelector");
                if (!smoke.check(rail && footer && scroll && slider, "missing pane controls")) return;
                const pinned = smoke.find(pane, "cpuplusMemoryPinned");
                const bottomRail = smoke.find(pane, "cpuplusCapBottomRail");
                if (pane.page === "CAP" && !smoke.check(bottomRail && bottomRail.visible
                    && Math.abs(bottomRail.mapToItem(pane, 0, bottomRail.height).y - pane.height) < 2,
                    "CAP bottom rail not stapled")) return;
                if (pane.width <= 0 || pane.height <= 0 || footer.height <= 0) return;
                if (!smoke.check(rail.height > 0 && scroll.y >= rail.y + rail.height
                        && scroll.y + scroll.height <= footer.y + 1,
                        "rail/footer overlap " + pane.width + "x" + pane.height + " rail=" + rail.height
                            + " scroll=" + scroll.y + "/" + scroll.height + " footer=" + footer.y)) return;
                if (pane.page === "CAP" && !smoke.check(pinned && pinned.y + pinned.height <= footer.y
                        && scroll.y >= pinned.y + pinned.height, "CAP pinned overlap")) return;
                if (smoke.phase === 0) {
                    if (!pane.received || !pane.exited) return;
                    // Supply stable synthetic observations after the real read-only probe exits.
                    pane.sample = {total:33554432, available:8388608, swap:25165820,
                        free:25165820, some:0, full:0, swappiness:60,
                        rows:[{name:"/dev/zram0",size:8388608,used:0,priority:100,kind:"ZRAM"},
                            {name:"/var/lib/post-apollo-memory-swap/swapfile",size:16777212,used:0,priority:10,kind:"OTHER SWAP"}]};
                    pane.stagedGiB = 16;
                    pane.stagedSwappiness = 60;
                    if (!smoke.check(rail.columns === 6 && slider.enabledSlider, "wide CAP geometry/availability")) return;
                    const shared = smoke.find(slider, "cpuplusSharedHorizontalSelector");
                    if (!smoke.check(shared && shared.horizontalStep && shared.rotation === 90
                            && shared.stepDetentCount === 17 && shared.handleTravel() > 0,
                            "shared horizontal STEP geometry")) return;
                    const left = shared.mapToItem(slider, shared.width / 2, shared.height);
                    const right = shared.mapToItem(slider, shared.width / 2, 0);
                    if (!smoke.check(left.x < right.x && Math.abs(left.y - right.y) < 1,
                            "horizontal low-to-high transform")) return;
                    shared.beginStepPreview(shared.handleYForValue(24));
                    if (!smoke.check(shared.pendingStepValue === 24 && pane.stagedGiB === 16,
                            "preview must not stage owner")) return;
                    shared.cancelStepPreview();
                    shared.requestStepDelta(1);
                    shared.requestStepDelta(1);
                    if (!smoke.check(pane.stagedGiB === 24 && pane.capacity.actualKiB === 16777212, "target versus actual")) return;
                    pinned.forceLayout();
                    const targetMountY=slider.mapToItem(pane,0,0).y;
                    pane.selectCapSection(1);
                    if (!smoke.check(!slider.visible && scroll.visible, "actions section")) return;
                    slider.valueRequested(32);
                    if (!smoke.check(pane.stagedGiB === 24, "hidden slider refusal")) return;
                    pane.selectCapSection(2);
                    if (!smoke.check(scroll.visible, "details section")) return;
                    const ram=smoke.find(pane,"cpuplusCapDetailRam");
                    const swap=smoke.find(pane,"cpuplusCapDetailSwap");
                    const ramView=smoke.find(pane,"cpuplusCapRamDetails");
                    if(!smoke.check(ram&&swap&&ramView&&!ramView.visible,"default swap details"))return;
                    ram.leftClicked(null);
                    if(!smoke.check(ramView.visible&&pane.ramDetailRows[0].fraction===0.25
                        &&pane.ramDetailRows[1].value===null&&pane.stagedGiB===24&&MemoryOperation.requests===0,
                        "RAM details selection and unavailable optional fields"))return;
                    pinned.forceLayout();
                    const detailRail=smoke.find(pane,"cpuplusCapDetailRail");
                    if(!smoke.check(detailRail&&detailRail.parent===pinned
                        &&Math.abs(detailRail.mapToItem(pane,0,0).y-targetMountY)<1
                        &&detailRail.height===28
                        && scroll.y>=detailRail.mapToItem(pane,0,detailRail.height).y,
                        "subject rail outside scroll"))return;
                    const railY=detailRail.mapToItem(pane,0,0).y;
                    scroll.contentY=Math.max(0,scroll.contentHeight-scroll.height);
                    if(!smoke.check(detailRail.mapToItem(pane,0,0).y===railY
                        &&ram.visible&&swap.visible,"RAM scroll preserves fixed subjects"))return;
                    const textItem=smoke.find(ramView,"cpuplusRamMetricText");
                    const glow=smoke.find(ramView,"cpuplusRamMetricGlow");
                    if(!smoke.check(textItem&&glow&&textItem.text.indexOf("GiB")>=0
                        &&textItem.text.indexOf("#00f782")>=0
                        &&String(glow.preferredGlowColor).toLowerCase()==="#00f782"
                        &&String(pane.ramDatasetGlow("UNRECLAIMABLE SLAB")).toLowerCase()==="#55cfca",
                        "semantic text and contextual white glow"))return;
                    const grid=smoke.find(ramView,"cpuplusRamCardGrid");
                    const card=smoke.find(ramView,"cpuplusRamMetricCard");
                    const bar=smoke.find(ramView,"cpuplusRamMetricBar");
                    if(!smoke.check(grid&&card&&bar&&grid.columns===(grid.width>=440?2:1)
                        &&card.width<=grid.width&&card.height>textItem.implicitHeight
                        &&bar.height===pane.detailMeterHeight&&String(pane.ramDatasetColor("ANONYMOUS")).toLowerCase()==="#a46aff",
                        "compact RAM card geometry and local purple"))return;
                    const fill=smoke.find(bar,"cpuplusRamMetricFill");
                    const info=smoke.find(pane,"cpuplusCapDetailsInfo");
                    const popup=smoke.find(pane,"cpuplusCapDetailsInfoPopup");
                    if(!smoke.check(fill&&fill.x===2&&fill.height===bar.height-4&&info&&popup&&!popup.visible,
                        "inset gauge and closed info"))return;
                    info.leftClicked(null);
                    if(!smoke.check(popup.visible&&pane.detailsInfoOpen,"info opens"))return;
                    info.leftClicked(null);
                    if(!smoke.check(!popup.visible,"info closes"))return;
                    console.log("CPU_M11D_INSTRUMENT_PASS // inset gauge and info popup");
                    const savedSample=pane.sample;
                    const originalCard=card;
                    pane.scanDiagnosticsOpen=true;
                    const transport=smoke.find(pane,"cpuplusScanPlayPause");
                    const stop=smoke.find(pane,"cpuplusScanStop");
                    const freq=smoke.find(pane,"cpuplusScanFrequencySlider");
                    if(!smoke.check(transport&&stop&&freq&&transport.width===28&&stop.width===28
                        &&freq.horizontalStep&&String(freq.valueFillColor).toLowerCase()==="#00f782"
                        &&String(freq.handleGlowColor).toLowerCase()===String(freq.handleColor).toLowerCase(),
                        "compact transport and white/green frequency slider"))return;
                    transport.leftClicked(null);
                    if(!smoke.check(pane.scanMode==="PAUSED"&&pane.scanBadge==="PAUSED","transport pauses"))return;
                    stop.leftClicked(null);
                    if(!smoke.check(stop.selected&&String(stop.fillColor).toLowerCase()===String(stop.pressedFillColor).toLowerCase()
                        &&String(stop.foregroundColor).toLowerCase()===String(stop.pressedForegroundColor).toLowerCase(),
                        "manual stop retains pressed state"))return;
                    pane.scanDiagnosticsOpen=false;
                    if(!smoke.check(pane.sample===null&&pane.displaySample===savedSample&&pane.scanBadge==="MANUAL"
                        &&smoke.find(ramView,"cpuplusRamMetricCard")===originalCard,"stop preserves display, invalidates operation input"))return;
                    pane.setScanInterval(15);
                    if(!smoke.check(pane.scanIntervalSeconds===15&&pane.scanNextMs===0,"manual interval does not start polling"))return;
                    pane.sample=Object.assign({},savedSample,{available:4194304});
                    if(!smoke.check(smoke.find(ramView,"cpuplusRamMetricCard")===originalCard,"metric delegate survives publication"))return;
                    pane.scanMode="LIVE"; pane.sample=savedSample;
                    swap.leftClicked(null);
                    const swapCard=smoke.find(pane,"cpuplusSwapDetailCard");
                    if(!smoke.check(swapCard&&swapCard.visible&&swapCard.width>0&&swapCard.height>0,
                        "SWAP detail card visible"))return;
                    console.log("CPU_M11C_COMPACT_CARDS_PASS // card geometry, local purple, no mutation");
                    if(!smoke.check(!ramView.visible&&pane.capDetailSubject==="SWAP"
                        &&detailRail.mapToItem(pane,0,0).y===railY&&scroll.contentY===0,
                        "return to swap details resets only body"))return;
                    console.log("CPU_M11B_PINNED_PALETTE_PASS // fixed rail and contextual glow");
                    console.log("CPU_M11A_RAM_DETAILS_PASS // native RAM/SWAP selection, no mutation");
                    pane.selectCapSection(0);
                    if (!smoke.check(!scroll.visible && slider.visible, "target section scroll-free")) return;
                    MemoryOperation.busy = true;
                    slider.valueRequested(32);
                    if (!smoke.check(pane.stagedGiB === 24 && !slider.enabledSlider, "busy refusal")) return;
                    pane.selectMenu(1);
                    smoke.phase = 1;
                    return;
                }
                if (smoke.phase === 1) {
                    const dial = smoke.find(pane, "cpuplusSwappinessDial");
                    if (!dial) return;
                    const actions = smoke.find(pane, "cpuplusPolicyActions");
                    const refresh = smoke.find(pane, "cpuplusPolicyRefresh");
                    if (!smoke.check(actions && refresh && actions.width > 60
                        && actions.mapToItem(pane,0,0).x >= dial.mapToItem(pane,dial.width,0).x
                        && !bottomRail.visible, "POL side actions geometry")) return;
                    if (!smoke.check(!dial.interactive && MemoryOperation.busy, "in-flight continuity")) return;
                    MemoryOperation.busy = false;
                    dial.valueRequested(150);
                    if (!smoke.check(pane.stagedSwappiness === 150 && pane.sample.swappiness === 60, "policy target versus actual")) return;
                    pane.selectPolicySection(1);
                    smoke.phase = 10;
                    return;
                }
                if (smoke.phase === 10) {
                    const priority = smoke.find(pane, "cpuplusPriorityDial");
                    const priorityRail = smoke.find(pane, "cpuplusPolicyBottomRail");
                    if (!priority) return;
                    if (!smoke.check(priorityRail && priorityRail.visible
                        && Math.abs(priorityRail.mapToItem(pane,0,priorityRail.height).y - pane.height)<2
                        && !smoke.find(pane,"cpuplusSwappinessDial"), "POL pinned priority navigation")) return;
                    pane.selectPriorityDevice("/dev/zram0");
                    if (!smoke.check(pane.stagedPriority === 100 && priority.interactive, "priority observed target")) return;
                    priority.valueRequested(101);
                    if (!smoke.check(pane.stagedPriority === 101 && pane.priorityRow.priority === 100
                        && MemoryOperation.requests === 0, "priority preview only")) return;
                    pane.copyPriorityProfile();
                    if(!smoke.check(pane.customProfileDraft.priority.value===101,"explicit priority copy"))return;
                    pane.selectPolicySection(2);
                    smoke.phase = 11;
                    return;
                }
                if (smoke.phase === 11) {
                    const zram = smoke.find(pane,"cpuplusZramPolicyPane");
                    if (!zram) return;
                    if (!smoke.check(zram.devices.length === 1 && !zram.canStage
                        && zram.selectedDevice === "", "ZRAM no auto read or target")) return;
                    zram.selectedDevice = "/dev/zram0";
                    zram.selectedSize = 8388608;
                    zram.raw = "lzo [lz4] zstd";
                    zram.received = true;
                    zram.exited = true;
                    zram.exitOk = true;
                    zram.finish();
                    zram.stageAlgorithm("zstd");
                    if (!smoke.check(zram.observation.actual === "lz4" && zram.targetAlgorithm === "zstd"
                        && MemoryOperation.requests === 0,"ZRAM synthetic preview")) return;
                    zram.stageAlgorithm("invalid");
                    if (!smoke.check(zram.targetAlgorithm === "zstd","ZRAM invalid target refusal")) return;
                    zram.copyToProfile();
                    if(!smoke.check(pane.customProfileDraft.zram.algorithm==="zstd","explicit ZRAM copy"))return;
                    pane.selectPolicySection(3);
                    smoke.phase = 12;
                    return;
                }
                if (smoke.phase === 12) {
                    const adv = smoke.find(pane,"cpuplusAdvancedPolicyPane");
                    const policyRail = smoke.find(pane,"cpuplusPolicyBottomRail");
                    if (!adv) return;
                    if (!smoke.check(policyRail && policyRail.visible
                        && Math.abs(policyRail.mapToItem(pane,0,policyRail.height).y-pane.height)<2
                        && !smoke.find(pane,"cpuplusZramPolicyPane")
                        && adv.status === "NOT CHECKED" && !adv.busy
                        && adv.cards.length === 0, "ADV demand-loaded, no automatic read")) return;
                    adv.raw = "100\n10\n0\n20\n0\n500\n3000\n";
                    adv.received = true;
                    adv.exited = true;
                    adv.exitOk = true;
                    adv.finish();
                    adv.selectPreview("background");
                    adv.stagePreview(15);
                    if (!smoke.check(adv.stagedValue === 15 && adv.observation.background.ratio === 10
                        && MemoryOperation.requests === 0, "ADV actual versus preview")) return;
                    adv.copyToProfile();
                    if(!smoke.check(pane.customProfileDraft.advanced.background.value===15 && pane.customProfileDraft.advanced.background.unit==="%","explicit ADV copy"))return;
                    pane.selectPolicySection(0);
                    smoke.phase = 13;
                    return;
                }
                if (smoke.phase === 13) {
                    if (!smoke.check(!smoke.find(pane,"cpuplusAdvancedPolicyPane")
                        && pane.stagedSwappiness === 150 && pane.stagedPriority === 101,
                        "ADV unload and prior targets retained")) return;
                    win.width = 220;
                    pane.selectMenu(2);
                    smoke.phase = 2;
                    return;
                }
                if (smoke.phase >= 2 && smoke.phase <= 5) {
                    if (!smoke.check(rail.columns === 3 && pane.menuIndex === smoke.phase
                            && !slider.visible && !smoke.find(pane, "cpuplusSwappinessDial"),
                            "narrow menu layout/hidden controls")) return;
                    if (smoke.phase >= 2 && smoke.phase <= 4) {
                        const top=smoke.find(pane,"cpuplusWorkHeader");
                        const bottom=smoke.find(pane,"cpuplusWorkFooter");
                        const refresh=smoke.find(pane,"cpuplusWorkRefresh");
                        const controls=smoke.find(pane,["cpuplusProcBottomControls","cpuplusAutoBottomControls","cpuplusDiagBottomControls"][smoke.phase-2]);
                        if (!top || !bottom || !refresh || !controls) return;
                        if (!smoke.check(top.visible && bottom.visible && (smoke.phase===3 ? controls.parent===smoke.find(pane,"cpuplusAutoSectionFooter") : controls.parent===bottom)
                            && scroll.y>=top.y+top.height && scroll.y+scroll.height<=footer.y+1
                            && scroll.height>0,"fixed work rails and positive middle viewport")) return;
                        const y=controls.mapToItem(pane,0,0).y;
                        const topY=refresh.mapToItem(pane,0,0).y;
                        scroll.contentY=Math.max(0,scroll.contentHeight-scroll.height);
                        if (!smoke.check(controls.mapToItem(pane,0,0).y===y
                            && refresh.mapToItem(pane,0,0).y===topY,"work controls moved with scroll")) return;
                        scroll.contentY=0;
                    }
                    if (smoke.phase === 2) {
                        const proc = smoke.find(pane,"cpuplusProcessPane");
                        if (!proc) return;
                        if (!smoke.check(!proc.view && !CpuPlusDiagnostics.busy,
                            "PROC demand loaded without census")) return;
                        const coverage={examinedPidEntries:4,unreadableOrExited:0,truncated:false};
                        const one={schema:"post-apollo-process-census-v1",event:"census",sequence:1,
                            tsMs:1000,scope:"same-user",observed:2,cpuMeasured:1,ioMeasured:1,
                            coverage:coverage,previousCoverage:coverage,focusMatches:1,
                            rows:[{pid:12,name:"quickshell",startTicks:99,rssKiB:1048576,threads:4,cpuPct:10,readBps:0,writeBps:0},
                                {pid:13,name:"brave",startTicks:100,rssKiB:2097152,threads:8,cpuPct:null,readBps:null,writeBps:null}]};
                        const two=Object.assign({},one,{sequence:2,tsMs:11000,rows:[
                            Object.assign({},one.rows[0],{rssKiB:3145728}),
                            Object.assign({},one.rows[1],{startTicks:101})]});
                        const end={schema:one.schema,event:"complete",samples:2};
                        CpuPlusDiagnostics.reports=Object.assign({},CpuPlusDiagnostics.reports,{census:{
                            status:"COMPLETE",finishedAt:"2026-11-24T12:00:00.000Z",
                            text:[one,two,end].map(row=>JSON.stringify(row)).join("\n")}});
                        if (!smoke.check(proc.view && proc.ranked[0].pid===12
                            && proc.ranked[0].change===2097152 && proc.ranked[1].change===null
                            && !CpuPlusDiagnostics.busy && MemoryOperation.requests===0,
                            "PROC historical rows and PID reuse refusal")) return;
                        const groups=smoke.find(pane,"cpuplusProcGroups");
                        const processes=smoke.find(pane,"cpuplusProcProcesses");
                        const groupView=smoke.find(proc,"cpuplusProcGroupWorkspace");
                        const protect=smoke.find(proc,"cpuplusProcGroupProtectionLocked");
                        const limit=smoke.find(proc,"cpuplusProcGroupLimitLocked");
                        const start=smoke.find(pane,"cpuplusProcStart");
                        if(!smoke.check(groups&&processes&&groupView&&protect&&limit&&start,"PROC group controls exist"))return;
                        groups.leftClicked(null);
                        if(!smoke.check(proc.section==="GROUPS"&&groupView.visible&&!proc.groupIdentityAvailable
                            &&!protect.available&&!limit.available&&!start.available,"group controls fail closed"))return;
                        start.leftClicked(null);protect.leftClicked(null);limit.leftClicked(null);
                        if(!smoke.check(!CpuPlusDiagnostics.busy&&MemoryOperation.requests===0,"group controls no scan or mutation"))return;
                        processes.leftClicked(null);
                        if(!smoke.check(proc.section==="PROCESSES"&&!groupView.visible&&proc.ranked[0].pid===12
                            &&MemoryOperation.requests===0,"return preserves historical census"))return;
                        console.log("CPU_PROC_GROUP_BOUNDARY_NATIVE_PASS");
                    }
                    if (smoke.phase === 3) {
                        const queue = smoke.find(pane,"cpuplusQueuePane");
                        if (!queue) return;
                        if (!smoke.check(queue.display.state === "NOT CONNECTED"
                            && queue.display.requestId === null && queue.capacityTargetGiB === 24
                            && queue.observedDiskKiB === 16777212, "AUTO disconnected truth and capacity preview")) return;
                        queue.runtimeProjection = {version:1,adjustment_outcome:"UNVERIFIED",can_execute:false,
                            notification_candidate:null,notification_error:null,
                            status:{version:1,request_id:"c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
                                target_gib:16,original_actual_kib:25165816,expires_at:200,
                                state:"READY_ADVISORY",code:"FRESH_AUTH_AND_ROOT_CHECK_REQUIRED",
                                can_execute:false,last_checked_at:100,next_check_monotonic_ms:11000,
                                ready_valid_before_monotonic_ms:11000,transition:true}};
                        if (!smoke.check(queue.display.state === "READY REPORTED // RECHECK REQUIRED"
                            && queue.display.outcome === "UNVERIFIED" && !queue.display.canExecute
                            && queue.display.originalActualKiB !== queue.observedDiskKiB,
                            "AUTO historical report not live capacity or authorization")) return;
                        const report = queue.runtimeProjection;
                        queue.runtimeProjection = null;
                        if (!smoke.check(queue.display.requestId === null && queue.display.state === "NOT CONNECTED"
                            && MemoryOperation.requests === 0,"AUTO owner loss clears report")) return;
                        queue.intentConfirmed.connect(intent => { smoke.intentCount++; smoke.lastIntent = intent; });
                        queue.prepareIntent("CANCEL"); queue.confirmIntent();
                        if (!smoke.check(smoke.intentCount === 0 && queue.preparation === null,
                            "disconnected controls cannot submit")) return;
                        const ownerId = "c23683a9-b2ab-4a2c-87ce-31bdf27a3013";
                        const owner = Consumer.connect(Consumer.initial(),ownerId);
                        const envelope = {version:1,owner_id:ownerId,sequence:1,next_action_sequence:1,
                            kind:"STATUS",can_execute:false,projection:report};
                        const state = Consumer.acceptStatus(owner,envelope,QueueView.project);
                        queue.actionContext = {state:state,projection:report};
                        queue.prepareIntent("CANCEL");
                        if (!smoke.check(queue.preparation && queue.preparation.expectedId === report.status.request_id
                            && smoke.intentCount === 0,"explicit prepare does not send")) return;
                        const newer = Consumer.acceptStatus(state,Object.assign({},envelope,{sequence:2}),QueueView.project);
                        queue.actionContext = {state:newer,projection:report};
                        queue.confirmIntent();
                        if (!smoke.check(queue.preparation === null && smoke.intentCount === 0,
                            "fresh status invalidates confirmation")) return;
                        queue.prepareIntent("CANCEL");
                        queue.visible = false;
                        queue.confirmIntent();
                        queue.visible = true;
                        if (!smoke.check(queue.preparation === null && smoke.intentCount === 0,
                            "hide invalidates confirmation")) return;
                        queue.prepareIntent("CANCEL");
                        queue.confirmIntent();
                        queue.confirmIntent();
                        queue.prepareIntent("CANCEL");
                        if (!smoke.check(smoke.intentCount === 1 && smoke.lastIntent.kind === "CANCEL"
                            && smoke.lastIntent.expectedId === report.status.request_id
                            && smoke.lastIntent.statusSequence === 2 && queue.preparation === null
                            && MemoryOperation.requests === 0,"only one explicit intent signal")) return;
                        // Same revision echo must not release the latch.
                        queue.actionContext = {state:newer,projection:report};
                        queue.prepareIntent("CANCEL");
                        if (!smoke.check(queue.submitted && queue.preparation === null,
                            "same revision cannot rearm")) return;
                        // Host clears the context during pending/reply, then publishes
                        // a newer status. The pane must not retain the old click latch.
                        queue.actionContext = null;
                        queue.prepareIntent("CANCEL");
                        if (!smoke.check(queue.preparation === null && queue.display.state === "NOT CONNECTED",
                            "owner loss disables controls")) return;
                        const after = Consumer.acceptStatus(newer,Object.assign({},envelope,{
                            sequence:4,next_action_sequence:2}),QueueView.project);
                        queue.actionContext = {state:after,projection:report};
                        queue.prepareIntent("CANCEL");
                        if (!smoke.check(queue.submitted === null && queue.preparation
                            && queue.preparation.statusSequence === 4 && queue.preparation.actionSequence === 2
                            && smoke.intentCount === 1,"new host publication releases previous click latch")) return;
                        queue.cancelIntent();
                        queue.actionContext = null;
                        const workspace=smoke.find(pane,"cpuplusAutoWorkspace");
                        if (!workspace) return;
                        // Use canonical host state from the disposable fixture;
                        // startup remains locked. No child or frame dispatch.
                        queue.actionContext=Qt.binding(()=>workspace.actionContext);
                        workspace.hostState=Object.assign({},Host.initial(Consumer),{
                            phase:"CONNECTED",generation:1,session:after,projection:report,sequence:4});
                        workspace.historyReadRequested.connect(id => {
                            smoke.readCount++;
                            const req=Host.readHistory(workspace.hostState,id);
                            if (req.frame) workspace.hostState=req.state;
                        });
                        workspace.recoveryReadRequested.connect((kind,value) => {
                            smoke.readCount++;
                            const req=Host.readRecovery(workspace.hostState,kind,value);
                            if (req.frame) workspace.hostState=req.state;
                        });
                        queue.prepareIntent("CANCEL");
                        if (!smoke.check(queue.preparation===null,"canonical startup lock prevents cancel")) return;
                        workspace.selectSection("HISTORY");
                        smoke.phase=30;
                        return;
                    }
                    if (smoke.phase === 5) {
                        const prof=smoke.find(pane,"cpuplusProfilePane");
                        const bottom=smoke.find(pane,"cpuplusProfileBottomControls");
                        if (!prof || !bottom) return;
                        if (!smoke.check(prof.view && !prof.view.canApply && prof.view.capacity.target===null
                            && bottom.parent===smoke.find(pane,"cpuplusWorkFooter"),"blank profile and stapled footer")) return;
                        pane.chooseProfile("CUSTOM");
                        pane.captureProfileTarget("capacityGiB");
                        pane.captureProfileTarget("swappiness");
                        if (!smoke.check(prof.view.capacity.target===24 && prof.view.swappiness.target===150
                            && MemoryOperation.requests===0,"explicit CUSTOM copy")) return;
                        pane.chooseProfile("GAMING");
                        if (!smoke.check(prof.view.capacity.target===null && pane.customProfileDraft.capacityGiB===24,
                            "unconfigured preset cannot alter custom draft")) return;
                        pane.chooseProfile("CUSTOM");
                        const cmp=smoke.find(pane,"cpuplusProfileComparison");
                        const compareButton=smoke.find(pane,"cpuplusProfileCompare");
                        if(!cmp||!compareButton)return;
                        if(!smoke.check(compareButton.available&&compareButton.parent===bottom
                            &&cmp.comparison===null,"explicit comparison, fixed control"))return;
                        // Use real comparator with synthetic output from previously observed POL fixture.
                        cmp.pending={draft:JSON.parse(JSON.stringify(pane.customProfileDraft)),
                            rows:[{name:"/dev/zram0",size:8388608,priority:100}],zramRead:true,advancedRead:true};
                        cmp.capturedSample=pane.sample;
                        cmp.output="lzo [lz4] zstd\n100\n10\n0\n20\n0\n500\n3000\n";
                        cmp.received=true;cmp.exited=true;cmp.exitOk=true;cmp.finish();
                        if(!smoke.check(cmp.comparison&&!cmp.comparison.canApply
                            &&cmp.comparison.rows.find(x=>x.key==="background").delta===5
                            &&cmp.comparison.rows.find(x=>x.key==="priority").delta===1,
                            "actual-target comparison fixture"))return;
                        pane.chooseProfile("GAMING");
                        if(!smoke.check(cmp.comparison===null,"comparison invalidated on profile change"))return;
                        pane.chooseProfile("CUSTOM");
                        // Run the real fixed /proc read without depending on a CI zram device.
                        smoke.comparisonDraft=JSON.parse(JSON.stringify(pane.customProfileDraft));
                        const readDraft=JSON.parse(JSON.stringify(smoke.comparisonDraft));
                        readDraft.zram=null;
                        pane.customProfileDraft=readDraft;
                        if(!smoke.check(cmp.canRead,"native comparison ready"))return;
                        cmp.refresh();
                        if(!smoke.check(cmp.activeReader!==null&&cmp.pending!==null,"real comparison child started"))return;
                        pane.chooseProfile("GAMING");
                        if(!smoke.check(cmp.pending===null&&cmp.comparison===null,"in-flight comparison invalidated"))return;
                        pane.chooseProfile("CUSTOM");
                        smoke.phase=61;return;
                    }
                    if (smoke.phase < 5) pane.selectMenu(smoke.phase + 1);
                    else pane.selectMenu(0);
                    smoke.phase++;
                    return;
                }
                if(smoke.phase>=61&&smoke.phase<=65){
                    if(smoke.phase===64){
                        if(!smoke.check(!smoke.find(pane,"cpuplusProfileComparison"),"comparison unloaded"))return;
                        pane.selectMenu(5);smoke.phase=65;return;
                    }
                    const prof=smoke.find(pane,"cpuplusProfilePane");
                    const cmp=smoke.find(pane,"cpuplusProfileComparison");
                    if(!prof||!cmp)return;
                    if(smoke.phase===61){
                        if(cmp.activeReader!==null)return;
                        if(!smoke.check(cmp.comparison===null&&cmp.pending===null&&cmp.canRead,"cancelled child drained without result"))return;
                        cmp.refresh();
                        if(!smoke.check(cmp.activeReader!==null,"fresh child after cancellation"))return;
                        smoke.phase=62;return;
                    }
                    if(smoke.phase===62){
                        if(cmp.activeReader!==null)return;
                        if(!smoke.check(cmp.comparison&&!cmp.comparison.canApply&&cmp.exitOk
                            &&cmp.completedAt>0&&cmp.status==="OBSERVED // HISTORICAL"
                            &&cmp.comparison.rows.find(x=>x.key==="cachePressure").actual!=="UNAVAILABLE"
                            &&cmp.comparison.rows.find(x=>x.key==="priority").delta===1,
                            "actual proc comparison after cancellation"))return;
                        cmp.refresh();
                        if(!smoke.check(cmp.activeReader!==null,"read before unload"))return;
                        pane.selectMenu(0);smoke.phase=64;return;
                    }
                    if(smoke.phase===65){
                        if(!smoke.check(cmp.comparison===null&&cmp.activeReader===null&&cmp.pending===null&&cmp.canRead,
                            "reopened comparison idle without replay"))return;
                        cmp.refresh();smoke.phase=63;return;
                    }
                    if(cmp.activeReader!==null)return;
                    if(!smoke.check(cmp.comparison&&cmp.exitOk&&!cmp.comparison.canApply&&MemoryOperation.requests===0,
                        "actual comparison after reopen"))return;
                    console.log("CPU_PROFILE_COMPARISON_NATIVE_PASS // actual proc read, cancel, refresh and reopen");
                    pane.customProfileDraft=smoke.comparisonDraft;smoke.comparisonDraft=null;
                    const load=smoke.find(pane,"cpuplusProfileLoadList");
                    const save=smoke.find(pane,"cpuplusProfileSaveNew");
                        if (!smoke.check(load && save && load.available && !save.available
                            && prof.catalog===null && prof.catalogStatus==="NOT LOADED"
                            && scroll.height>0,"catalog idle and fixed footer")) return;
                        load.leftClicked(null);
                        smoke.phase=50;
                        return;
                }
                if (smoke.phase===30 || smoke.phase===31 || smoke.phase===32) {
                    const workspace=smoke.find(pane,"cpuplusAutoWorkspace");
                    const nav=smoke.find(pane,"cpuplusAutoNavigation");
                    const outer=smoke.find(pane,"cpuplusAutoWorkspaceFooter");
                    if (!workspace || !nav || !outer) return;
                    if (!smoke.check(nav.parent===outer && outer.parent===smoke.find(pane,"cpuplusWorkFooter")
                        && scroll.height>0,"AUTO fixed navigation and positive viewport")) return;
                    const y=nav.mapToItem(pane,0,0).y;
                    scroll.contentY=Math.max(0,scroll.contentHeight-scroll.height);
                    if (!smoke.check(nav.mapToItem(pane,0,0).y===y,"AUTO nav stays fixed")) return;
                    if (smoke.phase===30) {
                        const history=smoke.find(pane,"cpuplusQueueHistoryPane");
                        if (!history) return;
                        if (!smoke.check(!smoke.find(pane,"cpuplusQueuePane") && history.readAvailable && !history.detail,
                            "HISTORY demand loaded, read allowed while locked")) return;
                        history.lookupText=workspace.hostState.session.status.requestId;
                        history.requestRead();
                        history.requestRead();
                        if (!smoke.check(smoke.readCount===1 && workspace.hostState.historyRead,
                            "one explicit history read")) return;
                        workspace.selectSection("RECOVERY");
                        smoke.phase=31;
                        return;
                    }
                    if (smoke.phase===31) {
                        const recovery=smoke.find(pane,"cpuplusQueueRecoveryPane");
                        if (!recovery) return;
                        recovery.requestRead("INVENTORY",16);
                        if (!smoke.check(!recovery.canRead && smoke.readCount===1
                            && workspace.hostState.historyRead,"pending read survives submenu switch")) return;
                        // Simulate owner loss through canonical host; no fake unlock.
                        workspace.hostState=Host.stop(workspace.hostState,Consumer,"TEST_EOF",1);
                        if (!smoke.check(!recovery.canRead && !recovery.view && !recovery.localView,
                            "owner loss clears recovery")) return;
                        workspace.selectSection("REQUESTS");
                        smoke.phase=32;
                        return;
                    }
                    const queue=smoke.find(pane,"cpuplusQueuePane");
                    if (!queue) return;
                    if (!smoke.check(!queue.preparation && !queue.sessionUsable && MemoryOperation.requests===0,
                        "return to requests remains locked")) return;
                    pane.recoverySession=externalSession;
                    workspace.selectSection("RECOVERY");
                    smoke.phase=33;
                    return;
                }
                if (smoke.phase===33) {
                    const workspace=smoke.find(pane,"cpuplusAutoWorkspace");
                    const header=smoke.find(pane,"cpuplusRecoverySessionControls");
                    const connect=smoke.find(pane,"cpuplusRecoverySessionOpen");
                    const close=smoke.find(pane,"cpuplusRecoverySessionClose");
                    if(!workspace||!header||!connect||!close)return;
                    if(!smoke.check(workspace.recoverySession===externalSession && connect.available && !close.available
                        && header.parent===smoke.find(pane,"cpuplusWorkHeader")
                        && externalSession.opens===0 && externalSession.closes===0,"borrowed session and fixed header"))return;
                    connect.leftClicked(null);connect.leftClicked(null);
                    if(!smoke.check(externalSession.opens===1&&!connect.available,"one explicit session open"))return;
                    pane.selectMenu(0);smoke.phase=34;return;
                }
                if(smoke.phase===34) {
                    if(!smoke.check(!smoke.find(pane,"cpuplusAutoWorkspace")&&externalSession.opens===1
                        &&externalSession.closes===0,"unmount does not stop session"))return;
                    pane.selectMenu(3);smoke.phase=35;return;
                }
                if(smoke.phase===35) {
                    const workspace=smoke.find(pane,"cpuplusAutoWorkspace");
                    if(!workspace)return;
                    if(!smoke.check(workspace.recoverySession===externalSession&&externalSession.opens===1
                        &&externalSession.closes===0&&!workspace.actionContext,"reopen preserves owner and lock"))return;
                    pane.recoverySession=null;
                    if(!smoke.check(workspace.recoverySession===null&&!workspace.actionContext,"detach fails closed"))return;
                    console.log("CPU_M9_EXTERNAL_SESSION_PASS // borrowed owner, header, single open, unload/reopen, detach");
                    pane.selectMenu(4);smoke.phase=4;return;
                }
                if (smoke.phase>=50 && smoke.phase<=60) {
                    const prof=smoke.find(pane,"cpuplusProfilePane");
                    if(smoke.phase===52) {
                        if (!smoke.check(!prof && pane.page==="CAP","profile page unloaded"))return;
                        pane.stageCapacity(32);
                        if (!smoke.check(pane.stagedGiB===32,"distinct CAP target before profile load"))return;
                        pane.selectMenu(1); smoke.phase=59; return;
                    }
                    if(smoke.phase===59) {
                        pane.selectPolicySection(0);
                        pane.stagePolicy(80);
                        if(!smoke.check(pane.stagedSwappiness===80,"distinct POL target before profile load"))return;
                        pane.selectPolicySection(1);smoke.phase=60;return;
                    }
                    if(smoke.phase===60) {
                        pane.selectPriorityDevice("/dev/zram0");
                        pane.stagePriority(110);
                        if(!smoke.check(pane.stagedPriority===110,"distinct priority target before profile load"))return;
                        pane.selectMenu(5);smoke.phase=53;return;
                    }
                    if(!prof)return;
                    if(smoke.phase===50) {
                        if(prof.catalogBusy)return;
                        if(!smoke.check(prof.catalogReady && prof.catalog.revision===0
                            && prof.savedRows.length===0,"actual empty catalog read"))return;
                        prof.saveName="Native Work";
                        const save=smoke.find(pane,"cpuplusProfileSaveNew");
                        if(!smoke.check(save && save.available,"named save available"))return;
                        save.leftClicked(null);
                        save.leftClicked(null);
                        smoke.phase=51;return;
                    }
                    if(smoke.phase===51) {
                        if(prof.catalogBusy)return;
                        if(!smoke.check(prof.catalogReady && prof.catalog.revision===1
                            && prof.savedRows.length===1 && prof.savedRows[0].name==="Native Work"
                            &&prof.savedRows[0].targets.zram.algorithm==="zstd"&&prof.savedRows[0].targets.priority.value===101
                            &&prof.savedRows[0].targets.advanced.background.value===15,
                            "one actual persisted profile"))return;
                        pane.clearProfileDraft();
                        pane.selectMenu(0);smoke.phase=52;return;
                    }
                    if(smoke.phase===53) {
                        const load=smoke.find(pane,"cpuplusProfileLoadList");
                        if(!smoke.check(load && load.available && prof.view.capacity.target===null,
                            "reopened PROF with cleared draft"))return;
                        load.leftClicked(null);smoke.phase=54;return;
                    }
                    if(smoke.phase===55) {
                        if(prof.catalogBusy)return;
                        if(!smoke.check(prof.catalogReady&&prof.catalog.revision===2
                            &&prof.savedRows[0].targets.swappiness===null,"explicit edit persisted"))return;
                        prof.selectedSaved="Native Work";prof.saveName="Native Office";
                        prof.prepareChange("rename");prof.confirmChange();
                        smoke.phase=56;return;
                    }
                    if(smoke.phase===56) {
                        if(prof.catalogBusy)return;
                        if(!smoke.check(prof.catalogReady&&prof.catalog.revision===3
                            &&prof.savedRows[0].name==="Native Office","exact rename persisted"))return;
                        prof.selectedSaved="Native Office";
                        prof.prepareChange("delete");prof.cancelChange();prof.confirmChange();
                        if(!smoke.check(prof.catalog.revision===3&&!prof.catalogBusy,"cancelled deletion no write"))return;
                        prof.prepareChange("delete");prof.confirmChange();prof.confirmChange();
                        smoke.phase=57;return;
                    }
                    if(smoke.phase===57) {
                        if(prof.catalogBusy)return;
                        if(!smoke.check(prof.catalogReady&&prof.catalog.revision===4&&prof.savedRows.length===0,
                            "one confirmed delete persisted"))return;
                        const load=smoke.find(pane,"cpuplusProfileLoadList");
                        load.leftClicked(null);smoke.phase=58;return;
                    }
                    if(smoke.phase===58) {
                        if(prof.catalogBusy)return;
                        if(!smoke.check(prof.catalogReady&&prof.catalog.revision===4&&prof.savedRows.length===0
                            &&MemoryOperation.requests===0,"deleted catalog reload and zero memory operations"))return;
                        pane.clearProfileDraft();pane.captureProfileTarget("capacityGiB");pane.captureProfileTarget("swappiness");
                        console.log("CPU_PROFILE_NATIVE_PASS // persisted save, unload/reopen, reload, edit, rename, delete and draft only");
                        pane.selectMenu(0);smoke.phase=6;return;
                    }
                    if(prof.catalogBusy)return;
                    if(!smoke.check(prof.catalogReady && prof.catalog.revision===1
                        && prof.savedRows.length===1,"disk re-read after reopen"))return;
                    prof.selectedSaved="Native Work";
                    const loadDraft=smoke.find(pane,"cpuplusProfileLoadDraft");
                    if(!smoke.check(loadDraft && loadDraft.available,"load draft available"))return;
                    loadDraft.leftClicked(null);
                    if(!smoke.check(prof.view.capacity.target===24 && prof.view.swappiness.target===150
                        && pane.stagedGiB===32 && pane.stagedSwappiness===80 && pane.stagedPriority===110 && MemoryOperation.requests===0
                        &&pane.customProfileDraft.zram.algorithm==="zstd"&&pane.customProfileDraft.priority.value===101
                        &&pane.customProfileDraft.advanced.background.unit==="%"&&pane.customProfileDraft.advanced.background.value===15,
                        "loaded draft only, no setting changes"))return;
                    pane.clearProfileDraft();pane.captureProfileTarget("capacityGiB");
                    prof.selectedSaved="Native Work";
                    prof.prepareChange("edit");
                    if(!smoke.check(!!prof.confirmation&&!prof.catalogBusy,"edit preparation does not write"))return;
                    prof.selectedSaved="";
                    prof.confirmChange();
                    if(!smoke.check(!prof.catalogBusy&&prof.catalog.revision===1,"selection change invalidates confirmation"))return;
                    prof.selectedSaved="Native Work";prof.prepareChange("edit");prof.confirmChange();
                    smoke.phase=55;return;
                }
                if (!smoke.check(pane.page === "CAP" && slider.visible
                        && pane.stagedGiB === 32 && pane.stagedSwappiness === 80 && pane.stagedPriority===110
                        && pane.customProfileDraft.capacityGiB===32 && pane.customProfileDraft.swappiness===80
                        && MemoryOperation.requests === 0, "navigation continuity or unexpected dispatch")) return;
                console.log("CPU_MEMORY_UI_NATIVE_PASS");
                smoke.done = true;
                Qt.quit();
            }
            }
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: smoke.armed && !smoke.done
        onTriggered: {
            if (++smoke.ticks > 150) {
                smoke.check(false, "timeout phase=" + smoke.phase);
                return;
            }
            if (scene.item) scene.item.testStep();
        }
    }
    Component.onCompleted: if (!armed) Qt.quit()
}
