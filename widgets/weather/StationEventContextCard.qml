import QtQuick
import "../../components"
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy

Rectangle {
    id: card

    property var eventContext: null
    property real weatherFixDistanceKm: -1
    property var radarContext: null
    property var lightningContext: null
    property var floodContext: null
    property var timelineRows: []
    property var relationshipRows: []
    property var companions: []
    property bool archiveAvailable: false
    property int archiveSnapshotCount: 0
    property string archiveStatusText: "NOT ARCHIVED"
    property real runtimeNowMs: Date.now()
    signal archiveRequested()
    property color accentColor: Colors.magenta

    readonly property int companionCount:
        Array.isArray(companions) ? companions.length : 0
    readonly property int timelineCount:
        Array.isArray(timelineRows) ? timelineRows.length : 0
    readonly property int relationshipCount:
        Array.isArray(relationshipRows) ? relationshipRows.length : 0
    readonly property bool floodRelevant:
        !!floodContext && floodContext.relevant === true
    readonly property int floodHeight:
        !floodRelevant ? 0
        : floodContext.available ? 198 : 64

    function timelineAgeMinutes(row) {
        return RuntimePolicy.ageMinutes(
            row ? row.timeMs : null,
            runtimeNowMs
        );
    }

    function timelineAgeLabel(row) {
        const minutes = timelineAgeMinutes(row);
        return minutes < 0
            ? "AGE --"
            : "AGE " + RuntimePolicy.compactAgeMinutes(minutes);
    }

    function timelineRecencyBand(row) {
        const minutes = timelineAgeMinutes(row);
        if (minutes < 0)
            return "UNKNOWN";
        if (minutes <= 15)
            return "FRESH";
        if (minutes <= 60)
            return "RECENT";
        if (minutes <= 360)
            return "AGING";
        return "OLDER";
    }

    function timelineFreshnessLabel(row) {
        const mode = String(
            row && row.freshnessMode
            ? row.freshnessMode : "AGE_ONLY"
        );
        if (mode === "AGE_ONLY")
            return "AGE ONLY";
        if (mode === "SNAPSHOT")
            return "SNAPSHOT";
        if (mode !== "PROVIDER_CONTRACT")
            return "UNKNOWN";

        const sourceId = row
            ? String(row.runtimeSourceId || "") : "";
        const spec = RuntimePolicy.sourceSpec(sourceId);
        if (!spec)
            return "UNKNOWN";

        const band = RuntimePolicy.temporalBand(
            spec,
            row ? row.receivedAtMs : null,
            runtimeNowMs
        );
        return "CONTRACT " + band;
    }

    visible: eventContext !== null
    width: parent ? parent.width : 0
    height: visible
        ? 292
          + Math.min(4, companionCount) * 42
          + Math.min(6, timelineCount) * 48
          + (relationshipCount > 0 ? 30 : 0)
          + Math.min(8, relationshipCount) * 58
          + floodHeight
        : 0

    color: Colors.dark
    border.width: 1
    border.color: accentColor

    Column {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 5

        Row {
            width: parent.width
            spacing: 10

            GohuText {
                width: Math.max(0, parent.width - 180)
                text: "CROSS-DOMAIN EVENT CONTEXT"
                font.pixelSize: 12
                color: Colors.magenta
                elide: Text.ElideRight
            }

            GohuText {
                width: 170
                text: card.eventContext
                    ? card.eventContext.sourceLabel : ""
                horizontalAlignment: Text.AlignRight
                font.pixelSize: 10
                color: card.accentColor
                elide: Text.ElideRight
            }
        }

        GohuText {
            width: parent.width
            text: card.eventContext
                ? card.eventContext.title : ""
            font.pixelSize: 13
            color: Colors.white
            elide: Text.ElideRight
        }

        QuietText {
            width: parent.width
            text: card.eventContext
                ? card.eventContext.typeLabel
                    + " // " + card.eventContext.coordinates
                    + " // " + card.eventContext.timeLabel
                : ""
            font.pixelSize: 9
            elide: Text.ElideRight
        }

        Row {
            width: parent.width
            height: 27
            spacing: 8

            ActionButton {
                width: 116
                height: 26
                label: "ARCHIVE"
                labelPixelSize: 9
                accentColor: Colors.magenta
                available: card.archiveAvailable
                onClicked: card.archiveRequested()
            }

            QuietText {
                anchors.verticalCenter: parent.verticalCenter
                width: Math.max(0, parent.width - 124)
                text: card.archiveStatusText
                    + " // OPERATOR SNAPSHOT // SOURCE IDENTITY PRESERVED"
                font.pixelSize: 8
                color: card.archiveSnapshotCount > 0
                    ? Colors.cyan : Colors.orange
                elide: Text.ElideRight
            }
        }

        QuietText {
            width: parent.width
            text: card.weatherFixDistanceKm >= 0
                ? "WEATHER FIX // "
                    + Math.round(card.weatherFixDistanceKm)
                    + " KM FROM EVENT // DISTANCE ONLY"
                : "WEATHER FIX // POINT DISTANCE UNAVAILABLE"
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            text: card.radarContext
                ? "MRMS // " + card.radarContext.status
                    + (card.radarContext.available
                       ? " // " + card.radarContext.frameLabel
                         + " // " + card.radarContext.timeLabel
                         + (card.radarContext.usingCache ? " // CACHE" : "")
                       : "")
                : "MRMS // NO LOADED FRAME"
            font.pixelSize: 9
            color: card.radarContext
                   && card.radarContext.covered
                   ? Colors.green : Colors.orange
            elide: Text.ElideRight
        }

        QuietText {
            width: parent.width
            text: "RADAR CONTEXT = GEOMETRIC FRAME COVERAGE ONLY // IMAGE PIXELS ARE NOT INTERPRETED"
            font.pixelSize: 8
            color: Colors.orange
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            text: card.lightningContext
                ? "LIGHTNING // " + card.lightningContext.status
                    + (card.lightningContext.available
                       ? " // " + card.lightningContext.windowMinutes
                         + "M DENSITY // "
                         + card.lightningContext.timeLabel
                         + (card.lightningContext.usingCache
                            ? " // CACHE" : "")
                       : "")
                : "LIGHTNING // NO LOADED LIGHTNING FRAME"
            font.pixelSize: 9
            color: card.lightningContext
                   && card.lightningContext.covered
                   ? Colors.magenta : Colors.orange
            elide: Text.ElideRight
        }

        QuietText {
            width: parent.width
            text: "LIGHTNING CONTEXT = GEOMETRIC FRAME COVERAGE ONLY // DENSITY PIXELS ARE NOT INTERPRETED"
            font.pixelSize: 8
            color: Colors.orange
            elide: Text.ElideRight
        }

        Column {
            width: parent.width
            spacing: 4
            visible: card.floodRelevant

            GohuText {
                width: parent.width
                text: "FLOOD DOSSIER // NOAA NWPS"
                font.pixelSize: 10
                color: Colors.cyan
            }

            QuietText {
                width: parent.width
                text: card.floodContext
                    ? card.floodContext.reason : ""
                font.pixelSize: 8
                color: card.floodContext
                       && card.floodContext.available
                       ? Colors.green : Colors.orange
                elide: Text.ElideRight
            }

            GohuText {
                visible: card.floodContext
                         && card.floodContext.available
                width: parent.width
                text: card.floodContext
                    ? card.floodContext.gaugeName
                      + " // LID " + card.floodContext.gaugeId
                      + " // EVENT "
                      + Math.round(
                          card.floodContext.eventGaugeDistanceKm
                        )
                      + " KM // FIX "
                      + Math.round(
                          card.floodContext.weatherFixGaugeDistanceKm
                        )
                      + " KM"
                    : ""
                font.pixelSize: 9
                color: Colors.white
                elide: Text.ElideRight
            }

            QuietText {
                visible: card.floodContext
                         && card.floodContext.available
                width: parent.width
                text: card.floodContext
                    ? "OBSERVED "
                      + card.floodContext.observedCategory
                      + " // "
                      + card.floodContext.observedReading
                      + " // FORECAST "
                      + card.floodContext.forecastCategory
                    : ""
                font.pixelSize: 8
                color: Colors.cyan
                elide: Text.ElideRight
            }

            QuietText {
                visible: card.floodContext
                         && card.floodContext.available
                         && card.floodContext.contextAvailable
                width: parent.width
                text: {
                    const state = card.floodContext
                        ? card.floodContext.thresholdContext : null;
                    if (!state)
                        return "OBSERVED THRESHOLD // UNAVAILABLE";
                    if (!state.available)
                        return "OBSERVED THRESHOLD // "
                            + state.reason;
                    if (!state.supported)
                        return "OBSERVED THRESHOLD // CLAIM WITHHELD // "
                            + state.reason;
                    if (!state.thresholdId)
                        return "OBSERVED THRESHOLD // BELOW ACTION // "
                            + state.categoryLabel;
                    let value = "OBSERVED THRESHOLD // "
                        + state.thresholdLabel
                        + " MET @ "
                        + Number(state.thresholdValue).toFixed(2)
                        + " " + state.units
                        + " // OBS "
                        + Number(state.observedValue).toFixed(2)
                        + " " + state.units;
                    if (state.crossedInSeries)
                        value += " // CROSSING OBSERVED "
                            + state.crossingFromTimeLabel
                            + " → " + state.crossingToTimeLabel;
                    else
                        value += " // CATEGORY ALIGNED";
                    if (state.nextThresholdLabel
                            && state.nextGap !== null)
                        value += " // NEXT "
                            + state.nextThresholdLabel
                            + " +"
                            + Number(state.nextGap).toFixed(2)
                            + " " + state.units;
                    return value;
                }
                font.pixelSize: 8
                color: card.floodContext
                       && card.floodContext.thresholdContext
                       && card.floodContext.thresholdContext.supported
                       ? Colors.green : Colors.orange
                elide: Text.ElideRight
            }

            QuietText {
                visible: card.floodContext
                         && card.floodContext.available
                         && card.floodContext.thresholds.length > 0
                width: parent.width
                text: card.floodContext
                    ? "OFFICIAL THRESHOLDS // "
                      + card.floodContext.thresholds.map(
                          function(row) {
                              return row.label + " "
                                  + (row.stage === null
                                     ? "--"
                                     : Number(row.stage).toFixed(2));
                          }
                        ).join(" // ")
                    : ""
                font.pixelSize: 8
                color: Colors.magenta
                elide: Text.ElideRight
            }

            QuietText {
                visible: card.floodContext
                         && card.floodContext.available
                         && card.floodContext.impacts.length > 0
                width: parent.width
                text: card.floodContext
                    ? "IMPACT CONTEXT // "
                      + card.floodContext.impacts.map(
                          function(row) {
                              return Number(row.stage).toFixed(2)
                                  + " // " + row.statement;
                          }
                        ).join(" | ")
                    : ""
                font.pixelSize: 8
                color: Colors.orange
                elide: Text.ElideRight
            }

            QuietText {
                width: parent.width
                text: "NEARBY GAUGE EVIDENCE ONLY // EVENT POINT ≠ GAUGE CATCHMENT // NOT A FLOOD WARNING"
                font.pixelSize: 8
                color: Colors.orange
                elide: Text.ElideRight
            }
        }

        GohuText {
            width: parent.width
            text: "NEARBY INDEPENDENT MAP RECORDS // "
                + card.companionCount
                + " WITHIN 250 KM"
            font.pixelSize: 9
            color: Colors.cyan
        }

        Repeater {
            model: Array.isArray(card.companions)
                ? card.companions.slice(0, 4) : []

            delegate: Rectangle {
                required property var modelData
                width: card.width - 20
                height: 37
                color: Colors.black
                border.width: 1
                border.color: Colors.blue

                Row {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 8

                    GohuText {
                        width: 88
                        text: modelData.sourceLabel
                        font.pixelSize: 9
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: 70
                        text: Math.round(modelData.distanceKm) + " KM"
                        font.pixelSize: 9
                        color: Colors.cyan
                    }

                    QuietText {
                        width: Math.max(0, parent.width - 174)
                        text: modelData.typeLabel
                            + " // " + modelData.title
                        font.pixelSize: 8
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Column {
            width: parent.width
            spacing: 4
            visible: card.relationshipCount > 0

            GohuText {
                width: parent.width
                text: "RELATIONSHIP BASIS // WHY THIS EVIDENCE IS SHOWN"
                font.pixelSize: 10
                color: Colors.cyan
            }

            Repeater {
                model: Array.isArray(card.relationshipRows)
                    ? card.relationshipRows.slice(0, 8) : []

                delegate: Rectangle {
                    required property var modelData
                    width: card.width - 20
                    height: 53
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.blue

                    Column {
                        anchors.fill: parent
                        anchors.margins: 5
                        spacing: 2

                        Row {
                            width: parent.width
                            spacing: 7

                            GohuText {
                                width: 116
                                text: modelData.evidenceClass
                                font.pixelSize: 8
                                color: Colors.blue
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: 116
                                text: modelData.sourceLabel
                                font.pixelSize: 8
                                color: Colors.magenta
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: Math.max(0, parent.width - 246)
                                text: modelData.relationClass
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }

                        QuietText {
                            width: parent.width
                            text: "SPACE // " + modelData.spatialLabel
                                + " // TIME // " + modelData.temporalLabel
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }

                        QuietText {
                            width: parent.width
                            text: modelData.reason
                                + " // LIMIT // "
                                + modelData.limitation
                            font.pixelSize: 8
                            color: Colors.orange
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            QuietText {
                width: parent.width
                text: "RELATIONSHIP BASIS EXPLAINS INCLUSION ONLY // NO SCORE // NO CAUSAL CLAIM // NO INCIDENT MERGE"
                font.pixelSize: 8
                color: Colors.orange
                elide: Text.ElideRight
            }
        }

        Column {
            width: parent.width
            spacing: 4
            visible: card.timelineCount > 0

            GohuText {
                width: parent.width
                text: "EVIDENCE TIMELINE // SOURCE-NATIVE TIMES"
                font.pixelSize: 10
                color: Colors.magenta
            }

            Repeater {
                model: Array.isArray(card.timelineRows)
                    ? card.timelineRows.slice(0, 6) : []

                delegate: Rectangle {
                    required property var modelData
                    width: card.width - 20
                    height: 43
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 2

                        Row {
                            width: parent.width
                            spacing: 7

                            GohuText {
                                width: 92
                                text: modelData.timeLabel
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: 98
                                text: card.timelineAgeLabel(modelData)
                                    + " // "
                                    + card.timelineRecencyBand(modelData)
                                font.pixelSize: 8
                                color: card.timelineRecencyBand(modelData)
                                       === "FRESH"
                                       ? Colors.green
                                       : card.timelineRecencyBand(modelData)
                                         === "RECENT"
                                         ? Colors.cyan
                                         : Colors.orange
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: 112
                                text: modelData.provenanceGroup
                                font.pixelSize: 8
                                color: Colors.blue
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: Math.max(0, parent.width - 323)
                                text: modelData.sourceLabel
                                font.pixelSize: 8
                                color: Colors.magenta
                                elide: Text.ElideRight
                            }
                        }

                        QuietText {
                            width: parent.width
                            text: modelData.kind + " // "
                                + modelData.label
                                + " // " + modelData.provenance
                                + " // FRESHNESS "
                                + card.timelineFreshnessLabel(modelData)
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            QuietText {
                width: parent.width
                text: "CHRONOLOGY ONLY // RECENCY = CLOCK AGE, NOT PROVIDER VALIDITY // PROVIDER FRESHNESS = RECEIVE-TIME CONTRACT ONLY FOR OPERATIONAL EVIDENCE // EVENT RECORDS = AGE ONLY // ROWS RETAIN SOURCE + GROUP PROVENANCE // NOT ONE MERGED INCIDENT HISTORY"
                font.pixelSize: 8
                color: Colors.orange
                elide: Text.ElideRight
            }
        }

        QuietText {
            width: parent.width
            text: "NEARBY ≠ SAME EVENT // SOURCE RECORDS REMAIN INDEPENDENT EVIDENCE"
            font.pixelSize: 8
            color: Colors.orange
            elide: Text.ElideRight
        }
    }
}
