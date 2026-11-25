import QtQuick
import "PublicHistoryDisplay.js" as Shape

// UI2-R1 isolated synthetic review. No live lifecycle, source, query,
// authority, R6 transport, decision or application. Owner independently
// establishes the local fixture lifetime; these correlations are not trust.
Item {
    id: root
    clip: true
    property bool syntheticOwner: false
    property var ownerScope: null
    readonly property bool eligible: visible && syntheticOwner && width >= 300
        && height >= 160 && validScope(ownerScope)
    property var _acceptedScope: null
    property string _state: "CLOSED"
    property var _rows: []
    property var _usedViews: ({})
    property int _viewCount: 0
    readonly property string reviewState: eligible && sameScope(_acceptedScope, ownerScope)
        ? _state : "CLOSED"
    readonly property var reviewRows: reviewState === "DISPLAYING" ? _rows : []
    readonly property bool sourceAuthenticated: false
    readonly property bool permissionGranted: false
    readonly property bool productionAuthority: false
    readonly property bool modelExecutionPermitted: false
    readonly property bool restorationEnabled: false
    readonly property bool sendEnabled: false
    readonly property bool stopEnabled: false

    // Explicit dismissal notification after local state is fully retired.
    // Consumers must pin the original ref; derived state changes are not intent.
    signal reviewDismissed(var ref)

    function token(value) {
        return typeof value === "string" && value.length === 32 && /^[0-9a-f]{32}$/.test(value);
    }
    function validScope(ref) {
        return Shape.exact(ref, ["treeKey","taskAlias","viewKey","planRevision"])
            && ref.treeKey === "CHERRY" && token(ref.taskAlias) && token(ref.viewKey)
            && ref.taskAlias !== ref.viewKey && Shape.integer(ref.planRevision,1);
    }
    function sameScope(a,b) {
        return validScope(a) && validScope(b) && a.treeKey === b.treeKey
            && a.taskAlias === b.taskAlias && a.viewKey === b.viewKey
            && a.planRevision === b.planRevision;
    }
    // Qt refuses to turn off activeFocusOnTab while the item holds active
    // focus. Retire local focus before removing tab eligibility; host focus
    // restoration remains the existing panel owner's responsibility.
    function releaseDismissFocus() {
        if (!dismiss) return;
        dismiss.focus = false;
        dismiss.activeFocusOnTab = false;
    }
    function syncDismissFocus() {
        if (!dismiss) return;
        if (eligible && reviewState !== "CLOSED")
            dismiss.activeFocusOnTab = true;
        else
            releaseDismissFocus();
    }
    onReviewStateChanged: syncDismissFocus()
    Component.onCompleted: syncDismissFocus()
    function clear() {
        releaseDismissFocus();
        _rows = [];
        _acceptedScope = null;
        _state = "CLOSED";
    }
    function observeOwner() {
        if (!eligible || !sameScope(_acceptedScope,ownerScope))
            clear();
    }
    onOwnerScopeChanged: observeOwner()
    onEligibleChanged: observeOwner()

    // Explicit open; owner must replace the whole scope object.
    // Bounded replay fence is local to this component lifetime, not custody.
    function openReview(ref) {
        if (!eligible || !sameScope(ref,ownerScope)
                || _usedViews[ref.viewKey] || _viewCount >= 64)
            return false;
        clear();
        _usedViews[ref.viewKey] = true;
        ++_viewCount;
        _acceptedScope = {treeKey:ref.treeKey,taskAlias:ref.taskAlias,
            viewKey:ref.viewKey,planRevision:ref.planRevision};
        _state = "PENDING";
        return reviewState === "PENDING";
    }
    function matching(ref) {
        return eligible && sameScope(ref,_acceptedScope) && sameScope(ref,ownerScope);
    }
    function refuseReview(ref) {
        if (!matching(ref)) return false;
        _rows = [];
        _state = "UNAVAILABLE";
        return true;
    }
    // Fixed finite fixture allowlist, exact order, no arbitrary payload text.
    // Construct display rows from local constants only after whole validation.
    function receiveReview(ref, rows) {
        if (!matching(ref)) return false;
        const expected = [
            {category:"CONTINUITY",state:"PRESERVED",label:"Continuity"},
            {category:"CONTEXT",state:"REVIEW",label:"Context"},
            {category:"WORKSHOP",state:"AVAILABLE",label:"Workshop"},
            {category:"MODEL_FORM",state:"DORMANT",label:"Model Form"},
            {category:"REASONING",state:"UNKNOWN",label:"Reasoning"}
        ];
        if (_state !== "PENDING" || !Array.isArray(rows) || rows.length !== expected.length) {
            refuseReview(ref);
            return false;
        }
        for (let i=0;i<expected.length;i++) {
            if (!Shape.exact(rows[i],["category","state"])
                    || rows[i].category !== expected[i].category
                    || rows[i].state !== expected[i].state) {
                refuseReview(ref);
                return false;
            }
        }
        _rows = expected;
        _state = "DISPLAYING";
        return reviewState === "DISPLAYING";
    }
    function dismissReview(ref) {
        if (!matching(ref)) return false;
        const original = _acceptedScope;
        clear();
        reviewDismissed(original);
        return true;
    }
    function stateColor(state) {
        if (state === "PRESERVED" || state === "AVAILABLE") return "#9ECE6A";
        if (state === "REVIEW") return "#ED981A";
        if (state === "DORMANT") return "#55CFCA";
        return "#AAAAAA";
    }

    Column {
        id: body
        objectName: "restorationReviewBody"
        anchors.fill: parent
        anchors.margins: 5
        spacing: 3
        visible: root.eligible && root.reviewState !== "CLOSED"
        Row {
            width: parent.width
            height: 20
            spacing: 4
            Text {
                width: parent.width - dismiss.width - parent.spacing
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "SPRING // CLEANING REVIEW"
                textFormat: Text.PlainText
                elide: Text.ElideRight
                color: "#9ECE6A"
                font.pixelSize: 11
            }
            Rectangle {
                id: dismiss
                objectName: "restorationReviewDismiss"
                width: 58
                height: 20
                color: "transparent"
                border.color: activeFocus ? "#55CFCA" : "#ED981A"
                activeFocusOnTab: false
                Accessible.role: Accessible.Button
                Accessible.name: "Dismiss review"
                Accessible.onPressAction: root.dismissReview(root._acceptedScope)
                Text {
                    anchors.centerIn: parent
                    text: "DISMISS"
                    color: "#ED981A"
                    font.pixelSize: 10
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: root.dismissReview(root._acceptedScope)
                }
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter
                            || event.key === Qt.Key_Space || event.key === Qt.Key_Escape) {
                        event.accepted = true;
                        root.dismissReview(root._acceptedScope);
                    }
                }
            }
        }
        Text {
            objectName: "restorationReviewSynthetic"
            width: parent.width
            height: 14
            text: "SYNTHETIC // NO LIVE SEASON OR AVAILABILITY"
            textFormat: Text.PlainText
            color: "#ED981A"
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        Repeater {
            model: root.reviewRows
            delegate: Item {
                required property var modelData
                width: body.width
                height: 14
                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: parent.modelData.label
                    textFormat: Text.PlainText
                    color: "#FFFFFF"
                    font.pixelSize: 11
                }
                Text {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: parent.modelData.state
                    textFormat: Text.PlainText
                    color: root.stateColor(parent.modelData.state)
                    font.pixelSize: 10
                }
            }
        }
        Text {
            visible: root.reviewState !== "DISPLAYING"
            width: parent.width
            height: 14
            text: root.reviewState === "PENDING" ? "REVIEW PENDING" : "REVIEW UNAVAILABLE"
            textFormat: Text.PlainText
            color: "#ED981A"
            font.pixelSize: 10
        }
        Text {
            objectName: "restorationReviewLocked"
            width: parent.width
            height: 14
            text: "READ ONLY // RESTORATION LOCKED"
            textFormat: Text.PlainText
            color: "#ED981A"
            font.pixelSize: 10
        }
    }
}
