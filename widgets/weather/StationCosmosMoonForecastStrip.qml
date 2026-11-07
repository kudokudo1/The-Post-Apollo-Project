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
            text: "7-DAY // LOCAL FORECAST"
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
