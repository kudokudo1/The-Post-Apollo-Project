#!/usr/bin/env python3
"""Weather Station notification producer: offline AQI policy and wiring tests."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/WeatherAqiPolicy.js"
PRODUCER = ROOT / "services/notifications/WeatherAqiNotificationProducer.qml"
SHELL = ROOT / "shell.qml"
WEATHER = ROOT / "services/weather/WeatherService.qml"
HUB = ROOT / "widgets/notifications/NotificationsHubW.qml"

source = PRODUCER.read_text()
shell = SHELL.read_text()
weather = WEATHER.read_text()
hub = HUB.read_text()

# One session-wide weather service continues refreshing independently of
# the Weather Station menu. Do not create a duplicate poll or alter Hospital.
assert 'WeatherAqiNotificationProducer {' in shell
assert 'weatherService: weatherService' in shell
assert 'WeatherService {' in shell
assert "interval: 900000" in weather
assert 'function onAqiChanged()' in source
assert 'function onAqiReadyChanged()' in source
assert "pushRich({" in source
assert '"source": "WEATHER STATION"' in source
assert '"sourceId": "weather-station"' in source
assert '"category": "internal"' in source
assert 'AqiPolicy.severityForBand(band)' in source
assert '"tags": ["weather", "air-quality", "aqi"]' in source
assert 'weatherService.refresh(' not in source
assert 'Process {' not in source
assert 'Quickshell.execDetached' not in source
assert 'sourceText === "cpu++" || sourceText === "weather station"' in hub

NODE = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8')
    .replace(/^\s*\.pragma library\s*$/m, '');
const ctx = {};
vm.runInNewContext(source, ctx, {filename:'WeatherAqiPolicy.js'});
const {bandForAqi, nextTransition, labelForBand, severityForBand} = ctx;
for (const [aqi, band] of [
    [-1,-1],[0,0],[100,0],[150,0],[151,1],[200,1],
    [201,2],[300,2],[301,3],[500,3],[501,-1]
]) assert.strictEqual(bandForAqi(aqi), band, 'AQI ' + aqi);
assert.strictEqual(bandForAqi(NaN), -1);
assert.strictEqual(bandForAqi(Infinity), -1);
assert.strictEqual(labelForBand(1), 'UNHEALTHY');
assert.strictEqual(labelForBand(2), 'VERY UNHEALTHY');
assert.strictEqual(labelForBand(3), 'HAZARDOUS');
assert.strictEqual(severityForBand(1), 'warning');
assert.strictEqual(severityForBand(3), 'critical');

let band=0;
function sample(aqi, expectedEmit, expectedBand) {
    const result = nextTransition(band, aqi);
    assert.strictEqual(result.shouldNotify, expectedEmit, 'AQI '+aqi+' emit');
    assert.strictEqual(result.nextBand, expectedBand, 'AQI '+aqi+' band');
    band = result.nextBand;
}
sample(85,false,0);
sample(151,true,1);
sample(165,false,1);
sample(151,false,1);
sample(201,true,2);
sample(180,false,2);
sample(205,false,2); // transient improvement cannot replay a warning
sample(301,true,3);
sample(301,false,3);
sample(-1,false,3); // missing data cannot reset the episode
sample(150,false,0);
sample(151,true,1); // a genuinely new episode
sample(100,false,0);
console.log('AQI transition policy: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY)], check=True)
print("Weather Station notification producer contracts: PASS")
