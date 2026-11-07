import QtQuick
import "../services/favorites" as FavoriteServices
import "../services/favorites/FavoritesResourcePolicy.js" as Resource

// U1 reusable view control for NEW FavoritesDefaultStore resources.
// No automatic migration, host actions, external provider calls or implicit
// protection. The caller supplies the stable descriptor and visible action.
ActionButton {
    id: button

    property var resource: null
    property string feature: "favorite" // favorite | pin
    readonly property var store: FavoriteServices.FavoritesDefaultStore
    readonly property var normalizedResource: Resource.normalize(resource)
    readonly property string resourceKey:
        normalizedResource.ok ? normalizedResource.record.key : ""
    readonly property bool featureSupported:
        normalizedResource.ok
        && normalizedResource.record.capabilities.indexOf(feature) >= 0
        && (feature === "favorite" || feature === "pin")
    readonly property bool canChange:
        featureSupported && store.canEdit && store.acceptsKey(resourceKey)

    signal changeAccepted(bool selectedValue)

    implicitWidth: feature === "pin" ? 76 : 38
    implicitHeight: 30
    acceptedButtons: Qt.LeftButton
    accentColor: Colors.magenta
    label: feature === "pin"
        ? (selected ? "PINNED" : "PIN")
        : (selected ? "★" : "☆")
    labelPixelSize: feature === "pin" ? 10 : 14
    selected: feature === "pin"
        ? store.isPinned(resourceKey) : store.isFavorite(resourceKey)
    available: canChange

    onLeftClicked: {
        if (!canChange)
            return;
        const ok = feature === "pin"
            ? store.togglePinned(resourceKey)
            : store.toggleFavorite(resourceKey);
        if (ok)
            changeAccepted(feature === "pin"
                ? store.isPinned(resourceKey) : store.isFavorite(resourceKey));
    }
}
