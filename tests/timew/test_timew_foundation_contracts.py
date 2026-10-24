#!/usr/bin/env python3
"""Source contracts for the isolated TimeW M1 chassis.

These are source-level checks, not proof of a rendered QML/live desktop.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
window = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
clock = (ROOT / "modules/Clock.qml").read_text(encoding="utf-8")
preview = (ROOT / "timew_click_preview.qml").read_text(encoding="utf-8")
finance = (ROOT / "widgets/FinanceW.qml").read_text(encoding="utf-8")
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")

# Real shared components, standalone preview, no duplicate control system.
for name in ("PanelWindow {", "WindowPanelFrame {", "ActionButton {",
             "ModeButton {", "SystemClock {"):
    assert name in window, name
assert 'import "widgets"' in preview and 'import "modules"' in preview
assert "Scope {" in preview and "TimeW {" in preview
assert "Clock {" in preview and "timeWindow: timewWindow" in preview
assert "screen: previewDockWindow.screen" in preview
# Integrated bar clock still owns one visible dock, now paired with TimeW.
clock_section = shell.split("        // Clock and TimeW.", 1)
assert len(clock_section) == 2, "Missing TimeW dock section"
clock_section = clock_section[1].split("        // Notifications", 1)[0]
assert shell.count("            Clock {") == 1, "Duplicate bar clock"
assert "width: clockDock.width" in clock_section
assert "height: clockDock.height" in clock_section
assert "id: clockDock" in clock_section
assert "timeWindow: timewWindow" in clock_section
assert "TimeW {" in clock_section
assert "id: timewWindow" in clock_section
assert 'screen: Quickshell.screens.find(s => s.name === "DP-5")' in clock_section
assert "keyboardActive: !relationshipFocus.active" in clock_section
assert "relationshipFocusModeActive: relationshipFocus.active" in clock_section
assert "anchors.fill: parent" not in clock_section, "Clock uses self-sized geometry"
assert shell.index("        // Clock and TimeW.") < shell.index("        // Notifications")


# No accidental clock-format or dock-chassis rewrite.
assert "property bool is24Hour: false" in clock
assert "property var timeWindow: null" in clock
assert "onRightClicked: {" in clock
assert "clockArea.is24Hour = !clockArea.is24Hour;" in clock
assert "onLeftClicked: {" in clock
assert "clockArea.timeWindow.toggle();" in clock
assert 'console.log("clockButton clicked");' in clock
assert "SystemClock.Seconds" in clock
assert "implicitHeight: 50" in clock

# The M1 window uses a known existing size rather than a new global metric.
for dim in ("frameWidth: 432", "frameHeight: 768", "glowGutter: 12"):
    assert dim in finance and dim in window, dim
assert "visible: true" in window
assert "width: timew.menuOpen ? timew.frameWidth : 0" in window
assert "height: timew.menuOpen ? timew.frameHeight : 0" in window
assert "WlrKeyboardFocus.OnDemand" in window
assert "WlrKeyboardFocus.Exclusive" not in window
assert "focusable: standardKeysAvailable" in window
assert "relationshipFocusModeActive" in window
assert "relationshipFocused" in window

# Mode changes and Escape are actual UI interactions.
for mode in ('id: "clock"', 'id: "calc"', 'id: "tools"',
             'id: "machine"'):
    assert mode in window, mode
assert "function chooseMode(index)" in window
assert "function cycleMainMode(direction)" in window
assert "onTriggered: timew.chooseMode(index)" in window
assert "onMenuOpenChanged:" in window
assert "Keys.onShortcutOverride:" in window
assert "Keys.onPressed:" in window
for key in ("Tab", "Shift+Tab", "Esc"):
    assert 'sequence: "' + key + '"' in window
assert "onLeftClicked: timew.menuOpen = false" in window

# TimeW-specific white identity and screenshot-corrected top alignment.
# Preserve the 8px right-dock top inset; adding 50px for dock height placed
# the TimeW frame too low in the 2026-10-22 operator screenshot.
assert "anchors.topMargin: 8" in shell
assert "implicitHeight: 50" in clock
assert "    margins {\n        top: 8\n        right: 13\n    }" in window
assert "top: 8 + 50 - timew.glowGutter" not in window
assert "readonly property color semanticColor: Colors.white" in window
assert "glowColor: timew.semanticColor" in window
assert "borderColor: timew.semanticColor" in window
assert "idlePrimaryColor: timew.semanticColor" in window
assert 'text: timew.selectedName + " // TIMEW"\n                        color: timew.semanticColor' in window
# TimeW displays the tested local-time formatter using its preexisting
# SystemClock tick. There is no second timer, backend, or global preference.
assert 'import "../services/hub/ApolloHubTimePolicy.js" as LocalTimePolicy' in window
assert "LocalTimePolicy.snapshot(localClock.date.getTime(), use24Hour)" in window
assert window.count("SystemClock {") == 1
assert window.count("\n    Timer {") == 3
assert window.count("ElapsedTimer {") == 3
assert "interval: 30000" in window
assert "running: timew.menuOpen && timew.selectedMode === \"clock\"" in window
assert "property bool use24Hour: true" in window
# Clock-page presentation: 24H retains PM, 12H retains leading zero;
# the time/control are orange in 24H and cyan in 12H (not chassis white).
assert "readonly property color clockReadoutColor:" in window
assert "use24Hour ? Colors.orange : Colors.cyan" in window
assert "readonly property string clockReadoutText:" in window
assert "localTimeSnapshot.state === \"ready\"" in window
assert "use24Hour ? localTimeSnapshot.time24" in window
assert "localTimeSnapshot.time12.slice(0, 8)" in window
assert '+ "//" + localTimeSnapshot.meridiem' in window
assert 'text: timew.clockReadoutText' in window
assert 'color: timew.clockReadoutColor' in window
assert 'accentColor: timew.clockReadoutColor' in window
assert "text: timew.localTimeSnapshot.displayTime" not in window
assert "text: timew.localTimeSnapshot.dateLabel" in window
assert "text: timew.localTimeSnapshot.utcOffsetLabel" in window
# Both local display modes now share the exact same font size.
assert "font.pixelSize: 22" in window
assert "font.pixelSize: timew.use24Hour ? 22 : 19" not in window
# The world-clock adapter reuses SystemClock seconds and only invokes the
# system's zone database via a read-only, fixed argv date command while open.
assert 'import Quickshell.Io' in window
assert 'import "../services/time/WorldClockPolicy.js" as WorldClockPolicy' in window
assert "readonly property var worldZones:" in window
for zone in ("UTC", "America/New_York", "Europe/London", "Asia/Tokyo"):
    assert '"'+zone+'"' in window, zone
assert "WorldClockPolicy.snapshot(localClock.date.getTime()," in window
assert 'command: ["date", "+%z"]' in window
assert 'environment: { TZ: worldLookupZone, LC_ALL: "C" }' in window
assert "Process {" in window
assert window.count("Process {") == 10
assert "worldLookup.running" in window
assert 'onLeftClicked:' in window
assert 'timew.chooseWorldZone(modelData.id)' in window
assert 'text: timew.worldTimeSnapshot.readout' in window
assert 'text: timew.worldClockReady' in window
assert 'text: "WORLD // CURRENT TIME"' in window
# Keep exactly four presets, plus WORLD as the searchable-mode selector.
assert 'property bool worldModeActive: false' in window
assert 'property string selectedQuickZone: "UTC"' in window
assert 'property string selectedSearchedZone: ""' in window
assert 'property string selectedWorldZone: "UTC"' in window
assert 'property string worldSearchQuery: ""' in window
assert 'import QtQuick.Controls' in window
assert 'import "../services/time/WorldZoneSearch.js" as WorldZoneSearch' in window
assert 'zoneCatalogLookup.exec(["timedatectl", "list-timezones", "--no-pager"])' in window
assert 'WorldZoneSearch.parseCatalog(this.text)' in window
assert 'WorldZoneSearch.search(worldZoneCatalog, worldSearchQuery,' in window
assert 'WorldZoneSearch.MAX_ZONES, worldCountryIndex)' in window
assert '120, worldCountryIndex)' not in window
assert 'WorldZoneSearch.parseCountryZones(worldCountryZoneTable, worldCountryNames)' in window
assert 'WorldZoneSearch.parseCountryNames(this.text)' in window
assert 'isoCountryLookup.exec(["cat", "/usr/share/zoneinfo/iso3166.tab"])' in window
assert 'zoneCountryLookup.exec(["cat", "/usr/share/zoneinfo/zone.tab"])' in window
assert 'property bool worldCountryLookupStarted: false' in window
assert 'function loadWorldCountryMetadata()' in window
assert 'loadWorldCountryMetadata();' in window
assert 'worldCountryLookupStarted = true;' in window
# ListView virtualizes many search hits while the host NeonScrollBar
# represents overflow rather than stretching TimeW past its frame.
assert 'id: worldSearchResults' in window
assert 'ListView {' in window
assert 'NeonScrollBar {' in window
assert 'flickable: worldSearchResults' in window
assert 'handleStyle: "star"' in window
assert 'handleColor: Colors.magenta' in window
assert 'handleBorderColor: Colors.magenta' in window
assert 'handleColor: Colors.white' not in window
assert 'geometryMode: "viewport"' in window
# The ListView reserves a separate gutter: its right edge is five px
# shy of the popup edge after the star track, while the rail begins
# only three px inward, leaving two px between rows and star rail.
assert 'id: worldSearchRail' in window
assert 'rightMargin: worldSearchRail.crossExtent + 5' in window
assert 'x: worldSearchPopup.width - width - 3' in window
assert 'y: worldSearchResults.y' in window
assert 'height: worldSearchResults.height' in window
assert 'Math.min(212, 34' in window
assert 'id: worldSearchCount' in window
assert 'top: worldSearchCount.bottom' in window
assert 'topMargin: 4' in window
assert '"ITEMS // "' in window
assert '"MATCHES // "' in window
assert '+ timew.worldSearchMatches.length' in window
assert 'modelData.country + " // "' in window
assert 'modelData.label + " // "' not in window
assert 'interactive: contentHeight > height' in window
assert 'model: timew.worldSearchMatches' in window
assert 'modelData.country' in window
assert 'TYPE CITY OR COUNTRY' in window
assert 'WorldZoneSearch.contains(worldZoneCatalog, zoneId)' in window
assert 'function toggleWorldMode()' in window
assert 'function selectWorldSearchResult(zoneId)' in window
assert 'placeholderText: "SEARCH CITY / TIME ZONE"' in window
assert 'id: worldSearchInput' in window
assert 'id: worldSearchPopup' in window
assert 'timew.worldSearchMatches[0].id' in window
assert 'timew.selectWorldSearchResult(' in window
assert 'available: !timew.worldModeActive' not in window
assert 'if (worldModeActive\n                || !worldZones.some' not in window
assert 'worldModeActive = false;\n        selectedQuickZone = zoneId;' in window
assert 'dismissWorldSearchPopup();\n        selectActiveZone(zoneId);' in window
assert 'selected: !timew.worldModeActive' in window
assert 'label: "WORLD"' in window
assert 'selected: timew.worldModeActive' in window
# The WORLD selector is the leftmost of five *enabled* choices, while
# the arrow sits LEFT of a shorter search field.
strip = window.split('id: worldZoneStrip', 1)[1]
assert strip.index('id: worldModeButton') < strip.index('model: timew.worldZones')
assert 'id: worldDropdownArrow' in window
assert 'label: "▾"' in window
assert 'onLeftClicked: timew.toggleWorldDropdown()' in window
assert 'id: worldSearchRow' in window
assert 'worldSearchRow.width' in window
assert '- worldDropdownArrow.width' in window
assert 'function toggleWorldDropdown()' in window
assert 'function dismissWorldSearchPopup()' in window
assert 'function openWorldSearchPopup()' in window
assert 'onPressed: timew.openWorldSearchPopup()' in window
# Typing is magenta and the Qt 6 cursor delegate renders orange.
search_field = window.split('TextField {\n                                    id: worldSearchInput', 1)[1].split('background: Rectangle', 1)[0]
assert 'color: Colors.magenta' in search_field
assert 'cursorDelegate: Rectangle {' in search_field
assert 'width: 2\n                                        color: Colors.orange' in search_field
# Popup is painted above the footer and below the shortcuts, so all
# five buttons still accept clicks with results visible.
assert 'z: timew.worldSearchPopupOpen ? 20 : 0' in window
assert 'y: worldZoneStrip.y + worldZoneStrip.height' in window
assert 'visible: !(timew.selectedMode === "clock"' in window
# Passive TapHandler keeps other controls usable. Clicking elsewhere in
# the menu closes the results and releases editor focus.
assert 'gesturePolicy: TapHandler.DragThreshold' in window
assert 'onTapped: function(point, button)' in window
assert 'const withinSearch =' in window
assert 'const withinPopup =' in window
assert 'if (!withinSearch && !withinPopup)' in window
assert 'timew.dismissWorldSearchPopup();' in window
assert 'worldSearchInput.focus = false;' in window
assert 'onLeftClicked: timew.toggleWorldMode()' in window
assert 'standardKeysAvailable && !worldSearchInput.activeFocus' in window
assert 'enabled: timew.navigationKeysAvailable' in window
assert 'WORLD // SELECT A SEARCH RESULT' in window
assert '"ZONE DIRECTORY UNAVAILABLE"' in window
# CLOCK WORLD search + CONVERT date/time + MATH date/time/duration fields.
assert window.count('onTextEdited:') == 15
# No dynamic command composition or arbitrary typed TZ values.
assert 'command: ["date", "+%z"]' in window
assert 'worldLookup.exec({' in window
assert 'environment: { TZ: worldLookupZone, LC_ALL: "C" }' in window
assert '["sh", "-c"' not in window
assert '["bash", "-c"' not in window
assert 'LOCAL + WORLD // LIVE // CALC HAS CONVERTER' in window
assert 'TIME ZONE CONVERTER // READ ONLY' in window
assert "label: timew.use24Hour ? \"24H\" : \"12H\"" in window
assert "onLeftClicked: timew.use24Hour = !timew.use24Hour" in window
assert "fillColor: Colors.black" in window
assert "border.color: Colors.cyan" in window
assert "accentColor: Colors.red" in window

# CALC now runs a bounded, manual zoneinfo conversion on user request.
# Its fixed script resolves from the Quickshell config root, and is never
# a dynamic command or a continuous local/system clock.
assert 'property string converterSourceZone: "UTC"' in window
assert 'property string converterTargetZone: "America/New_York"' in window
assert 'readonly property var converterZones: worldZones.concat(' in window
assert 'selectedSearchedZone !== ""' in window
assert 'function cycleConverterZone(which)' in window
assert 'function runTimeConverter()' in window
assert 'if (converterBusy || !menuOpen || selectedMode !== "calc")' in window
assert 'id: converterProcess' in window
assert 'converterProcess.exec([' in window
assert '"python3", "-B", "-I"' in window
assert 'Quickshell.shellPath("services/time/TimeZoneConverter.py")' in window
assert 'src, dst, converterDate, converterParsedTime.canonical' in window
assert 'id: converterPane' in window
assert 'id: converterDateInput' in window
assert 'id: converterTimeInput' in window
assert 'id: converterRunButton' in window
assert 'onLeftClicked: timew.runTimeConverter()' in window
assert 'timew.converterSubmittedKey !== timew.converterInputsKey' in window
assert 'REPEATED HOUR // TWO POSSIBLE INSTANTS' in window
assert 'TIME DOES NOT EXIST // DST CLOCK JUMP' in window
assert 'modelData.source,' in window
assert '!converterDateInput.activeFocus && !converterTimeInput.activeFocus' in window
assert 'TIME CALCULATOR // NOT CONNECTED' not in window
# Conversion adds one on-demand process, no persistent interval or clock tick.
assert window.count("SystemClock {") == 1
assert window.count("\n    Timer {") == 3
assert window.count("ElapsedTimer {") == 3

# Two independent CALC 12/24-hour presentation controls. The input is
# converted to backend-ready HH:MM; output formats the existing result only.
formatting = (ROOT / "services/time/TimeConverterFormat.js").read_text(encoding="utf-8")
assert 'import "../services/time/TimeConverterFormat.js" as ConverterFormat' in window
assert 'property bool converterInput24Hour: true' in window
assert 'property bool converterOutput24Hour: true' in window
assert 'converterInput24Hour ? Colors.orange : Colors.cyan' in window
assert 'converterOutput24Hour ? Colors.orange : Colors.cyan' in window
assert 'function toggleConverterInputFormat()' in window
assert 'function toggleConverterOutputFormat()' in window
assert 'ConverterFormat.convertInput(' in window
assert 'ConverterFormat.parseInput(converterTime, converterInput24Hour)' in window
assert 'converterInput24Hour = target24;' in window
assert 'converterTime = converted.text;' in window
assert 'if (!converted.valid)' in window
assert 'converterResult = {status: converted.error, options: []};' in window
assert 'if (!converterParsedTime.valid)' in window
assert 'converterParsedTime.canonical' in window
assert 'property bool converterBusy: false' in window
assert 'id: converterInputFormatButton' in window
assert 'id: converterOutputFormatButton' in window
assert 'label: timew.converterInput24Hour ? "24H" : "12H"' in window
assert 'label: timew.converterOutput24Hour ? "24H" : "12H"' in window
assert 'onLeftClicked: timew.toggleConverterInputFormat()' in window
assert 'onLeftClicked: timew.toggleConverterOutputFormat()' in window
assert 'id: converterResultHeader' in window
assert 'width: Math.max(0, parent.width' in window
assert 'converterResultHeader.spacing' in window
assert 'ConverterFormat.formatResult(' in window
assert window.count('timew.converterOutput24Hour)') >= 2
assert 'color: timew.converterOutputFormatColor' in window
assert 'color: timew.converterInputFormatColor' not in window or (
    'accentColor: timew.converterInputFormatColor' in window)
# No switch may trigger an extra process or overwrite another format state.
assert window.count('converterProcess.exec([') == 1
assert 'converterInput24Hour = !converterInput24Hour;' not in window
assert 'converterOutput24Hour = !converterOutput24Hour;' in window
assert 'converterResult = null;' not in window.split(
    'function toggleConverterOutputFormat()', 1)[1].split('}', 1)[0]
assert 'function parseInput(value, is24Hour)' in formatting
assert 'function convertInput(value, sourceIs24Hour, targetIs24Hour)' in formatting
assert 'function formatResult(value, use24Hour)' in formatting
assert 'const parsed = parseInput(value, sourceIs24Hour);' in formatting
assert 'return displayInput(parsed.canonical, targetIs24Hour);' in formatting

# CALC provides *independent* country-first IANA zone dropdowns. CHANGE
# remains the existing quick-cycle mechanism, not a replacement for search.
picker = (ROOT / "widgets/TimeZonePicker.qml").read_text(encoding="utf-8")
assert 'property string activeConverterDropdown: ""' in window
assert 'function openConverterDropdown(which)' in window
assert 'function toggleConverterDropdown(which)' in window
assert 'function closeConverterDropdowns()' in window
assert 'function chooseConverterSearchZone(which, zoneId)' in window
assert 'WorldZoneSearch.contains(worldZoneCatalog, zoneId)' in window
assert 'function converterZoneAllowed(zoneId)' in window
assert 'if (!converterZoneAllowed(src) || !converterZoneAllowed(dst))' in window
assert 'selectedMode !== "clock" && selectedMode !== "calc"' in window
assert 'selectedMode === "clock" || selectedMode === "calc"' in window
assert 'id: converterSourcePicker' in window
assert 'id: converterTargetPicker' in window
assert window.count("TimeZonePicker {") == 4
assert 'selectedZone: timew.converterSourceZone' in window
assert 'selectedZone: timew.converterTargetZone' in window
assert 'expanded: timew.activeConverterDropdown === "source"' in window
assert 'expanded: timew.activeConverterDropdown === "target"' in window
assert 'onZoneChosen: function(zoneId)' in window
assert 'timew.chooseConverterSearchZone("source", zoneId)' in window
assert 'timew.chooseConverterSearchZone("target", zoneId)' in window
# Two CONVERT CHANGE buttons + MATH source-zone quick-cycle button.
assert window.count('label: "CHANGE"') == 4
assert 'onLeftClicked: timew.cycleConverterZone("source")' in window
assert 'onLeftClicked: timew.cycleConverterZone("target")' in window
assert 'converterSourcePicker.searchFocused' in window
assert 'converterTargetPicker.searchFocused' in window
assert 'mathZonePicker.searchFocused' in window
assert 'converterSourcePicker.containsFramePoint(' in window
assert 'converterTargetPicker.containsFramePoint(' in window
assert 'mathZonePicker.containsFramePoint(' in window
assert 'const onMathZone = mathZonePicker.containsFramePoint(' in window
assert 'z: 40' in window and 'z: 30' in window
assert 'z: timew.activeConverterDropdown !== "" ? 20 : 0' in window
assert 'TIME ZONE CONVERTER // READ ONLY' in window
assert 'FROM and TO support independent country/zone search' in window
assert 'id: zoneResults' in picker
assert 'ZoneSearch.search(catalog, query, ZoneSearch.MAX_ZONES, countryIndex)' in picker
assert 'picker.query.trim() === "" ? "ITEMS // " : "MATCHES // "' in picker
assert 'modelData.country + " // " + modelData.label' in picker
assert 'NeonScrollBar {' in picker
assert 'flickable: zoneResults' in picker
assert 'handleStyle: "star"' in picker
assert 'handleColor: Colors.magenta' in picker
assert 'rightMargin: pickerRail.crossExtent + 5' in picker
assert 'id: searchInput' in picker
assert 'color: Colors.magenta' in picker
assert 'cursorDelegate: Rectangle { width: 2; color: Colors.orange }' in picker
assert 'onTextEdited:' in picker
assert 'picker.openRequested()' in picker
assert 'picker.zoneChosen(modelData.id)' in picker
assert 'function containsFramePoint(frame, px, py)' in picker
assert 'function dropFocus()' in picker

# CALC MATH introduces a manually triggered, separate Python zoneinfo
# elapsed-duration calculation. CONVERT and MATH are independent views and
# retain the user's shared civil date/time, input/output formats, FROM zone.
assert 'property string calcView: "convert"' in window
assert 'function setCalcView(which)' in window
assert 'function toggleMathOperation()' in window
assert 'function runTimeArithmetic()' in window
assert 'calcView !== "math"' in window
assert 'id: calcSubModeStrip' in window
assert 'labelText: "CONVERT"' in window
assert 'labelText: "MATH"' in window
assert 'onTriggered: timew.setCalcView("convert")' in window
assert 'onTriggered: timew.setCalcView("math")' in window
assert 'timew.calcView === "convert"' in window
assert 'timew.calcView === "math"' in window
assert 'id: mathPane' in window
# MATH has a dedicated popup, bound to the existing shared FROM zone;
# tapping another part of MATH dismisses it without touching the active
# source selection or the CONVERT target picker.
assert 'id: mathZonePicker' in window
assert 'selectedZone: timew.converterSourceZone' in window
assert 'expanded: timew.activeConverterDropdown === "math"' in window
assert 'onOpenRequested: timew.openConverterDropdown("math")' in window
assert 'onToggleRequested: timew.toggleConverterDropdown("math")' in window
assert 'timew.chooseConverterSearchZone("math", zoneId)' in window
assert 'if (which === "source" || which === "math")' in window
assert 'if (which !== "source" && which !== "target"' in window
assert '&& which !== "math" && which !== "difference")' in window
assert 'which === "math" && calcView !== "math"' in window
assert 'which === "difference"' in window
assert 'which !== "math" && calcView !== "convert"' not in window
assert 'mathZonePicker.dropFocus();' in window
assert 'timew.calcView === "math"' in window
assert 'z: (timew.activeConverterDropdown === "math"' in window
assert '|| timew.activeConverterDropdown === "difference")' in window
assert 'id: mathZoneRow' in window
assert 'mathZoneRow.spacing * 2' in window
assert 'catalog: timew.worldZoneCatalog' in window
assert 'countryIndex: timew.worldCountryIndex' in window
assert window.count('label: "CHANGE"') == 4
assert 'id: mathDateInput' in window
assert 'id: mathTimeInput' in window
assert 'id: mathDaysInput' in window
assert 'id: mathHoursInput' in window
assert 'id: mathMinutesInput' in window
assert 'id: mathTimeFormatButton' in window
assert 'id: mathResultFormatButton' in window
assert 'property string mathDays: "0"' in window
assert 'property string mathHours: "1"' in window
assert 'property string mathMinutes: "0"' in window
assert 'property string mathOperation: "add"' in window
assert 'mathOperation === "add" ? "subtract" : "add"' in window
assert 'onLeftClicked: timew.toggleMathOperation()' in window
assert 'onLeftClicked: timew.runTimeArithmetic()' in window
assert 'mathSubmittedKey !== timew.mathInputsKey' in window
assert 'property bool mathBusy: false' in window
assert 'onMathInputsKeyChanged: mathResult = null' in window
assert 'id: arithmeticProcess' in window
assert 'arithmeticProcess.exec([' in window
assert 'Quickshell.shellPath("services/time/TimeArithmetic.py")' in window
assert 'converterSourceZone, converterDate,' in window
assert 'converterParsedTime.canonical, mathOperation,' in window
assert 'mathDays, mathHours, mathMinutes' in window
assert 'ELAPSED // 1 DAY = 24 HOURS' in window
assert 'REPEATED HOUR // 2 RESULTS' in window
assert 'MATH // 1 RESULT' in window
assert 'TIME DOES NOT EXIST // DST CLOCK JUMP' in window
assert window.count("SystemClock {") == 1
assert window.count("\n    Timer {") == 3
assert window.count("ElapsedTimer {") == 3
assert window.count('arithmeticProcess.exec([') == 1
assert window.count('converterProcess.exec([') == 1
arithmetic = (ROOT / "services/time/TimeArithmetic.py").read_text(encoding="utf-8")
assert 'ZoneInfo(zone)' in arithmetic
assert 'utc + duration' in arithmetic
assert 'original.replace(tzinfo=None) != naive' in arithmetic
assert 'AMBIGUOUS_LOCAL_TIME' in arithmetic
assert 'NONEXISTENT_LOCAL_TIME' in arithmetic
assert 'DURATION_OUT_OF_RANGE' in arithmetic
assert 'operation == "subtract"' in arithmetic
assert '3650' in arithmetic

# MATH // BETWEEN compares two independently zoned civil times without
# changing the existing ADD/SUB calculator or introducing a recurring timer.
assert 'property string mathView: "elapsed"' in window
assert 'function setMathView(which)' in window
assert 'labelText: "ADD / SUB"' in window
assert 'labelText: "BETWEEN"' in window
assert 'id: mathTypeStrip' in window
assert 'timew.setMathView("elapsed")' in window
assert 'timew.setMathView("between")' in window
assert 'id: mathDifferencePane' in window
assert 'visible: timew.mathView === "between"' in window
assert 'id: differenceEndZoneRow' in window
assert 'id: differenceEndPicker' in window
assert 'selectedZone: timew.differenceEndZone' in window
assert 'expanded: timew.activeConverterDropdown === "difference"' in window
assert 'timew.openConverterDropdown("difference")' in window
assert 'timew.toggleConverterDropdown("difference")' in window
assert 'timew.chooseConverterSearchZone("difference", zoneId)' in window
assert 'differenceEndPicker.dropFocus();' in window
assert 'differenceEndPicker.searchFocused' in window
assert 'differenceEndPicker.containsFramePoint(' in window
assert 'property string differenceEndZone: "UTC"' in window
assert 'property bool differenceEnd24Hour: true' in window
assert 'function toggleDifferenceEndFormat()' in window
assert 'id: differenceEndDateInput' in window
assert 'id: differenceEndTimeInput' in window
assert 'id: differenceEndFormatButton' in window
assert 'id: differenceRunButton' in window
assert 'onLeftClicked: timew.runTimeDifference()' in window
assert 'function runTimeDifference()' in window
assert 'differenceEndParsedTime.canonical' in window
assert 'converterParsedTime.canonical,' in window
assert 'Quickshell.shellPath("services/time/TimeDifference.py")' in window
assert 'id: differenceProcess' in window
assert window.count('differenceProcess.exec([') == 1
assert 'differenceSubmittedKey !== timew.differenceInputsKey' in window
assert 'onDifferenceInputsKeyChanged: differenceResult = null' in window
assert 'id: differenceResultHeader' in window
assert 'id: differenceOutputFormatButton' in window
assert 'id: differenceResultsArea' in window
assert 'id: differenceResults' in window
assert 'id: differenceResultsRail' in window
assert 'flickable: differenceResults' in window
assert 'x: differenceResultsArea.width - width - 3' in window
assert 'handleColor: Colors.magenta' in window
assert 'modelData.sign' in window
assert 'modelData.days' in window
assert 'modelData.hours' in window
assert 'modelData.minutes' in window
assert 'DST OVERLAP // MULTIPLE DURATIONS' in window
assert 'ELAPSED DURATION // ZONES AND DST AWARE' in window
assert 'visible: timew.mathView === "elapsed"' in window
assert window.count("SystemClock {") == 1
assert window.count("\n    Timer {") == 3
assert window.count("ElapsedTimer {") == 3
difference = (ROOT / "services/time/TimeDifference.py").read_text(encoding="utf-8")
assert 'ZoneInfo(zone)' in difference
assert 'for fold in (0, 1)' in difference
assert 'roundtrip.replace(tzinfo=None) != naive' in difference
assert 'end_utc - start_utc' in difference
assert 'AMBIGUOUS_LOCAL_TIME' in difference
assert 'START_' in difference and 'END_' in difference

# TOOLS stopwatch: Quickshell's monotonic ElapsedTimer owns measurement;
# the display's 100ms Timer cannot determine elapsed time by tick counting.
stopwatch_policy = (ROOT / "services/time/StopwatchPolicy.js").read_text(encoding="utf-8")
assert 'import "../services/time/StopwatchPolicy.js" as StopwatchPolicy' in window
assert 'ElapsedTimer {' in window
assert 'id: stopwatchAnchor' in window
assert 'stopwatchAnchor.elapsed() * 1000' in window
assert 'stopwatchAnchor.restart();' in window
assert 'Date.now()' not in window
assert 'property bool stopwatchRunning: false' in window
assert 'property real stopwatchAccumulatedMs: 0' in window
assert 'property var stopwatchLaps: []' in window
assert 'readonly property int stopwatchMaxLaps: StopwatchPolicy.MAX_LAPS' in window
for method in ('refreshStopwatch', 'startStopwatch', 'pauseStopwatch',
               'lapStopwatch', 'resetStopwatch'):
    assert 'function ' + method + '()' in window
assert 'StopwatchPolicy.sample(' in window
assert 'StopwatchPolicy.appendLap(' in window
assert 'stopwatchLastLapMs = stopwatchDisplayMs' in window
assert 'id: stopwatchDisplayTimer' in window
assert 'interval: 100' in window
assert 'timew.stopwatchRunning' in window
assert '&& timew.menuOpen && timew.selectedMode === "tools"' in window
assert 'onTriggered: timew.refreshStopwatch()' in window
assert 'id: stopwatchPane' in window
assert 'STOPWATCH // ELAPSED TIME' in window
assert 'StopwatchPolicy.format(timew.stopwatchDisplayMs)' in window
assert 'STATUS // RUNNING' in window
assert 'STATUS // PAUSED' in window
assert 'STATUS // READY' in window
assert 'id: stopwatchRunButton' in window
assert 'id: stopwatchSecondaryButton' in window
assert '"PAUSE"' in window and '"RESUME"' in window and '"START"' in window
assert '"LAP"' in window and '"RESET"' in window
assert 'timew.pauseStopwatch();' in window
assert 'timew.startStopwatch();' in window
assert 'timew.lapStopwatch();' in window
assert 'timew.resetStopwatch();' in window
assert 'id: stopwatchLapList' in window
assert 'id: stopwatchLapRail' in window
assert 'x: stopwatchLapArea.width - width - 3' in window
assert 'flickable: stopwatchLapList' in window
assert 'handleColor: Colors.magenta' in window
assert 'stopwatchLapRail.crossExtent + 6' in window
assert 'model: timew.stopwatchLaps' in window
assert 'modelData.splitMs' in window and 'modelData.totalMs' in window
assert 'MONOTONIC // CONTINUES WHILE WINDOW IS CLOSED' in window
assert 'var MAX_LAPS = 100;' in stopwatch_policy
assert 'function sample(accumulatedMs, segmentMs)' in stopwatch_policy
assert 'function appendLap(existing, totalMs, previousLapMs, sequence)' in stopwatch_policy
assert 'return next.slice(0, MAX_LAPS);' in stopwatch_policy

# TOOLS countdown now owns a bounded collection of independent named
# timers, sharing one monotonic elapsed timeline and one heartbeat.
countdown_policy = (ROOT / "services/time/CountdownPolicy.js").read_text(encoding="utf-8")
assert 'import "../services/time/CountdownPolicy.js" as CountdownPolicy' in window
assert 'property string toolsView: "stopwatch"' in window
assert 'id: toolsSubModeStrip' in window
assert 'labelText: "STOPWATCH"' in window
assert 'labelText: "COUNTDOWN"' in window
assert 'selected: timew.toolsView === "stopwatch"' in window
assert 'selected: timew.toolsView === "countdown"' in window
assert 'timew.toolsView = "countdown";' in window
assert 'timew.toolsView = "stopwatch";' in window
assert 'id: countdownAnchor' in window
assert 'Component.onCompleted: restart()' in window
assert 'id: countdownHeartbeat' in window
assert 'running: timew.countdownRunningCount > 0' in window
assert 'onTriggered: timew.refreshCountdowns()' in window
assert '&& timew.toolsView === "countdown" ? 100 : 1000' in window
assert 'id: stopwatchDisplayTimer' in window
assert '&& timew.toolsView === "stopwatch"' in window
assert 'property var countdownTimers: [CountdownPolicy.createTimer(1)]' in window
assert 'property int countdownNextId: 2' in window
assert 'property int selectedCountdownId: 1' in window
assert 'readonly property var selectedCountdown:' in window
assert 'readonly property int countdownRunningCount:' in window
assert 'CountdownPolicy.byId(countdownTimers, selectedCountdownId)' in window
assert 'CountdownPolicy.runningCount(countdownTimers)' in window
assert 'CountdownPolicy.tick(countdownTimers, countdownNowMs())' in window
assert 'return countdownAnchor.elapsed() * 1000' in window
for method in ('countdownNowMs', 'refreshCountdowns', 'createCountdown',
               'startCountdown', 'pauseCountdown', 'resetCountdown',
               'removeCountdown'):
    assert 'function ' + method + '()' in window
assert 'function selectCountdown(id)' in window
assert 'function editCountdown(field, value)' in window
assert 'timer.status !== "ready"' in window
assert 'countdownTimers.length >= CountdownPolicy.MAX_TIMERS' in window
assert 'countdownTimers.length <= 1' in window
assert 'selectedCountdownId = countdownTimers[0].id' in window
assert 'CountdownPolicy.act(' in window
assert 'countdownTimers = countdownTimers.concat([newTimer])' in window
assert 'id: countdownPane' in window
assert 'id: countdownTimerList' in window
assert 'id: countdownListRail' in window
assert 'flickable: countdownTimerList' in window
assert 'x: countdownListArea.width - width - 3' in window
assert 'rightMargin: countdownListRail.crossExtent + 6' in window
assert 'handleColor: Colors.magenta' in window
assert 'id: newCountdownButton' in window
assert 'id: countdownNameField' in window
assert 'id: countdownHoursField' in window
assert 'id: countdownMinutesField' in window
assert 'id: countdownSecondsField' in window
assert 'readOnly: timew.selectedCountdown.status !== "ready"' in window
assert 'id: countdownRunButton' in window
assert 'id: countdownResetButton' in window
assert 'id: countdownRemoveButton' in window
assert 'onLeftClicked: timew.createCountdown()' in window
assert 'onLeftClicked: timew.resetCountdown()' in window
assert 'onLeftClicked: timew.removeCountdown()' in window
assert 'timew.pauseCountdown();' in window
assert 'timew.startCountdown();' in window
assert 'STATUS // ' in window
assert 'MAX 8 TIMERS // MONOTONIC // SESSION ONLY' in window
assert 'NO AUDIO OR DESKTOP NOTIFICATION // INITIAL SLICE' in window
assert 'countdownNameField.activeFocus' in window
assert 'countdownHoursField.activeFocus' in window
assert 'countdownMinutesField.activeFocus' in window
assert 'countdownSecondsField.activeFocus' in window
assert 'var MAX_TIMERS = 8;' in countdown_policy
assert 'var MAX_NAME_LENGTH = 32;' in countdown_policy
assert 'function parseDuration(hours, minutes, seconds)' in countdown_policy
assert 'function remaining(segmentBudgetMs, segmentElapsedMs)' in countdown_policy
assert 'function createTimer(id)' in countdown_policy
assert 'function tick(entries, nowMs)' in countdown_policy
assert 'function act(entries, id, action, nowMs)' in countdown_policy
assert 'function format(milliseconds)' in countdown_policy
# No notifier side effects, wall-clock queries or new background processes.
assert window.count("SystemClock {") == 1
assert window.count("ElapsedTimer {") == 3
assert window.count("\n    Timer {") == 3
assert 'property bool countdownStarted: false' not in window

# MACHINE milestone: a read-only TimeW-instance timer plus user-initiated
# session-only timestamp markers. These are NOT desktop/Sway snapshots,
# Hospital checkpoints, screenshots, or restoration actions.
machine_policy = (ROOT / "services/time/MachineTimelinePolicy.js").read_text(encoding="utf-8")
assert 'import "../services/time/MachineTimelinePolicy.js" as MachineTimelinePolicy' in window
assert 'id: machineLifetimeAnchor' in window
assert 'readonly property string machineInstanceAge:' in window
assert 'localClock.date' in window
assert 'MachineTimelinePolicy.ageLabel(machineLifetimeAnchor.elapsed() * 1000)' in window
assert 'MachineTimelinePolicy.utcStamp(localClock.date.getTime())' in window
assert 'property string machineMarkerDraft: ""' in window
assert 'property var machineMarkers: []' in window
assert 'property int machineMarkerNextId: 1' in window
assert 'function addMachineMarker()' in window
assert 'function removeMachineMarker(id)' in window
assert 'if (!menuOpen || selectedMode !== "machine")' in window
assert 'MachineTimelinePolicy.createMarker(' in window
assert 'MachineTimelinePolicy.appendMarker(machineMarkers, marker)' in window
assert 'MachineTimelinePolicy.removeMarker(machineMarkers, id)' in window
assert 'machineMarkerNextId += 1' in window
assert 'id: machinePane' in window
assert 'MACHINE // SESSION TIMELINE' in window
assert 'WINDOW INSTANCE // ELAPSED' in window
assert 'MANUAL TIME MARKERS // MEMORY ONLY' in window
assert 'id: machineMarkerInput' in window
assert 'maximumLength: MachineTimelinePolicy.MAX_NAME_LENGTH' in window
assert 'machineMarkerInput.activeFocus' in window
assert 'onTextEdited: timew.machineMarkerDraft = text' in window
assert 'onAccepted: timew.addMachineMarker()' in window
assert 'id: machineMarkButton' in window
assert 'onLeftClicked: timew.addMachineMarker()' in window
assert 'id: machineMarkerList' in window
assert 'model: timew.machineMarkers' in window
assert 'id: machineMarkerRail' in window
assert 'flickable: machineMarkerList' in window
assert 'rightMargin: machineMarkerRail.crossExtent + 6' in window
assert 'x: machineMarkerArea.width - width - 3' in window
assert 'handleStyle: "star"' in window
assert 'handleColor: Colors.magenta' in window
assert 'timew.removeMachineMarker(modelData.id)' in window
assert 'MARKERS ARE TIMESTAMPS ONLY // LOST ON RESTART' in window
assert 'NO SCREENSHOTS OR RESTORATION ACTIVE' in window
assert 'MACHINE // LOCAL CHECKPOINTS' in window
assert 'var MAX_MARKERS = 24;' in machine_policy
assert 'var MAX_NAME_LENGTH = 48;' in machine_policy
assert 'function createMarker(id, name, nowMs, elapsedMs)' in machine_policy
assert 'function appendMarker(existing, marker)' in machine_policy
assert 'function removeMarker(existing, id)' in machine_policy
assert 'function ageLabel(elapsedMs)' in machine_policy
assert 'function utcStamp(nowMs)' in machine_policy
# Preserve the dedicated CLOCK/STOPWATCH/COUNTDOWN clock architecture.
assert window.count("SystemClock {") == 1
assert window.count("ElapsedTimer {") == 3
assert window.count("\n    Timer {") == 3
# MACHINE now has one read-only Sway capture Process and one guarded SQLite store Process.
assert window.count("Process {") == 10
assert "id: machineCaptureProcess" in window
assert "id: machineStoreProcess" in window
assert "id: machineResolverProcess" in window

# Universal visual language remains: magenta header, cyan divider, borderless modes.
assert 'text: "TIME // W"' in window
assert "color: Colors.magenta" in window
assert "id: headerDivider" in window
assert "height: 2\n                color: Colors.cyan" in window
assert "bordered: false" in window
assert "trackDefaultGlowsLocally: true" in window

# The shared destructive Close is the real U+00D7 X, red in idle and hover.
start = window.index("id: closeButton")
end = window.index("onLeftClicked: timew.menuOpen = false", start)
close = window[start:end]
for prop in ('label: "×"', "labelPixelSize: 22", "destructive: true",
             "accentColor: Colors.red", "hoverForegroundColor: Colors.red",
             "hoverBorderColor: Colors.red"):
    assert prop in close, prop

# Both TOOLS clocks are session-local elapsed counters. Desktop alarms,
# system notifications, Sway restoration and persistence remain unimplemented.
assert "NO SCREENSHOTS OR RESTORATION ACTIVE" in window
assert "STOPWATCH + TIMERS // NOT CONNECTED" not in window
assert "COUNTDOWN TIMERS // NEXT DEVELOPMENT STAGE" not in window
assert "NO AUDIO OR DESKTOP NOTIFICATION // INITIAL SLICE" in window
assert "FOUNDATION PREVIEW // UI ONLY" in window
for primitive in ("JsonAdapter {", "FileView {", "swaymsg",
                  "grim ", "onTriggered: capture", "kill -",
                  '["sh", "-c"', '["bash", "-c"'):
    assert primitive not in window, primitive

print("TIMEW M1 SOURCE CONTRACTS: PASS (runtime preview still required)")
