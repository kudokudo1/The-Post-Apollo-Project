#!/usr/bin/env python3
"""Read-only external HTTPS reachability snapshots for Post-Apollo Network.

No local network changes, IP/SSID discovery, user credentials or raw network
errors in stdout. This tests direct HTTPS to TWO independent public hosts,
not the availability of the whole Internet or the user's configured proxy.
"""
import http.client
import json
import socket
import ssl

# Small, public, unauthenticated HTTPS checks from independent providers.
# These hosts see periodic requests. No redirect is followed.
TARGETS = (
    ("example.com", "/"),
    ("www.cloudflare.com", "/cdn-cgi/trace"),
)
TIMEOUT_SECONDS = 3.0


def probe_target(host, path):
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return "dns"
    except (OSError, ValueError):
        return "unknown"

    connection = None
    try:
        connection = http.client.HTTPSConnection(
            host, port=443, timeout=TIMEOUT_SECONDS,
            context=ssl.create_default_context()
        )
        connection.request(
            "GET", path,
            headers={"User-Agent": "Post-Apollo-NetworkHealth/1.0",
                     "Accept": "text/plain, */*"}
        )
        response = connection.getresponse()
        response.read(128)
        return "ok" if 200 <= response.status < 300 else "http"
    except (OSError, ssl.SSLError, http.client.HTTPException, ValueError):
        return "https"
    finally:
        if connection is not None:
            connection.close()


def snapshot(probe=probe_target):
    observations = []
    for host, path in TARGETS:
        try:
            stage = probe(host, path)
        except Exception:
            stage = "unknown"
        if stage not in ("ok", "dns", "https", "http", "unknown"):
            stage = "unknown"
        observations.append({"target": host, "stage": stage})

    successful = sum(x["stage"] == "ok" for x in observations)
    dns_failed = sum(x["stage"] == "dns" for x in observations)
    uncertain = any(x["stage"] == "unknown" for x in observations)
    if uncertain:
        status = "unknown"
    elif successful > 0:
        status = "reachable"
    elif dns_failed == len(TARGETS):
        status = "dns-failed"
    else:
        status = "https-failed"

    return {"schema": 1, "status": status,
            "successes": successful, "dnsFailures": dns_failed,
            "probeCount": len(TARGETS), "results": observations}


def main():
    print(json.dumps(snapshot(), separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
