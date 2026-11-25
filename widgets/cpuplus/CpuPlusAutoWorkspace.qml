import QtQuick
import "../../components"
import "../../services/memory/MemoryQueueSessionHost.js" as Host
import "CpuPlusQueueHistory.js" as History
import "CpuPlusQueueRecovery.js" as Recovery

// View only. The external session owner supplies one immutable canonical
// state and synchronously commits pending state before sending any frame.
// Destroying this view never stops the session, acknowledges, or replays.
Column {
    id: root
    objectName: "cpuplusAutoWorkspace"
    property Item headerTarget: null
    property Item footerTarget: null
    required property var observedDiskKiB
    required property int capacityTargetGiB
    property var hostState: null
    // Externally owned, preconfigured recovery-only session. Never create
    // a process or select launch paths in this demand-loaded view.
    property var recoverySession: null
    readonly property bool sessionActive: !!recoverySession && recoverySession.phase==="ACTIVE"
        && recoverySession.active() && recoverySession.startupLocked===true && recoverySession.canExecute===false
    readonly property bool sessionReadAvailable: sessionActive && Recovery.canRead(recoverySession.recoveryContext,true)
    function sessionAction(kind) {
        if (!visible || section!=="RECOVERY" || !recoverySession) return;
        if (kind==="OPEN" && recoverySession.phase==="IDLE") recoverySession.open();
        else if (kind==="CLOSE" && sessionActive) recoverySession.close();
    }
    property string section: "REQUESTS"
    signal sectionChangedByUser()
    signal intentConfirmed(var intent)
    signal historyReadRequested(string requestId)
    signal recoveryReadRequested(string kind, var value)
    signal reviewRequested(string actionId)
    signal acknowledgmentRequested(var selection, var generation)
    signal reviewReceiptRequested(string reviewId)
    readonly property var reviewContext: recoverySession ? (sessionActive ? recoverySession.reviewContext : null) : hostState ? Host.reviewContext(hostState) : null
    readonly property bool reviewAvailable: recoverySession ? sessionReadAvailable && !!reviewContext && ["IDLE","ACK_UNKNOWN"].includes(reviewContext.phase) : !!hostState && Host.reviewAvailable(hostState) && !hostState.checkpointWait
    readonly property var reviewGeneration: recoverySession ? recoverySession.generation : hostState ? hostState.generation : null
    function forwardReview(actionId) {
        if (recoverySession) {
            if (visible && section==="RECOVERY" && reviewAvailable && !reviewContext.unknownReviewId
                && !recoverySession.dispositionContext.unknownActionId && Recovery.uuid(actionId)) recoverySession.beginReview(actionId);
            return;
        }
        if (visible && section==="RECOVERY" && reviewAvailable && !hostState.reviewLost && Recovery.uuid(actionId))
            reviewRequested(actionId);
    }
    function forwardAcknowledgment(selection,generation) {
        if (recoverySession) {
            const current=Recovery.reviewSelection(reviewContext,reviewGeneration);
            if (visible && section==="RECOVERY" && sessionActive && generation===reviewGeneration
                && Recovery.sameSelection(current,selection))
                recoverySession.acknowledge({reviewId:current.reviewId,digest:current.digest,sequence:current.sequence});
            return;
        }
        if (!visible || section!=="RECOVERY" || !hostState || generation!==hostState.generation || hostState.checkpointWait) return;
        const current=Recovery.reviewSelection(Host.reviewContext(hostState),generation);
        if (current && Recovery.sameSelection(current,selection))
            acknowledgmentRequested({reviewId:current.reviewId,digest:current.digest,sequence:current.sequence},generation);
    }
    function forwardReceipt(reviewId) {
        if (recoverySession) {
            if (visible && section==="RECOVERY" && reviewAvailable && Recovery.uuid(reviewId)
                && (!reviewContext.unknownReviewId || reviewContext.unknownReviewId===reviewId))
                recoverySession.readAcknowledgment(reviewId);
            return;
        }
        if (visible && section==="RECOVERY" && reviewAvailable && Recovery.uuid(reviewId)
            && (!hostState.reviewLost || hostState.reviewLost.review_id===reviewId))
            reviewReceiptRequested(reviewId);
    }
    readonly property var actionContext: !recoverySession && hostState ? Host.context(hostState) : null
    readonly property var recoveryContext: recoverySession ? recoverySession.recoveryContext : hostState ? Host.recoveryContext(hostState) : null
    readonly property bool readAvailable: recoverySession ? sessionReadAvailable : canRead(hostState)
    function canRead(s) {
        return !!(s && s.phase==="CONNECTED" && s.session && s.session.status
            && !s.session.pending && !s.historyRead && !s.recoveryRead
            && !s.awaitingStatus && !s.publicationRequired && !s.reviewFlow && !s.checkpointWait && !s.buffer);
    }
    function selectSection(name) {
        if (!visible || !["REQUESTS","HISTORY","RECOVERY"].includes(name) || section===name) return;
        section=name;
        sectionChangedByUser();
    }
    // Read controls may operate while startup is locked or an outcome is
    // unresolved. Only the canonical host can accept the read or mutation.
    function forwardHistory(requestId) {
        if (!recoverySession && visible && section==="HISTORY" && canRead(hostState) && History.uuid(requestId))
            historyReadRequested(requestId);
    }
    function forwardRecovery(kind,value) {
        if (recoverySession) {
            if (!visible || section!=="RECOVERY" || !sessionReadAvailable) return;
            if (kind==="INVENTORY" && value===4) recoverySession.readInventory(value);
            else if (kind==="LOCAL_ACTION" && Recovery.uuid(value)) recoverySession.readAction(value);
            return;
        }
        if (!visible || section!=="RECOVERY" || !canRead(hostState)) return;
        if ((kind==="INVENTORY"&&value===16)||(kind==="LOCAL_ACTION"&&Recovery.uuid(value)))
            recoveryReadRequested(kind,value);
    }
    function forwardIntent(intent) {
        if (!recoverySession && visible && section==="REQUESTS" && canRead(hostState)
            && hostState.startupLocked===false && !hostState.session.unresolved)
            intentConfirmed(intent);
    }
    spacing: 5
    Column {
        id: fixedFooter
        parent: root.footerTarget || root
        objectName: "cpuplusAutoWorkspaceFooter"
        width: parent.width
        spacing: 3
        Column {
            id: sectionFooter
            objectName: "cpuplusAutoSectionFooter"
            width: parent.width
            spacing: 3
        }
        Row {
            id: nav
            objectName: "cpuplusAutoNavigation"
            width: parent.width
            spacing: 3
            Repeater {
                model: ["REQUESTS","HISTORY","RECOVERY"]
                delegate: ActionButton {
                    required property string modelData
                    width: Math.max(0,(nav.width-2*nav.spacing)/3)
                    height: 26
                    label: modelData
                    contentPadding: 2
                    labelFontSizeMode: Text.HorizontalFit
                    labelMinimumPixelSize: 8
                    selected: root.section===modelData
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: root.selectSection(modelData)
                }
            }
        }
    }
    Row {
        parent: root.headerTarget || root
        objectName: "cpuplusRecoverySessionControls"
        visible: root.section==="RECOVERY"
        width: parent.width
        spacing: 3
        GohuText {
            width: Math.max(0,parent.width-120-2*parent.spacing)
            text: root.recoverySession ? "SESSION // "+root.recoverySession.phase : "SESSION // NOT MOUNTED"
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        ActionButton {
            objectName: "cpuplusRecoverySessionOpen"
            width: 64
            height: 26
            label: "CONNECT"
            contentPadding: 2
            available: !!root.recoverySession && root.recoverySession.phase==="IDLE"
            acceptedButtons: Qt.LeftButton
            keyboardActivationSignal: "leftClicked"
            onLeftClicked: root.sessionAction("OPEN")
        }
        ActionButton {
            objectName: "cpuplusRecoverySessionClose"
            width: 56
            height: 26
            label: "CLOSE"
            contentPadding: 2
            available: root.sessionActive
            acceptedButtons: Qt.LeftButton
            keyboardActivationSignal: "leftClicked"
            onLeftClicked: root.sessionAction("CLOSE")
        }
    }
    GohuText {
        parent: root.headerTarget || root
        width: parent.width
        text: root.recoverySession ? Recovery.gate(root.recoveryContext ? root.recoveryContext.hostStatus : null)
            : root.hostState ? Recovery.gate(root.recoveryContext ? root.recoveryContext.hostStatus : null)
            : "AUTO // TRANSPORT NOT CONNECTED"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Loader {
        width: parent.width
        height: item ? item.implicitHeight : 0
        active: root.section==="REQUESTS"
        visible: active
        sourceComponent: CpuPlusQueuePane {
            headerTarget: root.headerTarget
            footerTarget: sectionFooter
            observedDiskKiB: root.observedDiskKiB
            capacityTargetGiB: root.capacityTargetGiB
            runtimeProjection: null
            actionContext: root.actionContext
            onIntentConfirmed: intent => root.forwardIntent(intent)
        }
    }
    Loader {
        width: parent.width
        height: item ? item.implicitHeight : 0
        active: root.section==="HISTORY"
        visible: active
        sourceComponent: CpuPlusQueueHistoryPane {
            hostMode: true
            footerTarget: sectionFooter
            hostHistory: root.hostState ? root.hostState.history : null
            historyAvailable: !root.recoverySession && root.readAvailable && hostHistory!==null
            readAvailable: !root.recoverySession && root.readAvailable
            readPending: !!(root.hostState && root.hostState.historyRead)
            onHistoryReadRequested: requestId => root.forwardHistory(requestId)
        }
    }
    Loader {
        width: parent.width
        height: item ? item.implicitHeight : 0
        active: root.section==="RECOVERY"
        visible: active
        sourceComponent: CpuPlusQueueRecoveryPane {
            atomicMode: true
            footerTarget: sectionFooter
            recoveryContext: root.recoveryContext
            readAvailable: root.readAvailable
            onRecoveryReadRequested: (kind,value) => root.forwardRecovery(kind,value)
            recoverySession: root.recoverySession
            sessionActive: root.sessionActive
            reviewContext: root.reviewContext
            reviewGeneration: root.reviewGeneration
            reviewAvailable: root.reviewAvailable
            onReviewRequested: actionId => root.forwardReview(actionId)
            onAcknowledgmentRequested: (selection,generation) => root.forwardAcknowledgment(selection,generation)
            onReviewReceiptRequested: reviewId => root.forwardReceipt(reviewId)
        }
    }
}
