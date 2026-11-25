import QtQuick
import "../../components"
import "CpuPlusQueueRecovery.js" as Recovery

// Read-only. Canonical host owns correlation and clears data on loss/timeout.
// Legacy standalone fixture inputs remain supported; atomic mode never falls back.
Column {
    id: root
    objectName: "cpuplusQueueRecoveryPane"
    property var hostStatus: null
    property var inventory: null
    property bool atomicMode: false
    property var recoveryContext: null
    // Host supplies this from its exact read gate; it revalidates every signal.
    property bool readAvailable: false
    property Item footerTarget: null
    property string lookupText: ""
    signal recoveryReadRequested(string kind, var value)
    property var reviewContext: null
    property var reviewGeneration: null
    property bool reviewAvailable: false
    property string receiptLookup: ""
    property var confirmation: null
    property var recoverySession: null
    property bool sessionActive: false
    property var dismissalConfirmation: null
    property var retentionConfirmation: null
    readonly property var dispositionContext: recoverySession ? recoverySession.dispositionContext : null
    readonly property var dismissedReceipt: dispositionContext ? Recovery.dispositionReceipt(dispositionContext.receipt) : null
    readonly property string unknownActionId: dispositionContext && Recovery.uuid(dispositionContext.unknownActionId) ? dispositionContext.unknownActionId : ""
    readonly property string dispositionLookupId: unknownActionId || lookupText
    readonly property var dismissalSelection: sessionActive ? Recovery.dismissalSelection(dispositionContext,reviewGeneration) : null
    readonly property var retainSelection: sessionActive && recoverySession
        ? Recovery.retentionSelection(recoverySession.retentionSelection,dismissedReceipt,reviewReceipt,
            reviewGeneration,recoverySession.storageGeneration) : null
    function clearConfirmations() {
        confirmation=null; dismissalConfirmation=null; retentionConfirmation=null;
    }
    function prepareDismissal() {
        if(visible && atomicMode && sessionActive && dismissalSelection && !confirmation && !retentionConfirmation && !dismissalConfirmation)
            dismissalConfirmation=Object.assign({},dismissalSelection);
    }
    function confirmDismissal() {
        const frozen=dismissalConfirmation;
        dismissalConfirmation=null;
        if(visible && atomicMode && sessionActive && recoverySession && Recovery.sameSelection(dismissalSelection,frozen))
            recoverySession.dismiss({reviewId:frozen.reviewId,digest:frozen.digest,sequence:frozen.sequence});
    }
    function lookupDisposition() {
        if(visible && atomicMode && sessionActive && recoverySession && reviewAvailable
            && Recovery.uuid(dispositionLookupId) && !unknownReviewId)
            recoverySession.readDisposition(dispositionLookupId);
    }
    function prepareRetention() {
        if(visible && atomicMode && sessionActive && retainSelection && !confirmation && !dismissalConfirmation && !retentionConfirmation)
            retentionConfirmation=Object.assign({},retainSelection);
    }
    function confirmRetention() {
        const frozen=retentionConfirmation;
        retentionConfirmation=null;
        if(visible && atomicMode && sessionActive && recoverySession && Recovery.sameRetention(retainSelection,frozen))
            recoverySession.advance({storageGeneration:frozen.storageGeneration,actionId:frozen.actionId,
                reviewDigest:frozen.reviewDigest,sequence:frozen.sequence});
    }
    onDismissalSelectionChanged: if(!Recovery.sameSelection(dismissalSelection,dismissalConfirmation)) dismissalConfirmation=null
    onRetainSelectionChanged: if(!Recovery.sameRetention(retainSelection,retentionConfirmation)) retentionConfirmation=null
    onRecoverySessionChanged: clearConfirmations()
    onSessionActiveChanged: if(!sessionActive) clearConfirmations()
    signal reviewRequested(string actionId)
    signal acknowledgmentRequested(var selection, var generation)
    signal reviewReceiptRequested(string reviewId)
    readonly property var reviewEvidence: reviewContext ? Recovery.reviewEvidence(reviewContext.review) : null
    readonly property var reviewReceipt: reviewContext ? Recovery.reviewReceipt(reviewContext.receipt) : null
    readonly property var currentSelection: Recovery.reviewSelection(reviewContext,reviewGeneration)
    readonly property string unknownReviewId: reviewContext && Recovery.uuid(reviewContext.unknownReviewId) ? reviewContext.unknownReviewId : ""
    readonly property string effectiveReceiptId: unknownReviewId || receiptLookup
    function beginReview() {
        if(visible && atomicMode && reviewAvailable && !unknownReviewId && !unknownActionId && Recovery.uuid(lookupText))
            reviewRequested(lookupText);
    }
    function prepareAcknowledgment() {
        if(visible && atomicMode && currentSelection && !confirmation && !dismissalConfirmation && !retentionConfirmation)
            confirmation=Object.assign({},currentSelection);
    }
    function confirmAcknowledgment() {
        const frozen=confirmation;
        confirmation=null;
        if(visible && atomicMode && Recovery.sameSelection(currentSelection,frozen))
            acknowledgmentRequested(frozen,frozen.generation);
    }
    function lookupReceipt() {
        if(visible && atomicMode && reviewAvailable && Recovery.uuid(effectiveReceiptId))
            reviewReceiptRequested(effectiveReceiptId);
    }
    onCurrentSelectionChanged: if(!Recovery.sameSelection(currentSelection,confirmation)) confirmation=null
    onVisibleChanged: if(!visible) clearConfirmations()
    onAtomicModeChanged: if(!atomicMode) clearConfirmations()
    onLookupTextChanged: clearConfirmations()

    readonly property var snapshot: atomicMode ? Recovery.context(recoveryContext) : null
    readonly property var effectiveHost: atomicMode ? (snapshot ? snapshot.host : null) : hostStatus
    readonly property var view: atomicMode ? (snapshot ? snapshot.inventory : null) : Recovery.project(inventory)
    readonly property var localView: snapshot ? snapshot.localAction : null
    readonly property bool canRead: atomicMode && Recovery.canRead(recoveryContext,readAvailable)
    function requestRead(kind,value) {
        if (!visible || !atomicMode || !Recovery.canRead(recoveryContext,readAvailable)) return;
        if (kind==="INVENTORY" && value===16) recoveryReadRequested(kind,value);
        else if (kind==="LOCAL_ACTION" && Recovery.uuid(value)) recoveryReadRequested(kind,value);
    }
    spacing: 5
    GohuText {
        width: parent.width
        text: "AUTO // STARTUP & RECOVERY"
        color: Colors.magenta
        font.pixelSize: 12
    }
    GohuText {
        width: parent.width
        text: Recovery.gate(root.effectiveHost)
        color: Colors.orange
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: root.view ? "PENDING REQUEST // " + (root.view.pendingId || "NONE REPORTED")
            + "\n" + (root.view.truncated ? "PARTIAL RECENT INVENTORY" : "RECENT INVENTORY REPORTED")
            : root.snapshot && root.snapshot.readPending ? "RECOVERY READ PENDING"
            : root.localView ? "EXACT ACTION LOOKUP // INVENTORY NOT DISPLAYED"
            : "RECOVERY INVENTORY UNAVAILABLE"
        color: Colors.cyan
        textFormat: Text.PlainText
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        visible: root.view !== null
        text: root.view && root.view.prepared
            ? "PREPARED ACTION // " + root.view.prepared.actionId
                + "\n" + root.view.prepared.kind + " // DO NOT REPLAY"
            : "NO PREPARED ACTION REPORTED // NOT PROOF OF NONCOMMIT"
        color: Colors.orange
        font.pixelSize: 10
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        visible: root.localView !== null
        text: root.localView ? "LOOKUP ACTION // "+root.localView.actionId
            + (root.localView.missing ? "\nNO RECORD REPORTED // NOT PROOF OF NONCOMMIT" : "\nEXACT LOCAL RECORD REPORTED") : ""
        color: Colors.orange
        textFormat: Text.PlainText
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Repeater {
        model: root.localView ? (root.localView.record ? [root.localView.record] : [])
            : root.view ? root.view.recent : []
        delegate: Rectangle {
            required property var modelData
            width: root.width
            height: body.implicitHeight + 8
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan
            Column {
                id: body
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 4
                spacing: 2
                GohuText {
                    width: parent.width
                    text: modelData.kind + " // " + (modelData.state==="COMMITTED"
                        ? "LOCAL INTENT COMMITTED" : "PREPARED // UNRESOLVED")
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
                GohuText {
                    width: parent.width
                    text: "ACTION // " + modelData.actionId
                        + "\nEXPECTED // " + (modelData.expectedId || "NEW REQUEST")
                        + "\nRESULT // " + (modelData.resultId || "NOT RECORDED")
                        + (modelData.target===null ? "" : "\nTARGET // "+modelData.target+" GiB"
                            + "\nEXPIRY // "+Recovery.utc(modelData.expiry))
                        + "\nPREPARED // "+Recovery.utc(modelData.preparedAt)
                        + (modelData.committedAt===null?"":"\nCOMMITTED // "+Recovery.utc(modelData.committedAt))
                    textFormat: Text.PlainText
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }
        }
    }
    Column {
        parent: root.footerTarget || root
        objectName: "cpuplusRecoveryReadControls"
        visible: root.atomicMode
        width: parent.width
        spacing: 3
        GohuText {
            width: parent.width
            text: "ACTION UUID // EXACT LOOKUP"
            color: Colors.cyan
            font.pixelSize: 10
        }
        Rectangle {
            width: parent.width
            height: 27
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan
            TextInput {
                anchors.fill: parent
                anchors.margins: 4
                color: Colors.white
                font.pixelSize: 10
                maximumLength: 36
                selectByMouse: true
                clip: true
                text: root.lookupText
                onTextEdited: root.lookupText=text
            }
        }
        Row {
            width: parent.width
            spacing: 3
            ActionButton {
                objectName: "cpuplusRecoveryInventoryRead"
                width: Math.max(0,(parent.width-parent.spacing)/2)
                height: 26
                label: "INVENTORY"
                contentPadding: 2
                available: root.canRead
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.requestRead("INVENTORY",16)
            }
            ActionButton {
                objectName: "cpuplusRecoveryActionRead"
                width: Math.max(0,(parent.width-parent.spacing)/2)
                height: 26
                label: "LOOKUP"
                contentPadding: 2
                available: root.canRead && Recovery.uuid(root.lookupText)
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.requestRead("LOCAL_ACTION",root.lookupText)
            }
        }
    }
    Column {
        width: parent.width
        spacing: 4
        visible: root.atomicMode
        GohuText {
            width: parent.width
            text: "RECOVERY REVIEW // "+(root.reviewContext ? root.reviewContext.phase : "UNAVAILABLE")
                +(root.unknownReviewId?"\nACK OUTCOME UNKNOWN // "+root.unknownReviewId+"\nLOOK UP RECEIPT; DO NOT REPEAT ACK":"")
            color: Colors.orange
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WrapAnywhere
        }
        ActionButton {
            objectName: "cpuplusRecoveryReviewRequest"
            width: parent.width
            height: 28
            label: "REVIEW ACTION UUID"
            available: root.reviewAvailable && !root.unknownReviewId && !root.unknownActionId && Recovery.uuid(root.lookupText)
            acceptedButtons: Qt.LeftButton
            keyboardActivationSignal: "leftClicked"
            onLeftClicked: root.beginReview()
        }
        GohuText {
            width: parent.width
            visible: root.reviewEvidence!==null
            text: root.reviewEvidence ? "REVIEW // "+root.reviewEvidence.reviewId
                +"\nACTION // "+root.reviewEvidence.action.actionId
                +"\n"+root.reviewEvidence.action.kind+" // "+root.reviewEvidence.action.state
                +"\nTARGET // "+(root.reviewEvidence.action.target===null?"N/A":root.reviewEvidence.action.target+" GiB")
                +"\nEXPECTED // "+(root.reviewEvidence.action.expectedId||"NEW REQUEST")
                +"\nRESULT // "+(root.reviewEvidence.action.resultId||"NOT RECORDED")
                +"\nPREPARED // "+Recovery.utc(root.reviewEvidence.action.preparedAt)
                +"\nCOMMITTED // "+(root.reviewEvidence.action.committedAt===null?"NOT RECORDED":Recovery.utc(root.reviewEvidence.action.committedAt))
                +"\nPENDING // "+(root.reviewEvidence.pendingId||"NONE REPORTED")
                +"\nDIGEST // "+root.reviewEvidence.digest
                +"\nHOST MAY EXPIRE OR REFUSE REVIEW; NO EXECUTION AUTHORITY":""
            color: Colors.cyan
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WrapAnywhere
        }
        ActionButton {
            objectName: "cpuplusRecoveryAckPrepare"
            width: parent.width
            height: 28
            label: "ACKNOWLEDGE REVIEW"
            visible: root.confirmation===null
            available: root.currentSelection!==null && !root.dismissalConfirmation && !root.retentionConfirmation
            acceptedButtons: Qt.LeftButton
            keyboardActivationSignal: "leftClicked"
            onLeftClicked: root.prepareAcknowledgment()
        }
        GohuText {
            width: parent.width
            visible: root.confirmation!==null
            text: "CONFIRM REVIEW ONLY // DOES NOT CLEAR UNRESOLVED STATE, RELEASE PREPARED OR UNLOCK EXECUTION"
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        Row {
            width: parent.width
            spacing: 3
            visible: root.confirmation!==null
            ActionButton {
                objectName: "cpuplusRecoveryAckConfirm"
                width: Math.max(0,(parent.width-parent.spacing)/2)
                height: 28
                label: "CONFIRM"
                available: Recovery.sameSelection(root.currentSelection,root.confirmation)
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.confirmAcknowledgment()
            }
            ActionButton {
                width: Math.max(0,(parent.width-parent.spacing)/2)
                height: 28
                objectName: "cpuplusRecoveryAckCancel"
                label: "CANCEL"
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.confirmation=null
            }
        }
        Column {
            width: parent.width
            spacing: 3
            visible: root.recoverySession!==null
            GohuText {
                width: parent.width
                text: "LOCAL DISPOSITION // "+(root.dispositionContext ? root.dispositionContext.phase : "UNAVAILABLE")
                    +(root.unknownActionId?"\nOUTCOME UNKNOWN // "+root.unknownActionId+"\nLOOK UP; NEVER REPEAT DISMISSAL":"")
                color: Colors.orange
                font.pixelSize: 10
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
            }
            ActionButton {
                objectName: "cpuplusRecoveryDismissPrepare"
                width: parent.width
                height: 28
                label: "DISMISS LOCAL PREPARATION"
                available: !!root.dismissalSelection && !root.confirmation && !root.retentionConfirmation && !root.dismissalConfirmation
                visible: !root.dismissalConfirmation
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.prepareDismissal()
            }
            GohuText {
                width: parent.width
                visible: !!root.dismissalConfirmation
                text: "CONFIRM LOCAL DISMISSAL ONLY // ORIGINAL EVIDENCE RETAINED; NO MEMORY CHANGE OR STARTUP UNLOCK"
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }
            Row {
                width: parent.width
                spacing: 3
                visible: !!root.dismissalConfirmation
                ActionButton {
                    objectName: "cpuplusRecoveryDismissConfirm"
                    width: Math.max(0,(parent.width-parent.spacing)/2)
                    height: 28
                    label: "CONFIRM"
                    available: Recovery.sameSelection(root.dismissalSelection,root.dismissalConfirmation)
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: root.confirmDismissal()
                }
                ActionButton {
                    objectName: "cpuplusRecoveryDismissCancel"
                    width: Math.max(0,(parent.width-parent.spacing)/2)
                    height: 28
                    label: "CANCEL"
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: root.dismissalConfirmation=null
                }
            }
            ActionButton {
                objectName: "cpuplusRecoveryDispositionLookup"
                width: parent.width
                height: 28
                label: "LOOK UP DISMISSAL"
                available: root.sessionActive && root.reviewAvailable && !root.unknownReviewId && Recovery.uuid(root.dispositionLookupId)
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.lookupDisposition()
            }
            GohuText {
                width: parent.width
                text: root.dismissedReceipt ? "LOCAL PREPARATION DISMISSED // "+root.dismissedReceipt.action.actionId
                    +"\nADJUSTMENT UNVERIFIED" : "NO DISMISSAL RECEIPT DISPLAYED"
                color: Colors.orange
                font.pixelSize: 10
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
            }
            GohuText {
                width: parent.width
                text: "RETENTION // GENERATION "+(root.recoverySession && root.recoverySession.storageGeneration>=0
                    ? root.recoverySession.storageGeneration : "UNAVAILABLE")
                    +(root.retainSelection ? "\n"+root.retainSelection.mode+" // "+root.retainSelection.actionId
                        : "\nFRESH HISTORICAL RECEIPT REQUIRED; CLOSE AND RECONNECT AFTER SAVE")
                color: Colors.cyan
                font.pixelSize: 10
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
            }
            ActionButton {
                objectName: "cpuplusRecoveryRetainPrepare"
                width: parent.width
                height: 28
                label: "RETAIN & ADVANCE"
                available: !!root.retainSelection && !root.confirmation && !root.dismissalConfirmation && !root.retentionConfirmation
                visible: !root.retentionConfirmation
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.prepareRetention()
            }
            GohuText {
                width: parent.width
                visible: !!root.retentionConfirmation
                text: "CONFIRM GENERATION RETENTION // ORIGINAL RECORDS KEPT; SESSION RETIRES; NO EXECUTION UNLOCK"
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }
            Row {
                width: parent.width
                spacing: 3
                visible: !!root.retentionConfirmation
                ActionButton {
                    objectName: "cpuplusRecoveryRetainConfirm"
                    width: Math.max(0,(parent.width-parent.spacing)/2)
                    height: 28
                    label: "CONFIRM"
                    available: Recovery.sameRetention(root.retainSelection,root.retentionConfirmation)
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: root.confirmRetention()
                }
                ActionButton {
                    objectName: "cpuplusRecoveryRetainCancel"
                    width: Math.max(0,(parent.width-parent.spacing)/2)
                    height: 28
                    label: "CANCEL"
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: root.retentionConfirmation=null
                }
            }
        }
        GohuText {
            width: parent.width
            text: "REVIEW UUID // HISTORICAL RECEIPT LOOKUP"
            color: Colors.cyan
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        Rectangle {
            width: parent.width
            height: 27
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan
            TextInput {
                anchors.fill: parent
                anchors.margins: 4
                color: Colors.white
                font.pixelSize: 10
                maximumLength: 36
                clip: true
                readOnly: !!root.unknownReviewId
                text: root.effectiveReceiptId
                onTextEdited: root.receiptLookup=text
            }
        }
        ActionButton {
            objectName: "cpuplusRecoveryReceiptLookup"
            width: parent.width
            height: 28
            label: "LOOK UP RECEIPT"
            available: root.reviewAvailable && Recovery.uuid(root.effectiveReceiptId)
            acceptedButtons: Qt.LeftButton
            keyboardActivationSignal: "leftClicked"
            onLeftClicked: root.lookupReceipt()
        }
        GohuText {
            width: parent.width
            text: root.reviewReceipt ? "HISTORICAL RECEIPT // REVIEW ACKNOWLEDGED ONLY\nREVIEW // "+root.reviewReceipt.reviewId
                +"\nACTION // "+root.reviewReceipt.action.actionId+"\nADJUSTMENT OUTCOME UNVERIFIED"
                : "NO RECEIPT DISPLAYED // NOT PROOF OF NONCOMMIT"
            color: Colors.orange
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WrapAnywhere
        }
    }
    GohuText {
        width: parent.width
        text: "ADJUSTMENT OUTCOME // UNVERIFIED\nLocal commit records queue intent only. Missing records do not establish noncommit. No retry or unlock is available."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
}
