import QtQuick
import "../../components"

// Presentation-only local search. Never selects a verified tenant or invokes
// a storage writer. No remote account lookup and no credential material.
Column {
    id: search
    property var directoryStore: null
    property var portfolioStore: null
    property var structureStore: null
    property var functionLocationStore: null
    property var branchLocationStore: null
    property var reportingStore: null
    property var socialLinksStore: null
    property var identitiesSnapshot: null
    property var accountDetailsStore: null

    property string searchText: ""
    property string scope: "all"
    property bool includeArchived: false
    readonly property string needle: searchText.trim().toLowerCase()
    readonly property var matches: collectMatches()
    readonly property int matchCount: matches.length
    readonly property var visibleMatches: matches.slice(0, 60)
    signal recordFocused(string orgId, string unitKind, string category)
    spacing: 6

    function records(store, key) {
        return store && store.state === "ready" && store.saved
            && Array.isArray(store.saved[key]) ? store.saved[key] : [];
    }
    function text(value) {
        return value === undefined || value === null ? "" : String(value);
    }
    function collectMatches() {
        if (needle.length === 0)
            return [];

        const orgs = records(directoryStore, "organizations");
        const ports = records(portfolioStore, "portfolios");
        const units = records(structureStore, "units");
        const orgsById = Object.create(null);
        const unitsById = Object.create(null);
        const branchesById = Object.create(null);
        const matched = [];
        for (const org of orgs) {
            orgsById[org.id] = org;
            if (Array.isArray(org.branches)) {
                for (const branch of org.branches)
                    branchesById[org.id + ":" + branch.id] = branch;
            }
        }
        for (const unit of units)
            unitsById[unit.id] = unit;

        function orgLabel(orgId) {
            const org = orgsById[orgId];
            return org ? search.text(org.name) : "MISSING ORGANIZATION " + search.text(orgId);
        }
        function unitLabel(unitId) {
            const unit = unitsById[unitId];
            return unit ? search.text(unit.kind).toUpperCase() + " " + search.text(unit.name)
                        : "MISSING UNIT " + search.text(unitId);
        }
        function branchLabel(orgId, branchId) {
            const branch = branchesById[orgId + ":" + branchId];
            return branch ? "BRANCH " + search.text(branch.name)
                          : "MISSING BRANCH " + search.text(branchId);
        }
        function archivedOrg(orgId) {
            const org = orgsById[orgId];
            return !org || org.archived === true;
        }
        function archivedUnit(unitId) {
            const unit = unitsById[unitId];
            return !unit || unit.archived === true || archivedOrg(unit.orgId);
        }
        function archivedBranch(orgId, branchId) {
            const branch = branchesById[orgId + ":" + branchId];
            return !branch || branch.archived === true || archivedOrg(orgId);
        }
        function add(category, label, id, orgId, kind, isArchived, extra) {
            if (search.scope !== "all" && search.scope !== category)
                return;
            if (isArchived && !search.includeArchived)
                return;
            const title = search.text(label);
            const searchable = (title + " " + search.text(id) + " "
                + search.text(orgId) + " " + search.text(extra)).toLowerCase();
            if (searchable.indexOf(search.needle) === -1)
                return;
            matched.push({
                category: category, label: title, id: search.text(id),
                orgId: search.text(orgId), kind: search.text(kind),
                archived: !!isArchived,
            });
        }

        for (const org of orgs) {
            add("organizations", "ORGANIZATION // " + search.text(org.name),
                org.id, org.id, "", org.archived === true, org.kind);
            for (const branch of (Array.isArray(org.branches) ? org.branches : []))
                add("organizations",
                    "BRANCH // " + search.text(branch.name) + " · " + orgLabel(org.id),
                    branch.id, org.id, "", org.archived || branch.archived,
                    search.text(org.kind));
        }

        for (const portfolio of ports) {
            const names = (Array.isArray(portfolio.orgIds) ? portfolio.orgIds : [])
                .map(function(id) { return orgLabel(id); }).join(" ");
            add("portfolios", "PORTFOLIO // " + search.text(portfolio.name),
                portfolio.id, "", "", portfolio.archived === true, names);
        }

        for (const unit of units)
            add("units", search.text(unit.kind).toUpperCase() + " // "
                + search.text(unit.name) + " · " + orgLabel(unit.orgId),
                unit.id, unit.orgId, unit.kind,
                archivedUnit(unit.id), search.text(unit.kind));

        for (const edge of records(functionLocationStore, "links"))
            add("links", orgLabel(edge.orgId) + " // "
                + unitLabel(edge.functionId) + " LOCATED AT " + unitLabel(edge.locationId),
                edge.id, edge.orgId, "", archivedUnit(edge.functionId)
                || archivedUnit(edge.locationId), "function location");

        for (const edge of records(branchLocationStore, "links"))
            add("links", orgLabel(edge.orgId) + " // "
                + branchLabel(edge.orgId, edge.branchId) + " LOCATED AT "
                + unitLabel(edge.locationId),
                edge.id, edge.orgId, "", archivedBranch(edge.orgId, edge.branchId)
                || archivedUnit(edge.locationId), "branch location");

        for (const edge of records(reportingStore, "links"))
            add("links", orgLabel(edge.orgId) + " // "
                + unitLabel(edge.childId) + " REPORTS TO " + unitLabel(edge.parentId),
                edge.id, edge.orgId, "", archivedUnit(edge.childId)
                || archivedUnit(edge.parentId), "reporting");

        const identities = identitiesSnapshot && identitiesSnapshot.writable
            && Array.isArray(identitiesSnapshot.identities)
            ? identitiesSnapshot.identities : [];
        for (const edge of records(socialLinksStore, "links")) {
            const identity = identities.find(function(item) {
                return item.id === edge.identityId;
            });
            let account = "";
            if (edge.serviceId !== null && edge.serviceId !== undefined) {
                account = " / " + search.text(edge.serviceId);
                if (accountDetailsStore && accountDetailsStore.state === "ready") {
                    const nicknames = accountDetailsStore.accountNamesFor(
                        edge.identityId, edge.serviceId);
                    const nickname = nicknames.find(function(item) {
                        return item.id === edge.accountId;
                    });
                    account += " / " + (nickname ? search.text(nickname.label)
                                                 : search.text(edge.accountId));
                }
            }
            const source = edge.branchId ? branchLabel(edge.orgId, edge.branchId)
                                         : "ORGANIZATION";
            add("links", orgLabel(edge.orgId) + " // " + source
                + " SOCIAL LABEL " + (identity ? search.text(identity.name)
                                               : search.text(edge.identityId))
                + account,
                edge.id, edge.orgId, "", archivedOrg(edge.orgId)
                || (edge.branchId && archivedBranch(edge.orgId, edge.branchId))
                || (identities.length > 0 && !identity),
                "social identity account nickname");
        }
        return matched;
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.4
    }
    Text {
        width: parent.width
        text: "SEARCH LOCAL ORGANIZATION RECORDS"
        color: Colors.cyan
        font.pixelSize: 11
        font.bold: true
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Search companies, branches, portfolios, units and saved links " +
              "without switching pages. Results are local labels, not verified access."
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    Row {
        width: parent.width
        spacing: 6
        Rectangle {
            width: Math.max(110, parent.width - 137)
            height: 32
            color: Colors.black
            border.color: Colors.cyan
            TextInput {
                id: searchInput
                anchors.fill: parent
                anchors.margins: 7
                text: search.searchText
                onTextChanged: search.searchText = text
                maximumLength: 80
                color: Colors.white
                font.pixelSize: 11
                verticalAlignment: TextInput.AlignVCenter
                clip: true
            }
            Text {
                anchors.left: parent.left
                anchors.leftMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                text: "Search all local records..."
                visible: searchInput.text.length === 0
                color: Colors.cyan
                opacity: 0.6
                font.pixelSize: 10
            }
        }
        ActionButton {
            width: 129
            height: 32
            label: "CLEAR SEARCH"
            labelPixelSize: 9
            interactive: search.searchText.length > 0
            onTriggered: search.searchText = ""
        }
    }
    Text {
        width: parent.width
        text: "RECORD ACTIONS // ADD, EDIT NAME + SAVE, ARCHIVE + CONFIRM, RESTORE"
        color: Colors.cyan
        font.pixelSize: 10
        font.bold: true
        wrapMode: Text.WordWrap
    }
    ActionButton {
        objectName: "localShowArchivedRecords"
        width: 188
        height: 29
        label: search.includeArchived ? "HIDE ARCHIVED RECORDS" : "SHOW ARCHIVED RECORDS"
        labelPixelSize: 9
        selected: search.includeArchived
        onTriggered: search.includeArchived = !search.includeArchived
    }
    Text {
        width: parent.width
        visible: search.includeArchived
        text: "Archived records retain their IDs. To restore an archived company, " +
              "select ALL / NO SELECTION above its Directory row."
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 5
        visible: search.needle.length > 0
        Repeater {
            model: [
                {id:"all", label:"ALL"},
                {id:"organizations", label:"ORGS / BRANCHES"},
                {id:"portfolios", label:"PORTFOLIOS"},
                {id:"units", label:"STRUCTURE"},
                {id:"links", label:"LINKS"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: modelData.id === "organizations" ? 142 : 106
                height: 28
                label: modelData.label
                labelPixelSize: 8
                selected: search.scope === modelData.id
                onTriggered: search.scope = modelData.id
            }
        }
    }
    Text {
        width: parent.width
        visible: search.needle.length > 0
        text: search.matchCount + " MATCHES" +
              (search.matchCount > 60 ? " // SHOWING FIRST 60" : "")
        color: Colors.cyan
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: search.needle.length > 0 && search.matchCount === 0
        text: "No matching local records. Clear search or change a filter."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: search.needle.length > 0 ? search.visibleMatches : []
        delegate: Row {
            id: resultRow
            required property var modelData
            width: search.width
            spacing: 6
            Text {
                width: Math.max(80, parent.width - 135)
                text: resultRow.modelData.label +
                      (resultRow.modelData.archived ? " // ARCHIVED OR STALE" : "")
                color: resultRow.modelData.archived ? Colors.orange : Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: 126
                height: 28
                visible: resultRow.modelData.category !== "portfolios"
                label: resultRow.modelData.archived ? "ARCHIVED" : "FOCUS COMPANY"
                labelPixelSize: 8
                interactive: !resultRow.modelData.archived
                    && resultRow.modelData.orgId !== ""
                onTriggered: search.recordFocused(
                    resultRow.modelData.orgId,
                    resultRow.modelData.kind,
                    resultRow.modelData.category)
            }
        }
    }
}
