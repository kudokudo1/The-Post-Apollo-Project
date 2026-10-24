import QtQuick
import "../components"

// FinanceW Research M1. Displays a saved Crawl snapshot; never launches Scrapy.
// Visible relationships are observed HTML hyperlinks, not inferred facts.
Item {
    id: pane
    property var crawlFeed: null
    property int selectedIndex: 0
    readonly property bool wide: width >= 650
    readonly property var pages: crawlFeed && crawlFeed.snapshot
                                  ? crawlFeed.snapshot.pages : []
    readonly property var selectedPage: selectedIndex >= 0 && selectedIndex < pages.length
                                     ? pages[selectedIndex] : null
    onPagesChanged: selectedIndex = 0

    GohuText {
        id: heading
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.topMargin: 9
        anchors.right: refreshButton.left
        anchors.rightMargin: 5
        text: "SOURCE CRAWL // SCRAPY"
        font.pixelSize: 13
        font.bold: true
        color: Colors.cyan
        elide: Text.ElideRight
    }

    ActionButton {
        id: refreshButton
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: 5
        width: 74
        height: 27
        label: crawlFeed && crawlFeed.loading ? "READING" : "REFRESH"
        labelPixelSize: 9
        accentColor: Colors.cyan
        available: crawlFeed && crawlFeed.monitoring && !crawlFeed.loading
        onLeftClicked: crawlFeed.refresh()
    }

    GohuText {
        id: stateLine
        anchors.top: heading.bottom
        anchors.topMargin: 12
        anchors.left: parent.left
        anchors.right: parent.right
        font.pixelSize: 9
        color: crawlFeed && crawlFeed.state === "failed" ? Colors.red : Colors.orange
        text: crawlFeed ? crawlFeed.message : "NO CRAWL READER"
        textFormat: Text.PlainText
        wrapMode: Text.WordWrap
    }

    GohuText {
        id: counts
        anchors.top: stateLine.bottom
        anchors.topMargin: 7
        anchors.left: parent.left
        anchors.right: parent.right
        text: "PAGES " + pane.pages.length + "  //  LINKS "
            + (crawlFeed && crawlFeed.snapshot ? crawlFeed.snapshot.linkCount : "—")
        textFormat: Text.PlainText
        font.pixelSize: 10
        color: Colors.white
    }

    Item {
        id: body
        anchors.top: counts.bottom
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: footer.top
        anchors.bottomMargin: 6

        Rectangle {
            id: pageList
            anchors.left: parent.left
            anchors.top: parent.top
            width: pane.wide ? Math.max(215, parent.width * 0.35) : parent.width
            height: pane.wide ? parent.height : Math.max(120, parent.height * 0.40)
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            GohuText {
                id: listTitle
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 7
                text: "VISITED PAGES"
                font.pixelSize: 10
                color: Colors.white
            }

            Flickable {
                id: pagesScroll
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: listTitle.bottom
                anchors.bottom: parent.bottom
                anchors.margins: 5
                clip: true
                contentWidth: width
                contentHeight: pageRows.height
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: pageRows
                    width: pagesScroll.width
                    spacing: 4
                    Repeater {
                        model: pane.pages
                        delegate: Rectangle {
                            id: pageRow
                            required property var modelData
                            required property int index
                            width: pageRows.width
                            height: 58
                            color: pane.selectedIndex === index ? Colors.dark : Colors.black
                            border.width: 1
                            border.color: pane.selectedIndex === index
                                          ? Colors.magenta : Colors.cyan
                            GohuText {
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.margins: 5
                                text: pageRow.modelData.title
                                textFormat: Text.PlainText
                                font.pixelSize: 10
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                            GohuText {
                                anchors.bottom: parent.bottom
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.margins: 5
                                text: pageRow.modelData.url
                                textFormat: Text.PlainText
                                font.pixelSize: 9
                                color: Colors.cyan
                                elide: Text.ElideMiddle
                            }
                            TapHandler {
                                onTapped: pane.selectedIndex = pageRow.index
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: detail
            anchors.top: pane.wide ? parent.top : pageList.bottom
            anchors.topMargin: pane.wide ? 0 : 8
            anchors.left: pane.wide ? pageList.right : parent.left
            anchors.leftMargin: pane.wide ? 8 : 0
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            Flickable {
                id: detailsScroll
                anchors.fill: parent
                anchors.margins: 9
                contentWidth: width
                contentHeight: detailContents.height
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: detailContents
                    width: detailsScroll.width
                    spacing: 10
                    GohuText {
                        width: parent.width
                        text: pane.selectedPage ? pane.selectedPage.title
                            : "NO PAGE SELECTED"
                        textFormat: Text.PlainText
                        font.pixelSize: 12
                        color: Colors.magenta
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: pane.selectedPage ? pane.selectedPage.url : ""
                        textFormat: Text.PlainText
                        font.pixelSize: 9
                        color: Colors.cyan
                        wrapMode: Text.WrapAnywhere
                    }
                    GohuText {
                        width: parent.width
                        text: pane.selectedPage
                            ? "CRAWLED // " + pane.selectedPage.observedAt : ""
                        textFormat: Text.PlainText
                        font.pixelSize: 9
                        color: Colors.white
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: "EXTRACTED TEXT"
                        font.pixelSize: 10
                        color: Colors.orange
                    }
                    GohuText {
                        width: parent.width
                        text: pane.selectedPage && pane.selectedPage.snippet
                            ? pane.selectedPage.snippet : "NO EXTRACTED TEXT"
                        textFormat: Text.PlainText
                        font.pixelSize: 10
                        color: Colors.white
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: "DISCOVERED HYPERLINKS // "
                            + (pane.selectedPage ? pane.selectedPage.links.length : 0)
                        font.pixelSize: 10
                        color: Colors.orange
                    }
                    Repeater {
                        model: pane.selectedPage ? pane.selectedPage.links : []
                        delegate: GohuText {
                            required property string modelData
                            width: detailContents.width
                            text: "↗  " + modelData
                            textFormat: Text.PlainText
                            font.pixelSize: 9
                            color: Colors.cyan
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
            }
        }
    }

    GohuText {
        id: footer
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 25
        text: "LOCAL SCRAPY JSON // READ ONLY // NOT LIVE"
        textFormat: Text.PlainText
        font.pixelSize: 9
        color: Colors.orange
        elide: Text.ElideRight
    }
}
