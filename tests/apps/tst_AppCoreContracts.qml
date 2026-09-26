import QtQuick
import QtTest
import "../../services/apps"

TestCase {
    name: "Team8AppCoreContracts"

    AppCoreProvider {
        id: core
    }

    AppMetadataPresentation {
        id: metadataPresentation
    }

    AppLaunchPlanner {
        id: launchPlanner
        coreProvider: core
        metadataPresentation: metadataPresentation
    }

    AppLaunchCommandBuilder {
        id: launchCommandBuilder
    }

    AppBottleProvider {
        id: bottleProvider
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

    QtObject {
        id: fakePresentationColors

        readonly property string orange: "orange"
        readonly property string red: "red"
        readonly property string omnitrix: "green"
        readonly property string cyan: "cyan"
        readonly property string magenta: "magenta"
        readonly property string yellow: "yellow"
        readonly property string dark: "dark"
        readonly property string black: "black"
        readonly property string white: "white"
    }

    AppIconGlowPolicy {
        id: iconGlowPolicy
        colors: fakePresentationColors
    }

    AppSelectorPresentation {
        id: selectorPresentation
        coreProvider: core
        colors: fakePresentationColors
    }

    QtObject {
        id: fakeIdentityEvidence

        function desktopEntryObservation(entry) {
            return {
                provider: "DESKTOP_ENTRY",
                providerKey: entry && entry.id
                    ? "desktop-entry:" + String(entry.id)
                    : "",
                lifetimeClass: "persistent",
                generation: null,
                raw: {
                    id: entry ? String(entry.id || "") : "",
                    name: entry ? String(entry.name || "") : ""
                },
                aliases: [{
                    kind: "desktop-entry.id",
                    value: entry ? String(entry.id || "") : "",
                    normalized: "owned-by-team7",
                    provider: "DESKTOP_ENTRY"
                }],
                relationships: []
            };
        }
    }

    AppIdentityAdapter {
        id: identityAdapter
        identityEvidence: fakeIdentityEvidence
    }

    AppCoreFacade {
        id: facade
        identityEvidence: fakeIdentityEvidence
        presentationColors: fakePresentationColors
        hiddenCommandNames: ["beta", "alpha"]
    }

    function nativeEntry() {
        return {
            id: "org.example.Native.desktop",
            name: "Native App",
            genericName: "Native",
            comment: "Native application",
            command: ["/usr/bin/native-app", "%U"],
            icon: "native-app",
            startupClass: "NativeApp"
        };
    }

    function flatpakEntry() {
        return {
            id: "com.example.Flatpak.desktop",
            name: "Flatpak App",
            command: ["flatpak", "run", "com.example.Flatpak", "%U"],
            startupClass: "FlatpakApp"
        };
    }

    function hiddenEntry() {
        return {
            _hiddenCommand: true,
            name: "secret-command --flag",
            command: ["secret-command", "--flag"]
        };
    }

    function braveEntry() {
        return {
            id: "brave-browser.desktop",
            name: "Brave Browser",
            command: ["/usr/bin/brave-browser", "%U"],
            startupClass: "Brave-browser",
            actions: []
        };
    }

    function firefoxEntry() {
        return {
            id: "firefox.desktop",
            name: "Firefox",
            command: ["/usr/bin/firefox", "%U"],
            startupClass: "firefox",
            actions: []
        };
    }

    function actionKinds(actions) {
        const kinds = [];

        for (let i = 0; i < actions.length; i++) {
            if (actions[i] && actions[i]._appControlBuiltin)
                kinds.push(String(actions[i]._appControlBuiltin));
        }

        return kinds;
    }

    function test_metadataPresentationOwnsOverridesAndFallbacks() {
        const native = nativeEntry();

        metadataPresentation.appOverrides = ({
            "Native App": {
                name: "Override Name",
                description: "Override Description",
                longDescription: "Override Long Description",
                icon: "file:/tmp/override-icon.svg"
            }
        });

        compare(
            metadataPresentation.displayName(native),
            "Override Name"
        );
        compare(
            metadataPresentation.displayDescription(native),
            "Override Description"
        );
        compare(
            metadataPresentation.longDescription(native),
            "Override Long Description"
        );
        compare(
            metadataPresentation.displayIcon(native),
            "file:/tmp/override-icon.svg"
        );
        compare(
            metadataPresentation.iconSource(native),
            "file:/tmp/override-icon.svg"
        );

        const plain = {
            name: "Plain App",
            genericName: "Plain Generic",
            comment: "Plain Comment",
            icon: "file:/tmp/plain-icon.svg"
        };

        compare(
            metadataPresentation.displayName(plain),
            "Plain App"
        );
        compare(
            metadataPresentation.displayDescription(plain),
            "Plain Generic"
        );
        compare(
            metadataPresentation.longDescription(plain),
            "Plain Comment"
        );
        compare(
            metadataPresentation.iconSource(plain),
            "file:/tmp/plain-icon.svg"
        );

        compare(
            metadataPresentation.displayName(null),
            "NO SELECTION"
        );
        compare(
            metadataPresentation.displayDescription(null),
            ""
        );
        compare(
            metadataPresentation.longDescription(null),
            ""
        );
        compare(
            metadataPresentation.displayIcon(null),
            ""
        );
        compare(
            metadataPresentation.iconSource(null),
            ""
        );
        compare(
            metadataPresentation.actionIconSource(
                "file:/tmp/action-icon.svg"
            ),
            "file:/tmp/action-icon.svg"
        );
        compare(
            metadataPresentation.actionIconSource(""),
            ""
        );

        metadataPresentation.appOverrides = ({});
    }

    function test_facadeRoutesMetadataThroughPresentationOrgan() {
        const native = nativeEntry();

        compare(facade.displayName(native), "Native App");
        compare(facade.displayDescription(native), "Native");
        compare(
            facade.longDescription(native),
            "Native application"
        );

        facade.appOverrides = ({
            "Native App": {
                name: "Facade Override",
                description: "Facade Description",
                longDescription: "Facade Long",
                icon: "file:/tmp/facade-icon.svg"
            }
        });

        compare(facade.displayName(native), "Facade Override");
        compare(
            facade.displayDescription(native),
            "Facade Description"
        );
        compare(facade.longDescription(native), "Facade Long");
        compare(
            facade.iconSource(native),
            "file:/tmp/facade-icon.svg"
        );
        compare(
            facade.actionIconSource(
                "file:/tmp/facade-action.svg"
            ),
            "file:/tmp/facade-action.svg"
        );

        facade.appOverrides = ({});
    }

    function test_catalogPolicyPreservesDonorSourceBehavior() {
        const native = nativeEntry();
        const flatpak = flatpakEntry();
        const rows = catalogPolicy.rows(
            [flatpak, native],
            [],
            "",
            core.sourceNative,
            null
        );

        // Native/Flatpak selection does not hide the other source.
        compare(rows.length, 2);
        compare(rows[0].name, "Flatpak App");
        compare(rows[1].name, "Native App");

        const flatpakSearch = catalogPolicy.rows(
            [native, flatpak],
            [],
            "flatpak",
            core.sourceNative,
            null
        );

        compare(flatpakSearch.length, 1);
        compare(flatpakSearch[0].name, "Flatpak App");
    }

    function test_catalogPreferenceIsInjectedNotOwned() {
        const native = nativeEntry();
        const flatpak = flatpakEntry();

        const rows = catalogPolicy.rows(
            [native, flatpak],
            [],
            "",
            core.sourceNative,
            function(entry) {
                return entry === native;
            }
        );

        compare(rows.length, 2);
        compare(rows[0], native);
        compare(rows[1], flatpak);
    }

    function test_hiddenCatalogUsesExternalRunRows() {
        const alpha = {
            _hiddenCommand: true,
            id: "hidden:alpha",
            name: "alpha-tool"
        };
        const beta = {
            _hiddenCommand: true,
            id: "hidden:beta",
            name: "beta-tool"
        };

        let rows = catalogPolicy.rows(
            [],
            [beta, alpha],
            "",
            core.sourceHidden,
            null
        );

        compare(rows.length, 2);
        compare(rows[0].name, "alpha-tool");
        compare(rows[1].name, "beta-tool");

        rows = catalogPolicy.rows(
            [],
            [beta, alpha],
            "beta",
            core.sourceHidden,
            null
        );

        compare(rows.length, 1);
        compare(rows[0].name, "beta-tool");
    }

    function test_hiddenAdapterProducesPureAppRows() {
        const desktop = [{
            id: "kitty.desktop",
            name: "Kitty",
            command: ["/usr/bin/kitty"],
            icon: "kitty-custom"
        }];

        const nvim = hiddenAdapter.recordForCommand(
            "nvim",
            desktop
        );

        verify(nvim !== null);
        compare(nvim._hiddenCommand, true);
        compare(nvim.id, "hidden:nvim");
        compare(nvim.name, "nvim");
        compare(nvim.genericName, "HIDDEN COMMAND");
        compare(nvim.command[0], "nvim");
        compare(nvim.icon, "nvim");
        compare(nvim.execute, undefined);

        const kitty = hiddenAdapter.recordForCommand(
            "kitty",
            desktop
        );

        // Donor-known icon mapping wins before DesktopEntry fallback.
        compare(kitty.icon, "kitty");

        const custom = hiddenAdapter.recordForCommand(
            "custom-app",
            [{
                id: "custom.desktop",
                name: "Custom",
                command: ["/usr/bin/custom-app"],
                icon: "custom-icon"
            }]
        );

        compare(custom.icon, "custom-icon");
    }

    function test_hiddenAdapterFeedsCatalogWithoutOwningDiscovery() {
        const rows = hiddenAdapter.records(
            ["beta", "alpha"],
            []
        );

        compare(rows.length, 2);

        const filtered = catalogPolicy.rows(
            [],
            rows,
            "",
            core.sourceHidden,
            null
        );

        compare(filtered.length, 2);
        compare(filtered[0].name, "alpha");
        compare(filtered[1].name, "beta");
    }

    function test_selectionPolicyRestoresRememberedApp() {
        const native = nativeEntry();
        const flatpak = flatpakEntry();
        const rows = [native, flatpak];

        compare(
            selectionPolicy.rememberedKeyFor(flatpak),
            "com.example.Flatpak.desktop"
        );

        compare(
            selectionPolicy.restoreIndex(
                rows,
                "com.example.Flatpak.desktop"
            ),
            1
        );

        compare(
            selectionPolicy.restoreIndex(
                rows,
                "missing.desktop"
            ),
            0
        );

        compare(
            selectionPolicy.restoreIndex(
                [],
                "anything"
            ),
            -1
        );
    }

    function test_identityAdapterDelegatesToTeam7Contract() {
        const entry = nativeEntry();
        const observation = identityAdapter.observationForEntry(entry);

        verify(observation !== null);
        compare(observation.provider, "DESKTOP_ENTRY");
        compare(
            observation.providerKey,
            "desktop-entry:org.example.Native.desktop"
        );
        compare(observation.lifetimeClass, "persistent");
        compare(observation.aliases[0].normalized, "owned-by-team7");

        compare(
            identityAdapter.providerKeyForEntry(entry),
            "desktop-entry:org.example.Native.desktop"
        );
        compare(
            identityAdapter.rawForEntry(entry).name,
            "Native App"
        );
    }

    function test_facadeComposesIsolatedAppCore() {
        const native = nativeEntry();
        const brave = braveEntry();

        compare(facade.sourceNative, core.sourceNative);
        compare(facade.launchNormal, core.launchNormal);
        compare(facade.entryKey(native), "org.example.Native.desktop");
        compare(facade.sourceLabel(native), "NORMAL");
        compare(
            facade.entryLaunchableForSource(
                native,
                facade.sourceNative
            ),
            true
        );

        const observation = facade.identityObservation(native);

        verify(observation !== null);
        compare(
            observation.providerKey,
            "desktop-entry:org.example.Native.desktop"
        );

        const actions = facade.actionsFor(brave);
        let newTabAction = null;

        for (let i = 0; i < actions.length; i++) {
            if (actions[i]
                    && actions[i]._appControlBuiltin === "new-tab") {
                newTabAction = actions[i];
                break;
            }
        }

        verify(newTabAction !== null);

        const actionPlan = facade.planAction(
            newTabAction,
            brave,
            0
        );

        compare(
            actionPlan.kind,
            actionPlanner.planBrowserLaunch
        );
        compare(
            actionPlan.extraArgs.join(" "),
            "--new-tab brave://newtab/"
        );

        const actionCommand = facade.buildActionCommand(
            actionPlan
        );

        compare(
            actionCommand.kind,
            actionCommandBuilder.commandBrowserLaunch
        );
        compare(
            actionCommand.argv.join(" "),
            "/usr/bin/brave-browser --new-tab brave://newtab/"
        );

        const launchPlan = facade.planLaunch(
            native,
            facade.sourceNative,
            facade.launchNormal,
            "",
            {
                ready: true,
                env: { ACCESSIBILITY_ENABLED: "1" },
                argvAfterExecutable: ["--surface-ready"],
                argvAppend: []
            }
        );

        compare(
            launchPlan.commandTokens.join(" "),
            "/usr/bin/native-app --surface-ready"
        );
        compare(
            launchPlan.launchEnv.ACCESSIBILITY_ENABLED,
            "1"
        );

        const launchCommand = facade.buildLaunchCommand(
            launchPlan,
            "/bin/zsh"
        );

        compare(
            launchCommand.kind,
            launchCommandBuilder.commandArgv
        );
        compare(
            launchCommand.argv.join(" "),
            "env ACCESSIBILITY_ENABLED=1 "
            + "/usr/bin/native-app --surface-ready"
        );

        compare(
            facade.restoreIndex(
                [native, brave],
                "brave-browser.desktop"
            ),
            1
        );
    }

    function test_modePolicyNormalizesSourceAndLaunchModes() {
        compare(
            modePolicy.normalizeSourceMode(core.sourceFlatpak),
            core.sourceFlatpak
        );
        compare(
            modePolicy.normalizeSourceMode(core.sourceHidden),
            core.sourceHidden
        );
        compare(
            modePolicy.normalizeSourceMode(999),
            core.sourceNative
        );

        compare(
            modePolicy.normalizeLaunchMode(core.launchToolbox),
            core.launchToolbox
        );
        compare(
            modePolicy.normalizeLaunchMode(core.launchBottle),
            core.launchBottle
        );
        compare(
            modePolicy.normalizeLaunchMode(999),
            core.launchNormal
        );
    }

    function test_modePolicyRestoresPackageCounterpart() {
        const native = {
            id: "org.example.App.desktop",
            name: "Example App",
            command: ["/usr/bin/example"]
        };
        const flatpak = {
            id: "org.example.App.Flatpak.desktop",
            name: "Example App",
            command: [
                "flatpak",
                "run",
                "org.example.App"
            ]
        };
        const rows = [native, flatpak];

        let change = modePolicy.sourceChangePlan(
            rows,
            "Example App",
            core.sourceFlatpak
        );

        compare(change.sourceMode, core.sourceFlatpak);
        compare(change.restoreIndex, 1);
        compare(change.needsHiddenCatalogRefresh, false);

        change = modePolicy.sourceChangePlan(
            rows,
            "Example App",
            core.sourceNative
        );

        compare(change.sourceMode, core.sourceNative);
        compare(change.restoreIndex, 0);
        compare(change.needsHiddenCatalogRefresh, false);

        change = modePolicy.sourceChangePlan(
            rows,
            "Example App",
            core.sourceHidden
        );

        compare(change.sourceMode, core.sourceHidden);
        compare(change.restoreIndex, 0);
        compare(change.needsHiddenCatalogRefresh, true);
    }

    function test_facadeOwnsOnlyAppSpecificModeAndBottleState() {
        compare(facade.setSourceMode(facade.sourceFlatpak),
                facade.sourceFlatpak);
        compare(facade.sourceMode, facade.sourceFlatpak);

        compare(facade.setLaunchMode(facade.launchBottle),
                facade.launchBottle);
        compare(facade.launchMode, facade.launchBottle);

        compare(facade.selectBottle("Gaming"), "Gaming");
        compare(facade.selectedBottleName, "Gaming");

        const change = facade.sourceChangePlan(
            [
                {
                    id: "native.desktop",
                    name: "Same App",
                    command: ["/usr/bin/same"]
                },
                {
                    id: "flat.desktop",
                    name: "Same App",
                    command: [
                        "flatpak",
                        "run",
                        "org.example.Same"
                    ]
                }
            ],
            "Same App",
            facade.sourceFlatpak
        );

        compare(change.restoreIndex, 1);

        // Reset shared test facade state.
        facade.setSourceMode(facade.sourceNative);
        facade.setLaunchMode(facade.launchNormal);
        facade.selectBottle("");
    }

    function test_iconGlowPolicyPreservesDonorClassification() {
        compare(iconGlowPolicy.classify([]), "orange");
        compare(
            iconGlowPolicy.classify([255, 0, 0, 255]),
            "red"
        );
        compare(
            iconGlowPolicy.classify([0, 255, 0, 255]),
            "green"
        );
        compare(
            iconGlowPolicy.classify([0, 200, 255, 255]),
            "cyan"
        );
        compare(
            iconGlowPolicy.classify([180, 0, 255, 255]),
            "magenta"
        );
        compare(
            iconGlowPolicy.classify([255, 255, 255, 255]),
            "white"
        );
        compare(
            iconGlowPolicy.classify([0, 0, 0, 255]),
            "magenta"
        );
    }

    function test_iconGlowCacheReassignsAndRespectsOverwritePolicy() {
        const before = iconGlowPolicy.cache;

        compare(
            iconGlowPolicy.remember(
                "icon://native",
                "cyan",
                false
            ),
            true
        );

        verify(iconGlowPolicy.cache !== before);
        compare(
            iconGlowPolicy.cached("icon://native"),
            "cyan"
        );

        compare(
            iconGlowPolicy.remember(
                "icon://native",
                "red",
                false
            ),
            false
        );
        compare(
            iconGlowPolicy.cached("icon://native"),
            "cyan"
        );

        compare(
            iconGlowPolicy.remember(
                "icon://native",
                "red",
                true
            ),
            true
        );
        compare(
            iconGlowPolicy.cached("icon://native"),
            "red"
        );
    }

    function test_facadeExposesAppPresentationPolicyOnly() {
        compare(
            facade.classifyIconGlow(
                [255, 0, 0, 255]
            ),
            "red"
        );

        compare(
            facade.rememberIconGlow(
                "icon://facade",
                "cyan",
                false
            ),
            true
        );
        compare(
            facade.cachedIconGlow("icon://facade"),
            "cyan"
        );
    }

    function test_selectorPresentationPreservesDonorModels() {
        let source = selectorPresentation.sourceOptions(false);

        compare(source.length, 3);
        compare(source[0].value, core.sourceNative);
        compare(source[0].label, "-⋆♱⋆-");
        compare(source[0].accent, "cyan");

        compare(source[1].value, core.sourceFlatpak);
        compare(source[1].label, "⋆˙⟡ ⌯⛟\nFLATPACK");
        compare(source[1].accent, "magenta");
        compare(source[1].size, 10);

        compare(source[2].value, core.sourceHidden);
        compare(source[2].label, "HIDDEN");
        compare(source[2].accent, "yellow");

        source = selectorPresentation.sourceOptions(true);

        compare(source[1].label, "⋆˙⟡ ⌯⛟");
        compare(source[1].size, 16);
        compare(source[2].label, "|ω-ς)");

        const launch = selectorPresentation.launchOptions();

        compare(launch.length, 3);
        compare(launch[0].value, core.launchNormal);
        compare(launch[0].label, "⌯♱ ๋࣭⭑");
        compare(launch[0].accent, "cyan");

        compare(launch[1].value, core.launchBottle);
        compare(launch[1].bottleIcon, true);
        compare(launch[1].accent, "magenta");

        compare(launch[2].value, core.launchToolbox);
        compare(launch[2].toolboxIcon, true);
        compare(launch[2].accent, "green");
    }

    function test_selectorPresentationPreservesHiddenFaceAndBadge() {
        compare(
            selectorPresentation.hiddenFace(false),
            "|ω-ς)"
        );
        compare(
            selectorPresentation.hiddenFace(true),
            "|ω･`ς)"
        );

        let badge = selectorPresentation.sourceBadge(
            nativeEntry(),
            false
        );

        compare(badge.label, "NORMAL");
        compare(badge.accent, "cyan");
        compare(badge.opacity, 0.82);

        badge = selectorPresentation.sourceBadge(
            flatpakEntry(),
            false
        );

        compare(badge.label, "FLATPAK");
        compare(badge.accent, "magenta");
        compare(badge.opacity, 0.82);

        badge = selectorPresentation.sourceBadge(
            flatpakEntry(),
            true
        );

        compare(badge.accent, "white");
        compare(badge.opacity, 0.58);
    }

    function test_selectorGlowSpecsPreserveDonorAPPSStyle() {
        let spec = selectorPresentation.sourceGlowSpec(
            core.sourceNative,
            false,
            false,
            false
        );

        compare(spec.glowColor, "cyan");
        compare(spec.fillColor, "dark");
        compare(spec.textColor, "cyan");
        compare(spec.glowRadius, 12);
        compare(spec.glowSamples, 11);
        compare(spec.glowOpacity, 0.66);
        compare(spec.shadowOpacity, 0.52);

        spec = selectorPresentation.sourceGlowSpec(
            core.sourceFlatpak,
            true,
            false,
            false
        );

        compare(spec.glowColor, "magenta");
        compare(spec.fillColor, "yellow");
        compare(spec.textColor, "magenta");
        compare(spec.glowRadius, 8);
        compare(spec.glowSamples, 7);
        compare(spec.glowOpacity, 0.64);
        compare(spec.shadowOpacity, 0.52);

        spec = selectorPresentation.launchGlowSpec(
            core.launchToolbox,
            false,
            true,
            false
        );

        compare(spec.glowColor, "orange");
        compare(spec.fillColor, "yellow");
        compare(spec.textColor, "orange");
        compare(spec.glowRadius, 8);
        compare(spec.glowSamples, 7);
        compare(spec.glowOpacity, 0.60);
        compare(spec.shadowOpacity, 0.52);
    }

    function test_facadeExposesSelectorPresentation() {
        const source = facade.sourceSelectorOptions(false);
        const launch = facade.launchSelectorOptions();

        compare(source[0].value, facade.sourceNative);
        compare(source[1].value, facade.sourceFlatpak);
        compare(source[2].value, facade.sourceHidden);

        compare(launch[0].value, facade.launchNormal);
        compare(launch[1].value, facade.launchBottle);
        compare(launch[2].value, facade.launchToolbox);

        compare(
            facade.hiddenSourceFace(true),
            "|ω･`ς)"
        );

        const badge = facade.sourceBadge(
            flatpakEntry(),
            false
        );

        compare(badge.label, "FLATPAK");
        compare(badge.accent, "magenta");
    }

    function test_sourceClassification() {
        const native = nativeEntry();
        const flatpak = flatpakEntry();
        const hidden = hiddenEntry();

        compare(core.entryIsFlatpak(native), false);
        compare(core.entryIsFlatpak(flatpak), true);

        compare(core.sourceLabel(native), "NORMAL");
        compare(core.sourceLabel(flatpak), "FLATPAK");
        compare(core.sourceLabel(hidden), "HIDDEN");

        compare(core.entryMatchesSource(native, core.sourceNative), true);
        compare(core.entryMatchesSource(native, core.sourceFlatpak), false);
        compare(core.entryMatchesSource(flatpak, core.sourceFlatpak), true);
        compare(core.entryMatchesSource(hidden, core.sourceHidden), true);
    }

    function test_launchabilityPreservesDonorSemantics() {
        const native = nativeEntry();
        const flatpak = flatpakEntry();
        const hidden = hiddenEntry();

        // NORMAL remains broad: both native and Flatpak DesktopEntries may launch.
        compare(core.entryLaunchableForSource(native, core.sourceNative), true);
        compare(core.entryLaunchableForSource(flatpak, core.sourceNative), true);

        // FLATPAK is strict.
        compare(core.entryLaunchableForSource(native, core.sourceFlatpak), false);
        compare(core.entryLaunchableForSource(flatpak, core.sourceFlatpak), true);

        // HIDDEN accepts only hidden-command records.
        compare(core.entryLaunchableForSource(hidden, core.sourceHidden), true);
        compare(core.entryLaunchableForSource(native, core.sourceHidden), false);
    }

    function test_cleanedDesktopEntryTokens() {
        const native = nativeEntry();
        const tokens = launchPlanner.cleanedCommandTokens(native);

        compare(tokens.length, 1);
        compare(tokens[0], "/usr/bin/native-app");
        compare(launchPlanner.launchExecutableName(native), "native-app");
    }

    function test_launchPlansDoNotExecute() {
        const native = nativeEntry();
        const hidden = hiddenEntry();

        let plan = launchPlanner.plan(
            native,
            core.sourceNative,
            core.launchNormal,
            ""
        );

        compare(plan.kind, launchPlanner.planDesktopEntry);
        compare(plan.entry.name, "Native App");

        plan = launchPlanner.plan(
            native,
            core.sourceNative,
            core.launchToolbox,
            ""
        );

        compare(plan.kind, launchPlanner.planToolboxArgv);
        compare(plan.argv[0], "/usr/bin/native-app");

        plan = launchPlanner.plan(
            native,
            core.sourceNative,
            core.launchBottle,
            "Gaming"
        );

        compare(plan.kind, launchPlanner.planBottle);
        compare(plan.bottleName, "Gaming");
        compare(plan.programName, "Native App");

        plan = launchPlanner.plan(
            hidden,
            core.sourceHidden,
            core.launchNormal,
            ""
        );

        compare(plan.kind, launchPlanner.planHidden);
        compare(plan.commandText, "secret-command --flag");
    }

    function test_bottleProgramNamePreservesMetadataOverride() {
        const native = nativeEntry();

        metadataPresentation.appOverrides = ({
            "Native App": {
                name: "Bottle Override"
            }
        });

        const plan = launchPlanner.plan(
            native,
            core.sourceNative,
            core.launchBottle,
            "Gaming"
        );

        compare(plan.kind, launchPlanner.planBottle);
        compare(plan.programName, "Bottle Override");

        metadataPresentation.appOverrides = ({});
    }

    function test_surfaceLaunchAugmentationUsesPublishedShape() {
        const native = nativeEntry();
        const supplied = {
            ready: true,
            correlationId: "surface-123",
            requestedCapabilities: ["ACCESSIBILITY", "DEVTOOLS"],
            appliedCapabilities: ["ACCESSIBILITY", "DEVTOOLS"],
            unsupportedCapabilities: [],
            env: {
                ACCESSIBILITY_ENABLED: "1"
            },
            argvAfterExecutable: ["--after-executable"],
            argvAppend: ["--append-last"],
            bootstrap: {
                debugPort: 9222
            },
            leases: [{ kind: "devtools-port", value: 9222 }],
            conflicts: []
        };

        const plan = launchPlanner.plan(
            native,
            core.sourceNative,
            core.launchNormal,
            "",
            supplied
        );

        compare(plan.kind, launchPlanner.planDesktopEntry);
        compare(plan.surfaceLaunchAugmentation.ready, true);
        compare(
            plan.surfaceLaunchAugmentation.correlationId,
            "surface-123"
        );
        compare(plan.launchEnv.ACCESSIBILITY_ENABLED, "1");
        compare(
            plan.commandTokens.join(" "),
            "/usr/bin/native-app --after-executable --append-last"
        );
        compare(
            plan.surfaceLaunchAugmentation.appliedCapabilities.join("+"),
            "ACCESSIBILITY+DEVTOOLS"
        );
        compare(plan.surfaceLaunchAugmentation.bootstrap.debugPort, 9222);
    }

    function test_surfaceLaunchNotReadyBlocksLaunch() {
        const native = nativeEntry();

        const plan = launchPlanner.plan(
            native,
            core.sourceNative,
            core.launchNormal,
            "",
            {
                ready: false,
                conflicts: [{
                    kind: "devtools-port",
                    value: 9222
                }]
            }
        );

        compare(plan.kind, launchPlanner.planUnavailable);
        compare(plan.reason, "surface-launch-not-ready");
        compare(plan.surfaceLaunchAugmentation.ready, false);
        compare(plan.surfaceLaunchAugmentation.conflicts.length, 1);
    }

    function test_surfaceLaunchFlatpakTransportWithoutExistingAppArgv() {
        const kittyFlatpak = {
            id: "net.kovidgoyal.kitty.desktop",
            name: "Kitty",
            command: [
                "flatpak",
                "run",
                "net.kovidgoyal.kitty",
                "%U"
            ]
        };

        const plan = launchPlanner.plan(
            kittyFlatpak,
            core.sourceFlatpak,
            core.launchNormal,
            "",
            {
                ready: true,
                argvAfterExecutable: [
                    "-o",
                    "allow_remote_control=socket-only",
                    "--listen-on",
                    "unix:@surface-kitty"
                ],
                argvAppend: []
            }
        );

        compare(plan.kind, launchPlanner.planDesktopEntry);
        compare(
            plan.commandTokens.join(" "),
            "flatpak run net.kovidgoyal.kitty "
            + "-o allow_remote_control=socket-only "
            + "--listen-on unix:@surface-kitty"
        );

        // Most importantly, Team 8 must not produce:
        //   flatpak -o ... run APP_ID
        compare(plan.commandTokens[0], "flatpak");
        compare(plan.commandTokens[1], "run");
    }

    function test_surfaceLaunchFlatpakTransportWithExistingAppArgv() {
        const kittyFlatpak = {
            id: "net.kovidgoyal.kitty.desktop",
            name: "Kitty",
            command: [
                "flatpak",
                "run",
                "net.kovidgoyal.kitty",
                "ssh",
                "host",
                "%U"
            ]
        };

        const plan = launchPlanner.plan(
            kittyFlatpak,
            core.sourceFlatpak,
            core.launchNormal,
            "",
            {
                ready: true,
                argvAfterExecutable: [
                    "-o",
                    "allow_remote_control=socket-only",
                    "--listen-on",
                    "unix:@surface-kitty"
                ],
                argvAppend: []
            }
        );

        compare(plan.kind, launchPlanner.planDesktopEntry);
        compare(
            plan.commandTokens.join(" "),
            "flatpak run net.kovidgoyal.kitty "
            + "-o allow_remote_control=socket-only "
            + "--listen-on unix:@surface-kitty "
            + "ssh host"
        );

        compare(plan.commandTokens[0], "flatpak");
        compare(plan.commandTokens[1], "run");
        compare(plan.commandTokens[2], "net.kovidgoyal.kitty");
        compare(plan.commandTokens[3], "-o");
        compare(plan.commandTokens[7], "ssh");
        compare(plan.commandTokens[8], "host");
    }

    function test_surfaceLaunchFlatpakBoundarySurvivesWrapperOptions() {
        const entry = {
            id: "org.example.App.desktop",
            name: "Example",
            command: [
                "flatpak",
                "run",
                "--branch",
                "stable",
                "--arch=x86_64",
                "org.example.App",
                "--existing",
                "%U"
            ]
        };

        const plan = launchPlanner.plan(
            entry,
            core.sourceFlatpak,
            core.launchNormal,
            "",
            {
                ready: true,
                argvAfterExecutable: ["--surface"],
                argvAppend: ["--tail"]
            }
        );

        compare(plan.kind, launchPlanner.planDesktopEntry);
        compare(
            plan.commandTokens.join(" "),
            "flatpak run --branch stable --arch=x86_64 "
            + "org.example.App --surface --existing --tail"
        );
    }

    function test_surfaceLaunchFlatpakUnknownBoundaryFailsClosed() {
        const entry = {
            id: "",
            name: "Broken Flatpak",
            command: [
                "flatpak",
                "run",
                "--branch"
            ]
        };

        const plan = launchPlanner.plan(
            entry,
            core.sourceFlatpak,
            core.launchNormal,
            "",
            {
                ready: true,
                argvAfterExecutable: ["--surface"]
            }
        );

        compare(plan.kind, launchPlanner.planUnavailable);
        compare(
            plan.reason,
            "flatpak-application-boundary-unresolved"
        );
    }

    function test_surfaceLaunchAugmentsToolboxArgvStructurally() {
        const native = nativeEntry();

        const plan = launchPlanner.plan(
            native,
            core.sourceNative,
            core.launchToolbox,
            "",
            {
                ready: true,
                env: { TEST_SURFACE: "1" },
                argvAfterExecutable: ["--first"],
                argvAppend: ["--last"]
            }
        );

        compare(plan.kind, launchPlanner.planToolboxArgv);
        compare(
            plan.argv.join(" "),
            "/usr/bin/native-app --first --last"
        );
        compare(plan.launchEnv.TEST_SURFACE, "1");
    }

    function test_launchCommandBuilderPreservesDesktopEntryFastPath() {
        const plan = launchPlanner.plan(
            nativeEntry(),
            core.sourceNative,
            core.launchNormal,
            "",
            null
        );

        const command = launchCommandBuilder.build(
            plan,
            "/bin/zsh"
        );

        compare(
            command.kind,
            launchCommandBuilder.commandDesktopEntry
        );
        compare(command.entry.name, "Native App");
    }

    function test_launchCommandBuilderCarriesEnvAndArgv() {
        const plan = launchPlanner.plan(
            nativeEntry(),
            core.sourceNative,
            core.launchNormal,
            "",
            {
                ready: true,
                correlationId: "surface-native",
                env: {
                    ZETA: "2",
                    ALPHA: "1"
                },
                argvAfterExecutable: ["--after"],
                argvAppend: ["--last"]
            }
        );

        const command = launchCommandBuilder.build(
            plan,
            "/bin/zsh"
        );

        compare(
            command.kind,
            launchCommandBuilder.commandArgv
        );
        compare(
            command.argv.join(" "),
            "env ALPHA=1 ZETA=2 "
            + "/usr/bin/native-app --after --last"
        );
        compare(command.correlationId, "surface-native");
    }

    function test_shellSurfaceArgvFailsClosed() {
        const shellEntry = {
            id: "org.example.Shell.desktop",
            name: "Shell App",
            command: "shell-app --existing %U"
        };

        const plan = launchPlanner.plan(
            shellEntry,
            core.sourceNative,
            core.launchNormal,
            "",
            {
                ready: true,
                env: { ACCESSIBILITY_ENABLED: "1" },
                argvAppend: ["--surface"]
            }
        );

        compare(
            plan.commandTokens[0],
            "__APPCONTROL_SHELL__"
        );
        compare(
            plan.commandTokens[1],
            "shell-app --existing"
        );

        const command = launchCommandBuilder.build(
            plan,
            "/bin/zsh"
        );

        compare(
            command.kind,
            launchCommandBuilder.commandUnavailable
        );
        compare(
            command.reason,
            "surface-launch-shell-argv-transport-unresolved"
        );
    }

    function test_shellSurfaceEnvOnlyIsTransportable() {
        const shellEntry = {
            id: "org.example.Shell.desktop",
            name: "Shell App",
            command: "shell-app --existing %U"
        };

        const plan = launchPlanner.plan(
            shellEntry,
            core.sourceNative,
            core.launchNormal,
            "",
            {
                ready: true,
                correlationId: "surface-shell",
                env: { ACCESSIBILITY_ENABLED: "1" }
            }
        );

        const command = launchCommandBuilder.build(
            plan,
            "/bin/zsh"
        );

        compare(
            command.kind,
            launchCommandBuilder.commandArgv
        );
        compare(
            command.argv.join(" "),
            "env ACCESSIBILITY_ENABLED=1 "
            + "/bin/zsh -lc shell-app --existing"
        );
        compare(command.correlationId, "surface-shell");
    }

    function test_toolboxCommandBuilderCarriesAugmentationInsideToolbox() {
        const plan = launchPlanner.plan(
            nativeEntry(),
            core.sourceNative,
            core.launchToolbox,
            "",
            {
                ready: true,
                correlationId: "surface-toolbox",
                env: { ACCESSIBILITY_ENABLED: "1" },
                argvAfterExecutable: ["--surface"],
                argvAppend: []
            }
        );

        const command = launchCommandBuilder.build(plan, "");

        compare(
            command.kind,
            launchCommandBuilder.commandArgv
        );
        compare(
            command.argv.join(" "),
            "toolbox run env ACCESSIBILITY_ENABLED=1 "
            + "/usr/bin/native-app --surface"
        );
        compare(command.correlationId, "surface-toolbox");
    }

    function test_bottleCommandBuilderPreservesDonorAndCarriesSurfaceLaunch() {
        let plan = launchPlanner.plan(
            nativeEntry(),
            core.sourceNative,
            core.launchBottle,
            "Gaming",
            null
        );

        let command = launchCommandBuilder.build(plan, "");

        compare(
            command.kind,
            launchCommandBuilder.commandArgv
        );
        compare(command.argv[0], "sh");
        compare(command.argv[1], "-lc");
        verify(
            command.argv[2].indexOf(
                "flatpak run --command=bottles-cli "
            ) !== -1
        );
        verify(
            command.argv[2].indexOf(
                "bottles-cli run -b 'Gaming' -p 'Native App'"
            ) !== -1
        );

        plan = launchPlanner.plan(
            nativeEntry(),
            core.sourceNative,
            core.launchBottle,
            "Gaming",
            {
                ready: true,
                correlationId: "surface-bottle",
                env: {
                    ACCESSIBILITY_ENABLED: "1"
                },
                argvAfterExecutable: [
                    "--force-renderer-accessibility=complete"
                ],
                argvAppend: [
                    "--remote-debugging-port=9222"
                ]
            }
        );

        command = launchCommandBuilder.build(plan, "");

        compare(
            command.kind,
            launchCommandBuilder.commandArgv
        );
        compare(command.correlationId, "surface-bottle");

        verify(
            command.argv[2].indexOf(
                "flatpak run '--env=ACCESSIBILITY_ENABLED=1' "
                + "--command=bottles-cli"
            ) !== -1
        );

        verify(
            command.argv[2].indexOf(
                "env 'ACCESSIBILITY_ENABLED=1' "
                + "bottles-cli run"
            ) !== -1
        );

        verify(
            command.argv[2].indexOf(
                "--args '--force-renderer-accessibility=complete "
                + "--remote-debugging-port=9222'"
            ) !== -1
        );
    }

    function test_bottleSurfaceLaunchComplexArgsFailClosed() {
        const plan = launchPlanner.plan(
            nativeEntry(),
            core.sourceNative,
            core.launchBottle,
            "Gaming",
            {
                ready: true,
                argvAppend: [
                    "--title=contains spaces"
                ]
            }
        );

        const command = launchCommandBuilder.build(plan, "");

        compare(
            command.kind,
            launchCommandBuilder.commandUnavailable
        );
        compare(
            command.reason,
            "surface-launch-bottle-arg-quoting-unresolved"
        );
    }

    function test_hiddenCommandBuildsRunDispatchNotProcessCommand() {
        const plan = launchPlanner.plan(
            hiddenEntry(),
            core.sourceHidden,
            core.launchNormal,
            "",
            {
                ready: true,
                correlationId: "surface-hidden"
            }
        );

        const command = launchCommandBuilder.build(plan, "");

        compare(
            command.kind,
            launchCommandBuilder.commandRunDispatch
        );
        compare(
            command.commandText,
            "secret-command --flag"
        );
        compare(
            command.surfaceLaunchAugmentation.correlationId,
            "surface-hidden"
        );
    }

    function test_bottlePayloadParsing() {
        let names = bottleProvider.namesFromPayload({
            bottles: [
                { name: "Gaming" },
                { Name: "Legacy" },
                { bottle: "Work" }
            ]
        });

        compare(names.length, 3);
        verify(names.indexOf("Gaming") !== -1);
        verify(names.indexOf("Legacy") !== -1);
        verify(names.indexOf("Work") !== -1);

        names = bottleProvider.namesFromPayload({
            Gaming: { path: "/tmp/gaming" },
            Work: { path: "/tmp/work" }
        });

        compare(names.length, 2);
        verify(names.indexOf("Gaming") !== -1);
        verify(names.indexOf("Work") !== -1);
    }

    function test_bottleTextFallbackParsing() {
        const names = bottleProvider.parseNames(
            "Bottles\n- Gaming\n* Legacy\nWork\n"
        );

        compare(names.length, 3);
        compare(names[0], "Gaming");
        compare(names[1], "Legacy");
        compare(names[2], "Work");
    }

    function test_browserActionCatalog() {
        const braveKinds = actionKinds(
            actionCatalog.desktopActions(braveEntry())
        );

        verify(braveKinds.indexOf("new-window") !== -1);
        verify(braveKinds.indexOf("new-private-window") !== -1);
        verify(braveKinds.indexOf("new-tab") !== -1);
        verify(braveKinds.indexOf("task-manager") !== -1);
        verify(braveKinds.indexOf("restore") !== -1);

        const firefoxKinds = actionKinds(
            actionCatalog.desktopActions(firefoxEntry())
        );

        verify(firefoxKinds.indexOf("firefox-view") !== -1);
        verify(firefoxKinds.indexOf("passwords") !== -1);
        verify(firefoxKinds.indexOf("profile-manager") !== -1);
        compare(firefoxKinds.indexOf("task-manager"), -1);
    }

    function test_actionPlannerPreservesDonorPolicy() {
        const brave = braveEntry();
        const firefox = firefoxEntry();

        let plan = actionPlanner.browserBuiltinPlan(
            "history",
            brave,
            0
        );

        compare(plan.kind, actionPlanner.planBrowserShortcut);
        compare(plan.sequence.join("+"), "ctrl+h");
        compare(plan.stableId, "builtin|history");

        plan = actionPlanner.browserBuiltinPlan(
            "downloads",
            firefox,
            0
        );

        compare(plan.kind, actionPlanner.planBrowserLaunch);
        compare(plan.extraArgs.join(" "), "--new-tab about:downloads");

        plan = actionPlanner.browserBuiltinPlan(
            "settings",
            firefox,
            0
        );

        compare(plan.kind, actionPlanner.planBrowserLaunch);
        compare(plan.extraArgs.join(" "), "--preferences");

        const rawAction = {
            name: "OPEN PROFILE"
        };

        plan = actionPlanner.plan(rawAction, firefox, 3);

        compare(plan.kind, actionPlanner.planDesktopAction);
        compare(plan.action, rawAction);
        compare(plan.stableId, "desktop|OPEN%20PROFILE");
    }

    function test_actionCommandBuilderPreservesDesktopEntryAction() {
        const action = {
            name: "OPEN PROFILE",
            execute: function() {}
        };

        const plan = actionPlanner.plan(
            action,
            firefoxEntry(),
            2
        );

        const command = actionCommandBuilder.build(plan);

        compare(
            command.kind,
            actionCommandBuilder.commandDesktopAction
        );
        compare(command.action, action);
        compare(command.entry.name, "Firefox");
        compare(command.stableId, "desktop|OPEN%20PROFILE");
    }

    function test_actionCommandBuilderBuildsBrowserLaunchArgv() {
        const actions = actionCatalog.desktopActions(braveEntry());
        let target = null;

        for (let i = 0; i < actions.length; i++) {
            if (actions[i]
                    && actions[i]._appControlBuiltin === "settings") {
                target = actions[i];
                break;
            }
        }

        verify(target !== null);

        const plan = actionPlanner.plan(
            target,
            braveEntry(),
            0
        );

        const command = actionCommandBuilder.build(plan);

        compare(
            command.kind,
            actionCommandBuilder.commandBrowserLaunch
        );
        compare(
            command.argv.join(" "),
            "/usr/bin/brave-browser brave://settings/"
        );
        compare(command.browserKind, "brave");
        compare(command.action, "settings");
    }

    function test_actionCommandBuilderKeepsShortcutNeutral() {
        const actions = actionCatalog.desktopActions(braveEntry());
        let target = null;

        for (let i = 0; i < actions.length; i++) {
            if (actions[i]
                    && actions[i]._appControlBuiltin === "history") {
                target = actions[i];
                break;
            }
        }

        verify(target !== null);

        const plan = actionPlanner.plan(
            target,
            braveEntry(),
            0
        );

        const command = actionCommandBuilder.build(plan);

        compare(
            command.kind,
            actionCommandBuilder.commandBrowserShortcut
        );
        compare(command.browserKind, "brave");
        compare(command.sequence.join("+"), "ctrl+h");
        compare(command.entry.name, "Brave Browser");

        compare(command.swayCriteria, undefined);
        compare(command.wtypeCommand, undefined);
    }

    function test_browserShellLaunchActionFailsClosed() {
        const shellBrowser = {
            id: "firefox-shell.desktop",
            name: "Firefox",
            startupClass: "firefox",
            command: "firefox %U",
            actions: []
        };

        const actions = actionCatalog.desktopActions(shellBrowser);
        let target = null;

        for (let i = 0; i < actions.length; i++) {
            if (actions[i]
                    && actions[i]._appControlBuiltin === "settings") {
                target = actions[i];
                break;
            }
        }

        const plan = actionPlanner.plan(
            target,
            shellBrowser,
            0
        );

        const command = actionCommandBuilder.build(plan);

        compare(
            command.kind,
            actionCommandBuilder.commandUnavailable
        );
        compare(
            command.reason,
            "browser-launch-shell-command-unresolved"
        );
    }

    function test_browserActionPlans() {
        compare(actionCatalog.browserKind(braveEntry()), "brave");
        compare(actionCatalog.browserKind(firefoxEntry()), "firefox");
        compare(actionCatalog.browserKind(nativeEntry()), "");

        compare(
            actionCatalog.shortcutSequence("brave", "history").join("+"),
            "ctrl+h"
        );

        compare(
            actionCatalog.launchArguments("brave", "new-private-window").join(" "),
            "--incognito --new-window"
        );

        compare(
            actionCatalog.launchArguments("firefox", "settings").join(" "),
            "--preferences"
        );
    }
}
