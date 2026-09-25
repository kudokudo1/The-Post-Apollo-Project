import QtQuick

QtObject {
    id: host

    required property var appControlWindow
    required property var cpuPlusWindow
    required property var thermalController

    // CPU++ owns its own navigation/focus state. The shared monitor views
    // mutate these properties just as they do on AppControl.
    property bool detailFocused: false
    property bool keyboardActive: false
    property bool modeRailFocused: false
    property int selectedDetailActionIndex: -1

    readonly property bool systemRebootArmed:
        appControlWindow
        ? !!appControlWindow.systemRebootArmed
        : false

    function selectedResult() {
        return cpuPlusWindow
               ? cpuPlusWindow.selectedMonitorEntry()
               : null;
    }

    function selectedResultIsThermal() {
        const entry = selectedResult();

        return !!cpuPlusWindow
               && cpuPlusWindow.selectedModeIndex === 2
               && !!entry
               && !!entry._thermalRecord;
    }

    function selectedResultIsSystemComponent() {
        const entry = selectedResult();

        return !!cpuPlusWindow
               && cpuPlusWindow.selectedModeIndex === 3
               && !!entry
               && !!entry._systemRecord;
    }

    function favoriteSourceItem(entry) {
        if (entry && entry._favoriteRecord)
            return entry._sourceItem;

        return entry;
    }

    function celsiusToFahrenheit(value) {
        return thermalController.celsiusToFahrenheit(value);
    }

    function thermalColorForCelsius(value) {
        return thermalController.thermalColorForCelsius(value);
    }

    function thermalAccent(entry) {
        return thermalController.thermalAccent(entry);
    }

    function systemAccent(entry) {
        return appControlWindow
               ? appControlWindow.systemAccent(entry)
               : "white";
    }

    function systemIconFor(entry) {
        return appControlWindow
               ? appControlWindow.systemIconFor(entry)
               : "🖳";
    }

    function systemRateMetricParts(entry) {
        return appControlWindow
               ? appControlWindow.systemRateMetricParts(entry)
               : [];
    }

    function systemComponentWarning(entry) {
        return appControlWindow
               ? appControlWindow.systemComponentWarning(entry)
               : "";
    }

    function contributorRows(entry) {
        if (appControlWindow)
            return appControlWindow.contributorRows(entry);

        return entry && Array.isArray(entry.contributors)
               ? entry.contributors
               : [];
    }

    // Monitor-box favorites still belong to AppControl's mode-aware favorite
    // store. Do not falsify its active mode from CPU++; expose them as inactive
    // until that store gets its own shared service.
    function isMonitorBoxFavorite(entry, boxId) {
        return false;
    }

    function toggleMonitorBoxFavorite(entry, boxId) {
        // Intentionally no-op for this first two-body transplant.
    }

    // Fan control remains the same shared backend.
    function fanControlUnlocked(entry) {
        return thermalController.fanControlUnlocked(entry);
    }

    function toggleFanControlUnlocked(entry) {
        thermalController.toggleFanControlUnlocked(entry);
    }

    function desiredFanPercentFor(entry) {
        return thermalController.desiredFanPercentFor(entry);
    }

    function setDesiredFanPercent(entry, percent) {
        thermalController.setDesiredFanPercent(entry, percent);
    }

    function clearDesiredFanPercent(entry) {
        thermalController.clearDesiredFanPercent(entry);
    }

    function pendingFanPercentFor(entry) {
        return thermalController.pendingFanPercentFor(entry);
    }

    function writeFanControl(entry, action, percent) {
        thermalController.writeFanControl(entry, action, percent);
    }

    function writeFanPercent(entry, percent) {
        thermalController.writeFanPercent(entry, percent);
    }

    // System actions reuse the existing backend and its safety behavior.
    function runSystemComponentAction(entry, action) {
        if (appControlWindow)
            appControlWindow.runSystemComponentAction(entry, action);
    }

    function terminateSystemContributor(entry) {
        if (appControlWindow)
            appControlWindow.terminateSystemContributor(entry);
    }
}
