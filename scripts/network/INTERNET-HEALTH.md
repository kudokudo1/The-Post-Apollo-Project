# Post-Apollo // Network Internet Health

Internet health is independent of the existing Wi-Fi/Ethernet **link** alerts.
A local link does not imply that external DNS or HTTPS succeeds.

## How it works

The existing Network dock supplies one \`nmcli\` device scan to both passive
notification observers. Only when that scan reports a connected Wi-Fi or
Ethernet link, the Internet-health observer may run the read-only Python
probe. It runs **no more than once every 120 seconds**.

\`scripts/network/internet_health_probe.py\` makes one TLS-verified HTTPS
request to each of these public hosts (two separate providers):

- \`https://example.com/\`
- \`https://www.cloudflare.com/cdn-cgi/trace\`

It does not follow redirects, save response bodies, send account details, or
print IP addresses, SSIDs, HTTP content or raw socket error messages. Probed
sites can see the requester's public IP address, as with any web request.

- **Reachable:** At least one HTTPS endpoint returns status 200–299. This only
  verifies *some* external HTTPS reachability, not every service.
- **DNS failure:** Both hosts fail to resolve. This identifies a *probe DNS*
  problem, not necessarily global DNS failure.
- **External HTTPS failure:** Neither endpoint succeeds but at least one
  resolution completes; this may be routing, filtering, proxy policy, TLS,
  a captive portal, endpoint failure, or Internet availability. This is **not**
  a proven ISP-wide outage.
- **Unknown:** Probe could not provide sound evidence; notification policy
  ignores it.

Two matching observations spanning at least a minute are needed to announce
DNS or HTTPS failure. Two successive reachable snapshots are needed to
announce recovery. Normal online startup is silent; a sustained offline
startup can warn. No repeated popups during the same impairment episode,
and gaps >7 minutes reset incomplete confirmation. The previous local-link
producer remains authoritative for interface disconnected/restored messages.

This tests **direct HTTPS**. Systems that require a configured HTTP proxy may
correctly work in browsers while this direct check cannot reach its targets.
Endpoint filtering or an isolated network can produce warnings; do not
present them as a confirmed whole-Internet failure.

## Verification

From the Post-Apollo repository:

\`\`\`bash
python3 tests/notifications/test_network_link_producer.py
python3 tests/notifications/test_network_internet_health_producer.py
\`\`\`

The tests use mocked network responses and never contact endpoints.

To inspect actual reachability on an operator-controlled desktop:

\`\`\`bash
python3 scripts/network/internet_health_probe.py
\`\`\`

That one command makes **two real external HTTPS requests** and prints a
single JSON snapshot. It does not generate notifications by itself.

A popup is possible only while the Network dock is running, shared
Notifications history is ready, and an existing device scan shows a
connected Wi-Fi/Ethernet link. The usual DND, snooze and Favorites policies
apply to source \`apollo-internet-health\`.

## Follow-up scope

Gateway diagnosis, path-specific reachability, proxy-aware tests, IPv4/IPv6
separation, configurable endpoints and an explicit opt-out control are future
work. Do not infer gateway reachability from an HTTPS failure, and do not
automatically rewrite DNS/routes or restart NetworkManager.
