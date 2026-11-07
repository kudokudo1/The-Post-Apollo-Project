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

    // Creation belongs only to the selector bay. The same single writer is
    // shared with Social; a request is not a successful save until onSaved.
    property bool creatingId: false
    property bool creationPending: false
    property string creationMode: "default"
    property string creationFeedback: ""
    readonly property bool editingText:
        area === "selector" ? newIdNameField.editingText
        : area === "details" ? detailEditor.editingText : false

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

    function requestCreate() {
        const title = newIdNameField.text.trim();
        if (!snapshot || !snapshot.writable || creationPending || title === "")
            return;
        const copyFrom = pane.effectiveId;
        if (SocialIdentityStore.createIdentity(title, creationMode, copyFrom)) {
            creationPending = true;
            creationFeedback = "SAVING NEW ID...";
        } else {
            creationFeedback = SocialIdentityStore.identityActionError
                               || "CREATE NOT AVAILABLE";
        }
    }

    Connections {
        target: SocialIdentityStore
        function onStorageStateChanged() {
            if (pane.area !== "selector" || !pane.creationPending)
                return;
            if (SocialIdentityStore.storageState === "ready") {
                pane.creationPending = false;
                pane.creatingId = false;
                pane.creationMode = "default";
                pane.creationFeedback = "NEW ID SAVED // LOCAL";
                newIdNameField.text = "";
                // Follow the new active layout only after its atomic save.
                pane.idRequested("");
            } else if (SocialIdentityStore.storageState === "error"
                       || SocialIdentityStore.storageState === "unsupported") {
                pane.creationPending = false;
                pane.creationFeedback = "ID CREATE FAILED // "
                                        + (SocialIdentityStore.errorCode
                                           || "STORAGE ERROR");
            }
        }
    }

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
                    text: "SELECT LOCAL ID // EDIT DETAILS"
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
                ActionButton {
                    width: parent.width
                    height: 36
                    label: pane.creatingId ? "CANCEL NEW ID" : "+ NEW ID"
                    labelPixelSize: 10
                    accentColor: Colors.magenta
                    selected: pane.creatingId
                    interactive: pane.snapshot && pane.snapshot.writable
                                 && !pane.creationPending
                                 && (pane.creatingId || pane.identities.length < 12)
                    onClicked: {
                        pane.creatingId = !pane.creatingId;
                        pane.creationMode = "default";
                        pane.creationFeedback = "";
                        newIdNameField.text = "";
                    }
                }
                Column {
                    width: parent.width
                    spacing: 8
                    visible: pane.creatingId

                    QuietText {
                        width: parent.width
                        text: "NEW LOCAL ID NAME"
                        color: Colors.cyan
                        font.pixelSize: 10
                    }
                    CpuPlusIdField {
                        id: newIdNameField
                        width: parent.width
                        height: 36
                        maxLength: 32
                        placeholder: "NEW ID NAME"
                    }
                    QuietText {
                        width: parent.width
                        text: "START FROM"
                        color: Colors.cyan
                        font.pixelSize: 9
                    }
                    Row {
                        width: parent.width
                        spacing: 4
                        Repeater {
                            model: [
                                { key: "default", title: "DEFAULT" },
                                { key: "copy", title: "COPY" },
                                { key: "empty", title: "EMPTY" }
                            ]
                            delegate: ActionButton {
                                required property var modelData
                                width: (selectorSection.width - 8) / 3
                                height: 31
                                label: modelData.title
                                labelPixelSize: 9
                                contentPadding: 3
                                accentColor: Colors.cyan
                                selected: pane.creationMode === modelData.key
                                onClicked: pane.creationMode = modelData.key
                            }
                        }
                    }
                    QuietText {
                        width: parent.width
                        visible: pane.creationMode === "copy"
                        text: "COPY LAYOUT FROM // " + (pane.inspectedId
                                                         ? pane.inspectedId.name : "NONE")
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: "CREATING A LOCAL LAYOUT ID DOES NOT SIGN IN "
                              + "OR CONNECT A PROVIDER."
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    ActionButton {
                        width: parent.width
                        height: 35
                        label: pane.creationPending ? "SAVING..." : "+ CREATE ID"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        interactive: pane.snapshot && pane.snapshot.writable
                                     && !pane.creationPending
                                     && newIdNameField.text.trim().length > 0
                                     && (pane.creationMode !== "copy"
                                         || pane.inspectedId !== null)
                        onClicked: pane.requestCreate()
                    }
                }
                QuietText {
                    width: parent.width
                    visible: pane.creationFeedback !== ""
                    text: pane.creationFeedback
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 30
                    visible: pane.snapshot && (pane.snapshot.state === "error"
                                              || pane.snapshot.state === "unsupported")
                    label: "RELOAD LOCAL IDS"
                    labelPixelSize: 9
                    accentColor: Colors.yellow
                    onClicked: SocialIdentityStore.reloadFromDisk()
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
                    text: "Choosing a row changes the editor focus only. "
                          + "It does not switch the active Social layout or sign in."
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

                CpuPlusIdDetailsEditor {
                    id: detailEditor
                    width: parent.width
                    height: implicitHeight
                    identityId: pane.effectiveId
                }
            }
        }
    }
}
