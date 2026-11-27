import QtQuick

// Opt-in host reaction. Reads the existing visual clock; never starts a timer,
// moves a window, changes operation state, or modifies an input target.
QtObject {
    id: root
    property var sources: []
    property bool enabled: true
    property bool reducedMotion: false
    property real strength: 1.0
    readonly property var reaction: {
        let best = null;
        let amplitude = 0;
        if (enabled && !reducedMotion) {
            for (const source of sources) {
                if (!source || !source.visible || !source.animationActive
                    || source.reducedMotion) continue;
                const f = source.visualFrame;
                const level = source.phase === "running"
                    ? .12 + .88 * f.intensity
                    : source.phase === "success" ? f.impact : 0;
                // Max, not sum: a bulk job cannot amplify shake without bound.
                if (level > amplitude) {
                    best = source;
                    amplitude = level;
                }
            }
        }
        const power = Math.min(1, Math.max(0, amplitude * strength));
        const t = best ? best.elapsed : 0;
        return {
            power: power,
            time: t,
            color: best ? best.energyColor : Colors.magenta,
            dx: power * (Math.sin(t*27)*2.3 + Math.sin(t*13)*.7),
            dy: power * (Math.sin(t*21)*1.5 + Math.sin(t*9)*.5)
        };
    }
    readonly property real pressure: reaction.power
    readonly property real offsetX: reaction.dx
    readonly property real offsetY: reaction.dy
    readonly property real motionTime: reaction.time
    readonly property color pressureColor: reaction.color
}
