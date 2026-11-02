import QtQuick
import Quickshell
import Quickshell.Io

// Display-only, experimental reader for a future privileged Identity host.
// No OAuth/session/authorization code, token or API URL ever enters QML.
// The fixed Python command can only request a validated read-only snapshot.
// No host is installed/activated by this component.
Item {
    id: reader

    property bool active: false
    property string pythonPath: "/usr/bin/python3"
    readonly property string readerPath: Quickshell.shellPath(
        "services/identity/identity_display_reader_cli_v0.py")
    readonly property string displaySchema:
        "post-apollo.identity.desktop-context-display.v0"

    property var snapshot: null
    // Invalidated on close, section change and overlapping refresh attempts.
    // Prevents an old in-flight stdout response from restoring an old user.
    property bool acceptResponse: false

    function clear() {
        snapshot = null;
    }

    function exactKeys(value, keys) {
        if (value === null || typeof value !== "object"
                || Array.isArray(value))
            return false;
        const actual = Object.keys(value);
        return actual.length === keys.length && keys.every(function(key) {
            return Object.prototype.hasOwnProperty.call(value, key);
        });
    }

    function identifier(value) {
        return typeof value === "string" &&
               /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value);
    }

    function validDisplay(view) {
        if (!exactKeys(view, [
                "schema", "status", "organizations", "portfolios",
                "canSwitchOrganization"
            ]) || view.schema !== displaySchema
            || view.canSwitchOrganization !== false
            || !["READY", "NO_MEMBERSHIPS", "SIGNED_OUT",
                  "NOT_CONNECTED", "UNAVAILABLE"].includes(view.status)
            || !Array.isArray(view.organizations)
            || !Array.isArray(view.portfolios)
            || view.organizations.length > 100 || view.portfolios.length > 100)
            return false;

        if (view.status !== "READY" && view.status !== "NO_MEMBERSHIPS")
            return view.organizations.length === 0
                   && view.portfolios.length === 0;

        if ((view.status === "READY") !== (view.organizations.length > 0))
            return false;

        const membershipIds = [];
        for (const org of view.organizations) {
            if (!exactKeys(org, ["organizationId", "kind", "scopeGrants"])
                    || !identifier(org.organizationId)
                    || !["llc", "nonprofit", "customer"].includes(org.kind)
                    || membershipIds.includes(org.organizationId)
                    || !Array.isArray(org.scopeGrants)
                    || org.scopeGrants.length > 64)
                return false;
            membershipIds.push(org.organizationId);
            for (const grant of org.scopeGrants) {
                if (!exactKeys(grant,
                        ["action", "divisionId", "unitId", "expiresAt"])
                        || !["records.read", "records.write"].includes(grant.action)
                        || (grant.divisionId !== null
                            && !identifier(grant.divisionId))
                        || (grant.unitId !== null && !identifier(grant.unitId))
                        || (grant.expiresAt !== null
                            && (!Number.isSafeInteger(grant.expiresAt)
                                || grant.expiresAt <= Date.now() / 1000)))
                    return false;
            }
        }

        const portfolioIds = [];
        for (const portfolio of view.portfolios) {
            if (!exactKeys(portfolio, ["portfolioId", "organizationIds"])
                    || !identifier(portfolio.portfolioId)
                    || portfolioIds.includes(portfolio.portfolioId)
                    || !Array.isArray(portfolio.organizationIds)
                    || portfolio.organizationIds.length === 0
                    || portfolio.organizationIds.length > 100)
                return false;
            portfolioIds.push(portfolio.portfolioId);
            const seen = [];
            for (const orgId of portfolio.organizationIds) {
                if (!identifier(orgId) || !membershipIds.includes(orgId)
                        || seen.includes(orgId))
                    return false;
                seen.push(orgId);
            }
        }
        return true;
    }

    function refresh() {
        // Revoke the previous display BEFORE attempting each read.
        // If Python or the host stalls, no stale company list remains.
        clear();
        acceptResponse = false;
        if (!active || snapshotProcess.running)
            return;
        snapshotProcess.command = [pythonPath, readerPath, "--json"];
        acceptResponse = true;
        snapshotProcess.running = true;
    }

    function receive(raw) {
        if (!active || !acceptResponse ||
                typeof raw !== "string" || raw.length > 65536) {
            clear();
            return;
        }
        acceptResponse = false;
        try {
            const next = JSON.parse(raw);
            if (validDisplay(next)) {
                snapshot = next;
                return;
            }
        } catch (error) {
            // No raw response or exception is sent to console/logs.
        }
        clear();
    }

    onActiveChanged: {
        if (!active) {
            acceptResponse = false;
            clear();
        } else {
            refresh();
        }
    }

    Timer {
        id: poll
        interval: 5000
        repeat: true
        running: reader.active
        onTriggered: reader.refresh()
    }

    Process {
        id: snapshotProcess
        stdout: StdioCollector {
            onStreamFinished: reader.receive(String(text || ""))
        }
        // Never echo stderr: it can contain local private paths.
        stderr: StdioCollector {
            onStreamFinished: {}
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0)
                reader.clear();
        }
    }
}
