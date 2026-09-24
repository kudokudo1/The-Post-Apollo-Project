import QtQuick
import Quickshell

Scope {
    id: taskSafety

    // Runtime-only safety state. Nothing here sends a signal to a process,
    // changes a resource limit, or performs a destructive action.
    property var unlockedKeys: ({})
    property var actionUnlockedKeys: ({})

    function protectedFromKillAll(entry) {
        if (!entry)
            return true;

        const name = String(entry.comm || entry.name || "")
                     .trim().toLowerCase();
        const protectedNames = [
            "quickshell", "sway", "systemd", "dbus-broker",
            "pipewire", "pipewire-pulse", "wireplumber",
            "xdg-desktop-portal", "xdg-document-portal",
            "xdg-permission-store", "at-spi-bus-launcher",
            "at-spi2-registryd", "gpg-agent", "ssh-agent"
        ];

        return protectedNames.indexOf(name) !== -1;
    }

    function dangerKey(entry) {
        if (!entry)
            return "";

        const pid = Number(entry.pid || 0);
        const name = String(entry.comm || entry.name || "PROCESS")
                     .trim().toLowerCase();
        const user = String(entry.user || "").trim().toLowerCase();

        return pid > 1
               ? ("pid:" + String(pid) + ":" + name + ":" + user)
               : "";
    }

    function dangerReason(entry) {
        if (!entry)
            return "";

        const name = String(entry.comm || entry.name || "")
                     .trim().toLowerCase();

        if (name === "sway")
            return "SWAY COMPOSITOR • FREEZING IT CAN LOCK THE DESKTOP, INPUT AND APPCONTROL";
        if (name === "quickshell")
            return "QUICKSHELL HOST • FREEZING IT CAN REMOVE THE APPCONTROL RESUME PATH";
        if (name === "pipewire" || name === "pipewire-pulse" || name === "wireplumber")
            return "CORE AUDIO SESSION SERVICE • STOPPING IT CAN BREAK DESKTOP AUDIO";
        if (name === "dbus-broker")
            return "SESSION MESSAGE BUS • STOPPING IT CAN BREAK DESKTOP IPC";
        if (name === "systemd")
            return "USER/SESSION SERVICE MANAGER • STOPPING IT CAN DESTABILIZE THE SESSION";
        if (name.indexOf("xdg-desktop-portal") === 0
                || name === "xdg-document-portal"
                || name === "xdg-permission-store")
            return "DESKTOP PORTAL SERVICE • STOPPING IT CAN BREAK FILE/APP INTEGRATION";
        if (name.indexOf("at-spi") === 0)
            return "ACCESSIBILITY SESSION SERVICE • APPCONTROL TABS MAY DEPEND ON IT";
        if (name === "gpg-agent" || name === "ssh-agent")
            return "SESSION AUTHENTICATION AGENT • STOPPING IT CAN BREAK ACTIVE AUTH FLOWS";

        return protectedFromKillAll(entry)
               ? "SESSION-CRITICAL PROCESS"
               : "";
    }

    function requiresDangerUnlock(entry) {
        return dangerReason(entry).length > 0;
    }

    function dangerUnlockMode(entry) {
        const key = dangerKey(entry);
        if (!key)
            return "";

        const value = String(unlockedKeys[key] || "");
        return value === "sticky" ? "sticky"
             : value === "once" ? "once"
             : "";
    }

    function dangerUnlocked(entry) {
        const mode = dangerUnlockMode(entry);
        return mode === "once" || mode === "sticky";
    }

    function dangerStickyUnlocked(entry) {
        return dangerUnlockMode(entry) === "sticky";
    }

    function dangerActionKey(entry, actionKind) {
        const base = dangerKey(entry);
        const action = String(actionKind || "").trim().toLowerCase();
        return base && action ? base + "|action:" + action : "";
    }

    function dangerActionUnlockMode(entry, actionKind) {
        const master = dangerUnlockMode(entry);

        if (master === "once" || master === "sticky")
            return master;

        const key = dangerActionKey(entry, actionKind);
        if (!key)
            return "";

        const value = String(actionUnlockedKeys[key] || "");
        return value === "sticky" ? "sticky"
             : value === "once" ? "once"
             : "";
    }

    function dangerActionUnlocked(entry, actionKind) {
        const mode = dangerActionUnlockMode(entry, actionKind);
        return mode === "once" || mode === "sticky";
    }

    function dangerActionStickyUnlocked(entry, actionKind) {
        return dangerActionUnlockMode(entry, actionKind) === "sticky";
    }

    function clearDangerActionUnlocks(entry) {
        const base = dangerKey(entry);
        if (!base)
            return;

        const prefix = base + "|action:";
        const next = Object.assign({}, actionUnlockedKeys);
        let changed = false;
        const keys = Object.keys(next);

        for (let i = 0; i < keys.length; i++) {
            if (String(keys[i]).indexOf(prefix) === 0) {
                delete next[keys[i]];
                changed = true;
            }
        }

        if (changed)
            actionUnlockedKeys = next;
    }

    function toggleDangerActionUnlock(entry, actionKind) {
        if (!entry || Number(entry.pid || 0) <= 1 || dangerUnlocked(entry))
            return;

        const key = dangerActionKey(entry, actionKind);
        if (!key)
            return;

        const next = Object.assign({}, actionUnlockedKeys);

        if (next[key])
            delete next[key];
        else
            next[key] = "once";

        actionUnlockedKeys = next;
    }

    function toggleDangerActionStickyUnlock(entry, actionKind) {
        if (!entry || Number(entry.pid || 0) <= 1 || dangerUnlocked(entry))
            return;

        const key = dangerActionKey(entry, actionKind);
        if (!key)
            return;

        const next = Object.assign({}, actionUnlockedKeys);

        if (String(next[key] || "") === "sticky")
            delete next[key];
        else
            next[key] = "sticky";

        actionUnlockedKeys = next;
    }

    function relockDangerAction(entry, actionKind) {
        const key = dangerActionKey(entry, actionKind);

        if (key && String(actionUnlockedKeys[key] || "") === "once") {
            const next = Object.assign({}, actionUnlockedKeys);
            delete next[key];
            actionUnlockedKeys = next;
        }

        relockDanger(entry);
    }

    // Left click: one-shot unlock. Clicking any already-unlocked lock closes it.
    function toggleDangerUnlock(entry) {
        if (!entry || Number(entry.pid || 0) <= 1)
            return;

        const key = dangerKey(entry);
        if (!key)
            return;

        const next = Object.assign({}, unlockedKeys);

        if (next[key]) {
            delete next[key];
            clearDangerActionUnlocks(entry);
        } else {
            next[key] = "once";
        }

        unlockedKeys = next;
    }

    // Right click: persistent/sticky unlock. It survives menu close/reopen and
    // ordinary selection changes because it is in-memory QML state.
    function toggleDangerStickyUnlock(entry) {
        if (!entry || Number(entry.pid || 0) <= 1)
            return;

        const key = dangerKey(entry);
        if (!key)
            return;

        const next = Object.assign({}, unlockedKeys);

        if (String(next[key] || "") === "sticky") {
            delete next[key];
            clearDangerActionUnlocks(entry);
        } else {
            next[key] = "sticky";
        }

        unlockedKeys = next;
    }

    // Automatic re-lock only consumes one-shot unlocks.
    function relockDanger(entry) {
        const key = dangerKey(entry);

        if (!key || String(unlockedKeys[key] || "") !== "once")
            return;

        const next = Object.assign({}, unlockedKeys);
        delete next[key];
        unlockedKeys = next;
    }
}
