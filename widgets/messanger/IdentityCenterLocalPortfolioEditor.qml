import QtQuick
import "../../components"

// A portfolio here is only a personal group of local company labels.
// It is NOT an authenticated tenant view or a selector for access rights.
Column {
    id: editor
    property var portfolioStore: null
    property var directoryStore: null
    property string searchQuery: ""
    readonly property string normalizedSearch: searchQuery.trim().toLowerCase()
    function matchesPortfolio(portfolio) {
        if (normalizedSearch.length === 0) return true;
        let values = String(portfolio.name) + " " + String(portfolio.id);
        for (const orgId of portfolio.orgIds) {
            const org = organizationFor(orgId);
            values += " " + (org ? String(org.name) + " " + String(org.kind)
                                  : String(orgId));
        }
        return values.toLowerCase().indexOf(normalizedSearch) !== -1;
    }
    property bool showArchived: false
    property bool useSharedArchiveControl: false
    onShowArchivedChanged: confirmationKey = ""
    property string confirmationKey: ""
    readonly property bool editable: portfolioStore !== null
                                     && portfolioStore.state === "ready"
    readonly property var portfolios: portfolioStore && portfolioStore.saved
        ? portfolioStore.saved.portfolios : []
    readonly property var organizations: directoryStore
                                         && directoryStore.state === "ready"
        ? directoryStore.saved.organizations : []
    spacing: 9

    function organizationFor(orgId) {
        return organizations.find(function(org) { return org.id === orgId; }) || null;
    }
    function availableToAdd(portfolio) {
        return organizations.filter(function(org) {
            return !org.archived && portfolio.orgIds.indexOf(org.id) === -1;
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
        text: "MY PORTFOLIOS // LOCAL GROUPS"
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Group LLCs and nonprofits under one or more personal portfolio names. " +
              "Grouping is local organization, not verified membership or permission " +
              "to access any company's data."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: !editor.editable
        text: !portfolioStore ? "PORTFOLIO STORAGE // UNAVAILABLE"
              : portfolioStore.state === "error"
              ? "PORTFOLIO STORAGE ERROR // " + portfolioStore.errorCode
              : "PORTFOLIO STORAGE // " + portfolioStore.state.toUpperCase()
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 152
        height: 28
        label: "RELOAD PORTFOLIOS"
        labelPixelSize: 9
        interactive: portfolioStore !== null
                     && portfolioStore.state !== "saving"
        onTriggered: portfolioStore.refresh()
    }
    Row {
        width: parent.width
        spacing: 6
        Rectangle {
            width: Math.max(100, parent.width - 148)
            height: 30
            color: Colors.black
            border.color: Colors.cyan
            TextInput {
                id: createName
                anchors.fill: parent
                anchors.margins: 6
                color: Colors.white
                font.pixelSize: 11
                maximumLength: 80
                enabled: editor.editable
                clip: true
                verticalAlignment: TextInput.AlignVCenter
            }
            Text {
                anchors.left: parent.left
                anchors.leftMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                text: "Portfolio name"
                color: Colors.cyan
                opacity: 0.65
                font.pixelSize: 10
                visible: createName.text.length === 0
            }
        }
        ActionButton {
            width: 136
            height: 30
            label: "+ PORTFOLIO"
            labelPixelSize: 9
            interactive: editor.editable && createName.text.trim().length > 0
            onTriggered: {
                if (portfolioStore.createPortfolio(createName.text))
                    createName.text = "";
            }
        }
    }
    ActionButton {
        width: 170
        height: 28
        visible: !editor.useSharedArchiveControl
        label: showArchived ? "HIDE ARCHIVED" : "SHOW ARCHIVED"
        labelPixelSize: 9
        onTriggered: {
            editor.showArchived = !editor.showArchived;
            editor.confirmationKey = "";
        }
    }
    Text {
        width: parent.width
        visible: editor.editable && editor.portfolios.length === 0
        text: "No local portfolios saved yet. You can group multiple companies " +
              "without changing their individual records."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }

    Repeater {
        model: editor.portfolios
        delegate: Column {
            id: portfolioRow
            required property var modelData
            width: editor.width
            spacing: 6
            visible: (!modelData.archived || editor.showArchived)
                     && editor.matchesPortfolio(modelData)
            height: visible ? implicitHeight : 0
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.3
            }
            Text {
                width: parent.width
                text: "PORTFOLIO // " + modelData.id +
                      (modelData.archived ? " // ARCHIVED" : " // LOCAL ONLY") +
                      " // " + modelData.orgIds.length + " ORGANIZATIONS"
                font.pixelSize: 10
                font.bold: true
                color: modelData.archived ? Colors.orange : Colors.cyan
                wrapMode: Text.WordWrap
            }
            Row {
                width: parent.width
                spacing: 6
                Rectangle {
                    width: Math.max(100, parent.width - 202)
                    height: 30
                    color: Colors.black
                    border.color: Colors.cyan
                    TextInput {
                        id: portfolioName
                        anchors.fill: parent
                        anchors.margins: 6
                        text: portfolioRow.modelData.name
                        font.pixelSize: 10
                        color: Colors.white
                        maximumLength: 80
                        readOnly: !editor.editable || portfolioRow.modelData.archived
                        clip: true
                        verticalAlignment: TextInput.AlignVCenter
                    }
                }
                ActionButton {
                    width: 62
                    height: 30
                    label: "SAVE"
                    labelPixelSize: 9
                    interactive: editor.editable && !portfolioRow.modelData.archived
                    onTriggered: portfolioStore.renamePortfolio(
                        portfolioRow.modelData.id, portfolioName.text)
                }
                ActionButton {
                    width: 128
                    height: 30
                    label: portfolioRow.modelData.archived ? "RESTORE"
                           : editor.confirmationKey === "p:" + portfolioRow.modelData.id
                           ? "CONFIRM ARCHIVE" : "ARCHIVE"
                    labelPixelSize: 8
                    accentColor: Colors.orange
                    interactive: editor.editable
                    onTriggered: {
                        if (portfolioRow.modelData.archived)
                            portfolioStore.restorePortfolio(portfolioRow.modelData.id);
                        else if (editor.confirmationKey ===
                                 "p:" + portfolioRow.modelData.id) {
                            portfolioStore.archivePortfolio(portfolioRow.modelData.id);
                            editor.confirmationKey = "";
                        } else
                            editor.confirmationKey = "p:" + portfolioRow.modelData.id;
                    }
                }
            }
            Column {
                width: parent.width - 16
                x: 16
                spacing: 6
                visible: !portfolioRow.modelData.archived
                height: visible ? implicitHeight : 0
                Text {
                    width: parent.width
                    text: "IN THIS PORTFOLIO"
                    font.pixelSize: 9
                    font.bold: true
                    color: Colors.cyan
                }
                Text {
                    width: parent.width
                    visible: portfolioRow.modelData.orgIds.length === 0
                    text: "No organizations assigned to this local portfolio yet."
                    font.pixelSize: 10
                    color: Colors.white
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: portfolioRow.modelData.orgIds
                    delegate: Row {
                        id: memberRow
                        required property string modelData
                        readonly property var currentOrg:
                            editor.organizationFor(modelData)
                        width: parent.width
                        height: 29
                        spacing: 6
                        Text {
                            width: Math.max(100, parent.width - 138)
                            height: 29
                            verticalAlignment: Text.AlignVCenter
                            text: memberRow.currentOrg
                                  ? memberRow.currentOrg.name +
                                    (memberRow.currentOrg.archived
                                     ? " // ARCHIVED" : "")
                                  : "MISSING ORGANIZATION // " + memberRow.modelData
                            color: memberRow.currentOrg && !memberRow.currentOrg.archived
                                   ? Colors.white : Colors.orange
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                        ActionButton {
                            width: 132
                            height: 28
                            label: editor.confirmationKey ===
                                   "member:" + portfolioRow.modelData.id +
                                   ":" + memberRow.modelData
                                   ? "CONFIRM REMOVE" : "REMOVE FROM GROUP"
                            labelPixelSize: 8
                            accentColor: Colors.orange
                            interactive: editor.editable
                            onTriggered: {
                                const key = "member:" + portfolioRow.modelData.id +
                                            ":" + memberRow.modelData;
                                if (editor.confirmationKey === key) {
                                    portfolioStore.detachOrganization(
                                        portfolioRow.modelData.id, memberRow.modelData);
                                    editor.confirmationKey = "";
                                } else {
                                    editor.confirmationKey = key;
                                }
                            }
                        }
                    }
                }
                Text {
                    width: parent.width
                    text: "ADD EXISTING ORGANIZATION"
                    font.pixelSize: 9
                    font.bold: true
                    color: Colors.cyan
                }
                Flow {
                    width: parent.width
                    spacing: 5
                    height: childrenRect.height
                    Repeater {
                        model: editor.availableToAdd(portfolioRow.modelData)
                        delegate: ActionButton {
                            required property var modelData
                            width: Math.min(200, Math.max(105, portfolioRow.width - 20))
                            height: 29
                            label: "+ " + modelData.name
                            labelPixelSize: 9
                            interactive: editor.editable
                            onTriggered: portfolioStore.attachOrganization(
                                portfolioRow.modelData.id, modelData.id)
                        }
                    }
                }
                Text {
                    width: parent.width
                    visible: editor.organizations.length === 0
                    text: "Add organizations in MY ORGANIZATIONS above first."
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
