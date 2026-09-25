import QtQuick
import Quickshell

Scope {
    id: systemMonitorController

    // Portable controller contract for SystemMonitorView.
    //
    // selectionAdapter is view-specific and owns selection/favorite unwrapping.
    // favoriteAdapter is optional and owns monitor-box favorite persistence.
    // presentation/control are shared Team 1 physiology.
    required property var selectionAdapter
    required property var presentation
    required property var control

    property var favoriteAdapter: null

    // Compatibility shim for the current SystemMonitorView contract.
    // AppControl's historical systemRebootArmed state is dead: it is never
    // armed, only reset false. Reboot confirmation belongs to host modal UI.
    readonly property bool systemRebootArmed: false

    signal rebootRequested(var entry)
    signal refreshRequested()

    function selectedResult() {
        return selectionAdapter && selectionAdapter.selectedResult
               ? selectionAdapter.selectedResult()
               : null;
    }

    function selectedResultIsSystemComponent() {
        return selectionAdapter
               && selectionAdapter.selectedResultIsSystemComponent
               ? !!selectionAdapter.selectedResultIsSystemComponent()
               : false;
    }

    function favoriteSourceItem(entry) {
        if (selectionAdapter && selectionAdapter.favoriteSourceItem)
            return selectionAdapter.favoriteSourceItem(entry);

        return entry && entry._favoriteRecord
               ? entry._sourceItem
               : entry;
    }

    function systemAccent(entry) {
        return presentation.systemAccent(entry);
    }

    function systemIconFor(entry) {
        return presentation.systemIconFor(entry);
    }

    function systemRateMetricParts(entry) {
        return presentation.systemRateMetricParts(entry);
    }

    function systemComponentWarning(entry) {
        return presentation.systemComponentWarning(entry);
    }

    function contributorRows(entry) {
        return presentation.contributorRows(entry);
    }

    function isMonitorBoxFavorite(entry, boxId) {
        return favoriteAdapter && favoriteAdapter.isMonitorBoxFavorite
               ? !!favoriteAdapter.isMonitorBoxFavorite(entry, boxId)
               : false;
    }

    function toggleMonitorBoxFavorite(entry, boxId) {
        if (favoriteAdapter && favoriteAdapter.toggleMonitorBoxFavorite)
            favoriteAdapter.toggleMonitorBoxFavorite(entry, boxId);
    }

    function runSystemComponentAction(entry, action) {
        return control.runComponentAction(entry, action);
    }

    function terminateSystemContributor(entry) {
        return control.terminateContributor(entry);
    }

    Connections {
        target: systemMonitorController.control

        function onRebootRequested(entry) {
            systemMonitorController.rebootRequested(entry);
        }

        function onRefreshRequested() {
            systemMonitorController.refreshRequested();
        }
    }
}
