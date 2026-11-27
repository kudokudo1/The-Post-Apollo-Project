.pragma library

// Shared read-only process description. Preserve donor wording and classification.
function taskSimplePurpose(entry) {
    if (!entry)
        return "";

    const comm = String(entry.comm || entry.name || "process");
    const lower = comm.toLowerCase();
    let purpose = comm + " is one live Linux process.";

    if (lower.indexOf("quickshell") !== -1)
        purpose = "Quickshell runs desktop-shell UI such as your panels, menus, widgets, and related QML.";
    else if (lower === "sway" || lower.indexOf("sway") === 0)
        purpose = "Sway is the Wayland window manager that places windows, handles workspaces, and receives many desktop key bindings.";
    else if (lower.indexOf("pipewire") !== -1)
        purpose = "PipeWire moves audio and video streams between applications and devices.";
    else if (lower.indexOf("wireplumber") !== -1)
        purpose = "WirePlumber manages PipeWire devices, routes, and audio/video policy.";
    else if (lower.indexOf("dbus") !== -1)
        purpose = "D-Bus carries messages between desktop applications and background services.";
    else if (lower.indexOf("xdg-desktop-portal") !== -1)
        purpose = "The desktop portal gives sandboxed apps controlled access to desktop features such as files, screens, and dialogs.";
    else if (lower.indexOf("kitty") !== -1)
        purpose = "Kitty is a terminal emulator process that displays and manages terminal windows.";
    else if (lower === "zsh" || lower === "bash" || lower === "fish")
        purpose = comm + " is a command shell that reads and runs terminal commands.";
    else if (lower.indexOf("brave") !== -1 || lower.indexOf("chromium") !== -1
             || lower.indexOf("chrome") !== -1)
        purpose = comm + " is part of the web browser. Browsers split tabs, graphics, networking, and extensions across multiple processes.";
    else if (lower === "code" || lower.indexOf("code-") === 0
             || lower.indexOf("codium") !== -1)
        purpose = comm + " is part of the code editor. Editors may use separate processes for the UI, extensions, language tools, and terminals.";
    else if (lower.indexOf("systemd") !== -1)
        purpose = "systemd manages services and the lifetime of many system or user-session processes.";
    else if (lower.indexOf("networkmanager") !== -1)
        purpose = "NetworkManager manages network devices and connections such as Wi-Fi and Ethernet.";

    return purpose
           + " This panel shows its live CPU, memory, I/O, and age and can limit, freeze, or end this exact process.";
}

