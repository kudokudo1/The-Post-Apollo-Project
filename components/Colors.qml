pragma Singleton

import QtQuick

QtObject {
    readonly property color red: "#D16041"
    readonly property color orange: "#ED981A"
    readonly property color yellow: "#F2BE4E"
    readonly property color green: "#9ECE6A"
    readonly property color omnitrix: "#00F782"
    readonly property color cyan: "#55CFCA"
    readonly property color blue: "#5B5FD4"
    readonly property color magenta: "#C74EC7"
    readonly property color purple: "#A879ED"
    readonly property color white: "#DCF3FA"
    readonly property color black: "#1B0623"
    readonly property color dark: "#16051F"

    // Subject palette; execution and warning state colors remain caller-owned.
    function resourceColor(subject) {
        switch (String(subject).toUpperCase()) {
        case "CPU": return orange;
        case "MEM":
        case "MEMORY": return magenta;
        case "RSS":
        case "DISK":
        case "STORAGE": return blue;
        case "THREADS":
        case "NET":
        case "NETWORK":
        case "SIGNALS": return cyan;
        case "PID":
        case "IDENTITY": return purple;
        case "SWAP": return yellow;
        case "GPU":
        case "FAN":
        case "FANS": return omnitrix;
        case "ALL":
        case "OFF":
        case "TIME":
        case "UPTIME":
        case "AGE": return white;
        default: return white;
        }
    }
}
