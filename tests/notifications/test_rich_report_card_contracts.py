#!/usr/bin/env python3
"""Weather/Solar rich notification history, normal cards unchanged."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
HUB = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text()
SOLAR = (ROOT / "services/notifications/SolarReportNotificationProducer.qml").read_text()
WEATHER = (ROOT / "services/notifications/WeatherReportNotificationProducer.qml").read_text()
BASE = (ROOT / "services/notifications/NotificationsService.qml").read_text()
assert "property int cardHeight: 116" in HUB, "Ordinary cards must not grow"
assert "property int reportCardHeight: 352" in HUB
assert "function reportKindFor(entry)" in HUB
assert 'eventType === "solar-daily-report" && sourceId === "weather-space"' in HUB
assert 'eventType === "weather-daily-report" && sourceId === "weather-brief"' in HUB
assert '"reportKind": reportKind' in HUB
assert '"reportDetails": root.reportDetailsFor(entry, reportKind)' in HUB
assert "required property string reportKind" in HUB
assert "required property string reportDetails" in HUB
assert "readonly property bool isReport: reportKind !== \"\"" in HUB
assert "notificationEntry.isReport ? root.reportCardHeight : root.cardHeight" in HUB
assert 'visible: !notificationEntry.isReport' in HUB
assert "id: reportText" in HUB
assert "visible: notificationEntry.isReport" in HUB
assert "text: notificationEntry.reportDetails" in HUB
assert "wrapMode: Text.Wrap" in HUB
assert "elide: Text.ElideNone" in HUB
assert 'function reportNumber(value, digits, suffix)' in HUB
assert 'function reportObserved(raw)' in HUB
assert 'metrics: toPlainValue(notification.metrics) || {}' not in BASE or '"metrics": toPlainValue(notification.metrics) || {}' in BASE
assert '"context": toPlainValue(notification.context) || {}' in BASE
for field in ('kp', 'solarWindKmS', 'magneticBtNt', 'magneticBzNt', 'solarFluxSfu'):
    assert field in SOLAR and f'm.{field}' in HUB
for field in ('temperatureF','feelsLikeF','humidityPercent','windMph',
              'windDirection','aqi','aqiLabel','pm25','pm10'):
    assert field in WEATHER and f'm.{field}' in HUB
# Only report cards receive the long deck. Ordinary notifications still keep
# their single-line message, card actions and original geometry.
assert "text: notificationEntry.message" in HUB
assert "id: bringHereButton" in HUB
assert re.search(r'id: notificationMessage.*?visible: !notificationEntry.isReport', HUB, re.S)
assert re.search(r'id: bringHereButton.*?visible: !notificationEntry.isReport', HUB, re.S)
print("Weather/Solar extended history card contracts: PASS")
