import QtQuick
import "../../components"

// W11 // Full-width, fixed, readable TWILIGHT timing grid using the exact
// StationSky calculations. The original solar curve occupies the other bay.
// No additional astronomical service, clock or observing source.
Rectangle {
    id: twilight
    objectName: "weather-w11-full-twilight-grid"
    property var sky: null
    readonly property bool ready: Boolean(sky && sky.twilightSummary
                                            && sky.twilightSummary.available)
    color: Colors.dark
    border.width: 1
    border.color: Colors.cyan
    clip: true

    function timing(key) {
        if (!ready) return "--";
        const v=sky.twilightSummary[key];
        return v === null || v === undefined || String(v)===""
                ? "--" : String(v);
    }
    function astronomy(key) {
        if (!sky || !sky.astronomySummary
                || !sky.astronomySummary.available) return "--";
        const v=sky.astronomySummary[key];
        return v===null || v===undefined || String(v)===""
                ? "--" : String(v);
    }
    function range(start,end) {
        return timing(start)+" → "+timing(end);
    }

    Column {
        anchors.fill: parent
        anchors.margins: 3
        spacing: 2

        Row {
            width: parent.width
            height: 14
            spacing: 5
            GohuText {
                width: parent.width*0.44
                height: parent.height
                text: "TWILIGHT // SOLAR WINDOWS"
                font.pixelSize: 10
                color: Colors.orange
                elide: Text.ElideRight
            }
            QuietText {
                width: parent.width*0.55
                height: parent.height
                horizontalAlignment: Text.AlignRight
                text: twilight.ready
                    ? (twilight.sky.currentSolarPosition
                       && twilight.sky.currentSolarPosition.available
                       ? "SUN NOW "+twilight.sky.currentSolarPosition.altitudeDegrees.toFixed(1)
                         +"° // AZ "
                         +twilight.sky.currentSolarPosition.azimuthDegrees.toFixed(0)+"°"
                       : "CALCULATED // CURRENT SUN UNAVAILABLE")
                    : "CALCULATED WINDOWS // SOURCE UNAVAILABLE"
                font.pixelSize: 9
                color: twilight.ready ? Colors.cyan : Colors.orange
                elide: Text.ElideRight
            }
        }

        Row {
            id: morning
            objectName: "weather-w11-twilight-morning"
            width: parent.width
            height: Math.max(25,(parent.height-14-2*2-30)*0.29)
            spacing: 3
            Repeater {
                model: [
                    {label:"MORNING // ASTRO",field:"astronomicalDawn",owner:"twilight"},
                    {label:"NAUTICAL",field:"nauticalDawn",owner:"twilight"},
                    {label:"CIVIL",field:"civilDawn",owner:"twilight"},
                    {label:"SUNRISE",field:"sunrise",owner:"astronomy"},
                    {label:"SOLAR NOON",field:"solarNoon",owner:"twilight"}
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1,(morning.width-12)/5)
                    height: morning.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.blue
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2
                        QuietText {
                            width: parent.width
                            height: 9
                            text: modelData.label
                            font.pixelSize: 8
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            height: 13
                            text: modelData.owner==="astronomy"
                                  ? twilight.astronomy(modelData.field)
                                  : twilight.timing(modelData.field)
                            font.pixelSize: 12
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        Row {
            id: evening
            objectName: "weather-w11-twilight-evening"
            width: parent.width
            height: morning.height
            spacing: 3
            Repeater {
                model: [
                    {label:"EVENING // SUNSET",field:"sunset",owner:"astronomy"},
                    {label:"CIVIL",field:"civilDusk",owner:"twilight"},
                    {label:"NAUTICAL",field:"nauticalDusk",owner:"twilight"},
                    {label:"ASTRONOMICAL",field:"astronomicalDusk",owner:"twilight"},
                    {label:"HORIZON",field:"horizon",owner:"position"}
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1,(evening.width-12)/5)
                    height: evening.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2
                        QuietText {
                            width: parent.width
                            height: 9
                            text: modelData.label
                            font.pixelSize: 8
                            color: Colors.magenta
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            height: 13
                            text: modelData.owner==="astronomy"
                                  ? twilight.astronomy(modelData.field)
                                  : modelData.owner==="position"
                                    ? (twilight.sky
                                       &&twilight.sky.currentSolarPosition
                                       &&twilight.sky.currentSolarPosition.available
                                       ? (twilight.sky.currentSolarPosition.aboveHorizon
                                          ? "ABOVE" : "BELOW") : "--")
                                    : twilight.timing(modelData.field)
                            font.pixelSize: 12
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        Row {
            id: photo
            objectName: "weather-w11-twilight-photo"
            width: parent.width
            height: Math.max(27,parent.height-14-morning.height-evening.height-3*2)
            spacing: 3
            Repeater {
                model: [
                    {label:"BLUE // MORNING",start:"blueMorningStart",
                     end:"blueMorningEnd",ink:Colors.blue},
                    {label:"GOLDEN // MORNING",start:"goldenMorningStart",
                     end:"goldenMorningEnd",ink:Colors.orange},
                    {label:"GOLDEN // EVENING",start:"goldenEveningStart",
                     end:"goldenEveningEnd",ink:Colors.orange},
                    {label:"BLUE // EVENING",start:"blueEveningStart",
                     end:"blueEveningEnd",ink:Colors.blue}
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1,(photo.width-9)/4)
                    height: photo.height
                    color: Colors.black
                    border.width: 1
                    border.color: modelData.ink
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2
                        QuietText {
                            width: parent.width
                            height: 9
                            text: modelData.label
                            font.pixelSize: 8
                            color: modelData.ink
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            height: 12
                            text: twilight.range(modelData.start,modelData.end)
                            font.pixelSize: 10
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
