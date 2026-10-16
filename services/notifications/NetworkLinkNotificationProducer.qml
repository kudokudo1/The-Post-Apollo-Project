import QtQuick
import Quickshell
import qs.services.notifications
import "NetworkLinkPolicy.js" as NetworkLinkPolicy

// Receives ONLY the Network dock's existing nmcli device scan output.
// Read-only and silent on startup; no new polling or connection commands.
Scope {
    id: producer
    property var linkState: NetworkLinkPolicy.initial()

    function observeDeviceResult(output) {
        const observation = NetworkLinkPolicy.parseDeviceStatus(output);
        if (!observation)
            return;

        const observedAt = Date.now();
        const outcome = NetworkLinkPolicy.transition(
            linkState, observation, observedAt);
        linkState = outcome.state;

        for (const change of outcome.events) {
            const disconnected = change.event === "disconnected";
            const kindLabel = change.kind === "wifi" ? "WI-FI" : "ETHERNET";
            NotificationsService.pushRich({
                "source": "NETWORK",
                "sourceId": "apollo-network-link",
                "category": "internal",
                "severity": disconnected ? "warning" : "normal",
                "title": "NETWORK // " + kindLabel + " LINK "
                         + (disconnected ? "DISCONNECTED" : "RESTORED"),
                "message": disconnected
                    ? kindLabel + " no longer reports a connected local link."
                      + " Another network connection may still be available."
                    : kindLabel + " reports a connected local link again."
                      + " Internet access has not been verified.",
                "tags": ["network", "system", "link-transition", change.kind],
                "context": {
                    "eventType": disconnected ? "network-link-disconnected"
                                              : "network-link-restored",
                    "origin": "apollo",
                    "domain": "system",
                    "linkType": change.kind,
                    "observedAtUtc": new Date(observedAt).toISOString(),
                    "observation": "local link only; internet not verified"
                }
            });
        }
    }
}
