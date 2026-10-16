#!/usr/bin/env python3
"""Offline current-conditions report contract and observation policy."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/WeatherReportPolicy.js"
PRODUCER = ROOT / "services/notifications/WeatherReportNotificationProducer.qml"
SHELL = ROOT / "shell.qml"
QM = ROOT / "services/notifications/qmldir"
WEATHER = ROOT / "services/weather/WeatherService.qml"
NOTIFY = ROOT / "services/notifications/NotificationsService.qml"

src = PRODUCER.read_text(encoding="utf-8")
shell = SHELL.read_text(encoding="utf-8")
assert "WeatherReportNotificationProducer {" in shell
assert 'weatherService: weatherService' in shell
assert 'WeatherReportNotificationProducer 1.0 WeatherReportNotificationProducer.qml' in QM.read_text()
assert '"source": "WEATHER REPORT"' in src
assert '"sourceId": "weather-brief"' in src
assert '"category": "internal"' in src
assert '"severity": "normal"' in src
assert '"id": id' in src
assert 'function historyContains(id)' in src
assert "NotificationsService.historyReady" in src
assert '"eventType": "weather-daily-report"' in src
assert '"weatherSource": "wttr.in"' in src
assert '"airQualitySource": record.aqi === null' in src
assert 'NotificationsService.pushRich({' in src
assert 'firstWeatherReadyMs < 90000' in src
assert 'function onAqiReadyChanged()' in src
assert 'function onLastUpdatedChanged()' in src
assert "function pushRich(notification)" in NOTIFY.read_text()
assert "interval: 900000" in WEATHER.read_text()
for forbidden in ['Process {', 'Quickshell.execDetached', 'weatherService.refresh(',
                  'weatherService.parseWeather(', 'weatherService.refreshAirQuality(']:
    assert forbidden not in src, forbidden

NODE = r"""
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const content=fs.readFileSync(process.argv[1],'utf8')
    .replace(/^\s*\.pragma library\s*$/m,'');
const ctx={Date, Number, String, isFinite, Math};
vm.runInNewContext(content,ctx,{filename:'WeatherReportPolicy.js'});
const now=Date.parse('2026-10-16T12:00:00Z');
const weather={
    ready:true, tempF:'71', feelsLikeF:'69', condition:'Partly cloudy',
    humidity:'66', windMph:'12', windDirection:'NW',
    aqiReady:true, aqi:87, aqiLabel:'MODERATE', pm25:14.3, pm10:28.4,
    lastUpdated:new Date('2026-10-16T11:48:00Z')
};
assert.strictEqual(ctx.localDayKey(new Date(2026,9,16,9)),'2026-10-16');
const record=ctx.snapshot(weather,now);
assert(record !== null);
assert.strictEqual(record.temperatureF,71);
assert.strictEqual(record.feelsLikeF,69);
assert.strictEqual(record.humidityPercent,66);
assert.strictEqual(record.windMph,12);
assert.strictEqual(record.aqi,87);
assert.strictEqual(record.pm25,14.3);
const summary=ctx.summary(record);
for(const token of ['71°F','FEELS 69°F','Partly cloudy',
    'WIND NW 12 MPH','HUMIDITY 66%','AIR QUALITY 87 MODERATE'])
    assert(summary.includes(token),token);
assert.strictEqual(ctx.snapshot({...weather,ready:false},now),null);
assert.strictEqual(ctx.snapshot({...weather,tempF:'--'},now),null);
assert.strictEqual(ctx.snapshot({...weather,lastUpdated:
    new Date('2026-10-16T09:00:00Z')},now),null);
assert.strictEqual(ctx.snapshot({...weather,lastUpdated:
    new Date('2026-10-16T13:00:00Z')},now),null);
const noAqi=ctx.snapshot({...weather,aqiReady:false},now);
assert(noAqi !== null && noAqi.aqi === null && noAqi.pm25 === null);
assert(ctx.summary(noAqi).includes('AIR QUALITY UNAVAILABLE'));
const badHumidity=ctx.snapshot({...weather,humidity:'400'},now);
assert.strictEqual(badHumidity.humidityPercent,null);
assert.strictEqual(ctx.snapshot({...weather,aqi:-1},now).aqi,null);
console.log('Daily Weather Report observation policy: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY)], check=True)
print("Daily Weather Report producer contracts: PASS")
