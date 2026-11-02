import QtQuick
import "StationCosmosSubjectPanelPolicy.js" as CosmosPanelPolicy

// Reuses existing SKY and SPACE QML instruments. No copied collectors,
// cache writers or provider ownership. CLASSIC routes keep their own loaders.
Rectangle {
    id: cosmosPane
    color: Colors.black

    property string subjectRoute: ""
    property var weatherService: null
    property var spaceService: null
    property var liveHistoryStore: null
    property real runtimeNowMs: Date.now()

    readonly property string kind:
        CosmosPanelPolicy.kindForRoute(subjectRoute)

    Loader {
        id: cosmosLoader
        anchors.fill: parent
        active: cosmosPane.visible && cosmosPane.kind !== ""
        sourceComponent: cosmosPane.kind === "overview"
                         ? overviewComponent : cosmosPane.kind === "sky"
                         ? skyComponent : spaceComponent
    }

    Component {
        id: skyComponent
        StationSky {
            subjectRoute: cosmosPane.subjectRoute
            weatherService: cosmosPane.weatherService
            runtimeNowMs: cosmosPane.runtimeNowMs
        }
    }

    Component {
        id: spaceComponent
        StationSpace {
            subjectRoute: cosmosPane.subjectRoute
            spaceService: cosmosPane.spaceService
            weatherService: cosmosPane.weatherService
            liveHistoryStore: cosmosPane.liveHistoryStore
            runtimeNowMs: cosmosPane.runtimeNowMs
        }
    }

    // Astronomy and solar weather inhabit ONE COSMOS overview workspace,
    // using full-width stacked viewports to preserve Gohu instrument widths.
    // Their original internal star scrollbars allow independent inspection.
    Component {
        id: overviewComponent
        Item {
            id: cosmosOverview
            Rectangle {
                id: astronomyBay
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: Math.max(0, (cosmosOverview.height - 8) / 2)
                color: Colors.black
                clip: true

                StationSky {
                    anchors.fill: parent
                    subjectRoute: cosmosPane.subjectRoute
                    weatherService: cosmosPane.weatherService
                    runtimeNowMs: cosmosPane.runtimeNowMs
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: astronomyBay.bottom
                anchors.topMargin: 8
                anchors.bottom: parent.bottom
                color: Colors.black
                clip: true

                StationSpace {
                    anchors.fill: parent
                    subjectRoute: cosmosPane.subjectRoute
                    spaceService: cosmosPane.spaceService
                    weatherService: cosmosPane.weatherService
                    liveHistoryStore: cosmosPane.liveHistoryStore
                    runtimeNowMs: cosmosPane.runtimeNowMs
                }
            }
        }
    }
}
