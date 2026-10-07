import QtQuick
import Qt5Compat.GraphicalEffects

// DropShadow with source lifetime tied to the source item's window.
//
// Qt5Compat DropShadow internally owns a QQuickShaderEffectSource. During
// Quickshell hot reloads and dynamic surface teardown, keeping that source
// attached after the sampled item leaves its window can crash QtQuick inside
// QQuickShaderEffectSource::itemChange(). Consumers provide safeSource instead
// of source; this component disconnects the effect before teardown.
DropShadow {
    id: root

    property Item safeSource: null
    property bool requestedVisible: true

    readonly property bool sourceAttached:
        safeSource !== null
        && safeSource.Window.window !== null

    source: sourceAttached ? safeSource : null
    visible: requestedVisible && sourceAttached
}
