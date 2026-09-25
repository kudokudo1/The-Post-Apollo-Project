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
    property var presentationColors: null

    readonly property int sourceNative: core.sourceNative
    readonly property int sourceFlatpak: core.sourceFlatpak
    readonly property int sourceHidden: core.sourceHidden

    readonly property int launchNormal: core.launchNormal
    readonly property int launchToolbox: core.launchToolbox
    readonly property int launchBottle: core.launchBottle

    property int sourceMode: sourceNative
    property int launchMode: launchNormal

    readonly property var bottleNames: bottles.names
    property alias selectedBottleName: bottles.selectedName
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

    AppLaunchCommandBuilder {
        id: launchCommandBuilder
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

    AppActionCommandBuilder {
        id: actionCommandBuilder
        launchPlanner: launchPlanner
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

    AppModePolicy {
        id: modePolicy
        coreProvider: core
    }

    AppIconGlowPolicy {
        id: iconGlowPolicy
        colors: facade.presentationColors
    }

    AppSelectorPresentation {
        id: selectorPresentation
        coreProvider: core
        colors: facade.presentationColors
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

    function resultRows(queryText, requestedSourceMode) {
        const mode = requestedSourceMode === undefined
            ? sourceMode
            : modePolicy.normalizeSourceMode(requestedSourceMode);

        return catalogPolicy.rows(
            core.desktopEntries(),
            hiddenEntries(),
            queryText,
            mode,
            preferencePredicate
        );
    }

    function sourceChangePlan(entries, previousName, requestedMode) {
        return modePolicy.sourceChangePlan(
            entries,
            previousName,
            requestedMode
        );
    }

    function setSourceMode(requestedMode) {
        sourceMode =
            modePolicy.normalizeSourceMode(requestedMode);
        return sourceMode;
    }

    function setLaunchMode(requestedMode) {
        launchMode =
            modePolicy.normalizeLaunchMode(requestedMode);
        return launchMode;
    }

    function selectBottle(name) {
        selectedBottleName =
            String(name || "").trim();
        return selectedBottleName;
    }

    function sourceLabel(entry) {
        return core.sourceLabel(entry);
    }

    function entryLaunchableForSource(entry, sourceMode) {
        return core.entryLaunchableForSource(
            entry,
            sourceMode
        );
    }

    function actionsAvailableForSource(entry, sourceMode) {
        return core.actionsAvailableForSource(
            entry,
            sourceMode
        );
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

    function buildActionCommand(plan) {
        return actionCommandBuilder.build(plan);
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

    function buildLaunchCommand(plan, shellPath) {
        return launchCommandBuilder.build(
            plan,
            shellPath
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

    function sourceSelectorOptions(compact) {
        return selectorPresentation.sourceOptions(compact);
    }

    function launchSelectorOptions() {
        return selectorPresentation.launchOptions();
    }

    function hiddenSourceFace(emphasized) {
        return selectorPresentation.hiddenFace(emphasized);
    }

    function sourceBadge(entry, unavailable) {
        return selectorPresentation.sourceBadge(
            entry,
            unavailable
        );
    }

    function sourceGlowSpec(sourceMode, selected, hovered, pressed) {
        return selectorPresentation.sourceGlowSpec(
            sourceMode,
            selected,
            hovered,
            pressed
        );
    }

    function launchGlowSpec(launchMode, selected, hovered, pressed) {
        return selectorPresentation.launchGlowSpec(
            launchMode,
            selected,
            hovered,
            pressed
        );
    }

    function cachedIconGlow(source) {
        return iconGlowPolicy.cached(source);
    }

    function rememberIconGlow(source, color, forceOverwrite) {
        return iconGlowPolicy.remember(
            source,
            color,
            forceOverwrite
        );
    }

    function classifyIconGlow(pixelData) {
        return iconGlowPolicy.classify(pixelData);
    }

    function identityObservation(entry) {
        return identityAdapter.observationForEntry(entry);
    }

    function refreshBottles() {
        bottles.refresh();
    }
}
