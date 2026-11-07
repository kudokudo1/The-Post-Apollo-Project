import QtQuick
import "../../components"
import qs.services.social

// CPU++ local-ID creation, inspection and guarded deletion in existing bays.
// Does not handle authenticated identities, provider logins or permissions.
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
    property string removeArmedId: ""
    property string removeArmedName: ""
    property string pendingRemoveId: ""
    property string removeFeedback: ""
    onSelectedIdChanged: {
        removeArmedId = "";
        removeArmedName = "";
    }
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

    function armRemove(id, name) {
        if (!snapshot || !snapshot.writable || creatingId
                || creationPending || pendingRemoveId !== "")
            return;
        idRequested(id); // Select for editing only; never activate a provider.
        removeArmedId = id;
        removeArmedName = name;
        removeFeedback = "";
    }

    function cancelRemove() {
        removeArmedId = "";
        removeArmedName = "";
        removeFeedback = "";
    }

    function requestRemove() {
        if (!snapshot || !snapshot.writable || creatingId || creationPending
                || pendingRemoveId !== "" || removeArmedId === "")
            return;
        const current = identities.find(function(item) {
            return item.id === pane.removeArmedId && item.name === pane.removeArmedName;
        });
        if (!current || effectiveId !== removeArmedId) {
            cancelRemove();
            removeFeedback = "ID CHANGED // SELECT REMOVE AGAIN";
            return;
        }
        if (SocialIdentityStore.removeIdentity(removeArmedId)) {
            pendingRemoveId = removeArmedId;
            removeFeedback = "REMOVING LOCAL ID...";
        } else {
            const code = SocialIdentityStore.identityActionError || "REMOVE NOT AVAILABLE";
            removeFeedback = code === "UNLINK_ORGANIZATION_FIRST"
                ? "UNLINK ORGANIZATION LINKS FIRST // SOCIAL ACCOUNT CENTER"
                : code === "CLEAR_CONTACT_AND_ACCOUNT_NAMES_FIRST"
                ? "CLEAR CONTACT AND ACCOUNT NAMES FIRST // THEN REMOVE"
                : code === "LAST_ID_REQUIRED" ? "KEEP AT LEAST ONE LOCAL ID"
                : code === "RELATED_DATA_UNAVAILABLE"
                ? "RELATED DATA UNAVAILABLE // RELOAD BEFORE REMOVAL"
                : "REMOVE BLOCKED // " + code;
        }
    }

    Connections {
        target: SocialIdentityStore
        function onStorageStateChanged() {
            if (pane.area !== "selector")
                return;
            if (pane.pendingRemoveId !== "") {
                if (SocialIdentityStore.storageState === "ready") {
                    pane.pendingRemoveId = "";
                    pane.removeArmedId = "";
                    pane.removeArmedName = "";
                    pane.removeFeedback = "LOCAL ID REMOVED";
                    pane.idRequested(""); // Inspect the remaining active ID.
                } else if (SocialIdentityStore.storageState === "error"
                           || SocialIdentityStore.storageState === "unsupported") {
                    pane.pendingRemoveId = "";
                    pane.removeFeedback = "REMOVE FAILED // "
                        + (SocialIdentityStore.errorCode || "STORAGE ERROR");
                }
                return;
            }
            if (!pane.creationPending)
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
                GohuText {
                    width: parent.width
                    text: "LOCAL ORGANIZATIONS // "
                          + (SocialOrganizationDirectoryStore.state === "ready"
                             ? SocialOrganizationDirectoryStore.saved.organizations.length
                             : "NOT LOADED")
                    color: Colors.cyan
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                QuietText {
                    width: parent.width
                    text: "ID ASSOCIATIONS // "
                          + (SocialOrganizationLinksStore.state === "ready"
                             ? SocialOrganizationLinksStore.saved.links.filter(function(link) {
                                   return link.identityId === pane.effectiveId;
                               }).length : "NOT LOADED")
                    color: Colors.white
                    font.pixelSize: 10
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
                    delegate: Row {
                        id: idRow
                        required property var modelData
                        width: selectorSection.width
                        height: 39
                        spacing: 4
                        ActionButton {
                            width: idRow.width - removeButton.width - idRow.spacing
                            height: parent.height
                            label: idRow.modelData.name
                            labelPixelSize: 10
                            labelElide: Text.ElideRight
                            contentPadding: 5
                            selected: pane.effectiveId === idRow.modelData.id
                            accentColor: Colors.cyan
                            onClicked: {
                                pane.cancelRemove();
                                pane.idRequested(idRow.modelData.id);
                            }
                        }
                        ActionButton {
                            id: removeButton
                            width: 34
                            height: parent.height
                            label: "X"
                            labelPixelSize: 11
                            destructive: true
                            accentColor: Colors.red
                            interactive: pane.snapshot && pane.snapshot.writable
                                         && pane.identities.length > 1
                                         && !pane.creatingId && !pane.creationPending
                                         && pane.pendingRemoveId === ""
                            onClicked: pane.armRemove(idRow.modelData.id,
                                                      idRow.modelData.name)
                        }
                    }
                }
                Column {
                    width: parent.width
                    spacing: 7
                    visible: pane.removeArmedId !== ""
                    GohuText {
                        width: parent.width
                        text: "REMOVE ID // " + pane.removeArmedName
                        color: Colors.red
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: "PERMANENTLY REMOVES THIS LOCAL LAYOUT. "
                              + "IF ACTIVE, THE FIRST REMAINING ID BECOMES ACTIVE. "
                              + "CLEAR CONTACTS, ACCOUNT NAMES AND ORGANIZATION LINKS FIRST."
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    ActionButton {
                        width: parent.width
                        height: 34
                        label: pane.pendingRemoveId !== "" ? "REMOVING..."
                               : "CONFIRM REMOVE ID"
                        labelPixelSize: 9
                        destructive: true
                        accentColor: Colors.red
                        interactive: pane.snapshot && pane.snapshot.writable
                                     && pane.pendingRemoveId === ""
                                     && !pane.creationPending
                        onClicked: pane.requestRemove()
                    }
                    ActionButton {
                        width: parent.width
                        height: 29
                        label: "CANCEL REMOVAL"
                        labelPixelSize: 9
                        accentColor: Colors.white
                        interactive: pane.pendingRemoveId === ""
                        onClicked: pane.cancelRemove()
                    }
                }
                QuietText {
                    width: parent.width
                    visible: pane.removeFeedback !== ""
                    text: pane.removeFeedback
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
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
                        pane.cancelRemove();
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
