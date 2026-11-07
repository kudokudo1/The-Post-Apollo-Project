import QtQuick
import "../../components"
import "../messanger"

// CPU++ is a read-only consumer of the existing token-free Identity Center
// display reader. A local Social identity-N key is NOT mapped to a principal,
// tenant membership, login, role, grant or permission by this view.
Item {
    id: view
    property bool activeMode: false
    property bool expanded: false
    readonly property var display: contextReader.snapshot
    readonly property bool displayReady:
        display !== null && display !== undefined
        && display.schema === "post-apollo.identity.desktop-context-display.v0"
        && display.status === "READY"
        && display.canSwitchOrganization === false
        && Array.isArray(display.organizations)
        && Array.isArray(display.portfolios)
    readonly property string displayStatus:
        !display ? "NOT CONNECTED" : display.status
    implicitHeight: content.implicitHeight

    // Hiding CPU++'s ID mode or retracting the section clears the host view.
    // The existing reader also revokes prior data before every refresh and
    // rejects late responses, malformed claims and expired scope previews.
    onActiveModeChanged: {
        if (!activeMode)
            expanded = false;
    }

    IdentityCenterOrganizationDisplayReader {
        id: contextReader
        active: view.activeMode && view.expanded
    }

    Column {
        id: content
        width: parent.width
        spacing: 9

        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }
        GohuText {
            width: parent.width
            text: "IDENTITY HOST // READ-ONLY"
            color: Colors.cyan
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: "HOST MEMBERSHIPS ARE SEPARATE FROM LOCAL SOCIAL IDS, "
                  + "ORGANIZATION LABELS AND ACCOUNT NAMES."
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: parent.width
            height: 34
            label: view.expanded ? "HIDE HOST CONTEXT" : "CHECK HOST CONTEXT"
            labelPixelSize: 10
            accentColor: Colors.magenta
            selected: view.expanded
            interactive: view.activeMode
            onClicked: view.expanded = !view.expanded
        }
        Column {
            width: parent.width
            spacing: 10
            visible: view.expanded

            GohuText {
                width: parent.width
                text: "HOST STATUS // " + view.displayStatus
                color: view.displayReady ? Colors.cyan : Colors.orange
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            QuietText {
                width: parent.width
                visible: !view.displayReady
                text: view.displayStatus === "NO_MEMBERSHIPS"
                      ? "HOST RETURNED NO CURRENT ORGANIZATION MEMBERSHIPS."
                      : view.displayStatus === "SIGNED_OUT"
                      ? "SIGN IN USING THE SEPARATELY OWNED IDENTITY HOST."
                      : "NO USABLE HOST MEMBERSHIP DISPLAY IS AVAILABLE. "
                        + "CPU++ DOES NOT START SIGN-IN OR MAKE UP ACCESS."
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: view.displayReady
                text: "HOST ORGANIZATIONS // "
                      + (view.displayReady ? view.display.organizations.length : 0)
                color: Colors.cyan
                font.pixelSize: 11
            }
            Repeater {
                model: view.displayReady ? view.display.organizations : []
                delegate: Column {
                    id: orgRow
                    required property var modelData
                    width: content.width
                    spacing: 6

                    GohuText {
                        width: parent.width
                        text: orgRow.modelData.organizationId
                              + " // " + orgRow.modelData.kind.toUpperCase()
                        color: Colors.white
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: "SCOPE PREVIEWS // "
                              + orgRow.modelData.scopeGrants.length
                        color: Colors.cyan
                        font.pixelSize: 9
                    }
                    Repeater {
                        model: orgRow.modelData.scopeGrants
                        delegate: QuietText {
                            required property var modelData
                            width: orgRow.width
                            text: modelData.action.toUpperCase()
                                  + " // DIVISION: " + (modelData.divisionId || "ANY")
                                  + " / UNIT: " + (modelData.unitId || "ANY")
                                  + (modelData.expiresAt === null
                                     ? "" : " / EXP: " + modelData.expiresAt)
                            color: Colors.white
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
            QuietText {
                width: parent.width
                visible: view.displayReady
                text: "HOST PORTFOLIOS // "
                      + (view.displayReady ? view.display.portfolios.length : 0)
                color: Colors.cyan
                font.pixelSize: 10
            }
            Repeater {
                model: view.displayReady ? view.display.portfolios : []
                delegate: QuietText {
                    required property var modelData
                    width: content.width
                    text: modelData.portfolioId + " // "
                          + modelData.organizationIds.join(", ")
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
            ActionButton {
                width: parent.width
                height: 31
                label: "REFRESH HOST CONTEXT"
                labelPixelSize: 9
                accentColor: Colors.cyan
                interactive: view.activeMode
                onClicked: contextReader.refresh()
            }
            QuietText {
                width: parent.width
                text: "DISPLAY PREVIEW ONLY // NO PERSON ID, ROLE EDITOR, "
                      + "ORGANIZATION SWITCH OR PERMISSION GRANT. EVERY BUSINESS "
                      + "OPERATION MUST BE REAUTHORIZED BY THE SERVER."
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
    }
}
