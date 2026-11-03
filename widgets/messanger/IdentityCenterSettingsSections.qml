import QtQuick
import "../../components"

// UI-only Identity Center navigation inside the existing Social settings.
// No auth state, tenant metadata, provider session, process or persistent writes.
// A future trusted backend must supply verified person/org/role summaries.
// Never infer enterprise rights from SocialIdentityStore's local identity-N.
Item {
    id: sections

    property string activeSection: "SOCIAL LAYOUT"
    // Parent settings visibility gates the display-only IPC reader.
    // This is NOT a login, account selection or authorization state.
    property bool settingsOpen: false
    // Injected by Social; null in synthetic Qt tests.
    property var localDirectoryStore: null
    // Editing focus for LOCAL saved records. This is not a verified tenant
    // selection, authorization context, membership, or sign-in.
    property string localEditingOrganizationId: ""
    readonly property var localOrganizationsForEditing:
        localDirectoryStore && localDirectoryStore.state === "ready"
        && localDirectoryStore.saved && Array.isArray(localDirectoryStore.saved.organizations)
        ? localDirectoryStore.saved.organizations.filter(function(org) {
            return !org.archived;
        }) : []
    readonly property string activeLocalEditingOrganizationId:
        localOrganizationsForEditing.some(function(org) {
            return org.id === sections.localEditingOrganizationId;
        }) ? sections.localEditingOrganizationId : ""
    // Local portfolio groupings are display metadata, never verified rights.
    property var localPortfoliosStore: null
    // Local division/department/location/team labels, never verified grants.
    property var localStructureStore: null
    // Local-only functional-unit to location planning labels.
    property var localUnitLocationLinksStore: null
    // Local branch/geographic associations only, no verified tenant rights.
    property var localBranchLocationLinksStore: null
    // Local functional reporting map, never trusted workforce authority.
    property var localFunctionalReportingStore: null
    // Manual Social label associations only, not Identity Center grants.
    property var localLinksStore: null
    property var socialIdentitiesSnapshot: null
    property var socialAccountDetailsStore: null
    // Display-only input for a FUTURE approved privileged host.
    // No current host feeds this value; never treat it as authorization.
    // Tokens, provider subjects and credentials must never enter QML.
    property var organizationDisplaySnapshot: null
    readonly property bool organizationDisplayReady:
        organizationDisplaySnapshot !== null
        && organizationDisplaySnapshot.schema === "post-apollo.identity.desktop-context-display.v0"
        && organizationDisplaySnapshot.status === "READY"
        && organizationDisplaySnapshot.canSwitchOrganization === false
        && Array.isArray(organizationDisplaySnapshot.organizations)
        && Array.isArray(organizationDisplaySnapshot.portfolios)
    // The reader uses only a fixed JSON snapshot operation. The actual
    // identity host is separate; no bearer, code or callback enters Social.
    IdentityCenterOrganizationDisplayReader {
        id: identityDisplayReader
        active: sections.settingsOpen
                && sections.activeSection === "ORGANIZATIONS"
        onSnapshotChanged: {
            sections.organizationDisplaySnapshot = snapshot;
        }
    }

    readonly property int navigationHeight: 42
    signal sectionRequested(string section)

    readonly property var sectionsList: [
        { id: "PROFILE", label: "PROFILE" },
        { id: "ORGANIZATIONS", label: "ORGANIZATIONS" },
        { id: "CONNECTED ACCOUNTS", label: "CONNECTED ACCOUNTS" },
        { id: "SECURITY", label: "SECURITY" },
        { id: "SOCIAL LAYOUT", label: "SOCIAL LAYOUT" }
    ]

    readonly property bool isPreviewSection: activeSection !== "SOCIAL LAYOUT"

    Rectangle {
        id: navigationBackground
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: sections.navigationHeight
        color: Colors.dark
        border.width: 1
        border.color: Colors.cyan

        Flickable {
            id: navigationScroller
            anchors.fill: parent
            anchors.margins: 4
            contentWidth: navigationRow.width
            contentHeight: height
            clip: true
            flickableDirection: Flickable.HorizontalFlick
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentWidth > width

            Row {
                id: navigationRow
                height: parent.height
                spacing: 5

                Repeater {
                    model: sections.sectionsList
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(96, modelData.label.length * 8 + 22)
                        height: navigationRow.height
                        label: modelData.label
                        labelPixelSize: 9
                        labelMinimumPixelSize: 8
                        contentPadding: 3
                        accentColor: Colors.cyan
                        selected: sections.activeSection === modelData.id
                        softGlowEnabled: false
                        trackLabelGlowLocally: true
                        onTriggered: sections.sectionRequested(modelData.id)
                    }
                }
            }
        }
    }

    // Read-only staging panels: the signed-in principal and tenant list
    // are NOT available from the current desktop process. Explicitly show
    // absence instead of fabricating names, roles or a successful sign-in.
    Rectangle {
        id: previewContent
        anchors.top: navigationBackground.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: sections.isPreviewSection
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan
        clip: true

        Flickable {
            anchors.fill: parent
            contentWidth: width
            contentHeight: previewColumn.height + 32
            flickableDirection: Flickable.VerticalFlick
            boundsBehavior: Flickable.StopAtBounds
            clip: true

            Column {
                id: previewColumn
                anchors.top: parent.top
                anchors.topMargin: 16
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.max(1, parent.width - 32)
                spacing: 12

                Text {
                    width: parent.width
                    text: "IDENTITY CENTER // " + sections.activeSection
                    color: Colors.cyan
                    font.pixelSize: 13
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    text: "NOT CONNECTED // TRUSTED BACKEND REQUIRED"
                    visible: sections.activeSection !== "ORGANIZATIONS"
                             || !sections.organizationDisplayReady
                    color: Colors.orange
                    font.pixelSize: 10
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    visible: sections.activeSection === "PROFILE"
                    text: "No verified Post-Apollo person session is available. " +
                          "Local Social layout identities do not establish " +
                          "workforce identity or company membership."
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }

                Column {
                    width: parent.width
                    spacing: 10
                    visible: sections.activeSection === "ORGANIZATIONS"

                    Text {
                        width: parent.width
                        text: "ACTIVE ORGANIZATION // NONE VERIFIED"
                        color: Colors.white
                        font.pixelSize: 11
                        font.bold: true
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        visible: !sections.organizationDisplayReady
                        text: "No authorized organizations or portfolios have " +
                              "been loaded. The future selector will show only " +
                              "memberships verified by the Identity Center API."
                        color: Colors.white
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }

                    IdentityCenterLocalRecordsSearch {
                        id: localRecordsSearch
                        objectName: "orgLocalSearch"
                        width: parent.width
                        directoryStore: sections.localDirectoryStore
                        portfolioStore: sections.localPortfoliosStore
                        structureStore: sections.localStructureStore
                        functionLocationStore: sections.localUnitLocationLinksStore
                        branchLocationStore: sections.localBranchLocationLinksStore
                        reportingStore: sections.localFunctionalReportingStore
                        socialLinksStore: sections.localLinksStore
                        identitiesSnapshot: sections.socialIdentitiesSnapshot
                        accountDetailsStore: sections.socialAccountDetailsStore
                        onRecordFocused: function(orgId, unitKind, category) {
                            if (!sections.localOrganizationsForEditing.some(function(org) {
                                return org.id === orgId;
                            }))
                                return;
                            sections.localEditingOrganizationId = orgId;
                            if (category === "units" &&
                                ["division", "department", "location", "team"].includes(unitKind))
                                localStructureEditor.selectedKind = unitKind;
                        }
                    }

                    IdentityCenterLocalSaveFeedback {
                        id: localSaveFeedback
                        objectName: "orgLocalSaveFeedback"
                        width: parent.width
                        directoryStore: sections.localDirectoryStore
                        portfolioStore: sections.localPortfoliosStore
                        structureStore: sections.localStructureStore
                        functionLocationStore: sections.localUnitLocationLinksStore
                        branchLocationStore: sections.localBranchLocationLinksStore
                        reportingStore: sections.localFunctionalReportingStore
                        socialLinksStore: sections.localLinksStore
                    }

                    // Shared local record editing context. ALL shows company records;
                    // Structure and Modifiers require an explicit active company.
                    Column {
                        id: localEditingContext
                        objectName: "orgLocalEditingContext"
                        width: parent.width
                        spacing: 6

                        Text {
                            width: parent.width
                            text: "LOCAL ORGANIZATION TO EDIT"
                            color: Colors.cyan
                            font.bold: true
                            font.pixelSize: 11
                        }
                        Text {
                            width: parent.width
                            text: "Choose once for Structure and Apply Modifier. " +
                                  "ALL keeps Organizations and Portfolios browsable. " +
                                  "This does not switch verified company access."
                            color: Colors.orange
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }
                        Flow {
                            width: parent.width
                            height: childrenRect.height
                            spacing: 5
                            ActionButton {
                                width: 147
                                height: 29
                                label: "ALL / NO SELECTION"
                                labelPixelSize: 9
                                selected: sections.activeLocalEditingOrganizationId === ""
                                onTriggered: sections.localEditingOrganizationId = ""
                            }
                            Repeater {
                                model: sections.localOrganizationsForEditing
                                delegate: ActionButton {
                                    required property var modelData
                                    width: Math.min(190, Math.max(110, localEditingContext.width - 12))
                                    height: 29
                                    label: modelData.name
                                    labelPixelSize: 9
                                    selected: sections.activeLocalEditingOrganizationId === modelData.id
                                    onTriggered: sections.localEditingOrganizationId = modelData.id
                                }
                            }
                        }
                        Text {
                            width: parent.width
                            visible: sections.localOrganizationsForEditing.length === 0
                            text: "Create or restore a local organization below to choose it here."
                            color: Colors.orange
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }
                    }

                    IdentityCenterLocalOrganizationEditor {
                        objectName: "orgLocalDirectoryEditor"
                        width: parent.width
                        directoryStore: sections.localDirectoryStore
                        focusedOrganizationId: sections.activeLocalEditingOrganizationId
                        searchQuery: localRecordsSearch.searchText
                        useSharedArchiveControl: true
                        showArchived: localRecordsSearch.includeArchived
                    }

                    IdentityCenterLocalPortfolioEditor {
                        objectName: "orgLocalPortfolioEditor"
                        width: parent.width
                        directoryStore: sections.localDirectoryStore
                        portfolioStore: sections.localPortfoliosStore
                        searchQuery: localRecordsSearch.searchText
                        useSharedArchiveControl: true
                        showArchived: localRecordsSearch.includeArchived
                    }

                    IdentityCenterLocalStructureEditor {
                        objectName: "localStructureEditor"
                        width: parent.width
                        directoryStore: sections.localDirectoryStore
                        structureStore: sections.localStructureStore
                        useSharedContext: true
                        selectedOrgId: sections.activeLocalEditingOrganizationId
                        searchQuery: localRecordsSearch.searchText
                        useSharedArchiveControl: true
                        showArchivedUnits: localRecordsSearch.includeArchived
                    }

                    // One source/target form applies existing link modifiers across
                    // organization, branch, division, department and team labels.
                    IdentityCenterLocalRelationshipModifiers {
                        id: organizationModifiers
                        objectName: "orgModifierForm"
                        width: parent.width
                        useSharedContext: true
                        selectedOrgId: sections.activeLocalEditingOrganizationId
                        searchQuery: localRecordsSearch.searchText
                        directoryStore: sections.localDirectoryStore
                        structureStore: sections.localStructureStore
                        functionLocationStore: sections.localUnitLocationLinksStore
                        branchLocationStore: sections.localBranchLocationLinksStore
                        reportingStore: sections.localFunctionalReportingStore
                        socialLinksStore: sections.localLinksStore
                        identitiesSnapshot: sections.socialIdentitiesSnapshot
                        accountDetailsStore: sections.socialAccountDetailsStore
                    }

                    Column {
                        width: parent.width
                        spacing: 7
                        visible: sections.organizationDisplayReady

                        Text {
                            width: parent.width
                            text: "MEMBERSHIPS // READ-ONLY DISPLAY"
                            font.pixelSize: 11
                            font.bold: true
                            color: Colors.cyan
                            wrapMode: Text.WordWrap
                        }

                        Repeater {
                            model: sections.organizationDisplayReady
                                   ? sections.organizationDisplaySnapshot.organizations
                                   : []
                            delegate: Text {
                                required property var modelData
                                width: parent.width
                                // IDs/kinds/summary counts only. Never render
                                // tokens, subjects or a client-managed role.
                                text: modelData.organizationId + " // " +
                                      modelData.kind.toUpperCase() + " // " +
                                      modelData.scopeGrants.length + " SCOPE PREVIEWS"
                                color: Colors.white
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                            }
                        }

                        Text {
                            width: parent.width
                            text: "PORTFOLIOS // " +
                                  (sections.organizationDisplayReady
                                   ? sections.organizationDisplaySnapshot.portfolios.length
                                   : 0)
                            font.pixelSize: 10
                            color: Colors.cyan
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            width: parent.width
                            text: "Display data is not proof of permission. " +
                                  "Actions always require fresh server authorization."
                            font.pixelSize: 9
                            color: Colors.orange
                            wrapMode: Text.WordWrap
                        }
                    }

                    ActionButton {
                        width: Math.min(parent.width, 260)
                        height: 35
                        label: "SWITCH ORGANIZATION // UNAVAILABLE"
                        labelPixelSize: 9
                        labelMinimumPixelSize: 8
                        interactive: false
                        accentColor: Colors.orange
                        softGlowEnabled: false
                    }

                    Text {
                        width: parent.width
                        text: "Portfolio views never grant rights to an LLC, " +
                              "nonprofit or customer account by themselves."
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                }

                Text {
                    width: parent.width
                    visible: sections.activeSection === "CONNECTED ACCOUNTS"
                    text: "Identity Center account delegation is not connected. " +
                          "Existing Social account names and provider sign-in " +
                          "controls remain under SOCIAL LAYOUT."
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    visible: sections.activeSection === "SECURITY"
                    text: "Identity Center devices, passkeys, MFA and session " +
                          "revocation are not connected to this screen. " +
                          "No local Social label is a verified login."
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    text: "Local organization edits save labels only. No verified " +
                          "company access, sign-in state or account connection " +
                          "is changed by selecting a section."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
