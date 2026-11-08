import QtQuick
import "../services/favorites/FavoritesResourcePolicy.js" as Resource

// Reusable U3a collection membership button. Storage and policy remain with
// the injected CollectionsStore. Does not add/remove the actual favorite.
ActionButton {
    id: button
    property var collectionStore: null
    property string collectionId: ""
    property var resource: null
    readonly property var normalized: Resource.normalize(resource)
    readonly property string resourceKey: normalized.ok
        ? normalized.record.key : ""
    readonly property bool supportsCollection:
        normalized.ok
        && normalized.record.capabilities.indexOf("collection") >= 0
    readonly property bool canChange: collectionStore !== null
        && collectionStore.canEdit && supportsCollection
        && collectionStore.acceptsKey(resourceKey)
    readonly property bool inCollection: collectionStore !== null
        && resourceKey !== ""
        && collectionStore.hasMember(collectionId,resourceKey)
    signal membershipAccepted(bool member)

    implicitWidth: 61
    implicitHeight: 28
    acceptedButtons: Qt.LeftButton
    accentColor: Colors.magenta
    label: inCollection ? "SAVED" : "ADD"
    labelPixelSize: 10
    selected: inCollection
    available: canChange
    onLeftClicked: {
        if (!canChange) return;
        const ok=collectionStore.toggleMember(collectionId,resourceKey);
        if (ok)
            membershipAccepted(collectionStore.hasMember(collectionId,resourceKey));
    }
}
