import QtQuick
import "EnergyVariantProfile.js" as Profiles

// Opt-in host reaction. Reads the existing visual clock; no independent
// timer, window movement, operation authority or input handling.
QtObject {
    id: root
    property var sources: []
    property bool enabled: true
    property bool reducedMotion: false
    property bool completionFlashEnabled: true
    property bool localLightingEnabled: true
    property real strength: 1.0
    readonly property var reaction: {
        let best = null;
        let clashLight = null;
        const localLights = [];
        let light = null;
        let flash = 0;
        let flashSource = null;
        let flashSpread = 0;
        let fragments = 0;
        let fragmentColor = Colors.magenta;
        let fragmentTime = 0;
        let fragmentStyle = "";
        if (enabled && !reducedMotion) {
            for (const source of sources) {
                if (!source || !source.visible || source.reducedMotion) continue;
                const f = source.visualFrame;
                if(source.variant==="ki-blast" && f.clash) {
                    const p=source.displayedFraction;
                    const level=source.phase==="failure" && !source.animationActive?.30:.48;
                    if(!clashLight || level>clashLight.level)
                        clashLight={source:source,fraction:p,heat:f.enemyHeat,level:level};
                }
                if(localLightingEnabled && (source.animationActive || (source.variant==="ki-blast" && f.clash))) {
                    const fire=source.variant==="flamethrower";
                    const level=source.variant==="ki-blast"?.26:fire?.22:source.variant==="tron"?.19:.17;
                    const p=source.displayedFraction;
                    if(p>0 && f.headVisible)
                        localLights.push({source:source,fraction:p,color:source.energyColor,
                            level:level*(.70+.30*f.intensity),fire:fire,side:-1});
                    if(source.variant==="ki-blast" && f.clash && f.enemyFraction>0)
                        localLights.push({source:source,fraction:p,color:Qt.rgba(1,.70-.59*f.enemyHeat,.32-.17*f.enemyHeat,1),
                            level:.26*f.enemyOpacity,fire:false,side:1});
                }
                if(!source.animationActive) continue;
                const level = source.phase === "running"
                    ? .12 + .88 * f.intensity
                    : source.phase === "success" ? f.impact : f.defeat || 0;
                const v = Profiles.host(source.variant, source.elapsed, level,
                    strength, source.phase, false, source.fireMode);
                // Independent maxima: bulk requests cannot stack displacement,
                // illumination, flash or debris amplitude without bound.
                if (!best || v.score > best.score) best = v;
                if (!light || v.power > light.power) {
                    light = {power:v.power, color:source.energyColor,
                        time:source.elapsed, style:v.style};
                }
                if (v.fragments > fragments) {
                    fragments = v.fragments;
                    fragmentColor = source.energyColor;
                    fragmentTime = source.elapsed;
                    fragmentStyle = v.style;
                }
                if (v.flash > flash) {
                    flash = v.flash;
                    flashSource = source;
                    flashSpread = v.flashSpread;
                }
            }
        }
        return {
            clashLight: clashLight,
            localLights: localLights.sort((a,b)=>b.level-a.level).slice(0,8),
            power: light ? light.power : 0,
            time: light ? light.time : 0,
            color: light ? light.color : Colors.magenta,
            dx: best ? best.dx : 0,
            dy: best ? best.dy : 0,
            flash: completionFlashEnabled ? flash : 0,
            flashSource: completionFlashEnabled ? flashSource : null,
            flashSpread: completionFlashEnabled ? flashSpread : 0,
            style: light ? light.style : "",
            fragments: fragments,
            fragmentColor: fragmentColor,
            fragmentTime: fragmentTime,
            fragmentStyle: fragmentStyle
        };
    }
    readonly property var clashLight: reaction.clashLight
    readonly property var localLights: reaction.localLights
    readonly property real pressure: reaction.power
    readonly property real offsetX: reaction.dx
    readonly property real offsetY: reaction.dy
    readonly property real motionTime: reaction.time
    readonly property color pressureColor: reaction.color
    readonly property real completionFlash: reaction.flash
    readonly property Item flashSource: reaction.flashSource
    readonly property real flashSpread: reaction.flashSpread
    readonly property color flashColor: flashSource ? flashSource.energyColor : Colors.omnitrix
    readonly property string reactionStyle: reaction.style
    readonly property real fragmentPressure: reaction.fragments
    readonly property color fragmentColor: reaction.fragmentColor
    readonly property real fragmentTime: reaction.fragmentTime
    readonly property string fragmentStyle: reaction.fragmentStyle
}
