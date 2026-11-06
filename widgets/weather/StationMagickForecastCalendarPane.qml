import QtQuick
import "../../components"
import "StationMagickForecastCalendarPolicy.js" as Calendar

// M7a // A source-labelled local forecast outlook, NOT predicted phase instants
// or a personal ritual calendar. The UI never writes an event.
Rectangle {
    id: outlook
    color: Colors.dark
    border.width: 1
    border.color: Colors.magenta
    clip: true
    property var weatherService: null
    property string selectedDate: ""
    readonly property var model: Calendar.build(
        weatherService && weatherService.forecastReady
            ? weatherService.dailyForecast : [])
    readonly property string focusedDate: selectedDate!=="" &&
        Calendar.select(model,selectedDate) ? selectedDate :
        Calendar.initialDate(model,weatherService
            ? String(weatherService.localObservationDateTime||"") : "")
    readonly property var focusedDay: Calendar.select(model,focusedDate)
    onModelChanged: selectedDate=""
    onFocusedDateChanged: bars.requestPaint()
    onWidthChanged: bars.requestPaint()

    Column {
        anchors.fill: parent
        anchors.margins: 7
        spacing: 5
        GohuText {
            width: parent.width
            height: 20
            text: "LUNAR + SOLAR // FORECAST OUTLOOK"
            color: Colors.magenta
            font.pixelSize: 12
            elide: Text.ElideRight
        }
        QuietText {
            width: parent.width
            height: 16
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: outlook.model.ready
                ? outlook.model.firstDate+" TO "+outlook.model.lastDate+
                  " // "+outlook.model.source
                : outlook.model.reason
        }
        Grid {
            id: daysGrid
            width: parent.width
            columns: 7
            spacing: 3
            Repeater {
                model: outlook.model.ready ? outlook.model.rows : []
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(20,(daysGrid.width-6*daysGrid.spacing)/7)
                    height: 32
                    label: modelData.date.slice(8)+" "+modelData.weekday
                    labelPixelSize: 8
                    contentPadding: 1
                    selected: outlook.focusedDate===modelData.date
                    accentColor: selected ? Colors.magenta : Colors.cyan
                    onClicked: outlook.selectedDate=modelData.date
                }
            }
        }
        Canvas {
            id: bars
            width: parent.width
            height: Math.max(90,Math.min(178,outlook.height-190))
            onPaint: {
                const ctx=getContext("2d");
                ctx.clearRect(0,0,width,height);
                if(!outlook.model.ready)return;
                const entries=outlook.model.rows;
                const w=width/entries.length;
                for(let i=0;i<entries.length;i++){
                    const row=entries[i],x=i*w+w*0.16;
                    const barW=Math.max(2,w*0.29);
                    const active=row.date===outlook.focusedDate;
                    if(row.illumination!==null){
                        const v=row.illumination/100;
                        ctx.fillStyle=String(active?Colors.magenta:Colors.cyan);
                        ctx.globalAlpha=active?1:0.66;
                        ctx.fillRect(x,height-4-v*(height-17),
                                     barW,v*(height-17));
                    }
                    if(row.dayFraction!==null){
                        const v=row.dayFraction;
                        ctx.fillStyle=String(Colors.yellow);
                        ctx.globalAlpha=active?0.95:0.6;
                        ctx.fillRect(x+barW+2,height-4-v*(height-17),
                                     barW,v*(height-17));
                    }
                }
                ctx.globalAlpha=1;
                ctx.fillStyle=String(Colors.white);
                ctx.font="9px monospace";
                ctx.fillText("CYAN: MOON ILLUM.  YELLOW: DAYLIGHT SHARE",
                             3,10,Math.max(1,width-6));
            }
            Connections {
                target: outlook
                function onModelChanged() { bars.requestPaint(); }
            }
        }
        QuietText {
            width: parent.width
            height: 21
            font.pixelSize: 11
            color: Colors.white
            elide: Text.ElideRight
            text: outlook.focusedDay
                ? outlook.focusedDay.date+"  /  "+
                  outlook.focusedDay.phase+
                  "  /  "+(outlook.focusedDay.illumination===null
                      ? "--":outlook.focusedDay.illumination+"%")+" LIT"
                : "SELECT A VERIFIED FORECAST DAY"
        }
        QuietText {
            width: parent.width
            height: 19
            color: Colors.cyan
            font.pixelSize: 9
            elide: Text.ElideRight
            text: outlook.focusedDay
                ? "RISE "+outlook.focusedDay.sunrise+
                  " // SET "+outlook.focusedDay.sunset+
                  " // DAYLIGHT "+(outlook.focusedDay.daylightMinutes===null
                      ? "--":Math.round(outlook.focusedDay.daylightMinutes/60*10)/10+"H")
                : "NO VERIFIED SUNRISE / SUNSET DATA"
        }
        QuietText {
            width: parent.width
            height: 17
            font.pixelSize: 9
            color: Colors.orange
            elide: Text.ElideRight
            text: "DAILY FORECAST SNAPSHOTS // NOT PRECISE LUNAR EVENT UTC"
        }
        QuietText {
            width: parent.width
            height: 16
            font.pixelSize: 9
            color: Colors.yellow
            elide: Text.ElideRight
            text: "NO EQUINOX INSTANTS / NO SAVED PERSONAL CALENDAR EVENTS"
        }
    }
}
