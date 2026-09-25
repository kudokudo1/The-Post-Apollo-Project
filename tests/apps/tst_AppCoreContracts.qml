import QtQuick
import QtTest
import "../../services/apps"

TestCase {
    name: "Team8AppCoreContracts"

    AppCoreProvider {
        id: core
    }

    AppLaunchPlanner {
        id: launchPlanner
        coreProvider: core
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

    function test_suppliedSurfaceLaunchAugmentationIsOpaque() {
        const native = nativeEntry();
        const supplied = {
            capabilities: ["KITTY_REMOTE", "ACCESSIBILITY"],
            token: "t5-owned-payload"
        };

        const plan = launchPlanner.plan(
            native,
            core.sourceNative,
            core.launchNormal,
            "",
            supplied
        );

        compare(plan.kind, launchPlanner.planDesktopEntry);
        compare(plan.surfaceLaunchAugmentation, supplied);
        compare(plan.surfaceLaunchAugmentation.token, "t5-owned-payload");

        // Team 8 must not infer or rewrite capability semantics here.
        compare(
            plan.surfaceLaunchAugmentation.capabilities.join("+"),
            "KITTY_REMOTE+ACCESSIBILITY"
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
