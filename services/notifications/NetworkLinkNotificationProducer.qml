import QtQuick
import Quickshell
import qs.services.notifications
import "NetworkLinkPolicy.js" as NetworkLinkPolicy

// Observes only the ALREADY RUNNING Network dock's nmcli device scan.
// Does not initiate another command or network poll; no network control.
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
        if (outcome.event === "")
            return;

        const disconnected = outcome.event === "disconnected";
        NotificationsService.pushRich({
            "source": "NETWORK",
            "sourceId": "apollo-network-link",
            "category": "internal",
            "severity": disconnected ? "warning" : "normal",
            "title": disconnected ? "NETWORK // LINK DISCONNECTED"
                                  : "NETWORK // LINK RESTORED",
            "message": disconnected
                ? "No Wi-Fi or Ethernet device currently reports a connected link."
                : "A Wi-Fi or Ethernet device reports a connected link again.",
            "tags": ["network", "system", "link-transition"],
            "context": {
                "eventType": disconnected ? "network-link-disconnected"
                                          : "network-link-restored",
                "origin": "apollo",
                "domain": "system",
                "observedAtUtc": new Date(observedAt).toISOString(),
                "observation": "local link only; internet not verified"
            }
        });
    }
}
