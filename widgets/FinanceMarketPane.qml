import QtQuick
import "../components"

// FinanceW Market M1: in-place public-market explorer.
// The service is owned by FinanceW, not the pane or the resizing surface.
Item {
    id: pane
    property var marketFeed: null
    property var stockFeed: null
    property string displayLevel: "compact"
    property int selectedIndex: 0
    readonly property bool wide: width >= 660
    readonly property var markets:
        marketFeed && marketFeed.snapshot ? marketFeed.snapshot.markets : []
    readonly property var selected:
        selectedIndex >= 0 && selectedIndex < markets.length
            ? markets[selectedIndex] : null
    // The scroll viewport, not the independent market-detail panel, owns
    // the track. FULL is the preferred narrow-window layout.
    property string marketScrollPolicy: "fill" // fill | split | fixed
    property int fixedMarketListHeight: 210
    property bool narrowDetailOpen: false
    onMarketScrollPolicyChanged: narrowDetailOpen = false
    onWideChanged: { if (wide) narrowDetailOpen = false; }
    // Tool selection is independent of FinanceW main modes and window size.
    property string activeTool: "markets"
    onActiveToolChanged: { if (activeTool !== "markets") narrowDetailOpen = false; }
    onMarketsChanged: {
        selectedIndex = 0;
        narrowDetailOpen = false;
    }

    Row {
        id: marketToolStrip
        anchors.top: parent.top
        anchors.topMargin: 4
        anchors.left: parent.left
        height: 32
        spacing: 6

        ActionButton {
            width: 106
            height: 28
            label: "POLYMARKET"
            labelPixelSize: 10
            selected: pane.activeTool === "markets"
            accentColor: Colors.cyan
            onLeftClicked: pane.activeTool = "markets"
        }
        ActionButton {
            width: 90
            height: 28
            label: "OSIRIS"
            labelPixelSize: 10
            selected: pane.activeTool === "osiris"
            accentColor: Colors.orange
            onLeftClicked: pane.activeTool = "osiris"
        }
        ActionButton {
            width: 90
            height: 28
            label: "STOCKS"
            labelPixelSize: 10
            selected: pane.activeTool === "stocks"
            accentColor: Colors.magenta
            onLeftClicked: pane.activeTool = "stocks"
        }
    }

    Item {
        id: marketsView
        anchors.top: marketToolStrip.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: pane.activeTool === "markets"

        GohuText {
            id: title
            anchors.top: parent.top
            anchors.topMargin: 12
            anchors.left: parent.left
            anchors.right: refreshButton.left
            anchors.rightMargin: 8
            height: 28
            verticalAlignment: Text.AlignVCenter
            font.bold: true
            font.pixelSize: 13
            color: Colors.cyan
            text: "POLYMARKET // EXPLORER"
            elide: Text.ElideRight
        }

        ActionButton {
            id: refreshButton
            anchors.top: title.top
            anchors.right: parent.right
            width: 78
            height: 27
            label: marketFeed && marketFeed.loading ? "READING" : "REFRESH"
            labelPixelSize: 10
            accentColor: Colors.cyan
            available: marketFeed && marketFeed.monitoring && !marketFeed.loading
            onLeftClicked: marketFeed.refresh()
        }

        GohuText {
            id: status
            anchors.top: title.bottom
            anchors.topMargin: 4
            anchors.left: parent.left
            anchors.right: parent.right
            font.pixelSize: 9
            color: marketFeed && marketFeed.state === "failed" ? Colors.red : Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            text: marketFeed ? marketFeed.message : "Market feed is not connected."
        }

        // Layout control changes the viewport allocation, not track geometry.
        Row {
            id: marketLayoutControls
            anchors.top: status.bottom
            anchors.topMargin: 5
            anchors.left: parent.left
            anchors.right: parent.right
            height: visible ? 25 : 0
            spacing: 5
            visible: !pane.wide
            Repeater {
                model: [
                    {mode:"fill", label:"FULL"},
                    {mode:"split", label:"SPLIT"},
                    {mode:"fixed", label:"FIXED"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(0, (marketLayoutControls.width - 10) / 3)
                    height: 24
                    label: modelData.label
                    labelPixelSize: 9
                    accentColor: Colors.magenta
                    selected: pane.marketScrollPolicy === modelData.mode
                    onLeftClicked: pane.marketScrollPolicy = modelData.mode
                }
            }
        }

        Item {
            id: body
            anchors.top: marketLayoutControls.visible
                         ? marketLayoutControls.bottom : status.bottom
            anchors.topMargin: marketLayoutControls.visible ? 8 : 12
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: footer.top
            anchors.bottomMargin: 7

            Rectangle {
                id: marketList
                anchors.left: parent.left
                anchors.top: parent.top
                width: pane.wide ? Math.max(245, Math.round(parent.width * 0.39)) : parent.width
                height: pane.wide ? parent.height : marketScrollPane.preferredExtent
                visible: pane.wide || pane.marketScrollPolicy !== "fill"
                         || !pane.narrowDetailOpen
                color: Colors.dark
                border.color: Colors.cyan
                border.width: 1

                GohuText {
                    id: marketListTitle
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 8
                    font.pixelSize: 10
                    color: Colors.white
                    text: "ACTIVE BINARY MARKETS // " + pane.markets.length
                }

                NeonScrollPaneV2 {
                    id: marketScrollPane
                    objectName: "financeMarketScrollPane"
                    anchors.top: marketListTitle.bottom
                    anchors.topMargin: 7
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 4
                    viewportPolicy: pane.wide ? "fill" : pane.marketScrollPolicy
                    availableExtent: body.height
                    splitFraction: 0.46
                    fixedExtent: pane.fixedMarketListHeight
                    contentExtent: marketRows.height
                    handleStyle: "bar"
                    rightInset: 2

                    Column {
                        id: marketRows
                        width: Math.max(0, marketScrollPane.flickable.width - marketScrollPane.contentGutter)
                        spacing: 3
                        Repeater {
                            model: pane.markets
                            delegate: Rectangle {
                                id: marketRow
                                required property var modelData
                                required property int index
                                width: marketRows.width
                                height: 57
                                color: pane.selectedIndex === index ? Colors.dark : Colors.black
                                border.width: 1
                                border.color: pane.selectedIndex === index ? Colors.magenta : Colors.cyan
                                opacity: pane.selectedIndex === index ? 1 : 0.75

                                GohuText {
                                    anchors.top: parent.top
                                    anchors.topMargin: 6
                                    anchors.left: parent.left
                                    anchors.leftMargin: 6
                                    anchors.right: parent.right
                                    anchors.rightMargin: 5
                                    text: marketRow.modelData.question
                                    textFormat: Text.PlainText
                                    font.pixelSize: 10
                                    color: Colors.white
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 6
                                    anchors.left: parent.left
                                    anchors.leftMargin: 6
                                    text: "YES " + marketRow.modelData.yesPct.toFixed(1) + "%"
                                    font.pixelSize: 10
                                    color: Colors.cyan
                                }
                                GohuText {
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 6
                                    anchors.right: parent.right
                                    anchors.rightMargin: 6
                                    text: marketRow.modelData.volume24h === null
                                        ? "24H N/A"
                                        : "24H $" + marketRow.modelData.volume24h.toLocaleString()
                                    font.pixelSize: 9
                                    color: Colors.orange
                                }
                                TapHandler {
                                    onTapped: {
                                        pane.selectedIndex = marketRow.index;
                                        if (!pane.wide && pane.marketScrollPolicy === "fill")
                                            pane.narrowDetailOpen = true;
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: marketDetail
                visible: pane.wide || pane.marketScrollPolicy !== "fill"
                         || pane.narrowDetailOpen
                anchors.top: (pane.wide || pane.marketScrollPolicy === "fill")
                             ? parent.top : marketList.bottom
                anchors.topMargin: (pane.wide || pane.marketScrollPolicy === "fill")
                                   ? 0 : 8
                anchors.left: pane.wide ? marketList.right : parent.left
                anchors.leftMargin: pane.wide ? 8 : 0
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                color: Colors.dark
                border.color: Colors.cyan
                border.width: 1
                clip: true

                ActionButton {
                    id: backToMarketList
                    visible: !pane.wide && pane.marketScrollPolicy === "fill"
                             && pane.narrowDetailOpen
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.top: parent.top
                    anchors.topMargin: 6
                    width: 61
                    height: 24
                    label: "BACK"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    onLeftClicked: pane.narrowDetailOpen = false
                }

                GohuText {
                    id: detailTitle
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: backToMarketList.visible
                                   ? backToMarketList.left : parent.right
                    anchors.margins: 10
                    font.pixelSize: 11
                    color: Colors.white
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    text: pane.selected ? pane.selected.question : "SELECT A PUBLIC MARKET"
                }

                GohuText {
                    id: yesLabel
                    anchors.top: detailTitle.bottom
                    anchors.topMargin: 14
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    text: pane.selected ? "YES  " + pane.selected.yesPct.toFixed(1) + "%" : "NO MARKET SELECTED"
                    font.pixelSize: 16
                    color: Colors.cyan
                }

                Rectangle {
                    id: probabilityTrack
                    anchors.top: yesLabel.bottom
                    anchors.topMargin: 9
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    height: 14
                    color: Colors.black
                    border.color: Colors.white
                    border.width: 1
                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: pane.selected
                            ? (parent.width - 2) * pane.selected.yesPct / 100 : 0
                        color: Colors.cyan
                    }
                }

                GohuText {
                    id: noLabel
                    anchors.top: probabilityTrack.bottom
                    anchors.topMargin: 7
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    text: pane.selected ? "NO  " + pane.selected.noPct.toFixed(1) + "%" : ""
                    font.pixelSize: 11
                    color: Colors.magenta
                }

                GohuText {
                    id: volumeLabel
                    anchors.top: noLabel.bottom
                    anchors.topMargin: 16
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 10
                    text: pane.selected
                        ? "24H VOLUME  " + (pane.selected.volume24h === null
                            ? "UNAVAILABLE" : "$" + pane.selected.volume24h.toLocaleString())
                        : ""
                    font.pixelSize: 10
                    color: Colors.orange
                }

                GohuText {
                    id: liquidityLabel
                    anchors.top: volumeLabel.bottom
                    anchors.topMargin: 7
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    text: pane.selected
                        ? "LIQUIDITY  " + (pane.selected.liquidity === null
                            ? "UNAVAILABLE" : "$" + pane.selected.liquidity.toLocaleString())
                        : ""
                    font.pixelSize: 10
                    color: Colors.white
                }

                GohuText {
                    id: changeLabel
                    anchors.top: liquidityLabel.bottom
                    anchors.topMargin: 7
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    text: pane.selected
                        ? "24H YES CHANGE  " + (pane.selected.change24hPct === null
                            ? "UNAVAILABLE"
                            : pane.selected.change24hPct.toFixed(1) + " POINTS")
                        : ""
                    font.pixelSize: 9
                    color: Colors.white
                }

                GohuText {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 9
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 10
                    text: "Market-implied price, not an AI forecast or investment advice."
                    font.pixelSize: 9
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                }
            }
        }

        GohuText {
            id: footer
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 23
            font.pixelSize: 9
            color: Colors.white
            elide: Text.ElideRight
            text: "SOURCE: POLYMARKET GAMMA // SNAPSHOT "
                + (marketFeed && marketFeed.snapshot
                    ? marketFeed.snapshot.retrievedAt : "NOT READ")
        }
    }

    FinanceStockHistoryPane {
        id: stocksTool
        anchors.top: marketToolStrip.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: pane.activeTool === "stocks"
        stockFeed: pane.stockFeed
    }

    FinanceOsirisPane {
        id: osirisTool
        anchors.top: marketToolStrip.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: pane.activeTool === "osiris"
        shown: pane.activeTool === "osiris" && pane.visible
    }
}
