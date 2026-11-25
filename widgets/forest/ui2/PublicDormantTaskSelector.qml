import QtQuick
import Quickshell
import "PublicHistoryDisplay.js" as Shape

// UI2 R2 fixed-public synthetic fixture only; never mounted by ForestW.
// Local correlation and monotonic expiry are not lifecycle or access proof.
Item {
    id: root
    clip: true
    property bool syntheticOwner: false
    property var ownerScope: null
    property var ownerPlanScope: null
    readonly property bool eligible: visible && syntheticOwner && width >= 300
        && height >= 160 && validScope(ownerScope)
    property var _scope: null
    property var _plan: null
    property var _rows: []
    property string _selection: ""
    property string _state: "CLOSED"
    property var _usedLists: ({})
    property var _usedPlans: ({})
    property int _listCount: 0
    property int _planCount: 0
    property bool _openingReview: false
    readonly property int lifetimeMs: 120000
    readonly property string catalogState: eligible && sameScope(_scope,ownerScope) ? _state : "CLOSED"
    readonly property var catalogRows: catalogState === "DISPLAYING" && !_plan ? _rows : []
    readonly property string selectedAlias: catalogState === "DISPLAYING" ? _selection : ""
    readonly property string reviewState: _plan && eligible ? review.reviewState : "CLOSED"
    readonly property var reviewRows: _plan && eligible ? review.reviewRows : []
    readonly property bool sourceAuthenticated: false
    readonly property bool permissionGranted: false
    readonly property bool productionAuthority: false
    readonly property bool modelExecutionPermitted: false
    readonly property bool restorationEnabled: false
    readonly property bool sendEnabled: false
    readonly property bool stopEnabled: false
    signal dismissed()
    ElapsedTimer { id: clock }
    Timer {
        id: expiry
        repeat: false
        interval: root.lifetimeMs
        onTriggered: {
            if (!root._scope) return;
            const elapsed=clock.elapsedMs();
            if (!root.observeElapsed(root._scope,elapsed)) {
                interval=Math.max(1,root.lifetimeMs-elapsed);
                start();
            }
        }
    }
    function token(v) {
        return typeof v==="string" && v.length===32 && /^[0-9a-f]{32}$/.test(v);
    }
    function validScope(s) {
        return Shape.exact(s,["treeKey","viewKey","catalogRevision"]) && s.treeKey==="CHERRY"
            && token(s.viewKey) && Shape.integer(s.catalogRevision,1);
    }
    function sameScope(a,b) {
        return validScope(a) && validScope(b) && a.treeKey===b.treeKey
            && a.viewKey===b.viewKey && a.catalogRevision===b.catalogRevision;
    }
    function validPlan(p) {
        return review.validScope(p);
    }
    function samePlan(a,b) {
        return review.sameScope(a,b);
    }
    function retireReview(returnFocus=false) {
        _plan=null;
        if (returnFocus && eligible && catalogState==="DISPLAYING" && reviewButton.visible)
            reviewButton.forceActiveFocus();
    }
    function clear() {
        // Retire focused local controls before hiding them.
        for (let i=0;choices && i<choices.count;i++) {
            const item=choices.itemAt(i);
            if (item) item.releaseFocus();
        }
        if (reviewButton) reviewButton.releaseFocus();
        if (closeButton) closeButton.releaseFocus();
        if (expiry) expiry.stop();
        retireReview();
        _selection="";
        _rows=[];
        _scope=null;
        _state="CLOSED";
    }
    function observeOwner() {
        if (!eligible || !sameScope(_scope,ownerScope)) clear();
    }
    onOwnerScopeChanged: observeOwner()
    onEligibleChanged: observeOwner()
    onOwnerPlanScopeChanged: {
        if (_plan && !samePlan(_plan,ownerPlanScope)) retireReview();
    }
    // An observed elapsed duration can only retire the matching original.
    // The native timer uses the local monotonic clock; the deterministic
    // fixture also exercises the boundary without waiting 120 seconds.
    function observeElapsed(ref,elapsed) {
        if (!sameScope(ref,_scope) || !sameScope(ref,ownerScope)
                || !Shape.integer(elapsed,0) || elapsed<lifetimeMs) return false;
        clear();
        return true;
    }
    function current(ref) {
        if (!eligible || !sameScope(ref,_scope) || !sameScope(ref,ownerScope)) return false;
        if (clock.elapsedMs()>=lifetimeMs) { clear(); return false; }
        return true;
    }
    function openCatalog(ref) {
        if (!eligible || !sameScope(ref,ownerScope) || _usedLists[ref.viewKey]
                || _usedPlans[ref.viewKey] || _listCount>=64) return false;
        clear();
        _usedLists[ref.viewKey]=true;
        ++_listCount;
        _scope={treeKey:ref.treeKey,viewKey:ref.viewKey,catalogRevision:ref.catalogRevision};
        clock.restartMs();
        expiry.interval=lifetimeMs;
        expiry.start();
        _state="PENDING";
        return catalogState==="PENDING";
    }
    function refuseCatalog(ref) {
        if (!current(ref)) return false;
        retireReview();
        _selection="";
        _rows=[];
        _state="UNAVAILABLE";
        return true;
    }
    function receiveCatalog(ref,rows) {
        if (!current(ref)) return false;
        if (_state!=="PENDING" || !Array.isArray(rows) || rows.length>3) {
            refuseCatalog(ref); return false;
        }
        const next=[];
        for (let i=0;i<rows.length;i++) {
            const row=rows[i];
            if (!Shape.exact(row,["taskAlias"]) || !token(row.taskAlias)
                    || row.taskAlias===ref.viewKey || next.some(x=>x.taskAlias===row.taskAlias)) {
                refuseCatalog(ref); return false;
            }
            next.push({taskAlias:row.taskAlias,label:"PUBLIC TASK "+(i+1)});
        }
        _rows=next;
        _state=next.length?"DISPLAYING":"EMPTY";
        return true;
    }
    function selectTask(ref,alias) {
        if (!current(ref) || _state!=="DISPLAYING" || !token(alias)
                || !_rows.some(x=>x.taskAlias===alias)) return false;
        if (_selection!==alias) {
            retireReview();
            _selection=alias;
        }
        return true;
    }
    function openReview(ref,plan) {
        if (!current(ref) || _state!=="DISPLAYING" || !_selection || _plan
                || !validPlan(plan) || !samePlan(plan,ownerPlanScope)
                || plan.taskAlias!==_selection || _usedLists[plan.viewKey]
                || _usedPlans[plan.viewKey] || _planCount>=64) return false;
        _usedPlans[plan.viewKey]=true;
        ++_planCount;
        _openingReview=true;
        _plan={treeKey:plan.treeKey,taskAlias:plan.taskAlias,viewKey:plan.viewKey,
            planRevision:plan.planRevision};
        const ok=review.openReview(_plan);
        _openingReview=false;
        if (!ok || !current(ref) || !samePlan(_plan,ownerPlanScope)) {
            retireReview();
            return false;
        }
        return true;
    }
    function receivePlan(ref,plan,rows) {
        if (!current(ref) || !samePlan(plan,_plan) || !samePlan(plan,ownerPlanScope))
            return false;
        return review.receiveReview(plan,rows);
    }
    function dismissPlan(ref,plan) {
        if (!current(ref) || !samePlan(plan,_plan) || !samePlan(plan,ownerPlanScope))
            return false;
        return review.dismissReview(plan);
    }
    function dismissCatalog(ref) {
        if (!current(ref)) return false;
        clear();
        dismissed();
        return true;
    }

    // Controls remain instantiated across catalog changes. A press captures
    // its exact scope/alias/plan, so release cannot select a replacement row.
    component LocalButton: Rectangle {
        id: control
        property string label: ""
        property var intent: null
        property bool usable: false
        property var pressedIntent: null
        signal invoked(var intent)
        color: "transparent"
        border.color: activeFocus ? "#55CFCA" : "#ED981A"
        activeFocusOnTab: false
        enabled: usable && visible
        function releaseFocus() {
            focus=false;
            activeFocusOnTab=false;
            pressedIntent=null;
        }
        function syncFocus() {
            if (enabled) activeFocusOnTab=true;
            else releaseFocus();
        }
        onEnabledChanged: syncFocus()
        Component.onCompleted: syncFocus()
        Accessible.role: Accessible.Button
        Accessible.name: label
        Accessible.onPressAction: if (enabled && intent) invoked(intent)
        Text {
            anchors.fill: parent
            anchors.margins: 3
            text: control.label
            color: control.enabled ? "#FFFFFF" : "#777777"
            font.pixelSize: 10
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
        MouseArea {
            anchors.fill: parent
            enabled: control.enabled
            onPressed: control.pressedIntent=control.intent
            onCanceled: control.pressedIntent=null
            onClicked: {
                const pin=control.pressedIntent;
                control.pressedIntent=null;
                if (control.enabled && pin) control.invoked(pin);
            }
        }
        Keys.onPressed: function(event) {
            if (enabled && intent && (event.key===Qt.Key_Return || event.key===Qt.Key_Enter
                    || event.key===Qt.Key_Space)) {
                event.accepted=true;
                invoked(intent);
            }
        }
    }
    Column {
        id: listBody
        objectName: "dormantCatalogBody"
        anchors.fill: parent
        anchors.margins: 5
        spacing: 3
        visible: root.catalogState!=="CLOSED" && !root._plan
        Row {
            width: parent.width; height: 20; spacing: 4
            Text {
                width: parent.width-closeButton.width-parent.spacing
                height: parent.height
                text: "WINTER // DORMANT TASKS"
                textFormat: Text.PlainText
                color: "#55CFCA"; font.pixelSize: 11
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            LocalButton {
                id: closeButton
                objectName: "dormantCatalogDismiss"
                width: 58; height: 20; label: "DISMISS"
                usable: listBody.visible
                intent: root._scope
                onInvoked: pin=>root.dismissCatalog(pin)
            }
        }
        Text {
            width: parent.width; height: 14
            text: "SYNTHETIC // NO LIVE DORMANCY"
            textFormat: Text.PlainText
            color: "#ED981A"; font.pixelSize: 10
        }
        Repeater {
            id: choices
            model: 3
            LocalButton {
                required property int index
                objectName: "dormantChoice"+index
                readonly property var entry: root.catalogRows[index] || null
                width: listBody.width; height: visible?20:0
                visible: entry!==null
                usable: listBody.visible && entry!==null
                label: entry ? entry.label+(root.selectedAlias===entry.taskAlias?" // SELECTED":"") : ""
                intent: entry ? {scope:root._scope,alias:entry.taskAlias} : null
                onInvoked: pin=>root.selectTask(pin.scope,pin.alias)
            }
        }
        Text {
            width: parent.width; height: visible?14:0
            visible: root.catalogState!=="DISPLAYING"
            text: root.catalogState==="PENDING"?"CATALOG PENDING":
                root.catalogState==="EMPTY"?"NO PUBLIC FIXTURE TASKS":"CATALOG UNAVAILABLE"
            textFormat: Text.PlainText
            color: "#ED981A"; font.pixelSize: 10
        }
        LocalButton {
            id: reviewButton
            objectName: "dormantOpenReview"
            width: listBody.width; height: 20
            visible: root.catalogState==="DISPLAYING"
            label: "OPEN CLEANING REVIEW"
            usable: listBody.visible && !!root.selectedAlias && root.validPlan(root.ownerPlanScope)
                && root.ownerPlanScope.taskAlias===root.selectedAlias
            intent: {scope:root._scope,plan:root.ownerPlanScope}
            onInvoked: pin=>root.openReview(pin.scope,pin.plan)
        }
        Text {
            width: parent.width; height: 14
            text: "READ ONLY // RESTORATION LOCKED"
            textFormat: Text.PlainText
            color: "#ED981A"; font.pixelSize: 10
        }
    }
    PublicRestorationReview {
        id: review
        anchors.fill: parent
        visible: root.eligible && root._plan!==null
        syntheticOwner: root.syntheticOwner
        ownerScope: root._plan ? root.ownerPlanScope : null
        onReviewStateChanged: {
            if (!root._openingReview && root._plan && reviewState==="CLOSED")
                root.retireReview(root.eligible && root.sameScope(root._scope,root.ownerScope)
                    && root.samePlan(root._plan,root.ownerPlanScope));
        }
    }
}
