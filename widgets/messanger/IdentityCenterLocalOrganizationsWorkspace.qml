import QtQuick
import "../../components"

// Presentation-only consolidation of seven existing editors. No new account,
// tenant, graph or authorization semantics; all writes stay in their old stores.
Column {
    id: workspace
    property var directoryStore: null
    property var portfolioStore: null
    property var structureStore: null
    property var functionLocationStore: null
    property var branchLocationStore: null
    property var reportingStore: null
    property var socialLinksStore: null
    property var identitiesSnapshot: null
    property var accountDetailsStore: null

    property string activeWorkspace: "overview"
    property string companyMode: "organizations"
    property string relationshipMode: "reporting"
    property string selectedOrganizationId: ""
    property string organizationFilter: ""
    spacing: 10

    readonly property var localOrganizations:
        directoryStore && directoryStore.state === "ready"
        ? directoryStore.saved.organizations : []
    readonly property var activeOrganizations:
        localOrganizations.filter(function(org) { return !org.archived; })
    // One LOCAL edit context; never a verified Identity Center tenant switch.
    readonly property string currentOrgId:
        activeOrganizations.some(function(org) {
            return org.id === workspace.selectedOrganizationId;
        }) ? selectedOrganizationId
          : activeOrganizations.length > 0 ? activeOrganizations[0].id : ""
    readonly property var visibleOrganizations:
        activeOrganizations.filter(function(org) {
            return org.name.toLowerCase().indexOf(
                workspace.organizationFilter.trim().toLowerCase()) !== -1;
        })
    readonly property string currentOrgName:
        activeOrganizations.some(function(org) {
            return org.id === workspace.currentOrgId;
        }) ? activeOrganizations.find(function(org) {
            return org.id === workspace.currentOrgId;
        }).name : "NO ACTIVE LOCAL ORGANIZATION"

    function count(store, field) {
        return store && store.state === "ready" && store.saved
            && Array.isArray(store.saved[field]) ? store.saved[field].length : 0;
    }
    function selectWorkspace(name) {
        activeWorkspace = name;
    }
    function selectMode(name) {
        relationshipMode = name;
    }

    Text {
        width: parent.width
        text: "ORGANIZATION MANAGER // LOCAL WORKSPACES"
        font.bold: true
        font.pixelSize: 12
        color: Colors.cyan
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Choose one workspace at a time. Existing data and save/archive " +
              "actions are unchanged. Local selection does NOT switch verified " +
              "company identity or grant access."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Flow {
        width: parent.width
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: [
                {id:"overview", label:"OVERVIEW"},
                {id:"companies", label:"COMPANIES"},
                {id:"structure", label:"STRUCTURE"},
                {id:"relationships", label:"RELATIONSHIPS"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: Math.min(142, Math.max(109, (workspace.width - 20) / 2))
                height: 30
                label: modelData.label
                labelPixelSize: 9
                selected: workspace.activeWorkspace === modelData.id
                onTriggered: workspace.selectWorkspace(modelData.id)
            }
        }
    }

    Column {
        width: parent.width
        spacing: 6
        visible: workspace.activeWorkspace === "structure"
                 || workspace.activeWorkspace === "relationships"
        Text {
            width: parent.width
            text: "EDITING LOCAL ORGANIZATION // " + workspace.currentOrgName
            font.bold: true
            font.pixelSize: 10
            color: Colors.cyan
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: "Local record filter only. No verified account, role or session change."
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: parent.width
            height: 29
            color: Colors.black
            border.color: Colors.cyan
            TextInput {
                id: organizationSearch
                anchors.fill: parent
                anchors.margins: 6
                text: workspace.organizationFilter
                onTextChanged: workspace.organizationFilter = text
                color: Colors.white
                font.pixelSize: 10
                clip: true
                verticalAlignment: TextInput.AlignVCenter
            }
            Text {
                anchors.left: parent.left
                anchors.leftMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                text: "Filter organizations..."
                color: Colors.cyan
                opacity: 0.65
                font.pixelSize: 10
                visible: organizationSearch.text.length === 0
            }
        }
        Flow {
            width: parent.width
            spacing: 5
            height: childrenRect.height
            Repeater {
                model: workspace.visibleOrganizations
                delegate: ActionButton {
                    required property var modelData
                    width: Math.min(184, Math.max(108, workspace.width - 10))
                    height: 28
                    label: modelData.name
                    labelPixelSize: 9
                    selected: workspace.currentOrgId === modelData.id
                    onTriggered: workspace.selectedOrganizationId = modelData.id
                }
            }
        }
        Text {
            width: parent.width
            visible: workspace.currentOrgId === ""
            text: "Create an organization in COMPANIES before editing its structure."
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
    }

    Column {
        width: parent.width
        spacing: 9
        visible: workspace.activeWorkspace === "overview"
        Text {
            width: parent.width
            text: "OVERVIEW // LOCAL MANAGEMENT"
            color: Colors.cyan
            font.pixelSize: 11
            font.bold: true
        }
        Text {
            width: parent.width
            text: workspace.count(directoryStore, "organizations") +
                  " ORGANIZATIONS  //  " + workspace.count(portfolioStore, "portfolios") +
                  " PORTFOLIOS  //  " + workspace.count(structureStore, "units") +
                  " STRUCTURE UNITS"
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: (workspace.count(functionLocationStore, "links")
                   + workspace.count(branchLocationStore, "links")
                   + workspace.count(reportingStore, "links")
                   + workspace.count(socialLinksStore, "links")) +
                  " SAVED LOCAL RELATIONSHIPS"
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: "Counts include archived records. No verified company memberships " +
                  "or external account permissions are implied."
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: 180
            height: 29
            label: "OPEN COMPANIES"
            labelPixelSize: 9
            onTriggered: workspace.selectWorkspace("companies")
        }
        ActionButton {
            width: 180
            height: 29
            label: "OPEN STRUCTURE"
            labelPixelSize: 9
            onTriggered: workspace.selectWorkspace("structure")
        }
        ActionButton {
            width: 180
            height: 29
            label: "OPEN RELATIONSHIPS"
            labelPixelSize: 9
            onTriggered: workspace.selectWorkspace("relationships")
        }
    }

    Column {
        width: parent.width
        spacing: 9
        visible: workspace.activeWorkspace === "companies"
        Text {
            width: parent.width
            text: "COMPANIES & PORTFOLIOS"
            color: Colors.cyan
            font.bold: true
            font.pixelSize: 11
        }
        Flow {
            width: parent.width
            spacing: 5
            height: childrenRect.height
            Repeater {
                model: [
                    {id:"organizations", label:"ORGANIZATIONS & BRANCHES"},
                    {id:"portfolios", label:"PORTFOLIOS"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: modelData.id === "organizations" ? 204 : 145
                    height: 30
                    label: modelData.label
                    labelPixelSize: 9
                    selected: workspace.companyMode === modelData.id
                    onTriggered: workspace.companyMode = modelData.id
                }
            }
        }
        IdentityCenterLocalOrganizationEditor {
        objectName: "navV2Companies"
            width: parent.width
            visible: workspace.companyMode === "organizations"
            directoryStore: workspace.directoryStore
        }
        IdentityCenterLocalPortfolioEditor {
        objectName: "navV2Portfolios"
            width: parent.width
            visible: workspace.companyMode === "portfolios"
            directoryStore: workspace.directoryStore
            portfolioStore: workspace.portfolioStore
        }
    }

    IdentityCenterLocalStructureEditor {
        objectName: "navV2Structure"
        width: parent.width
        visible: workspace.activeWorkspace === "structure"
        directoryStore: workspace.directoryStore
        structureStore: workspace.structureStore
        useSharedContext: true
        selectedOrgId: workspace.currentOrgId
    }

    Column {
        width: parent.width
        spacing: 10
        visible: workspace.activeWorkspace === "relationships"
        Text {
            width: parent.width
            text: "RELATIONSHIP MANAGER // ONE EDITOR AT A TIME"
            font.bold: true
            font.pixelSize: 11
            color: Colors.cyan
            wrapMode: Text.WordWrap
        }
        Flow {
            width: parent.width
            spacing: 5
            height: childrenRect.height
            Repeater {
                model: [
                    {id:"reporting", label:"REPORTING"},
                    {id:"functions", label:"FUNCTION / LOCATION"},
                    {id:"branches", label:"BRANCH / LOCATION"},
                    {id:"social", label:"SOCIAL ASSOCIATIONS"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.min(196, Math.max(145, (workspace.width - 12) / 2))
                    height: 29
                    label: modelData.label
                    labelPixelSize: 9
                    selected: workspace.relationshipMode === modelData.id
                    onTriggered: workspace.selectMode(modelData.id)
                }
            }
        }
        Text {
            width: parent.width
            text: "Only this relationship type is shown. Create and remove " +
                  "actions still use the original validated private stores."
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        IdentityCenterLocalFunctionalReportingEditor {
        objectName: "navV2Reporting"
            width: parent.width
            visible: workspace.relationshipMode === "reporting"
            directoryStore: workspace.directoryStore
            structureStore: workspace.structureStore
            reportingStore: workspace.reportingStore
            useSharedContext: true
            selectedOrgId: workspace.currentOrgId
        }
        IdentityCenterLocalUnitLocationsEditor {
        objectName: "navV2Functions"
            width: parent.width
            visible: workspace.relationshipMode === "functions"
            directoryStore: workspace.directoryStore
            structureStore: workspace.structureStore
            linkStore: workspace.functionLocationStore
            useSharedContext: true
            selectedOrgId: workspace.currentOrgId
        }
        IdentityCenterLocalBranchLocationsEditor {
        objectName: "navV2Branches"
            width: parent.width
            visible: workspace.relationshipMode === "branches"
            directoryStore: workspace.directoryStore
            structureStore: workspace.structureStore
            linkStore: workspace.branchLocationStore
            useSharedContext: true
            selectedOrgId: workspace.currentOrgId
        }
        IdentityCenterLocalSocialLinksEditor {
        objectName: "navV2Social"
            width: parent.width
            visible: workspace.relationshipMode === "social"
            directoryStore: workspace.directoryStore
            linksStore: workspace.socialLinksStore
            identitiesSnapshot: workspace.identitiesSnapshot
            accountDetailsStore: workspace.accountDetailsStore
            useSharedContext: true
            selectedOrgId: workspace.currentOrgId
        }
    }
}
