#!/usr/bin/env python3
"""QML startup preflight: shared diagnostics must be exported by qmldir."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
components = root / "components"
registry = (components / "qmldir").read_text().splitlines()
exports = {}
for line in registry:
    fields = line.strip().split()
    if len(fields) != 3 or fields[0] in ("module", "singleton", "internal"):
        continue
    name, version, filename = fields
    assert name not in exports, f"Duplicate qmldir type: {name}"
    exports[name] = (version,filename)
    assert (components / filename).is_file(), f"Missing exported QML: {filename}"

for name in ("DiagnosticsDockButton", "DiagnosticsServicePopup"):
    assert exports.get(name) == ("1.0", f"{name}.qml"), (
        f"{name} exists but cannot be imported from ../components"
    )

weather = (root / "widgets/weather/WeatherStationW.qml").read_text()
finance = (root / "widgets/FinanceW.qml").read_text()
adapter = (root / "widgets/weather/StationWeatherProviderDiagnostics.qml").read_text()
assert 'import "../../components"' in weather
assert 'import "../components"' in finance
assert 'import "../../components"' in adapter
assert "DiagnosticsDockButton {" in weather and "DiagnosticsDockButton {" in finance
assert "DiagnosticsServicePopup {" in finance and "DiagnosticsServicePopup {" in adapter
assert "StationWeatherProviderDiagnostics {" in weather
assert "DiagnosticsServicePopup {" not in weather  # adapter owns Weather reuse

# A successful source contract alone missed this failure when qmldir was omitted.
print("Shared diagnostics QML type registration preflight: PASS")
