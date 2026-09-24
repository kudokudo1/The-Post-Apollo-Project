import QtQuick

QtObject {
    id: taskHost

    // AppControl-specific adapter for TaskManagerView's remaining host/UI
    // contract. The shared view no longer knows or depends on AppControl.
    required property var controller

    readonly property bool detailFocused:
        !!controller && !!controller.detailFocused
    readonly property bool keyboardActive:
        !!controller && !!controller.keyboardActive
    readonly property int selectedDetailActionIndex:
        controller ? Number(controller.selectedDetailActionIndex) : -1
    readonly property bool menuOpen:
        !!controller && !!controller.menuOpen
    readonly property bool hunterMetricView:
        !!controller
        && controller.selectedModeIndex === controller.killModeIndex
        && controller.killViewMode === controller.killViewHunter

    function setKeyboardActive(value) {
        if (controller)
            controller.keyboardActive = !!value;
    }

    function clearModeRailFocus() {
        if (controller)
            controller.modeRailFocused = false;
    }

    function setDetailFocused(value) {
        if (controller)
            controller.detailFocused = !!value;
    }

    function setDetailActionIndex(index) {
        if (controller)
            controller.selectedDetailActionIndex = Number(index);
    }

    function moveDetailSelection(direction) {
        if (controller)
            controller.moveDetailSelection(Number(direction || 0));
    }

    function ensureDetailActionVisible() {
        if (controller)
            controller.ensureDetailActionVisible();
    }

    function isTaskMetricFavorite(entry, metricId) {
        return controller
               ? controller.isTaskMetricFavorite(entry, metricId)
               : false;
    }

    function toggleTaskMetricFavorite(entry, metricId) {
        if (controller)
            controller.toggleTaskMetricFavorite(entry, metricId);
    }
}
