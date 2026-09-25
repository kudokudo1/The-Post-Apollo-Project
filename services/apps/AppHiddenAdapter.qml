import QtQuick

// Team 8 — APPS Core HIDDEN adapter.
//
// Converts externally discovered command names into APPS-shaped presentation
// records. Command discovery/history remains outside Team 8 (future RunService).
// These records contain no execute callback and no AppControl back-reference;
// execution is routed through AppLaunchPlanner as HIDDEN launch intent.
QtObject {
    id: adapter

    required property var launchPlanner

    function knownIcon(commandName) {
        const name = String(commandName || "").trim().toLowerCase();

        const known = {
            "cava": "audio-card",
            "nvim": "nvim",
            "vim": "vim",
            "htop": "htop",
            "btop": "btop",
            "fastfetch": "utilities-system-monitor",
            "neofetch": "utilities-system-monitor",
            "zsh": "utilities-terminal",
            "bash": "utilities-terminal",
            "fish": "utilities-terminal",
            "kitty": "kitty",
            "cat": "text-x-generic",
            "less": "text-x-generic",
            "man": "help-browser",
            "hollywood": "utilities-terminal",
            "pipes.sh": "utilities-terminal",
            "pipes": "utilities-terminal",
            "cmatrix": "utilities-terminal"
        };

        return known[name] || "";
    }

    function desktopEntryIcon(commandName, desktopEntries) {
        const name = String(commandName || "").trim().toLowerCase();
        const entries = Array.isArray(desktopEntries)
            ? desktopEntries
            : [];

        if (!name)
            return "";

        for (let i = 0; i < entries.length; i++) {
            const entry = entries[i];

            if (launchPlanner.launchExecutableName(entry) === name
                    && entry
                    && entry.icon) {
                return entry.icon;
            }
        }

        return "";
    }

    function iconForCommand(commandName, desktopEntries) {
        const known = knownIcon(commandName);

        if (known)
            return known;

        return desktopEntryIcon(
            commandName,
            desktopEntries
        );
    }

    function recordForCommand(commandName, desktopEntries) {
        const name = String(commandName || "").trim();

        if (!name)
            return null;

        return {
            _hiddenCommand: true,
            id: "hidden:" + name,
            name: name,
            genericName: "HIDDEN COMMAND",
            comment: "Command-line application from $PATH",
            keywords: "terminal cli hidden command",
            icon: iconForCommand(name, desktopEntries),
            actions: [],
            command: [name],
            startupClass: ""
        };
    }

    function records(commandNames, desktopEntries) {
        const source = Array.isArray(commandNames)
            ? commandNames
            : [];
        const rows = [];

        for (let i = 0; i < source.length; i++) {
            const record = recordForCommand(
                source[i],
                desktopEntries
            );

            if (record)
                rows.push(record);
        }

        return rows;
    }
}
