import QtQuick
import Quickshell
import Quickshell.Io
import qs.services.notifications
import "NetworkLinkPolicy.js" as LinkPolicy
import "NetworkInternetHealthPolicy.js" as InternetPolicy

// Two independent direct HTTPS checks, at most once per 120 seconds, only
// after existing nmcli device observations confirm Wi-Fi or Ethernet link.
// No router settings, network changes, retry storms, local addresses or SSIDs.
Scope {
    id: producer

    property bool localLinkAvailable: false
    property int linkEpoch: 0
    property int pendingEpoch: -1
    property double lastProbeAtMs: 0
    property var reachabilityState: InternetPolicy.initial()

    function observeDeviceResult(output) {
        const links = LinkPolicy.parseDeviceStatus(output);
        if (!links)
            return;
        const connected = links.wifi === true || links.ethernet === true;
        // Unknown states are not proof of a lost link.
        if (!connected && links.wifi === null && links.ethernet === null)
            return;
        if (connected !== producer.localLinkAvailable) {
            producer.localLinkAvailable = connected;
            producer.linkEpoch++;
            if (connected)
                producer.refresh();
        }
    }

    function refresh() {
        if (!producer.localLinkAvailable || !NotificationsService.historyReady
                || probeProcess.running)
            return;
        const now = Date.now();
        if (producer.lastProbeAtMs > 0
                && now - producer.lastProbeAtMs < 120000)
            return;
        producer.lastProbeAtMs = now;
        producer.pendingEpoch = producer.linkEpoch;
        probeProcess.running = true;
    }

    function acceptResponse(raw) {
        if (!producer.localLinkAvailable || !NotificationsService.historyReady
                || producer.pendingEpoch !== producer.linkEpoch)
            return;
        const observation = InternetPolicy.parseResult(raw);
        if (!observation)
            return; // corrupt/failed probe is NOT an Internet outage.
        const at = Date.now();
        const decision = InternetPolicy.transition(
            producer.reachabilityState, observation, at);
        producer.reachabilityState = decision.state;
        if (!decision.event)
            return;

        const restored = decision.event === "restored";
        const dnsFailed = decision.event === "dns-failed";
        const label = restored ? "EXTERNAL HTTPS REACHABLE AGAIN"
                    : dnsFailed ? "DNS RESOLUTION FAILED"
                    : "EXTERNAL HTTPS PROBES FAILED";
        const detail = restored
            ? "At least one configured external HTTPS probe is reachable again."
            : dnsFailed
            ? "Neither configured hostname resolved in two consecutive checks."
            : "Neither configured external HTTPS endpoint returned a valid "
              + "response in two consecutive checks.";
        NotificationsService.pushRich({
            "source": "NETWORK",
            "sourceId": "apollo-internet-health",
            "category": "internal",
            "severity": restored ? "normal" : "warning",
            "title": "NETWORK // " + label,
            "message": detail + " These probes cannot establish whole-Internet "
                       + "or gateway health. Review Network diagnostics.",
            "tags": ["network", "system", "internet-health"],
            "context": {
                "eventType": restored ? "internet-probe-reachable"
                                      : dnsFailed ? "internet-probe-dns-failed"
                                                  : "internet-probe-https-failed",
                "origin": "apollo",
                "domain": "system",
                "evidence": "two direct TLS-verified HTTPS endpoints",
                "successCount": observation.successes,
                "probeCount": observation.probeCount,
                "observedAtUtc": new Date(at).toISOString()
            }
        });
    }

    Process {
        id: probeProcess
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("scripts/network/internet_health_probe.py")]
        stdout: StdioCollector {
            onStreamFinished: producer.acceptResponse(text)
        }
    }

    Timer {
        interval: 120000
        repeat: true
        running: true
        onTriggered: producer.refresh()
    }
    Connections {
        target: NotificationsService
        function onHistoryReadyChanged() { producer.refresh(); }
    }
}
