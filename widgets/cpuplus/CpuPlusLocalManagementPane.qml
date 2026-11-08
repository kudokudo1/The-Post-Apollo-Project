import QtQuick
import "../../components"
import "../messanger"
import qs.services.social

// Local company/branch/unit/portfolio inventory using Social's ORIGINAL stores
// and ORIGINAL editors/removal controller. Does not authenticate a person,
// switch a tenant, modify provider grants, or clone organization data.
Item {
    id: pane
    required property string area
    property string section: "ORGANIZATIONS"
    property string selectedOrganizationId: ""
    property string selectedPortfolioId: ""
    signal organizationRequested(string id)
    signal portfolioRequested(string id)

    readonly property var organizations:
        SocialOrganizationDirectoryStore.state === "ready"
        ? SocialOrganizationDirectoryStore.saved.organizations : []
    readonly property var activeOrganizations:
        organizations.filter(function(entry) { return !entry.archived; })
    readonly property var portfolios:
        SocialLocalPortfoliosStore.state === "ready"
        ? SocialLocalPortfoliosStore.saved.portfolios : []
    readonly property var activePortfolios:
        portfolios.filter(function(entry) { return !entry.archived; })
    readonly property var units:
        SocialLocalOrganizationStructureStore.state === "ready"
        ? SocialLocalOrganizationStructureStore.saved.units : []
    readonly property var selectedOrganization:
        activeOrganizations.find(function(entry) {
            return entry.id === pane.selectedOrganizationId;
        }) || null
    readonly property var selectedPortfolio:
        activePortfolios.find(function(entry) {
            return entry.id === pane.selectedPortfolioId;
        }) || null
    readonly property string title:
        section === "PORTFOLIOS" ? "PORTFOLIOS"
        : section === "STRUCTURE" ? "STRUCTURE / UNITS"
        : "ORGANIZATIONS / BRANCHES"

    readonly property string normalizedSearch: searchField.text.trim().toLowerCase()
    readonly property bool editingText: pane.area === "selector" && searchField.editingText
    onSectionChanged: {
        if (searchField)
            searchField.text = "";
        if (pane.area === "details" && archiveTray)
            archiveTray.cancelDelete();
    }
    onSelectedOrganizationIdChanged: {
        if (pane.area === "details" && archiveTray)
            archiveTray.cancelDelete();
    }
    onSelectedPortfolioIdChanged: {
        if (pane.area === "details" && archiveTray)
            archiveTray.cancelDelete();
    }

    function matches(item) {
        if (normalizedSearch === "")
            return true;
        return (String(item.name) + " " + String(item.id)
                + (item.kind ? " " + String(item.kind) : ""))
            .toLowerCase().indexOf(normalizedSearch) !== -1;
    }
    function selectRecord(record) {
        if (section === "PORTFOLIOS")
            pane.portfolioRequested(record.id);
        else
            pane.organizationRequested(record.id);
    }

    Flickable {
        id: scroller
        anchors.fill: parent
        contentWidth: width
        contentHeight: Math.max(height, content.implicitHeight + 18)
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick

        Column {
            id: content
            x: 5
            y: 7
            width: Math.max(1, scroller.width - 13)
            spacing: 10

            Column {
                id: overview
                width: parent.width
                spacing: 10
                visible: pane.area === "overview"
                GohuText {
                    width: parent.width
                    color: Colors.cyan
                    text: pane.title + " // LOCAL"
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "ORGANIZATIONS // " + pane.activeOrganizations.length
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "BRANCHES // "
                          + pane.organizations.reduce(function(total, org) {
                              return total + org.branches.filter(function(branch) {
                                  return !branch.archived;
                              }).length;
                          }, 0)
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "STRUCTURE UNITS // "
                          + pane.units.filter(function(unit) {
                              return !unit.archived;
                          }).length
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "PORTFOLIOS // " + pane.activePortfolios.length
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                GohuText {
                    width: parent.width
                    text: pane.section === "PORTFOLIOS"
                          ? "SELECT A PORTFOLIO IN THE MIDDLE BAY."
                          : "SELECT AN ORGANIZATION IN THE MIDDLE BAY."
                    color: Colors.magenta
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: pane.section === "STRUCTURE"
                          ? "EDIT DIVISIONS, DEPARTMENTS, TEAMS AND LOCATION LABELS IN DETAILS."
                          : pane.section === "PORTFOLIOS"
                            ? "GROUP SAVED COMPANIES IN PORTFOLIOS. THIS IS A LOCAL VIEW, NOT ACCESS."
                            : "CREATE, RENAME, ARCHIVE, RESTORE OR DELETE COMPANIES AND BRANCHES."
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "LOCAL RECORDS ONLY // NOT VERIFIED TENANT MEMBERSHIP. "
                          + "NO SIGN-IN OR COMPANY SWITCH PERFORMED."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "STORES // DIRECTORY " + SocialOrganizationDirectoryStore.state.toUpperCase()
                          + " / STRUCTURE " + SocialLocalOrganizationStructureStore.state.toUpperCase()
                          + " / PORTFOLIOS " + SocialLocalPortfoliosStore.state.toUpperCase()
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }

            Column {
                id: selector
                width: parent.width
                spacing: 8
                visible: pane.area === "selector"
                GohuText {
                    width: parent.width
                    text: pane.section === "PORTFOLIOS"
                          ? "SELECT PORTFOLIO"
                          : "SELECT ORGANIZATION"
                    font.pixelSize: 11
                    color: Colors.cyan
                    wrapMode: Text.WordWrap
                }
                CpuPlusIdField {
                    id: searchField
                    width: parent.width
                    placeholder: "SEARCH LOCAL RECORDS"
                    maxLength: 80
                }
                Repeater {
                    model: pane.section === "PORTFOLIOS"
                           ? pane.activePortfolios : pane.activeOrganizations
                    delegate: Column {
                        id: record
                        required property var modelData
                        width: selector.width
                        spacing: 4
                        visible: pane.matches(modelData)
                        height: visible ? implicitHeight : 0
                        ActionButton {
                            width: parent.width
                            height: 35
                            label: record.modelData.name
                            labelPixelSize: 10
                            selected: pane.section === "PORTFOLIOS"
                                      ? pane.selectedPortfolioId === record.modelData.id
                                      : pane.selectedOrganizationId === record.modelData.id
                            accentColor: Colors.cyan
                            onClicked: pane.selectRecord(record.modelData)
                        }
                        QuietText {
                            width: parent.width
                            text: pane.section === "PORTFOLIOS"
                                  ? "LOCAL GROUP // " + record.modelData.orgIds.length + " COMPANIES"
                                  : record.modelData.kind.toUpperCase()
                                    + " // " + record.modelData.branches.filter(function(branch) {
                                        return !branch.archived;
                                    }).length + " BRANCHES"
                            color: Colors.orange
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                        }
                    }
                }
                QuietText {
                    width: parent.width
                    visible: (pane.section === "PORTFOLIOS"
                              ? pane.activePortfolios.length : pane.activeOrganizations.length) === 0
                    text: "NO LOCAL RECORDS YET // CREATE IN THE RIGHT BAY"
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "SELECTION CONTROLS EDITOR FOCUS ONLY. "
                          + "IT DOES NOT SWITCH VERIFIED ACCOUNTS."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }

            Column {
                id: details
                width: parent.width
                spacing: 13
                visible: pane.area === "details"

                GohuText {
                    width: parent.width
                    text: pane.title + " // EDIT"
                    color: Colors.magenta
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "SAVED LOCAL RECORDS. USE THE EXISTING SOCIAL WRITERS; "
                          + "NO PROVIDER LOGIN OR ORGANIZATION PERMISSION CHANGES."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                // These are the SAME Social editors used in User Settings.
                // The existing guarded seven-store controller supplies red X
                // confirmation and archive restore with no backup requirement.
                IdentityCenterLocalOrganizationEditor {
                    width: parent.width
                    visible: pane.section === "ORGANIZATIONS"
                    height: visible ? implicitHeight : 0
                    directoryStore: SocialOrganizationDirectoryStore
                    removalController: archiveTray
                    focusedOrganizationId: pane.selectedOrganizationId
                    useSharedArchiveControl: true
                }
                IdentityCenterLocalStructureEditor {
                    width: parent.width
                    visible: pane.section === "STRUCTURE"
                    height: visible ? implicitHeight : 0
                    directoryStore: SocialOrganizationDirectoryStore
                    structureStore: SocialLocalOrganizationStructureStore
                    removalController: archiveTray
                    useSharedContext: true
                    selectedOrgId: pane.selectedOrganizationId
                    useSharedArchiveControl: true
                }
                IdentityCenterLocalPortfolioEditor {
                    width: parent.width
                    visible: pane.section === "PORTFOLIOS"
                    height: visible ? implicitHeight : 0
                    directoryStore: SocialOrganizationDirectoryStore
                    portfolioStore: SocialLocalPortfoliosStore
                    removalController: archiveTray
                    focusedPortfolioId: pane.selectedPortfolioId
                    useSharedArchiveControl: true
                }
                IdentityCenterLocalArchiveTray {
                    id: archiveTray
                    width: parent.width
                    directoryStore: SocialOrganizationDirectoryStore
                    portfolioStore: SocialLocalPortfoliosStore
                    structureStore: SocialLocalOrganizationStructureStore
                    unitLocationStore: SocialLocalUnitLocationLinksStore
                    branchLocationStore: SocialLocalBranchLocationLinksStore
                    reportingStore: SocialLocalFunctionalReportingStore
                    socialLinksStore: SocialOrganizationLinksStore
                }
            }
        }
    }
}
