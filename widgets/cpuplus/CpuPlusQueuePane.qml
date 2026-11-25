import QtQuick
import "../../components"
import "CpuPlusQueuePresentation.js" as QueueView
import "CpuPlusQueueConsumer.js" as Consumer

// R2c display and explicit confirmation seam. Session host owns pending actions;
// the demand-loaded pane retains only an unsubmitted preparation.
Column {
    id: root
    objectName: "cpuplusQueuePane"
    required property var observedDiskKiB
    required property int capacityTargetGiB
    property var runtimeProjection: null
    // Atomic host-owned view: {state: Consumer state, projection: R1 packet}.
    // Null in production until transport, lifecycle and history review.
    property var actionContext: null
    readonly property var session: actionContext ? actionContext.state : null
    readonly property var display: QueueView.project(actionContext
        ? (session && session.status ? actionContext.projection : null) : runtimeProjection)
    readonly property bool sessionUsable: usableContext(actionContext)
    function usableContext(context) {
        if (!context || !context.state || !context.projection) return false;
        const current = context.state;
        const view = QueueView.project(context.projection);
        return !!(current.status && !current.pending && !current.unresolved
            && current.status.state === view.state && current.status.requestId === view.requestId
            && current.status.targetGiB === view.targetGiB && current.status.canExecute === false
            && view.canExecute === false && view.outcome === "UNVERIFIED"
            && context.projection.status && current.status.code === context.projection.status.code);
    }
    property var preparation: null
    property var submitted: null
    property string expiryText: ""
    signal intentConfirmed(var intent)
    onActionContextChanged: {
        preparation = null;
        // A new, correlated host snapshot or pending/uncertain state can
        // supersede the local click latch; a same-revision echo cannot.
        // Use the new input directly: the derived session binding may not
        // have re-evaluated when this QML change signal fires.
        const current = actionContext ? actionContext.state : null;
        if (submitted && current && (current.ownerId !== submitted.ownerId
                || current.sequence > submitted.statusSequence || current.pending || current.unresolved))
            submitted = null;
    }
    onVisibleChanged: if (!visible) preparation = null
    onCapacityTargetGiBChanged: preparation = null
    onObservedDiskKiBChanged: preparation = null
    onExpiryTextChanged: preparation = null

    function expirySeconds(value) {
        if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(value)) return null;
        const iso = value.replace(" ","T") + ":00.000Z";
        const ms = Date.parse(iso);
        if (!Number.isFinite(ms) || ms <= 0 || new Date(ms).toISOString() !== iso) return null;
        return ms / 1000;
    }
    function candidate(kind) {
        const context = actionContext;
        if (!visible || submitted || !usableContext(context)) return null;
        const current = context.state;
        const hasTarget = kind === "QUEUE" || kind === "REPLACE";
        // This is only a UI bound. DOC 4 must validate exact current base target,
        // independent identities, expiry and supported withdrawal scope.
        if (hasTarget && (!Number.isSafeInteger(observedDiskKiB)
                || capacityTargetGiB * 1048576 >= observedDiskKiB)) return null;
        const result = Consumer.prepare(current,kind,
            hasTarget ? capacityTargetGiB : null, hasTarget ? expirySeconds(expiryText) : null);
        return result !== current ? result.prepared : null;
    }
    function prepareIntent(kind) {
        if (preparation) return;
        const next = candidate(kind);
        if (next) preparation = next;
    }
    function cancelIntent() { preparation = null; }
    function confirmIntent() {
        const frozen = preparation;
        if (!frozen) return;
        const current = candidate(frozen.kind);
        if (!current || ["ownerId","statusSequence","actionSequence","kind","expectedId","targetGiB","expiresAt"]
                .some(key=>frozen[key] !== current[key])) {
            preparation = null;
            return;
        }
        // One explicit signal only. The external host must synchronously
        // revalidate the preparation, establish pending state and supply a
        // fresh action ID through Consumer.submit before any transport send.
        submitted = frozen;
        preparation = null;
        intentConfirmed(Object.assign({},frozen));
    }
    spacing: 6
    GohuText {
        width: parent.width
        text: "AUTO // DEFERRED ADJUSTMENTS"
        color: Colors.magenta
        font.pixelSize: 12
    }
    GohuText {
        width: parent.width
        text: "NOTIFY ONLY // PROTECTED EXECUTION HOLD"
        color: Colors.orange
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: [
            {label:"OBSERVED MANAGED DISK",value:QueueView.gib(root.observedDiskKiB),accent:Colors.cyan},
            {label:"CAP TARGET // NOT QUEUED",value:root.capacityTargetGiB + " GiB",accent:Colors.yellow},
            {label:"QUEUE STATUS",value:root.display.state,accent:Colors.orange},
            {label:"ADJUSTMENT OUTCOME",value:root.display.outcome,accent:Colors.orange}
        ]
        delegate: Rectangle {
            required property var modelData
            width: root.width
            height: tileBody.implicitHeight + 8
            color: Colors.black
            border.width: 1
            border.color: modelData.accent
            Column {
                id: tileBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 4
                spacing: 2
                GohuText {
                    width: parent.width
                    text: modelData.label
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: modelData.value
                    textFormat: Text.PlainText
                    color: modelData.accent
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
    GohuText {
        width: parent.width
        text: root.display.reason
        color: Colors.white
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    Column {
        width: parent.width
        spacing: 4
        visible: root.display.requestId !== null
        GohuText {
            width: parent.width
            text: "REQUEST // " + (root.display.requestId || "")
            color: Colors.cyan
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "AT REQUEST // " + QueueView.gib(root.display.originalActualKiB)
                + "\nREQUESTED TARGET // " + root.display.targetGiB + " GiB"
                + "\nLAST CHECK // " + QueueView.timestamp(root.display.checkedAt)
                + "\nEXPIRY // " + QueueView.timestamp(root.display.expiresAt)
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: root.display.scheduled ? "NEXT CHECK // OWNER REPORTED SCHEDULE"
                : "NEXT CHECK // NOT SCHEDULED IN REPORT"
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
    }
    GohuText {
        width: parent.width
        visible: root.display.notificationIssue
        text: "NOTIFICATION STAGING ISSUE // DELIVERY UNVERIFIED"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: !root.actionContext ? "REQUEST CONTROLS // TRANSPORT NOT CONNECTED"
            : root.session && root.session.unresolved ? "OUTCOME UNKNOWN // REVIEW HISTORY"
            : root.session && root.session.pending ? "ACTION PENDING // WAIT FOR RESPONSE"
            : root.submitted ? "ACTION SUBMITTED // WAIT FOR HOST"
            : root.sessionUsable ? "REQUEST CONTROLS // EXPLICIT INTENT ONLY"
            : "FRESH OWNER STATUS REQUIRED"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: "EXPIRY // UTC (YYYY-MM-DD HH:MM)"
        color: Colors.cyan
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Rectangle {
        width: parent.width
        height: 30
        color: Colors.black
        border.width: 1
        border.color: root.sessionUsable && !root.submitted ? Colors.cyan : Colors.orange
        TextInput {
            id: expiryEditor
            objectName: "cpuplusQueueExpiry"
            anchors.fill: parent
            anchors.margins: 4
            text: root.expiryText
            readOnly: !root.sessionUsable || !!root.preparation || !!root.submitted
            selectByMouse: true
            maximumLength: 16
            color: Colors.white
            font.pixelSize: 11
            verticalAlignment: TextInput.AlignVCenter
            onTextEdited: root.expiryText = text
        }
    }
    Grid {
        width: parent.width
        columns: 2
        spacing: 4
        Repeater {
            model: ["QUEUE","REPLACE","CANCEL","RECHECK","EXPIRE"]
            delegate: ActionButton {
                required property string modelData
                objectName: "cpuplusQueueAction" + modelData
                width: Math.max(0,(root.width-4)/2)
                height: 28
                label: modelData
                contentPadding: 2
                available: !root.preparation && root.candidate(modelData) !== null
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.prepareIntent(modelData)
            }
        }
    }
    Column {
        width: parent.width
        spacing: 4
        visible: root.preparation !== null
        GohuText {
            width: parent.width
            text: root.preparation ? "CONFIRM " + root.preparation.kind
                + "\nREQUEST // " + (root.preparation.expectedId || "NEW REQUEST")
                + (root.preparation.targetGiB === null ? "" : "\nTARGET // " + root.preparation.targetGiB
                    + " GiB\nEXPIRY // " + QueueView.timestamp(root.preparation.expiresAt)) : ""
            color: Colors.yellow
            textFormat: Text.PlainText
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "Changes queue intent only. Does not authorize or cancel a kernel operation."
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        Row {
            width: parent.width
            spacing: 4
            ActionButton {
                width: Math.max(0,(root.width-4)/2)
                height: 28
                label: "CONFIRM"
                objectName: "cpuplusQueueConfirm"
                available: root.preparation !== null && root.sessionUsable && !root.submitted
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.confirmIntent()
            }
            ActionButton {
                width: Math.max(0,(root.width-4)/2)
                height: 28
                label: "BACK"
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.cancelIntent()
            }
        }
    }
    GohuText {
        width: parent.width
        text: "QUEUE / REPLACE use the CAP target and explicit expiry. The owner must independently validate the supported base target and source identity."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: "Queue reports are historical advisory evidence, not current readiness or authority. The capacity slider alone never creates a request. No automatic adjustment or notification delivery is connected."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
}
