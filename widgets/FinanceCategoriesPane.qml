import QtQuick
import "../components"

// Category organization and allocation access. This pane never mutates Actual.
Item {
    id: categoryPane
    property var snapshot: null
    property string filterText: ""
    signal editBudgetRequested(var category)
    readonly property var categories: snapshot && Array.isArray(snapshot.categories)
        ? snapshot.categories : []
    readonly property var displayed: {
        const needle=filterText.trim().toLowerCase();
        if(!needle)return categories;
        return categories.filter(function(c){
            return c && (String(c.name||"").toLowerCase().indexOf(needle)>=0
                 || String(c.group||"").toLowerCase().indexOf(needle)>=0);
        });
    }
    width: parent ? parent.width : 0
    height: content.implicitHeight
    Column {
        id: content
        width: categoryPane.width
        spacing: 7
        GohuText {
            width: parent.width
            text: "CATEGORIES"
            font.pixelSize: 12
            color: Colors.cyan
        }
        Rectangle {
            width: parent.width
            height: 30
            color: Colors.dark
            border.color: Colors.cyan
            TextInput {
                anchors.fill: parent
                anchors.margins: 6
                text: categoryPane.filterText
                color: Colors.white
                font.pixelSize: 11
                selectByMouse: true
                onTextEdited: categoryPane.filterText=text
            }
        }
        GohuText {
            width: parent.width
            text: "CATEGORY / GROUP // "+categoryPane.displayed.length
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
        Repeater {
            model: categoryPane.displayed
            delegate: Rectangle {
                id: item
                required property var modelData
                width: content.width
                height: 63
                color: Colors.black
                border.color: modelData.availableCents<0?Colors.orange:Colors.cyan
                GohuText {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.leftMargin: 5
                    anchors.topMargin: 4
                    width: parent.width-10
                    text: modelData.name+" / "+modelData.group
                    font.pixelSize: 10
                    color: Colors.white
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                }
                GohuText {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 5
                    anchors.bottomMargin: 8
                    width: parent.width-97
                    text: "SET $"+(modelData.budgetedCents/100).toFixed(2)
                        +"  LEFT $"+(modelData.availableCents/100).toFixed(2)
                    font.pixelSize: 9
                    color: Colors.cyan
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                }
                ActionButton {
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 5
                    width: 85
                    height: 25
                    label: "EDIT SET"
                    labelPixelSize: 9
                    accentColor: Colors.orange
                    trackLabelGlowLocally: true
                    onLeftClicked: categoryPane.editBudgetRequested(item.modelData)
                }
            }
        }
        GohuText {
            width: parent.width
            visible: categoryPane.displayed.length===0
            text: "NO MATCHING CATEGORIES"
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
        }
        GohuText {
            width: parent.width
            text: "CREATE / RENAME / DELETE CATEGORIES REQUIRES A SEPARATE GUARDED WRITER"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
