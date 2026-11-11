import QtQuick
import "../../components"

// W14 // WEATHER-only, single-ink line artwork.
// Not an emoji, image asset, colored illustration or new forecast classifier.
// The existing SKY/WeatherCyclePolicy still chooses day/night and condition.
Item {
    id: glyph
    objectName: "weather-w14-monochrome-line-glyph"
    property string mode: "weather"
    property string condition: ""
    property var weatherCode: null
    property string moonPhase: "unknown"
    property string weatherKind: "clear"
    property color ink: Colors.orange

    readonly property string conditionKind: {
        const n = Number(weatherCode);
        const text = String(condition || "").toLowerCase();
        if(weatherCode !== null && weatherCode !== undefined &&
           String(weatherCode).trim() !== "" && isFinite(n)) {
            if(n>=95) return "storm";
            if(n>=85 && n<=86 || n>=71 && n<=77) return "snow";
            if(n>=80 && n<=82 || n>=51 && n<=67) return "rain";
            if(n===45 || n===48) return "fog";
            if(n>=1 && n<=3) return "cloud";
            if(n===0) return "clear";
        }
        if(text.indexOf("thunder")>=0 || text.indexOf("storm")>=0)
            return "storm";
        if(text.indexOf("snow")>=0 || text.indexOf("sleet")>=0)
            return "snow";
        if(text.indexOf("rain")>=0 || text.indexOf("drizzle")>=0)
            return "rain";
        if(text.indexOf("fog")>=0 || text.indexOf("mist")>=0)
            return "fog";
        if(text.indexOf("cloud")>=0 || text.indexOf("overcast")>=0)
            return "cloud";
        return "clear";
    }
    readonly property bool lunar: mode==="moon" || mode==="moon-cloud"
        || mode==="night-weather"
    readonly property bool clouded: conditionKind!=="clear"
        || mode==="moon-cloud" || mode==="sun-cloud"
        || (mode==="night-weather" && weatherKind!=="clear")
    readonly property bool rainy: conditionKind==="rain" ||
        (mode==="night-weather" && weatherKind==="rain")
    readonly property bool snowy: conditionKind==="snow" ||
        (mode==="night-weather" && weatherKind==="snow")
    readonly property bool stormy: conditionKind==="storm" ||
        (mode==="night-weather" && weatherKind==="storm")
    readonly property bool foggy: conditionKind==="fog"

    implicitWidth: 48
    implicitHeight: 48

    Canvas {
        id: drawing
        anchors.fill: parent
        antialiasing: true
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Component.onCompleted: requestPaint()
        onPaint: {
            const c=getContext("2d");
            const w=Math.max(1,width), h=Math.max(1,height);
            c.reset();
            c.scale(w/100,h/100);
            c.lineWidth=3.6;
            c.lineCap="round";
            c.lineJoin="round";
            c.strokeStyle=glyph.ink.toString();
            c.fillStyle="rgba(0,0,0,0)";

            function strokeSun(x,y,r) {
                c.beginPath(); c.arc(x,y,r,0,Math.PI*2); c.stroke();
                for(let a=0;a<8;a++) {
                    const t=Math.PI*2*a/8;
                    c.beginPath();
                    c.moveTo(x+Math.cos(t)*(r+6),y+Math.sin(t)*(r+6));
                    c.lineTo(x+Math.cos(t)*(r+16),y+Math.sin(t)*(r+16));
                    c.stroke();
                }
            }
            function strokeMoon(x,y,r) {
                const phase=String(glyph.moonPhase||"");
                if(phase==="full" || phase==="unknown") {
                    c.beginPath(); c.arc(x,y,r,0,2*Math.PI); c.stroke();
                    return;
                }
                c.beginPath(); c.arc(x,y,r,-Math.PI/2,Math.PI/2,false);
                const waning=phase.indexOf("waning")===0
                    || phase==="last-quarter";
                const bend=phase.indexOf("gibbous")>=0 ? -r*0.53
                    : phase.indexOf("quarter")>=0 ? 0 : r*0.56;
                c.bezierCurveTo(x+(waning?-bend:bend),y+r,
                    x+(waning?-bend:bend),y-r,x,y-r);
                c.stroke();
            }
            function strokeCloud(x,y) {
                c.beginPath();
                c.moveTo(x+7,y+31);
                c.bezierCurveTo(x-2,y+31,x-3,y+16,x+10,y+13);
                c.bezierCurveTo(x+12,y-6,x+37,y-9,x+48,y+9);
                c.bezierCurveTo(x+69,y+6,x+76,y+30,x+61,y+32);
                c.lineTo(x+7,y+32);
                c.stroke();
            }
            function strokeRain() {
                for(let i=0;i<3;i++) {
                    c.beginPath();
                    c.moveTo(28+i*20,74);
                    c.lineTo(22+i*20,86);
                    c.stroke();
                }
            }
            function strokeSnow() {
                for(let i=0;i<3;i++) {
                    const x=28+i*20,y=81;
                    c.beginPath();c.moveTo(x-5,y);c.lineTo(x+5,y);
                    c.moveTo(x,y-5);c.lineTo(x,y+5);c.stroke();
                }
            }
            function strokeStorm() {
                c.beginPath();
                c.moveTo(52,70);c.lineTo(42,81);
                c.lineTo(52,81);c.lineTo(43,95);
                c.stroke();
            }
            function strokeFog() {
                for(let i=0;i<3;i++) {
                    c.beginPath();c.moveTo(22,74+i*8);c.lineTo(76,74+i*8);
                    c.stroke();
                }
            }

            if(glyph.lunar) strokeMoon(glyph.clouded ? 36:50,
                                      glyph.clouded ? 36:50,
                                      glyph.clouded ? 20:25);
            else if(!glyph.clouded || glyph.mode==="sun-cloud")
                strokeSun(glyph.clouded ? 35:50,
                          glyph.clouded ? 35:50,
                          glyph.clouded ? 14:23);

            if(glyph.clouded) {
                strokeCloud(9,25);
                if(glyph.rainy) strokeRain();
                else if(glyph.snowy) strokeSnow();
                else if(glyph.stormy) strokeStorm();
                else if(glyph.foggy) strokeFog();
            }
        }
    }
    onModeChanged: drawing.requestPaint()
    onConditionChanged: drawing.requestPaint()
    onWeatherCodeChanged: drawing.requestPaint()
    onWeatherKindChanged: drawing.requestPaint()
    onMoonPhaseChanged: drawing.requestPaint()
    onInkChanged: drawing.requestPaint()
}
