import QtQuick
import "../../components"
import "StationMagickPlanetaryHoursPolicy.js" as Hours
import "StationMagickTimingAtlasPolicy.js" as Timing

// M7a // Date-selectable source clock, NOT electional advice. Uses M6d.
Rectangle {
    id: timing
    color: Colors.black
    clip: true
    property var weatherService: null
    property string selectedDate: ""
    property int selectedHour: 0
    readonly property var daily: weatherService && weatherService.forecastReady
        ? weatherService.dailyForecast : []
    readonly property var dates: Timing.availableDates(
        daily,Hours.validDate,Hours.nextDate)
    readonly property string localDate: weatherService
        ? Hours.observedDate(String(weatherService.localObservationDateTime||""))
        : ""
    readonly property string targetDate: selectedDate!=="" &&
        dates.indexOf(selectedDate)>=0 ? selectedDate :
        dates.indexOf(localDate)>=0 ? localDate
        : dates.length>0?dates[0]:""
    readonly property var plan: Hours.build(daily,"",targetDate)
    readonly property var stats: Timing.histogram(plan)
    readonly property var activeHour: Timing.choose(plan,selectedHour)
    onDailyChanged: { selectedDate="";selectedHour=0; }
    onPlanChanged: selectedHour=0

    function ink(name) {
        if(name==="sun")return Colors.yellow;
        if(name==="venus")return Colors.magenta;
        if(name==="mars")return Colors.orange;
        if(name==="jupiter")return Colors.blue;
        if(name==="moon"||name==="mercury")return Colors.cyan;
        return Colors.white;
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6
        GohuText {
            width: parent.width
            height: 22
            font.pixelSize: 13
            color: Colors.magenta
            elide: Text.ElideRight
            text: "PLANETARY TIMING // DAY + NIGHT"
        }
        QuietText {
            width: parent.width
            height: 17
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "FORECAST-LOCAL DATES // CHALDEAN HISTORICAL ORDER"
        }
        Row {
            id: dateRow
            width: parent.width
            height: 29
            spacing: 4
            Repeater {
                model: timing.dates
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(24,(dateRow.width-
                           Math.max(0,timing.dates.length-1)*dateRow.spacing)/
                           Math.max(1,timing.dates.length))
                    height: 28
                    label: modelData.slice(5)
                    labelPixelSize: 9
                    selected: modelData===timing.targetDate
                    accentColor: selected?Colors.magenta:Colors.cyan
                    onClicked: timing.selectedDate=modelData
                }
            }
        }
        QuietText {
            width: parent.width
            height: 21
            font.pixelSize: 10
            color: timing.plan.ready?Colors.cyan:Colors.orange
            elide: Text.ElideRight
            text: timing.plan.ready
                ? "DAY RULER "+timing.plan.dayRuler.toUpperCase()+
                  " // "+timing.plan.date+" // 24 DIVISIONS"
                : timing.plan.reason
        }
        // Twenty-four individual numbered intervals, with real M6d
        // source-derived clock boundaries when the data is valid.
        Grid {
            id: hourGrid
            width: parent.width
            columns: 12
            spacing: 3
            Repeater {
                model: timing.plan.ready ? timing.plan.hours : []
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(15,(hourGrid.width-11*hourGrid.spacing)/12)
                    height: 35
                    label: String(modelData.index+1)
                    labelPixelSize: 9
                    contentPadding: 1
                    selected: modelData.index===timing.selectedHour
                    accentColor: selected?Colors.magenta:
                                 timing.ink(modelData.ruler)
                    onClicked: timing.selectedHour=modelData.index
                }
            }
        }
        Canvas {
            id: rulerChart
            width: parent.width
            height: Math.min(150,Math.max(80,timing.height-261))
            onPaint: {
                const ctx=getContext("2d");
                ctx.clearRect(0,0,width,height);
                if(!timing.plan.ready)return;
                for(let i=0;i<24;i++){
                    const h=timing.plan.hours[i],x=i*width/24;
                    const selected=i===timing.selectedHour;
                    ctx.fillStyle=String(timing.ink(h.ruler));
                    ctx.globalAlpha=selected?1:h.phase==="day"?0.8:0.42;
                    ctx.fillRect(x+2,selected?8:20,
                                 Math.max(2,width/24-4),height-24);
                }
                ctx.globalAlpha=1;
                ctx.font="9px monospace";
                ctx.fillStyle=String(Colors.white);
                ctx.fillText("1–12 DAY / 13–24 NIGHT",6,10);
            }
            Connections {
                target: timing
                function onPlanChanged(){ rulerChart.requestPaint(); }
                function onSelectedHourChanged(){ rulerChart.requestPaint(); }
            }
        }
        QuietText {
            width: parent.width
            height: 23
            color: Colors.yellow
            font.pixelSize: 11
            elide: Text.ElideRight
            text: timing.activeHour
                ? timing.activeHour.ruler.toUpperCase()+" / "+
                  timing.activeHour.phase.toUpperCase()+" "+
                  timing.activeHour.ordinal+" // "+
                  timing.activeHour.startLabel+" TO "+
                  timing.activeHour.endLabel
                : "SELECT SOURCE HOURS WHEN FORECAST IS READY"
        }
        QuietText {
            width: parent.width
            height: 19
            color: Colors.cyan
            font.pixelSize: 9
            elide: Text.ElideRight
            text: timing.plan.ready
                ? "RISE "+timing.plan.sunrise+" / SET "+
                  timing.plan.sunset+" / NEXT RISE "+timing.plan.nextSunrise
                : "NO VERIFIED TWO-DAY SOLAR WINDOW"
        }
        QuietText {
            width: parent.width
            height: 17
            color: Colors.orange
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "CIVIL CLOCK ONLY // DST ACTUAL ELAPSED TIME UNVERIFIED"
        }
        QuietText {
            width: parent.width
            height: 17
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "HISTORICAL SYMBOLIC RULERS // NO AUSPICIOUSNESS CLAIM"
        }
    }
}
