#!/usr/bin/env node
"use strict";

// Weather Station palette contract after domain separation. This pass protects
// semantic identities and telemetry severity colors while layout polish remains
// intentionally deferred.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");

function read(relative) {
    return fs.readFileSync(path.join(root, relative), "utf8");
}

const windowSource = read("widgets/weather/WeatherStationW.qml");
const homeSource = read("widgets/weather/StationHome.qml");
const groundSource = read("widgets/weather/StationGround.qml");
const skySource = read("widgets/weather/StationSky.qml");
const spaceSource = read("widgets/weather/StationSpace.qml");
const weatherServiceSource = read("services/weather/WeatherService.qml");
const spaceServiceSource = read("services/weather/SpaceService.qml");

const mainHeaderStart = windowSource.indexOf("id: header");
const mainHeaderEnd = windowSource.indexOf("// NAVIGATION", mainHeaderStart);
assert.ok(mainHeaderStart >= 0 && mainHeaderEnd > mainHeaderStart);
const header = windowSource.slice(mainHeaderStart, mainHeaderEnd);
assert.match(
    header,
    /text: "✦ WEATHER STATION ✦"[\s\S]*?color: Colors\.magenta/
);
assert.match(header, /height: 2\s+color: Colors\.magenta/);
assert.match(header, /border\.color: weatherStation\.sourceStatusColor/);
assert.match(header, /accentColor: Colors\.red/);

// HOME no longer owns the three domains.
for (const title of ["⌁  GROUND", "☁  SKY", "✦  SPACE"])
    assert.ok(!homeSource.includes(title), "HOME still contains " + title);
assert.ok(homeSource.includes("FAVORITES // RELEVANT // AUTO"));

// Stable domain identities survive the structural split.
assert.match(groundSource, /text: "⌁  GROUND"[\s\S]*?color: Colors\.green/);
assert.match(skySource, /text: "☁  SKY"[\s\S]*?color: Colors\.cyan/);
assert.match(spaceSource, /text: "✦  SPACE"[\s\S]*?color: Colors\.magenta/);

// Existing semantic telemetry severity remains independent from page identity.
assert.match(groundSource, /readonly property color aqiColor:/);
for (const color of ["cyan", "yellow", "orange", "red"])
    assert.ok(groundSource.includes("Colors." + color));

for (const property of ["kpColor", "solarWindColor", "bzColor"])
    assert.ok(spaceSource.includes("readonly property color " + property));
for (const color of ["cyan", "yellow", "orange", "red"])
    assert.ok(spaceSource.includes("Colors." + color));

// Current weather content remains on SKY rather than being lost in the split.
for (const token of [
    "weatherService.tempF",
    "weatherService.feelsLikeF",
    "weatherService.condition",
    "weatherService.humidity",
    "weatherService.windMph",
])
    assert.ok(skySource.includes(token), token);

// The first expansion pass wires real provider fields before redesigning
// the instruments around them.
for (const token of [
    "pressureHpa",
    "visibilityMiles",
    "cloudCover",
    "precipMm",
    "hourlyForecast",
    "dailyForecast",
])
    assert.ok(weatherServiceSource.includes(token), "weather service " + token);

for (const token of [
    "carbonMonoxide",
    "nitrogenDioxide",
    "ozone",
    "carbonMonoxideAqi",
    "nitrogenDioxideAqi",
    "ozoneAqi",
    "dust",
    "grassPollen",
    "ragweedPollen",
    "pollenAvailable",
])
    assert.ok(weatherServiceSource.includes(token), "air quality " + token);

for (const token of [
    "weatherService.pressureHpa",
    "weatherService.visibilityMiles",
    "weatherService.cloudCover",
    "weatherService.precipMm",
    "weatherService.uvIndex",
    "weatherService.hourlyForecast",
    "weatherService.dailyForecast",
    "FORECAST // NEXT HOURS",
    "FORECAST // DAILY",
])
    assert.ok(skySource.includes(token), "SKY expansion " + token);

for (const token of [
    "weatherService.ozone",
    "weatherService.nitrogenDioxide",
    "weatherService.carbonMonoxide",
    "weatherService.dust",
    "weatherService.pollenAvailable",
    "POLLEN // PEAK",
])
    assert.ok(groundSource.includes(token), "GROUND expansion " + token);

