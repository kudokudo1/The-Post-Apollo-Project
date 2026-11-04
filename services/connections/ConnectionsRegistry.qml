pragma Singleton

import QtQuick
import Quickshell
import qs.services.social
import qs.services.notifications
import qs.services.hub
import "../weather/FirmsHotspotPolicy.js" as FirmsPolicy
import "ConnectionsPolicy.js" as ConnectionPolicy

// C1 read-only service inventory. Social owns identity metadata, Notifications
// owns notifications, Weather owns provider requests. This registry never
// takes ownership of their state or of the operator's secrets.
Scope {
    id: registry

    readonly property var socialView: SocialIdentityStore.snapshot
    readonly property var socialAccountDocument: SocialAccountDetailsStore.saved
    // Presence/shape only. A key-shaped value is NOT authenticated access.
    // Never publish Quickshell.env's raw value to a property, model or log.
    readonly property bool firmsKeyPresent:
        FirmsPolicy.configuredKey(
            Quickshell.env("POST_APOLLO_FIRMS_MAP_KEY")
        ) !== ""

    readonly property var rows: ConnectionPolicy.build({
        socialState: SocialIdentityStore.storageState,
        socialSnapshot: socialView,
        socialAccountState: SocialAccountDetailsStore.state,
        socialAccounts: socialAccountDocument,
        notificationsReady: NotificationsService.historyReady,
        firmsKeyPresent: firmsKeyPresent,
        // Read only the existing C2 broker and sole TASKS store. These
        // are status bits, never Secret Service credentials or grants.
        tasksProviderStatus: ConnectionsBroker.status,
        tasksProviderChecking: ConnectionsBroker.checking,
        tasksBrokerActionsEnabled: ConnectionsBroker.credentialActionsEnabled,
        tasksRecoveryEnabled: ApolloHubTodoStore.encryptedRecoveryEnabled,
        tasksRecoveryStorageAuthorized:
            ApolloHubTodoStore.encryptedRecoveryStorageAuthorized,
        tasksRecoveryUnlockAuthorized:
            ApolloHubTodoStore.encryptedRecoveryUnlockAuthorized,
        tasksDraftHostEnabled: ApolloHubTodoStore.encryptedDraftHostEnabled,
        tasksDraftHostWriteAuthorized:
            ApolloHubTodoStore.encryptedDraftHostWriteAuthorized
    })
    readonly property var summary: ConnectionPolicy.counters(rows)

    function entry(id) {
        return ConnectionPolicy.find(rows, id);
    }

    function refreshSocial() {
        // Explicit operator action, read-only disk reload of existing owners.
        // Does not switch a browser profile, authenticate or write to disk.
        const identities = SocialIdentityStore.reloadFromDisk();
        const names = SocialAccountDetailsStore.refresh();
        return identities || names;
    }
}
