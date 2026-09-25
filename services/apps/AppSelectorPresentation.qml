import QtQuick

// Team 8 — APPS Core selector/result presentation policy.
//
// Pure APPS-specific presentation data. It does not own selector widgets,
// hover/press state, shared navigation, Favorites UI, or theme globals.
// A palette is injected by the consumer.
QtObject {
    id: presentation

    required property var coreProvider
    property var colors: null

    function palette(name) {
        if (!colors)
            return null;

        const value = colors[name];
        return value === undefined ? null : value;
    }

    function sourceOptions(compact) {
        const isCompact = !!compact;

        return [
            {
                group: "appSource",
                value: coreProvider.sourceNative,
                label: "-⋆♱⋆-",
                accent: palette("cyan"),
                size: 14
            },
            {
                group: "appSource",
                value: coreProvider.sourceFlatpak,
                label: isCompact
                    ? "⋆˙⟡ ⌯⛟"
                    : "⋆˙⟡ ⌯⛟\nFLATPACK",
                accent: palette("magenta"),
                size: isCompact ? 16 : 10
            },
            {
                group: "appSource",
                value: coreProvider.sourceHidden,
                label: isCompact ? "|ω-ς)" : "HIDDEN",
                accent: palette("yellow"),
                size: 14
            }
        ];
    }

    function launchOptions() {
        return [
            {
                group: "appLaunch",
                value: coreProvider.launchNormal,
                label: "⌯♱ ๋࣭⭑",
                accent: palette("cyan"),
                size: 16
            },
            {
                group: "appLaunch",
                value: coreProvider.launchBottle,
                label: "",
                accent: palette("magenta"),
                size: 18,
                bottleIcon: true
            },
            {
                group: "appLaunch",
                value: coreProvider.launchToolbox,
                label: "",
                accent: palette("omnitrix"),
                size: 14,
                toolboxIcon: true
            }
        ];
    }

    function hiddenFace(emphasized) {
        return emphasized
            ? "|ω･`ς)"
            : "|ω-ς)";
    }

    function sourceBadge(entry, unavailable) {
        const unavailableState = !!unavailable;

        return {
            label: coreProvider.sourceLabel(entry),
            accent: unavailableState
                ? palette("white")
                : coreProvider.entryIsFlatpak(entry)
                ? palette("magenta")
                : palette("cyan"),
            opacity: unavailableState ? 0.58 : 0.82
        };
    }

    function sourceGlowSpec(sourceMode, selected, hovered, pressed) {
        const mode =
            sourceMode === coreProvider.sourceFlatpak
            ? coreProvider.sourceFlatpak
            : sourceMode === coreProvider.sourceHidden
            ? coreProvider.sourceHidden
            : coreProvider.sourceNative;

        const baseAccent =
            mode === coreProvider.sourceFlatpak
            ? palette("magenta")
            : mode === coreProvider.sourceHidden
            ? palette("yellow")
            : palette("cyan");

        const glow =
            selected
            ? palette("magenta")
            : hovered
            ? palette("orange")
            : baseAccent;

        return {
            glowColor: glow,
            fillColor:
                pressed
                ? palette("magenta")
                : hovered || selected
                ? palette("yellow")
                : palette("dark"),
            textColor:
                pressed
                ? palette("black")
                : glow,
            glowRadius:
                mode === coreProvider.sourceNative ? 12 : 8,
            glowSamples:
                mode === coreProvider.sourceNative ? 11 : 7,
            glowOpacity:
                pressed
                ? 0.0
                : mode === coreProvider.sourceNative
                ? selected
                  ? 0.84
                  : hovered
                  ? 0.78
                  : 0.66
                : selected
                ? 0.64
                : hovered
                ? 0.60
                : 0.50,
            shadowOpacity:
                mode === coreProvider.sourceNative
                ? hovered || selected
                  ? 0.72
                  : 0.52
                : hovered || selected
                ? 0.52
                : 0.34
        };
    }

    function launchGlowSpec(launchMode, selected, hovered, pressed) {
        const mode =
            launchMode === coreProvider.launchToolbox
            ? coreProvider.launchToolbox
            : launchMode === coreProvider.launchBottle
            ? coreProvider.launchBottle
            : coreProvider.launchNormal;

        const baseAccent =
            mode === coreProvider.launchToolbox
            ? palette("omnitrix")
            : mode === coreProvider.launchBottle
            ? palette("magenta")
            : palette("cyan");

        const glow =
            selected
            ? palette("magenta")
            : hovered
            ? palette("orange")
            : baseAccent;

        const strongGlow =
            mode === coreProvider.launchNormal
            || mode === coreProvider.launchBottle;

        return {
            glowColor: glow,
            fillColor:
                pressed
                ? palette("magenta")
                : hovered || selected
                ? palette("yellow")
                : palette("dark"),
            textColor:
                pressed
                ? palette("black")
                : glow,
            glowRadius: strongGlow ? 12 : 8,
            glowSamples: strongGlow ? 11 : 7,
            glowOpacity:
                pressed
                ? 0.0
                : strongGlow
                ? selected
                  ? 0.84
                  : hovered
                  ? 0.78
                  : 0.66
                : selected
                ? 0.64
                : hovered
                ? 0.60
                : 0.50,
            shadowOpacity:
                strongGlow
                ? hovered || selected
                  ? 0.72
                  : 0.52
                : hovered || selected
                ? 0.52
                : 0.34
        };
    }
}
