import QtQuick
import Quickshell
import qs.services.connections
import "widgets/cpuplus"

// C1 isolated native Quickshell test. It exercises the real provider buttons,
// setup guide and Social reload in a disposable config, with no credentials.
ShellRoot {
    id: root
    property string selectedId: "social"
    property string phase: "boot"
    property bool done: false
    property int ticks: 0

    FloatingWindow {
        id: window
        visible: true
        title: "C1-CONNECTIONS"
        implicitWidth: 1400
        implicitHeight: 850

        Rectangle {
            anchors.fill: parent
            color: "#1B0623"

            CpuPlusSettingsConnectionsOverviewPane {
                id: overview
                x: 18
                y: 30
                width: 395
                height: parent.height - 45
            }
            CpuPlusSettingsConnectionsListPane {
                id: inventory
                x: 434
                y: 30
                width: 355
                height: parent.height - 45
                selectedId: root.selectedId
                onProviderSelected: function(providerId) {
                    root.selectedId = providerId;
                }
            }
            CpuPlusSettingsConnectionsDetailsPane {
                id: details
                x: 806
                y: 30
                width: parent.width - 828
                height: parent.height - 45
                selectedId: root.selectedId
            }
        }
    }

    function find(item, predicate) {
        if (!item) return null;
        if (predicate(item)) return item;
        const list = item.children || [];
        for (let i = 0; i < list.length; i++) {
            const match = find(list[i], predicate);
            if (match) return match;
        }
        return null;
    }
    function providerButton(id) {
        return find(window.contentItem, function(item) {
            return item.modelData && item.modelData.id === id
                && item.available !== undefined && item.selected !== undefined;
        });
    }
    function button(label) {
        return find(window.contentItem, function(item) {
            return item.label === label && item.available !== undefined;
        });
    }
    function revealInDetails(item) {
        if (!item) return;
        const scroller = find(details, function(candidate) {
            return candidate.contentY !== undefined
                   && candidate.contentHeight !== undefined
                   && candidate.contentItem !== undefined;
        });
        if (!scroller) return;
        const pt = item.mapToItem(scroller.contentItem, 0, 0);
        scroller.contentY = Math.max(0, Math.min(
            Math.max(0, scroller.contentHeight - scroller.height),
            pt.y - 40));
    }
    function announce(item, marker) {
        if (!item || !item.visible || item.width < 4 || item.height < 4)
            return false;
        const xy = item.mapToItem(window.contentItem,
                                  item.width/2, item.height/2);
        if (!isFinite(xy.x) || !isFinite(xy.y)
                || xy.x < 3 || xy.y < 3
                || xy.x >= window.width-3 || xy.y >= window.height-3)
            return false;
        console.log("C1_" + marker + "_READY // x=" + Math.round(xy.x)
                    + " y=" + Math.round(xy.y));
        return true;
    }
    function c2gSynthetic(state, reason, remaining) {
        return {
            ok:true, requestId:"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            state:state, provider:"nasa-firms", consumer:"weather-earth",
            operation:"fires.hotspots.read", profile:"ci-only-profile",
            reason:reason, expiresInMs:remaining,
            credentialPresent:false, realGrantActive:false,
            canApproveInProduction:false, simulated:true
        };
    }
    function fail(reason) {
        if (done) return;
        done = true;
        console.error("C1_FAIL // " + reason + " // " + phase);
    }
    Timer {
        interval: 85
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if (root.ticks % 60 === 0)
                console.log("C1_TICK // " + root.phase);
            if (root.phase === "boot") {
                if (!ConnectionsRegistry.rows
                        || ConnectionsRegistry.rows.length !== 7
                        || !inventory.visible || !details.visible)
                    return;
                if (root.selectedId !== "social"
                        || !details.source
                        || details.source.id !== "social") {
                    root.fail("BAD_SOCIAL_DEFAULT"); return;
                }
                if (root.announce(root.providerButton("nasa-firms"),
                                  "FIRMS_BUTTON"))
                    root.phase = "firmsClicked";
            } else if (root.phase === "firmsClicked") {
                if (root.selectedId !== "nasa-firms") return;
                if (!details.source || details.source.id !== "nasa-firms"
                        || details.guideOpen) {
                    root.fail("WRONG_FIRMS_SELECTION");return;
                }
                if (root.announce(root.button("SETUP / DETAILS"),
                                  "GUIDE_BUTTON"))
                    root.phase = "guideClicked";
            } else if (root.phase === "guideClicked") {
                if (!details.guideOpen) return;
                if (!details.source.setup
                        || details.source.setup.indexOf("BROKER") < 0
                           && details.source.setup.indexOf("NASA") < 0) {
                    root.fail("FAKE_READY_SETUP_GUIDE");return;
                }
                if (!root.announce(root.button("CHECK KEYRING"),
                                   "KEYRING_BUTTON"))
                    return;
                root.phase = "keyringClicked";
            } else if (root.phase === "keyringClicked") {
                if (ConnectionsBroker.status === "NOT CHECKED"
                        || ConnectionsBroker.status === "CHECKING")
                    return;
                const status = ConnectionsBroker.status;
                if (["SERVICE_ACQUIRED", "SERVICE_NOT_RUNNING",
                     "DBUS_PROBE_TOOL_MISSING", "SESSION_BUS_UNAVAILABLE",
                     "UNEXPECTED_DBUS_RESPONSE"].indexOf(status) < 0) {
                    root.fail("PROBE_RESULT_NOT_PARSED"); return;
                }
                if (ConnectionsBroker.credentialActionsEnabled
                        || ConnectionsBroker.lastCheckedMs <= 0
                        || ConnectionsBroker.available &&
                           ConnectionsBroker.authorize({
                               provider:"nasa-firms",consumer:"weather-earth",
                               operation:"fires.hotspots.read"
                           }).allowed) {
                    root.fail("UNTRUSTED_KEYRING_GRANT"); return;
                }
                console.log("C2A_PASS // READONLY_KEYRING_PROBE // "
                            + ConnectionsBroker.status);
                if (root.announce(root.button("REVIEW ACCESS"),
                                  "REVIEW_ACCESS"))
                    root.phase = "accessReviewClicked";
            } else if (root.phase === "accessReviewClicked") {
                if (!details.permissionReviewOpen) return;
                const preview = details.permissionPreview;
                const approve = root.button("APPROVE // UNAVAILABLE");
                if (!preview.known || preview.provider !== "nasa-firms"
                        || preview.canApprove || preview.hasActiveGrant
                        || !approve || approve.available
                        || ConnectionsBroker.credentialActionsEnabled) {
                    root.fail("FALSE_ACCESS_REVIEW_AUTHORITY"); return;
                }
                const dismiss = root.button("DISMISS REVIEW");
                root.revealInDetails(dismiss);
                if (root.announce(dismiss, "DISMISS_REVIEW"))
                    root.phase = "reviewDismissClicked";
            } else if (root.phase === "reviewDismissClicked") {
                if (details.permissionReviewOpen) return;
                if (details.reviewFeedback !==
                        "REVIEW CLOSED // NO ACCESS GRANTED" ||
                        ConnectionsBroker.authorize({
                           provider:"nasa-firms",consumer:"weather-earth",
                           operation:"fires.hotspots.read"
                        }).allowed) {
                    root.fail("REVIEW_CREATED_A_GRANT"); return;
                }
                console.log("C2E_PASS // NATIVE_ACCESS_REVIEW_DISMISS_NO_GRANT");
                const opener = root.button("VIEW REQUEST STATUS");
                root.revealInDetails(opener);
                if (root.announce(opener, "STATUS_OPEN"))
                    root.phase = "statusOpened";
            } else if (root.phase === "statusOpened") {
                if (!details.requestStatusOpen) return;
                if (details.requestStatusView.state !== "OFFLINE"
                        || details.requestStatusView.title !== "HOST NOT CONNECTED"
                        || ConnectionsBroker.credentialActionsEnabled) {
                    root.fail("STATUS_PRETENDED_CONNECTED"); return;
                }
                details.syntheticStatusPreview = root.c2gSynthetic(
                    "PENDING", "AWAITING_SIMULATED_REVIEW", 15000);
                root.phase = "statusPending";
            } else if (root.phase === "statusPending") {
                if (details.requestStatusView.state !== "PENDING"
                        || details.requestStatusView.title !== "SIMULATED // PENDING"
                        || details.requestStatusView.live
                        || details.requestStatusView.canApprove
                        || details.requestStatusView.grantActive) {
                    root.fail("UNSAFE_PENDING_STATUS"); return;
                }
                details.syntheticStatusPreview = root.c2gSynthetic(
                    "APPROVED", "SIMULATED_HOST_APPROVED", 5000);
                root.phase = "statusApproved";
            } else if (root.phase === "statusApproved") {
                if (details.requestStatusView.state !== "APPROVED"
                        || details.requestStatusView.title !== "SIMULATED // APPROVED"
                        || details.requestStatusView.grantActive
                        || details.requestStatusView.canApprove) {
                    root.fail("FAKE_APPROVED_AS_REAL_GRANT"); return;
                }
                details.syntheticStatusPreview = root.c2gSynthetic(
                    "CANCELLED", "HOST_CANCELLED", 0);
                root.phase = "statusCancelled";
            } else if (root.phase === "statusCancelled") {
                if (details.requestStatusView.state !== "CANCELLED"
                        || details.requestStatusView.grantActive) {
                    root.fail("CANCELLED_LEFT_GRANT"); return;
                }
                const closer = root.button("CLOSE REQUEST STATUS");
                root.revealInDetails(closer);
                if (root.announce(closer, "STATUS_CLOSE"))
                    root.phase = "statusClosed";
            } else if (root.phase === "statusClosed") {
                if (details.requestStatusOpen) return;
                details.syntheticStatusPreview = null;
                if (details.requestStatusView.state !== "OFFLINE"
                        || ConnectionsBroker.authorize({
                           provider:"nasa-firms",consumer:"weather-earth",
                           operation:"fires.hotspots.read"
                        }).allowed) {
                    root.fail("STATUS_CREATED_PERMISSION"); return;
                }
                console.log("C2G_PASS // NATIVE_OFFLINE_SIMULATED_STATES_NO_GRANTS");
                if (root.announce(root.providerButton("social"),
                                  "SOCIAL_BUTTON"))
                    root.phase = "socialClicked";
            } else if (root.phase === "socialClicked") {
                if (root.selectedId !== "social") return;
                if (!details.source || details.source.id !== "social"
                        || details.guideOpen) {
                    root.fail("SOCIAL_SELECTION_OR_GUIDE_STALE");return;
                }
                if (root.announce(root.button("RELOAD SOCIAL STATUS"),
                                  "RELOAD_BUTTON"))
                    root.phase = "reloadClicked";
            } else if (root.phase === "reloadClicked") {
                if (overview.feedback === "") return;
                if (!overview.social
                        || overview.social.status !== "LAYOUT READY"
                           && overview.social.status !== "LAYOUT UNAVAILABLE") {
                    root.fail("INVALID_SOCIAL_READOUT");return;
                }
                root.done = true;
                console.log("C1_PASS // NATIVE_PROVIDER_SELECT_GUIDE_SOCIAL_RELOAD");
            }
        }
    }
    Timer {
        interval: 26000
        running: !root.done
        repeat: false
        onTriggered: root.fail("TIMEOUT")
    }
    Timer {
        interval: 350
        running: root.done
        repeat: false
        onTriggered: Qt.quit()
    }
}
