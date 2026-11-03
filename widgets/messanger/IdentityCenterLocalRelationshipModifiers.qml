import QtQuick
import "../../components"

// One in-place modifier form for existing local organization relationships.
// The four original private writers remain the sole source of validation.
// This is not an authenticated tenant, workforce, or provider access selector.
Column {
    id: editor
    property var directoryStore: null
    property var structureStore: null
    property var functionLocationStore: null
    property var branchLocationStore: null
    property var reportingStore: null
    property var socialLinksStore: null
    property var identitiesSnapshot: null
    property var accountDetailsStore: null

    property string selectedOrgId: ""
    // Parent page may supply the same local editing focus used by Structure.
    property bool useSharedContext: false
    property string selectedSourceId: ""
    property string selectedSourceKind: ""
    property string modifier: "location"
    property string selectedTargetId: ""
    property string selectedServiceId: ""
    property string selectedAccountId: ""
    property string subjectQuery: ""
    property string confirmUnlinkKey: ""
    property bool showAll: false
    spacing: 9

    readonly property bool directoryReady:
        directoryStore !== null && directoryStore.state === "ready"
    readonly property bool structureReady:
        structureStore !== null && structureStore.state === "ready"
    readonly property var organizations: directoryReady
        ? directoryStore.saved.organizations : []
    readonly property var activeOrganizations:
        organizations.filter(function(org) { return !org.archived; })
    readonly property var selectedOrg:
        activeOrganizations.find(function(org) {
            return org.id === editor.selectedOrgId;
        }) || null
    readonly property var allUnits: structureReady
        ? structureStore.saved.units : []
    readonly property var functions:
        allUnits.filter(function(unit) {
            return unit.orgId === editor.selectedOrgId
                && unit.kind !== "location" && !unit.archived;
        })
    readonly property var locations:
        allUnits.filter(function(unit) {
            return unit.orgId === editor.selectedOrgId
                && unit.kind === "location" && !unit.archived;
        })
    readonly property var subjects: selectedOrg
        ? [{id:selectedOrg.id, kind:"organization",
            name:"ORGANIZATION // " + selectedOrg.name}]
            .concat(selectedOrg.branches.filter(function(branch) {
                return !branch.archived;
            }).map(function(branch) {
                return {id:branch.id, kind:"branch",
                        name:"BRANCH // " + branch.name};
            }))
            .concat(functions.map(function(unit) {
                return {id:unit.id, kind:"function",
                        name:unit.kind.toUpperCase() + " // " + unit.name};
            }))
        : []
    readonly property var visibleSubjects:
        subjects.filter(function(item) {
            return item.name.toLowerCase().indexOf(
                editor.subjectQuery.trim().toLowerCase()) !== -1;
        })
    readonly property var selectedSource:
        subjects.find(function(item) {
            return item.id === editor.selectedSourceId
                && item.kind === editor.selectedSourceKind;
        }) || null
    readonly property var identities:
        identitiesSnapshot && identitiesSnapshot.writable
        && Array.isArray(identitiesSnapshot.identities)
        ? identitiesSnapshot.identities : []
    readonly property var targets:
        modifier === "location" ? locations.map(function(unit) {
            return {id:unit.id, name:unit.name};
        }) : modifier === "reporting" ? functions.filter(function(unit) {
            return unit.id !== editor.selectedSourceId;
        }).map(function(unit) {
            return {id:unit.id, name:unit.kind.toUpperCase() + " // " + unit.name};
        }) : identities.map(function(identity) {
            return {id:identity.id, name:identity.name};
        })
    readonly property var availableServices:
        modifier === "social" && selectedTargetId !== ""
        && accountDetailsStore && accountDetailsStore.state === "ready"
        ? Object.keys(accountDetailsStore.recordFor(selectedTargetId).accounts || {})
            .filter(function(service) {
                return accountDetailsStore.accountNamesFor(
                    editor.selectedTargetId, service).length > 0;
            }).sort()
        : []
    readonly property var availableAccounts:
        accountDetailsStore && accountDetailsStore.state === "ready"
        && availableServices.includes(selectedServiceId)
        ? accountDetailsStore.accountNamesFor(selectedTargetId, selectedServiceId)
        : []
    readonly property var currentStore:
        modifier === "location"
        ? selectedSourceKind === "branch" ? branchLocationStore
          : functionLocationStore
        : modifier === "reporting" ? reportingStore : socialLinksStore
    readonly property var savedEntries:
        items(functionLocationStore, "function-location")
        .concat(items(branchLocationStore, "branch-location"))
        .concat(items(reportingStore, "reporting"))
        .concat(items(socialLinksStore, "social"))
    readonly property bool validSelection:
        directoryReady && structureReady && selectedOrg !== null
        && selectedSource !== null
        && allowed(modifier)
        && targets.some(function(target) {
            return target.id === editor.selectedTargetId;
        })
        && currentStore !== null && currentStore.state === "ready"
        && !alreadyLinked() && !wouldCycle()

    onSelectedOrgIdChanged: {
        selectedSourceId = "";
        selectedSourceKind = "";
        selectedTargetId = "";
        selectedServiceId = "";
        selectedAccountId = "";
        confirmUnlinkKey = "";
    }

    function items(store, kind) {
        return store && store.saved && Array.isArray(store.saved.links)
            ? store.saved.links.map(function(link) {
                return Object.assign({type:kind, key:kind + ":" + link.id}, link);
            }) : [];
    }
    function chooseSource(item) {
        selectedSourceId = item.id;
        selectedSourceKind = item.kind;
        modifier = item.kind === "organization" ? "social" : "location";
        selectedTargetId = "";
        selectedServiceId = "";
        selectedAccountId = "";
        confirmUnlinkKey = "";
    }
    function chooseModifier(name) {
        if (!allowed(name)) return;
        modifier = name;
        selectedTargetId = "";
        selectedServiceId = "";
        selectedAccountId = "";
    }
    function allowed(name) {
        if (!selectedSource) return false;
        if (name === "social")
            return selectedSourceKind === "organization"
                   || selectedSourceKind === "branch";
        if (name === "reporting")
            return selectedSourceKind === "function";
        if (name === "location")
            return selectedSourceKind === "branch"
                   || selectedSourceKind === "function";
        return false;
    }
    function alreadyLinked() {
        if (!selectedSource || !selectedTargetId || !currentStore
                || !currentStore.saved) return false;
        return currentStore.saved.links.some(function(link) {
            if (link.orgId !== editor.selectedOrgId) return false;
            if (modifier === "location" && selectedSourceKind === "branch")
                return link.branchId === editor.selectedSourceId
                    && link.locationId === editor.selectedTargetId;
            if (modifier === "location")
                return link.functionId === editor.selectedSourceId
                    && link.locationId === editor.selectedTargetId;
            if (modifier === "reporting")
                return link.childId === editor.selectedSourceId
                    && link.parentId === editor.selectedTargetId;
            if (modifier === "social")
                return link.branchId ===
                    (selectedSourceKind === "branch" ? editor.selectedSourceId : null)
                    && link.identityId === editor.selectedTargetId
                    && link.serviceId ===
                    (editor.selectedAccountId ? editor.selectedServiceId : null)
                    && link.accountId ===
                    (editor.selectedAccountId ? editor.selectedAccountId : null);
            return false;
        });
    }
    function wouldCycle() {
        if (modifier !== "reporting" || !selectedSourceId
                || !selectedTargetId || !reportingStore
                || !reportingStore.saved) return false;
        const seen = {};
        const pending = [selectedSourceId];
        while (pending.length > 0) {
            const current = pending.pop();
            if (current === selectedTargetId) return true;
            if (seen[current]) continue;
            seen[current] = true;
            reportingStore.saved.links.forEach(function(link) {
                if (link.orgId === editor.selectedOrgId
                        && link.parentId === current)
                    pending.push(link.childId);
            });
        }
        return false;
    }
    function applyModifier() {
        if (!validSelection) return false;
        if (modifier === "location" && selectedSourceKind === "branch")
            return branchLocationStore.linkBranch(
                selectedOrgId, selectedSourceId, selectedTargetId);
        if (modifier === "location")
            return functionLocationStore.linkToLocation(
                selectedOrgId, selectedSourceId, selectedTargetId);
        if (modifier === "reporting")
            return reportingStore.addRelationship(
                selectedOrgId, selectedTargetId, selectedSourceId);
        const branchId = selectedSourceKind === "branch" ? selectedSourceId : null;
        if (selectedAccountId)
            return socialLinksStore.linkAccountLabel(
                selectedOrgId, branchId, selectedTargetId,
                selectedServiceId, selectedAccountId);
        return socialLinksStore.linkIdentity(selectedOrgId, branchId, selectedTargetId);
    }
    function orgFor(id) {
        return organizations.find(function(org) { return org.id === id; }) || null;
    }
    function unitFor(id) {
        return allUnits.find(function(unit) { return unit.id === id; }) || null;
    }
    function branchFor(link) {
        const org = orgFor(link.orgId);
        return org ? org.branches.find(function(b) {
            return b.id === link.branchId;
        }) || null : null;
    }
    function unitLabel(id) {
        const unit = unitFor(id);
        return unit ? unit.kind.toUpperCase() + " " + unit.name
                   + (unit.archived ? " [ARCHIVED]" : "")
                    : "MISSING UNIT (" + id + ")";
    }
    function branchLabel(link) {
        const branch = branchFor(link);
        return branch ? "BRANCH " + branch.name
                + (branch.archived ? " [ARCHIVED]" : "")
                : "MISSING BRANCH (" + link.branchId + ")";
    }
    function identityLabel(id) {
        const found = identities.find(function(identity) {
            return identity.id === id;
        });
        return found ? found.name : "MISSING SOCIAL IDENTITY (" + id + ")";
    }
    function describe(link) {
        const org = orgFor(link.orgId);
        const prefix = org ? org.name + (org.archived ? " [ARCHIVED]" : "")
                           : "MISSING ORGANIZATION";
        if (link.type === "function-location")
            return prefix + " // " + unitLabel(link.functionId) + " LOCATED AT "
                + unitLabel(link.locationId);
        if (link.type === "branch-location")
            return prefix + " // " + branchLabel(link) + " LOCATED AT "
                + unitLabel(link.locationId);
        if (link.type === "reporting")
            return prefix + " // " + unitLabel(link.childId) + " REPORTS TO "
                + unitLabel(link.parentId);
        const source = link.branchId === null
                ? "ORGANIZATION" : branchLabel(link);
        let account = "";
        if (link.serviceId !== null) {
            const available = accountDetailsStore
                    && accountDetailsStore.state === "ready"
                    ? accountDetailsStore.accountNamesFor(
                        link.identityId, link.serviceId) : [];
            const found = available.find(function(item) {
                return item.id === link.accountId;
            });
            account = " / " + link.serviceId.toUpperCase() + " / "
                + (found ? found.label : "MISSING ACCOUNT NICKNAME");
        }
        return prefix + " // " + source + " SOCIAL LABEL "
            + identityLabel(link.identityId) + account;
    }
    function current(link) {
        const org = orgFor(link.orgId);
        if (!org || org.archived) return false;
        if (link.type === "social") {
            const branch = link.branchId === null ? null : branchFor(link);
            if (link.branchId !== null && (!branch || branch.archived))
                return false;
            if (!identities.some(function(identity) {
                return identity.id === link.identityId;
            })) return false;
            if (link.serviceId === null) return true;
            if (!accountDetailsStore || accountDetailsStore.state !== "ready")
                return false;
            return accountDetailsStore.accountNamesFor(
                link.identityId, link.serviceId).some(function(item) {
                return item.id === link.accountId;
            });
        }
        const target = link.type === "reporting"
            ? unitFor(link.parentId) : unitFor(link.locationId);
        if (!target || target.archived || target.orgId !== link.orgId)
            return false;
        if (link.type === "reporting") {
            const child = unitFor(link.childId);
            return !!(child && !child.archived
                && child.orgId === link.orgId
                && child.kind !== "location" && target.kind !== "location");
        }
        if (target.kind !== "location") return false;
        if (link.type === "branch-location") {
            const branch = branchFor(link);
            return !!(branch && !branch.archived);
        }
        const unit = unitFor(link.functionId);
        return !!(unit && !unit.archived && unit.orgId === link.orgId
                  && unit.kind !== "location");
    }
    function unlink(link) {
        if (link.type === "function-location")
            return functionLocationStore && functionLocationStore.unlinkFromLocation(link.id);
        if (link.type === "branch-location")
            return branchLocationStore && branchLocationStore.unlinkBranch(link.id);
        if (link.type === "reporting")
            return reportingStore && reportingStore.removeRelationship(link.id);
        return socialLinksStore && socialLinksStore.unlink(link.id);
    }
    function storeFor(link) {
        if (link.type === "function-location") return functionLocationStore;
        if (link.type === "branch-location") return branchLocationStore;
        if (link.type === "reporting") return reportingStore;
        return socialLinksStore;
    }
    function reloadLinks() {
        [functionLocationStore, branchLocationStore, reportingStore,
         socialLinksStore].forEach(function(store) {
            if (store && store.state !== "saving") store.refresh();
        });
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.45
    }
    Text {
        width: parent.width
        text: "ORGANIZATION LINKS // APPLY MODIFIER"
        font.pixelSize: 12
        font.bold: true
        color: Colors.cyan
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Choose an organization and what you're modifying. Apply " +
              "LOCATED AT, REPORTS TO or SOCIAL LABEL directly. The same form " +
              "works for existing branches, divisions, departments and teams."
        font.pixelSize: 10
        color: Colors.orange
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: !directoryReady || !structureReady
        text: "ORGANIZATION SOURCE // " +
              (!directoryStore ? "UNAVAILABLE" :
               directoryStore.state === "error" ? directoryStore.errorCode :
               directoryStore.state.toUpperCase()) + " / STRUCTURE // " +
              (!structureStore ? "UNAVAILABLE" :
               structureStore.state === "error" ? structureStore.errorCode :
               structureStore.state.toUpperCase())
        font.pixelSize: 10
        color: Colors.orange
        wrapMode: Text.WordWrap
    }

    Text {
        width: parent.width
        visible: !editor.useSharedContext
        text: "ORGANIZATION"
        font.pixelSize: 10
        font.bold: true
        color: Colors.cyan
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 5
        visible: !editor.useSharedContext
        Repeater {
            model: editor.activeOrganizations
            delegate: ActionButton {
                required property var modelData
                width: Math.min(200, Math.max(110, editor.width - 10))
                height: 29
                label: modelData.name
                labelPixelSize: 9
                selected: editor.selectedOrgId === modelData.id
                onTriggered: editor.selectedOrgId = modelData.id
            }
        }
    }
    Text {
        width: parent.width
        visible: editor.activeOrganizations.length === 0
        text: "Create or restore an organization above first."
        font.pixelSize: 10
        color: Colors.orange
        wrapMode: Text.WordWrap
    }
    Rectangle {
        width: parent.width
        height: 29
        color: Colors.black
        border.color: Colors.cyan
        visible: editor.selectedOrg !== null
        TextInput {
            id: subjectSearch
            anchors.fill: parent
            anchors.margins: 6
            color: Colors.white
            font.pixelSize: 10
            text: editor.subjectQuery
            onTextChanged: editor.subjectQuery = text
            clip: true
            verticalAlignment: TextInput.AlignVCenter
        }
        Text {
            anchors.left: parent.left
            anchors.leftMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            text: "Filter levels, branches and units..."
            font.pixelSize: 10
            color: Colors.cyan
            opacity: 0.6
            visible: subjectSearch.text.length === 0
        }
    }
    Text {
        width: parent.width
        text: "APPLY TO // ORGANIZATION / BRANCH / FUNCTIONAL UNIT"
        font.pixelSize: 10
        font.bold: true
        color: Colors.cyan
        visible: editor.selectedOrg !== null
        wrapMode: Text.WordWrap
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 5
        visible: editor.selectedOrg !== null
        Repeater {
            model: editor.visibleSubjects
            delegate: ActionButton {
                required property var modelData
                width: Math.min(220, Math.max(118, editor.width - 10))
                height: 29
                label: modelData.name
                labelPixelSize: 9
                selected: editor.selectedSourceId === modelData.id
                onTriggered: editor.chooseSource(modelData)
            }
        }
    }
    Text {
        width: parent.width
        text: "MODIFIER"
        font.pixelSize: 10
        font.bold: true
        color: Colors.cyan
        visible: editor.selectedSource !== null
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 6
        visible: editor.selectedSource !== null
        Repeater {
            model: [
                {id:"location", label:"LOCATED AT"},
                {id:"reporting", label:"REPORTS TO"},
                {id:"social", label:"SOCIAL LABEL"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: 140
                height: 30
                label: modelData.label
                labelPixelSize: 9
                interactive: editor.allowed(modelData.id)
                selected: editor.modifier === modelData.id
                onTriggered: editor.chooseModifier(modelData.id)
            }
        }
    }
    Text {
        width: parent.width
        text: editor.modifier === "location" ? "LOCATION"
            : editor.modifier === "reporting" ? "PARENT FUNCTION"
            : "SOCIAL LAYOUT IDENTITY"
        font.pixelSize: 10
        font.bold: true
        color: Colors.cyan
        visible: editor.selectedSource !== null
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 5
        visible: editor.selectedSource !== null
        Repeater {
            model: editor.targets
            delegate: ActionButton {
                required property var modelData
                width: Math.min(220, Math.max(118, editor.width - 10))
                height: 29
                label: modelData.name
                labelPixelSize: 9
                selected: editor.selectedTargetId === modelData.id
                onTriggered: {
                    editor.selectedTargetId = modelData.id;
                    editor.selectedServiceId = "";
                    editor.selectedAccountId = "";
                }
            }
        }
    }
    Text {
        width: parent.width
        visible: editor.selectedSource !== null && editor.targets.length === 0
        text: editor.modifier === "social"
                ? "Social layout identity list is unavailable or empty."
                : "Create an eligible target in MY STRUCTURE above first."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "OPTIONAL ACCOUNT NICKNAME // OTHERWISE LINK SOCIAL IDENTITY"
        font.pixelSize: 9
        color: Colors.cyan
        visible: editor.modifier === "social" && editor.selectedTargetId !== ""
        wrapMode: Text.WordWrap
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 5
        visible: editor.modifier === "social" && editor.selectedTargetId !== ""
        ActionButton {
            width: 155
            height: 28
            label: "IDENTITY ONLY"
            labelPixelSize: 9
            selected: editor.selectedAccountId === ""
            onTriggered: {
                editor.selectedServiceId = "";
                editor.selectedAccountId = "";
            }
        }
        Repeater {
            model: editor.availableServices
            delegate: ActionButton {
                required property string modelData
                width: 130
                height: 28
                label: modelData.toUpperCase()
                labelPixelSize: 9
                selected: editor.selectedServiceId === modelData
                onTriggered: {
                    editor.selectedServiceId = modelData;
                    editor.selectedAccountId = "";
                }
            }
        }
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 5
        visible: editor.modifier === "social"
                 && editor.selectedTargetId !== ""
                 && editor.selectedServiceId !== ""
        Repeater {
            model: editor.availableAccounts
            delegate: ActionButton {
                required property var modelData
                width: Math.min(200, Math.max(110, editor.width - 10))
                height: 28
                label: modelData.label
                labelPixelSize: 9
                selected: editor.selectedAccountId === modelData.id
                onTriggered: editor.selectedAccountId = modelData.id
            }
        }
    }
    Text {
        width: parent.width
        visible: editor.selectedSource !== null
                && (editor.alreadyLinked() || editor.wouldCycle())
        text: editor.alreadyLinked() ? "This modifier is already saved."
            : "This reporting relation would create a loop."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: editor.selectedSource !== null
                 && (!editor.currentStore || editor.currentStore.state !== "ready")
        text: !editor.currentStore ? "MODIFIER STORAGE // UNAVAILABLE"
            : editor.currentStore.state === "error"
            ? "MODIFIER ERROR // " + editor.currentStore.errorCode
            : "MODIFIER STORAGE // " + editor.currentStore.state.toUpperCase()
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 185
        height: 32
        label: "APPLY MODIFIER"
        labelPixelSize: 10
        interactive: editor.validSelection
        onTriggered: editor.applyModifier()
    }
    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.4
    }
    Text {
        width: parent.width
        text: "SAVED ORGANIZATION LINKS // " + editor.savedEntries.length
        font.pixelSize: 11
        font.bold: true
        color: Colors.cyan
        wrapMode: Text.WordWrap
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 6
        ActionButton {
            width: 155
            height: 28
            label: editor.showAll ? "SHOW SELECTED ORG" : "SHOW ALL ORGS"
            labelPixelSize: 9
            onTriggered: {
                editor.showAll = !editor.showAll;
                editor.confirmUnlinkKey = "";
            }
        }
        ActionButton {
            width: 150
            height: 28
            label: "REFRESH LINKS"
            labelPixelSize: 9
            onTriggered: editor.reloadLinks()
        }
    }
    Text {
        width: parent.width
        visible: editor.savedEntries.length === 0
        text: "No local organization link modifiers saved yet."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: editor.savedEntries
        delegate: Column {
            id: itemRow
            required property var modelData
            width: editor.width
            spacing: 5
            visible: editor.showAll || (
                editor.selectedOrgId !== ""
                && editor.selectedOrgId === modelData.orgId)
            height: visible ? implicitHeight : 0
            Rectangle {
                width: parent.width
                height: 1
                opacity: 0.25
                color: Colors.cyan
            }
            Text {
                width: parent.width
                text: editor.describe(itemRow.modelData)
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: editor.current(itemRow.modelData)
                    ? "LOCAL MODIFIER // NOT AN ACCESS GRANT"
                    : "STALE OR UNAVAILABLE // NOT AN ACCESS GRANT"
                color: editor.current(itemRow.modelData)
                    ? Colors.cyan : Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: 162
                height: 28
                label: editor.confirmUnlinkKey === itemRow.modelData.key
                    ? "CONFIRM UNLINK" : "UNLINK MODIFIER"
                labelPixelSize: 9
                accentColor: Colors.orange
                interactive: editor.storeFor(itemRow.modelData) !== null
                    && editor.storeFor(itemRow.modelData).state === "ready"
                onTriggered: {
                    if (editor.confirmUnlinkKey === itemRow.modelData.key) {
                        editor.unlink(itemRow.modelData);
                        editor.confirmUnlinkKey = "";
                    } else {
                        editor.confirmUnlinkKey = itemRow.modelData.key;
                    }
                }
            }
        }
    }
}
