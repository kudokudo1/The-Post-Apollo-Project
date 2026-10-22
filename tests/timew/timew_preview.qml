import Quickshell
import "../../widgets"

// Isolated TimeW visual/keyboard preview; not loaded by shell.qml.
// No background logging, screenshot capture, timer engine or restore calls.
Scope {
    TimeW {
        menuOpen: true
        keyboardActive: true
        screen: Quickshell.screens.find(s => s.name === "DP-5")
    }
}