for (const token of [
    "spaceService.magneticFieldBt",
    "spaceService.kpTime",
    "spaceService.solarWindTime",
    "spaceService.magneticFieldTime",
    "spaceService.solarFluxTime",
    "IMF BT",
])
    assert.ok(spaceSource.includes(token), "SPACE expansion " + token);

for (const token of [
    "property real magneticFieldBt",
    "property string kpTime",
    "property string solarWindTime",
    "property string magneticFieldTime",
    "property string solarFluxTime",
])
    assert.ok(spaceServiceSource.includes(token), "space service " + token);

// Restored bars are not decorative/random meters. Their fill widths remain
// direct normalized functions of the real telemetry already displayed.
const meterSpecs = [
    {
        source: groundSource,
        objectName: "ground",
        fill: "green",
        meters: {
            aqi: "aqiValue / 500",
            pm25: "pm25Value / 100",
            pm10: "pm10Value / 150",
            ozone: "ozoneAqiValue / 500",
            nitrogenDioxide: "nitrogenDioxideAqiValue / 500",
            carbonMonoxide: "carbonMonoxideAqiValue / 500",
        },
    },
    {
        source: skySource,
        objectName: "sky",
        fill: "orange",
        meters: {
            temperature: "temperatureValue / 120",
            aqi: "aqiValue / 500",
            humidity: "humidityValue / 100",
            wind: "windValue / 50",
            cloudCover: "cloudCoverValue / 100",
            uv: "uvValue / 11",
        },
    },
    {
        source: spaceSource,
        objectName: "space",
        fill: "magenta",
        meters: {
            kp: "kpValue / 9",
            solarWind: "solarWindValue / 1000",
            bz: "Math.abs(bzValue) / 20",
            bt: "btValue / 20",
            solarFlux: "solarFluxValue / 300",
        },
    },
];

for (const spec of meterSpecs) {
    for (const [name, scale] of Object.entries(spec.meters)) {
        assert.ok(
            spec.source.includes("readonly property real " + name + "Meter"),
            name + " meter property"
        );
        assert.ok(spec.source.includes(scale), name + " real telemetry scale");
        assert.ok(
            spec.source.includes(
                "width: (parent.width - 4) * " +
                (spec.source === groundSource ? "ground."
                 : spec.source === skySource ? "sky." : "space.") +
                name + "Meter"
            ),
            name + " live fill width"
        );
    }

    assert.match(
        spec.source,
        new RegExp(
            "readonly property color meterBorderColor:\\s*Colors\\.cyan"
        )
    );
    assert.match(
        spec.source,
        new RegExp(
            "readonly property color meterFillColor:\\s*Colors\\."
            + spec.fill
        )
    );

    const borderBinding =
        "border.color: " + spec.objectName + ".meterBorderColor";
    const fillBinding =
        "color: " + spec.objectName + ".meterFillColor";

    assert.ok(
        spec.source.split(borderBinding).length - 1 >=
            Object.keys(spec.meters).length,
        spec.objectName + " meter border identity"
    );
    assert.ok(
        spec.source.split(fillBinding).length - 1 >=
            Object.keys(spec.meters).length,
        spec.objectName + " meter fill identity"
    );
}


// Forecast probability bars use their intrinsic 0-100 percent scale. There
// should be one meter path in each hourly and daily forecast delegate.
assert.match(
    skySource,
    /function chanceMeter\(value\)[\s\S]*?number \/ 100/
);
assert.ok(
    skySource.split("sky.chanceMeter(").length - 1 >= 2,
    "hourly and daily rain chance meters"
);
assert.ok(
    skySource.split("border.color: sky.meterBorderColor").length - 1 >= 8,
    "all SKY meter exteriors use cyan"
);
assert.ok(
    skySource.split("color: sky.meterFillColor").length - 1 >= 8,
    "all SKY meter interiors use orange"
);

// Fields without a defensible intrinsic/provider scale stay numeric for now.
// Do not invent pressure, visibility, precipitation, dust, pollen, or sample-time meters.
for (const forbidden of [
    "pressureMeter",
    "visibilityMeter",
    "precipMeter",
    "dustMeter",
    "pollenMeter",
    "sampleTimeMeter",
])
    assert.ok(!groundSource.includes(forbidden)
              && !skySource.includes(forbidden)
              && !spaceSource.includes(forbidden),
              forbidden + " should not be an arbitrary meter");

console.log("Weather Station domain palette contracts: PASS");
