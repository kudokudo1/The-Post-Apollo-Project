pragma Singleton
import QtQml

// CI-only stand-in. No real Quickshell runtime or desktop shell is started.
QtObject {
    function shellPath(source) {
        return "/ci-fake-shell/" + source;
    }
}
