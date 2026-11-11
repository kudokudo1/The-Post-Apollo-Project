import QtQuick
import "../../components"
import "StationMagickSubjectPanelPolicy.js" as MagickPolicy

// MAGICK W7 // A capability / dependency dossier, not a new background
// daemon. Each route is classified from the existing registered policy.
// Shared COSMOS, JPL and WEATHER owners remain the only source owners.
Rectangle {
    id: magickServices
    objectName: "magick-w7-services-pane"
    color: Colors.black
    clip: true

    property var weatherService: null
    property var celestialSource: null
    property real runtimeNowMs: 0
    readonly property alias dashboard: servicesConsole

    readonly property bool forecastSourceReady:
        !!weatherService && !!weatherService.forecastReady
    readonly property bool jplSourceReady:
        !!celestialSource && !!celestialSource.ready

    function capabilityType(path, source) {
        if (path === "magick/planetary/hours"
            || path === "magick/planetary/timing")
            return "LOCAL CALC // REUSED WEATHER";
        if (path === "magick/divination/tarot"
            || path === "magick/grimoire/journal")
            return "SESSION LOCAL";
        if (path === "magick/grimoire/references"
            || path === "magick/divination/symbolism"
            || path === "magick/planetary/correspondences")
            return "LOCAL REFERENCE";
        if (path.indexOf("magick/astrology/") === 0)
            return "JPL / COSMOS REFERENCE";
        return source !== "" ? "REUSED OBSERVATION" : "MAGICK REFERENCE";
    }

    function capabilityState(path) {
        if (path === "magick/planetary/hours"
            || path === "magick/planetary/timing")
            return forecastSourceReady ? "FORECAST AVAILABLE" : "FORECAST REQUIRED";
        if (path === "magick/grimoire/journal") return "SESSION ONLY // NO SAVE";
        if (path === "magick/divination/tarot") return "SESSION ONLY";
        if (path === "magick/grimoire/references"
            || path === "magick/divination/symbolism"
            || path === "magick/planetary/correspondences")
            return "LOCAL REFERENCE";
        if (path.indexOf("magick/astrology/") === 0)
            return jplSourceReady ? "JPL SOURCE LOADED" : "JPL ON-DEMAND";
        return "SOURCE REFERENCE // NOT A LIVE CHECK";
    }

    readonly property var directoryRows: {
        const rows = [];
        const paths = Object.keys(MagickPolicy.ROUTES).filter(function(path) {
            return path !== "magick/services/health";
        });
        for (let i = 0; i < paths.length; i++) {
            const path = paths[i];
            const source = MagickPolicy.sourceFor(path);
            const secondary = MagickPolicy.secondarySourceFor(path);
            rows.push({
                id:path,
                name:MagickPolicy.titleFor(path),
                state:capabilityState(path),
                owner:capabilityType(path,source),
                detail:source !== "" ? source
                       + (secondary !== "" ? " // " + secondary : "")
                       : path
            });
        }
        rows.push({
            id:"shared/observation-date",
            name:"LOCATION + LOCAL DATE CONTEXT",
            state:weatherService && weatherService.localObservationDateTime
                  ? "SOURCE DATE AVAILABLE" : "SOURCE DATE UNAVAILABLE",
            owner:"SHARED // WEATHER CONTEXT",
            detail:"EXISTING LOCAL OBSERVATION CLOCK / LOCATION DEPENDENCY"
        });
        rows.push({
            id:"shared/station-clock",
            name:"STATION UTC TIME BASE",
            state:Number.isFinite(runtimeNowMs) && runtimeNowMs > 0
                  ? "TIME CONTEXT AVAILABLE" : "TIME CONTEXT UNAVAILABLE",
            owner:"SHARED // STATION CLOCK",
            detail:"EXISTING RUNTIME TIMESTAMP // NO SECOND CLOCK"
        });
        return rows;
    }

    readonly property var summaryCards: [
        {label:"PLANETARY HOURS",value:forecastSourceReady?"SOURCE READY":"SOURCE NEEDED",
         color:forecastSourceReady?Colors.cyan:Colors.orange,
         detail:"LOCAL TIMING / WEATHER REUSE"},
        {label:"JPL ASTROLOGY",value:jplSourceReady?"JPL LOADED":"ON-DEMAND",
         color:jplSourceReady?Colors.cyan:Colors.yellow,
         detail:"EXISTING CELESTIAL OWNER"},
        {label:"MOON + SUN",value:"REUSED",
         color:Colors.blue,detail:"COSMOS OBSERVATION"},
        {label:"TAROT",value:"SESSION",
         color:Colors.magenta,detail:"LOCAL RANDOM DRAW"},
        {label:"GRIMOIRE",value:"REFERENCE",
         color:Colors.yellow,detail:"AGRIPPA INDEX / LOCAL"},
        {label:"DATE + CLOCK",value:"SHARED",
         color:Colors.cyan,detail:"WEATHER / STATION"}
    ]

    StationServicesConsole {
        id: servicesConsole
        objectName: "magick-w7-services-console"
        anchors.fill: parent
        familyLabel: "MAGICK"
        statusScope: "MAGICK"
        primaryStripLabel: "INSTRUMENTS // LOCAL + REUSED + SHARED"
        secondaryStripLabel: "SOURCE DIRECTORY // " + magickServices.directoryRows.length
        headerStatus: "CAPABILITY INDEX // READ ONLY"
        runtimeRows: []
        directoryRows: magickServices.directoryRows
        customCards: magickServices.summaryCards
    }
}
