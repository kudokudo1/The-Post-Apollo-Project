import QtQuick
import Quickshell

// Team 8 — standalone APPS Core facade.
//
// This is a composition surface for future host integration. It contains no
// AppControlW dependency and does not own any sibling-team physiology.
//
// External contracts:
//   - identityEvidence: Team 7 DesktopIdentityEvidence-compatible object
//   - hiddenCommandNames: command catalog supplied by future RunService
//   - preferencePredicate: optional Team 2/host ranking signal
//   - supplied SurfaceLaunch augmentation: T5-domain launcher-neutral payload
Scope {
    id: facade

    property var identityEvidence: null
    property var hiddenCommandNames: []
    property var preferencePredicate: null
    property var appOverrides: ({})

    readonly property int sourceNative: core.sourceNative
    readonly property int sourceFlatpak: core.sourceFlatpak
    readonly property int sourceHidden: core.sourceHidden

    readonly property int launchNormal: core.launchNormal
    readonly property int launchToolbox: core.launchToolbox
    readonly property int launchBottle: core.launchBottle

    readonly property var bottleNames: bottles.names
    readonly property string selectedBottleName: bottles.selectedName
    readonly property bool bottlesLoading: bottles.loading
    readonly property string bottlesError: bottles.errorText

    AppCoreProvider {
        id: core
        appOverrides: facade.appOverrides
    }

    AppLaunchPlanner {
        id: launchPlanner
        coreProvider: core
    }

    AppBottleProvider {
        id: bottles
    }

    AppActionCatalog {
        id: actionCatalog
    }

    AppActionPlanner {
        id: actionPlanner
        actionCatalog: actionCatalog
    }

    AppCatalogPolicy {
        id: catalogPolicy
        coreProvider: core
    }

    AppHiddenAdapter {
        id: hiddenAdapter
        launchPlanner: launchPlanner
    }

    AppSelectionPolicy {
        id: selectionPolicy
        catalogPolicy: catalogPolicy
    }

    AppIdentityAdapter {
        id: identityAdapter
        identityEvidence: facade.identityEvidence
    }

    function desktopEntries() {
        return core.desktopEntries();
    }

    function hiddenEntries() {
        return hiddenAdapter.records(
            hiddenCommandNames,
            core.desktopEntries()
        );
    }

    function resultRows(queryText, sourceMode) {
        return catalogPolicy.rows(
            core.desktopEntries(),
            hiddenEntries(),
            queryText,
            sourceMode,
            preferencePredicate
        );
    }

    function sourceLabel(entry) {
        return core.sourceLabel(entry);
    }

    function entryKey(entry) {
        return catalogPolicy.entryKey(entry);
    }

    function displayName(entry) {
        return core.displayName(entry);
    }

    function displayDescription(entry) {
        return core.displayDescription(entry);
    }

    function longDescription(entry) {
        return core.longDescription(entry);
    }

    function iconSource(entry) {
        return core.iconSource(entry);
    }

    function actionsFor(entry) {
        return actionCatalog.desktopActions(entry);
    }

    function planAction(action, entry, fallbackIndex) {
        return actionPlanner.plan(
            action,
            entry,
            fallbackIndex
        );
    }

    function planLaunch(entry, sourceMode, launchMode,
                        bottleName, surfaceLaunchAugmentation) {
        return launchPlanner.plan(
            entry,
            sourceMode,
            launchMode,
            bottleName,
            surfaceLaunchAugmentation
        );
    }

    function rememberedKeyFor(entry) {
        return selectionPolicy.rememberedKeyFor(entry);
    }

    function restoreIndex(entries, rememberedKey) {
        return selectionPolicy.restoreIndex(
            entries,
            rememberedKey
        );
    }

    function identityObservation(entry) {
        return identityAdapter.observationForEntry(entry);
    }

    function refreshBottles() {
        bottles.refresh();
    }
}
