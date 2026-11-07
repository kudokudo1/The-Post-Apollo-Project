import QtQuick
import "../../components"
import "StationMagickForecastCalendarPolicy.js" as ForecastCalendar

// C19 // Compact view of MAGICK's existing provider-local daily forecast.
// No independent fetch, JPL activity, invented phases, or calendar writes.
Rectangle {
    id: forecastStrip
    objectName: "cosmos-c19-moon-forecast-strip"
    color: Colors.dark
    border.width: 1
    border.color: Colors.magenta
    clip: true

    property var weatherService: null
    // COSMOS Moon overview stacks seven scientific observations vertically;
    // the original horizontal strip remains available to other callers.
    property bool verticalMode: false
    property string selectedDate: ""
    readonly property var model: ForecastCalendar.build(
        weatherService && weatherService.forecastReady
            ? weatherService.dailyForecast : [])
    readonly property var rows: model.ready ? model.rows.slice(0,7) : []
    readonly property string focusedDate:
        selectedDate !== "" && ForecastCalendar.select(model,selectedDate)
        ? selectedDate
        : ForecastCalendar.initialDate(model,weatherService
            ? String(weatherService.localObservationDateTime||"") : "")
    readonly property var focusedDay: ForecastCalendar.select(model,focusedDate)
    onModelChanged: selectedDate=""

    Row {
        id: titleRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 3
        anchors.rightMargin: 3
        anchors.topMargin: 1
        height: 11
        spacing: 3
        QuietText {
            width: Math.max(1,titleRow.width*0.33)
            height: parent.height
            text: forecastStrip.verticalMode ? "7D // LUNAR OUTLOOK" : "7-DAY // LOCAL FORECAST"
            color: Colors.magenta
            font.pixelSize: 8
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        QuietText {
            objectName: "cosmos-c19-forecast-focused-reading"
            width: Math.max(1,titleRow.width*0.67-3)
            height: parent.height
            font.pixelSize: 8
            color: Colors.cyan
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
            text: forecastStrip.focusedDay
                ? forecastStrip.focusedDay.phase+" // "+
                    (forecastStrip.focusedDay.illumination===null
                        ? "--" : forecastStrip.focusedDay.illumination+"%")
                    +" LIT // SUN "+forecastStrip.focusedDay.sunrise
                    +"–"+forecastStrip.focusedDay.sunset
                : (forecastStrip.model.reason || "NO VERIFIED DAILY FORECAST")
        }
    }
    // C20 // Lateral instrument: one day per row with an illumination bar.
    // No invented angular events. Yellow denotes verified daylight fraction.
    Column {
        id: verticalDays
        objectName: "cosmos-c20-moon-vertical-forecast"
        visible: forecastStrip.verticalMode
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: titleRow.bottom
        anchors.bottom: verticalDaylight.top
        anchors.leftMargin: 3
        anchors.rightMargin: 3
        spacing: 1
        Repeater {
            model: forecastStrip.rows
            delegate: Rectangle {
                objectName: "cosmos-c20-forecast-day-row"
                required property var modelData
                readonly property bool chosen: modelData.date===forecastStrip.focusedDate
                width: verticalDays.width
                height: Math.max(1,(verticalDays.height
                    -Math.max(0,forecastStrip.rows.length-1)*verticalDays.spacing)
                    /Math.max(1,forecastStrip.rows.length))
                color: chosen ? Colors.dark : Colors.black
                border.width: chosen ? 1 : 0
                border.color: Colors.magenta
                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 2
                    anchors.rightMargin: 2
                    spacing: 3
                    QuietText {
                        width: Math.max(1,parent.width*0.24)
                        height: parent.height
                        text: modelData.weekday+" "+modelData.date.slice(8)
                        color: chosen ? Colors.yellow : Colors.cyan
                        font.pixelSize: 8
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    Item {
                        width: Math.max(1,parent.width*0.48)
                        height: Math.max(6,parent.height-5)
                        anchors.verticalCenter: parent.verticalCenter
                        Rectangle {
                            anchors.fill: parent
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.blue
                        }
                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            height: Math.max(1,parent.height*0.57)
                            width: modelData.illumination===null ? 0
                                : Math.max(0,parent.width*modelData.illumination/100)
                            color: chosen ? Colors.magenta : Colors.cyan
                        }
                        Rectangle {
                            anchors.left: parent.left
                            anchors.bottom: parent.bottom
                            height: Math.max(1,parent.height*0.30)
                            width: modelData.dayFraction===null ? 0
                                : Math.max(0,parent.width*modelData.dayFraction)
                            color: Colors.yellow
                        }
                    }
                    GohuText {
                        width: Math.max(1,parent.width*0.28-6)
                        height: parent.height
                        text: modelData.illumination===null
                            ? "--" : modelData.illumination+"%"
                        color: chosen ? Colors.yellow : Colors.white
                        font.pixelSize: 9
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: forecastStrip.selectedDate=modelData.date
                }
            }
        }
        QuietText {
            visible: !forecastStrip.model.ready
            width: parent.width
            height: parent.height
            text: forecastStrip.model.reason || "NO VERIFIED FORECAST"
            color: Colors.orange
            font.pixelSize: 8
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
    }
    QuietText {
        id: verticalDaylight
        objectName: "cosmos-c20-forecast-selected-daylight"
        visible: forecastStrip.verticalMode
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 3
        anchors.rightMargin: 3
        anchors.bottomMargin: 2
        height: forecastStrip.verticalMode ? 12 : 0
        text: forecastStrip.focusedDay
            ? "SUN "+forecastStrip.focusedDay.sunrise
                +" → "+forecastStrip.focusedDay.sunset
            : "SUNRISE / SET UNAVAILABLE"
        font.pixelSize: 8
        color: Colors.orange
        elide: Text.ElideRight
    }

    Row {
        id: dayRow
        objectName: "cosmos-c19-forecast-days"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: titleRow.bottom
        anchors.bottom: parent.bottom
        anchors.leftMargin: 3
        anchors.rightMargin: 3
        anchors.bottomMargin: 2
        spacing: 2
        visible: !forecastStrip.verticalMode
        Repeater {
            model: forecastStrip.rows
            delegate: Rectangle {
                objectName: "cosmos-c19-forecast-day"
                required property var modelData
                readonly property bool chosen:
                    modelData.date===forecastStrip.focusedDate
                width: Math.max(1,(dayRow.width
                    -Math.max(0,forecastStrip.rows.length-1)*dayRow.spacing)
                    /Math.max(1,forecastStrip.rows.length))
                height: dayRow.height
                color: Colors.black
                border.width: 1
                border.color: chosen ? Colors.magenta : Colors.blue
                clip: true
                Column {
                    anchors.fill: parent
                    anchors.margins: 1
                    spacing: 1
                    QuietText {
                        width: parent.width
                        height: 9
                        text: modelData.weekday+" "+modelData.date.slice(8)
                        color: chosen ? Colors.yellow : Colors.cyan
                        font.pixelSize: 8
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                    }
                    Item {
                        width: parent.width
                        height: Math.max(3,Math.min(9,dayRow.height-24))
                        Rectangle {
                            anchors.fill: parent
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.blue
                        }
                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            height: parent.height
                            width: modelData.illumination===null ? 0
                                : Math.max(0,parent.width*modelData.illumination/100)
                            color: chosen ? Colors.magenta : Colors.cyan
                        }
                    }
                    GohuText {
                        width: parent.width
                        height: 10
                        text: modelData.illumination===null
                            ? "-- LIT" : modelData.illumination+"% LIT"
                        color: Colors.white
                        font.pixelSize: 8
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: forecastStrip.selectedDate=modelData.date
                }
            }
        }
        QuietText {
            visible: !forecastStrip.model.ready
            width: parent.width
            height: parent.height
            text: forecastStrip.model.reason
            color: Colors.orange
            font.pixelSize: 9
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
    }
}
