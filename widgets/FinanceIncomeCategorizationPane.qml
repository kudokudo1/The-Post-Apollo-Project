import QtQuick
import "../components"

// D16 income categorization preview. Zero mutating methods, no Process,
// no write authorization, and no assumption that positive means income.
Item {
    id: incomePane
    property var snapshot: null
    property bool expanded: false
    property string selectedTransactionId: ""
    property string selectedAccountId: ""
    property string proposedCategoryId: ""
    readonly property var review: snapshot ? snapshot.incomeReview : null
    readonly property var selectedCandidate: {
        if(!review || !Array.isArray(review.candidates))return null;
        const matches=review.candidates.filter(function(t) {
            return t.id===selectedTransactionId && t.accountId===selectedAccountId;
        });
        return matches.length===1 ? matches[0] : null;
    }
    readonly property var selectedCategory: {
        if(!review || !Array.isArray(review.incomeCategories))return null;
        const matches=review.incomeCategories.filter(function(c) {
            return c.id===proposedCategoryId;
        });
        return matches.length===1 ? matches[0] : null;
    }
    readonly property bool proposalReady: !!selectedCandidate && !!selectedCategory
        && !!snapshot && snapshot.readOnly===true
        && !!snapshot.sourceKey && review && review.month===snapshot.month
        && review.categoriesOverflow!==true

    visible: expanded
    width: parent ? parent.width : 0
    height: visible ? content.implicitHeight+14 : 0

    function clear() {
        expanded=false;
        selectedTransactionId="";
        selectedAccountId="";
        proposedCategoryId="";
    }
    onSnapshotChanged: clear()

    function openReview() {
        if(!review || !snapshot || snapshot.readOnly!==true
                || review.readOnly!==true || review.month!==snapshot.month)
            return false;
        clear();
        expanded=true;
        return true;
    }
    function selectCandidate(item) {
        if(!expanded || !review || !item || !Array.isArray(review.candidates))
            return false;
        const matches=review.candidates.filter(function(t) {
            return t.id===item.id && t.accountId===item.accountId;
        });
        if(matches.length!==1 || !(matches[0].amountCents>0))
            return false;
        selectedTransactionId=item.id;
        selectedAccountId=item.accountId;
        proposedCategoryId="";
        return true;
    }
    function previewCategory(item) {
        if(!expanded || !selectedCandidate || !review
                || review.categoriesOverflow || !item
                || !Array.isArray(review.incomeCategories))
            return false;
        const matches=review.incomeCategories.filter(function(c) {
            return c.id===item.id;
        });
        if(matches.length!==1)return false;
        proposedCategoryId=item.id;
        return true;
    }

    Rectangle {
        anchors.fill: parent
        color: Colors.black
        border.color: Colors.cyan
        border.width: 1
    }
    Column {
        id: content
        x: 7
        y: 7
        width: Math.max(0,incomePane.width-14)
        spacing: 6
        GohuText {
            width: parent.width
            text: "INCOMING TRANSACTIONS // CATEGORY PREVIEW"
            font.pixelSize: 10
            color: Colors.cyan
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: incomePane.review
                ? "POTENTIAL ITEMS // "+incomePane.review.candidateCount
                  +" / DISPLAYED "+incomePane.review.showingCount : "NO REVIEW DATA"
            color: Colors.white
            font.pixelSize: 9
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: incomePane.review && incomePane.review.truncated
            text: "LIST LIMITED TO 12 // REVIEW REMAINING ITEMS IN ACTUAL"
            color: Colors.orange
            font.pixelSize: 9
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: incomePane.review && incomePane.review.candidateCount===0
            text: "NO POSITIVE UNCATEGORIZED ITEMS IN SELECTED MONTH"
            color: Colors.cyan
            font.pixelSize: 9
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: incomePane.review ? incomePane.review.candidates : []
            delegate: Rectangle {
                required property var modelData
                width: content.width
                height: 72
                color: Colors.black
                border.color: incomePane.selectedTransactionId===modelData.id
                    && incomePane.selectedAccountId===modelData.accountId
                    ? Colors.magenta : Colors.cyan
                Column {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.leftMargin: 5
                    anchors.topMargin: 5
                    width: parent.width-10
                    spacing: 4
                    GohuText {
                        width: parent.width
                        text: modelData.date+" // "+root.moneyText(modelData.amountCents)
                        font.pixelSize: 10
                        textFormat: Text.PlainText
                        color: Colors.white
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        text: modelData.accountName+" // UNCATEGORIZED"
                        font.pixelSize: 9
                        textFormat: Text.PlainText
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }
                ActionButton {
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 4
                    width: 74
                    height: 23
                    label: "REVIEW"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    trackLabelGlowLocally: true
                    onLeftClicked: incomePane.selectCandidate(modelData)
                }
            }
        }
        GohuText {
            width: parent.width
            visible: !!incomePane.selectedCandidate
            text: "PROPOSE INCOME CATEGORY // REVIEW ONLY"
            font.pixelSize: 10
            color: Colors.cyan
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: !!incomePane.selectedCandidate
                && !!incomePane.review && incomePane.review.categoriesOverflow
            text: "TOO MANY INCOME CATEGORIES // REVIEW IN ACTUAL"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: !!incomePane.selectedCandidate && !!incomePane.review
                && incomePane.review.incomeCategories.length===0
                && !incomePane.review.categoriesOverflow
            text: "NO VISIBLE INCOME CATEGORY // CHECK ACTUAL"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: incomePane.selectedCandidate && incomePane.review
                && !incomePane.review.categoriesOverflow
                ? incomePane.review.incomeCategories : []
            delegate: ActionButton {
                required property var modelData
                width: content.width
                height: 25
                label: modelData.name
                labelPixelSize: 9
                accentColor: incomePane.proposedCategoryId===modelData.id
                    ? Colors.magenta : Colors.cyan
                trackLabelGlowLocally: true
                onLeftClicked: incomePane.previewCategory(modelData)
            }
        }
        GohuText {
            width: parent.width
            visible: incomePane.proposalReady
            text: incomePane.proposalReady
                ? "PREVIEW // "+incomePane.selectedCandidate.date+" / "
                  +root.moneyText(incomePane.selectedCandidate.amountCents)
                  +" / UNCATEGORIZED → "+incomePane.selectedCategory.name : ""
            font.pixelSize: 9
            color: Colors.white
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "POSITIVE IS NOT PROOF OF INCOME // CHECK SOURCE IN ACTUAL"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "PREVIEW ONLY // NO WRITE // TO BUDGET NOT RECALCULATED"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: parent.width
            height: 26
            label: "CLOSE PREVIEW"
            labelPixelSize: 9
            accentColor: Colors.orange
            trackLabelGlowLocally: true
            onLeftClicked: incomePane.clear()
        }
    }
}
