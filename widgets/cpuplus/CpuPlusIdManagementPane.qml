import QtQuick
import "../../components"
import qs.services.social

// Read-only CPU++ ID inspection, embedded in each existing fixed-size bay.
// Never authorizes an organization, switches live provider accounts or writes.
Item {
    id: pane
    required property string area
    property string selectedId: ""
    signal idRequested(string localId)

    readonly property var snapshot: SocialIdentityStore.snapshot
    readonly property var identities:
        snapshot && Array.isArray(snapshot.identities) ? snapshot.identities : []
    readonly property string effectiveId: {
        const chosen = identities.find(function(item) {
            return item.id === pane.selectedId;
        });
        return chosen ? chosen.id : String(snapshot ? snapshot.activeId : "");
    }
    readonly property var inspectedId:
        identities.find(function(item) { return item.id === pane.effectiveId; }) || null
    readonly property var contact:
        effectiveId !== "" && SocialAccountDetailsStore.state === "ready"
        ? SocialAccountDetailsStore.recordFor(effectiveId) : null

    Flickable {
        id: scroller
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: Math.max(height, contentColumn.y + contentColumn.implicitHeight + 16)
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: contentColumn
            x: 5
            y: 8
            width: Math.max(1, scroller.width - 12)
            spacing: 12

            Column {
                id: overviewSection
                width: parent.width
                spacing: 12
                visible: pane.area === "overview"

                GohuText {
                    width: parent.width
                    text: "LOCAL SOCIAL IDS"
                    color: Colors.magenta
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "POST-APOLLO ID MANAGEMENT // LOCAL INVENTORY"
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "IDS // " + pane.identities.length
                    color: Colors.cyan
                    font.pixelSize: 13
                }
                GohuText {
                    width: parent.width
                    text: pane.snapshot && pane.snapshot.activeName
                          ? "ACTIVE SOCIAL LAYOUT // " + pane.snapshot.activeName
                          : "ACTIVE SOCIAL LAYOUT // NONE LOADED"
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: pane.snapshot && pane.snapshot.error
                          ? "STORAGE // " + pane.snapshot.error
                          : "STORAGE // " + (pane.snapshot ? pane.snapshot.state : "UNAVAILABLE")
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                QuietText {
                    width: parent.width
                    text: "LOCAL IDS ARE LAYOUT LABELS, NOT SIGNED-IN PERSONS, "
                          + "VERIFIED ORGANIZATIONS OR PERMISSION GRANTS."
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }

            Column {
                id: selectorSection
                width: parent.width
                spacing: 8
                visible: pane.area === "selector"

                QuietText {
                    width: parent.width
                    text: "SELECT LOCAL ID // INSPECT ONLY"
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: pane.identities
                    delegate: ActionButton {
                        required property var modelData
                        width: selectorSection.width
                        height: 39
                        label: modelData.name
                        labelPixelSize: 10
                        labelElide: Text.ElideRight
                        contentPadding: 5
                        selected: pane.effectiveId === modelData.id
                        accentColor: Colors.cyan
                        onClicked: pane.idRequested(modelData.id)
                    }
                }
                QuietText {
                    width: parent.width
                    visible: pane.identities.length === 0
                    text: "NO LOCAL IDS LOADED"
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "Choosing a row updates this inspection only. "
                          + "It does not switch Social layouts or sign anyone in."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }

            Column {
                id: detailsSection
                width: parent.width
                spacing: 10
                visible: pane.area === "details"

                GohuText {
                    width: parent.width
                    text: pane.inspectedId ? pane.inspectedId.name : "NO ID SELECTED"
                    color: Colors.magenta
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "LOCAL KEY // " + (pane.inspectedId ? pane.inspectedId.id : "NONE")
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "LAYOUT FAMILIES // "
                          + (pane.inspectedId ? pane.inspectedId.familyCount : 0)
                    color: Colors.white
                    font.pixelSize: 11
                }
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                QuietText {
                    width: parent.width
                    text: "CONTACT DEFAULTS // LOCAL NOTES"
                    color: Colors.cyan
                    font.pixelSize: 10
                }
                QuietText {
                    width: parent.width
                    text: "EMAIL // " + (pane.contact ? (pane.contact.email || "NOT SET")
                                                     : "NOT LOADED")
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WrapAnywhere
                }
                QuietText {
                    width: parent.width
                    text: "PHONE // " + (pane.contact ? (pane.contact.phone || "NOT SET")
                                                     : "NOT LOADED")
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                QuietText {
                    width: parent.width
                    text: "READ-ONLY FOUNDATION // ID EDITING WILL REUSE THE "
                          + "EXISTING STORES AFTER EDITOR REVIEW."
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
