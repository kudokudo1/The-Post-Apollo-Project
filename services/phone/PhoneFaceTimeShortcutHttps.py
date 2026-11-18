#!/usr/bin/env python3
"""Opt-in iPhone HTTPS ingress to the existing FaceTime Shortcut relay.

Shares one in-memory request queue with a separate loopback operator listener.
The iPhone listener exposes ONLY GET /v1/iphone/next and POST /v1/iphone/ack.
No service, certificate, firewall, iPhone Shortcut or host setting is installed.

Running this requires a new explicit operator authorization for host/network
activation. Importing the module opens no socket and reads no credentials.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path
import socket
import ssl
import stat
import threading

from http.server import ThreadingHTTPServer

from PhoneFaceTimeShortcutRelay import (
    Relay, _Handler, _LoopbackOnly, _load_token,
)

_RFC1918 = tuple(ipaddress.IPv4Network(network) for network in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
))


def _safe_address(raw: object, *, allow_loopback: bool = False) -> str:
    """Exact IPv4 literal only, no wildcard, DNS, public or link-local bind."""
    if type(raw) is not str:
        raise ValueError("invalid private IPv4 address")
    try:
        address = ipaddress.IPv4Address(raw)
    except ipaddress.AddressValueError:
        raise ValueError("invalid private IPv4 address") from None
    if any(address in network for network in _RFC1918):
        return str(address)
    if allow_loopback and address.is_loopback:
        return str(address)
    raise ValueError("invalid private IPv4 address")


def _private_tls_key(path: str) -> None:
    """No deployment with symlink, shared or foreign private key."""
    try:
        item = Path(path).lstat()
    except OSError:
        raise ValueError("unavailable TLS key") from None
    if (not stat.S_ISREG(item.st_mode)
            or item.st_uid != os.getuid()
            or item.st_mode & 0o077
            or item.st_size <= 0
            or item.st_size > 100000):
        raise ValueError("unsafe TLS key")


def _tls_context(certfile: str, keyfile: str) -> ssl.SSLContext:
    """iPhone must independently trust the hostname/SAN certificate."""
    _private_tls_key(keyfile)
    try:
        certificate = Path(certfile).lstat()
        if not stat.S_ISREG(certificate.st_mode) or certificate.st_size > 100000:
            raise ValueError("invalid TLS certificate")
    except OSError:
        raise ValueError("invalid TLS certificate") from None
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.options |= ssl.OP_NO_COMPRESSION
    # No insecure HTTP fallback and no anonymous/self-signed bypass.
    # Certificate trust is enforced by iPhone TLS client, not by this server.
    try:
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    except (OSError, ssl.SSLError, ValueError):
        raise ValueError("TLS identity unavailable") from None
    return context


class _PhoneOnlyHandler(_Handler):
    """No operator route reachable even with an operator bearer credential."""

    def do_GET(self) -> None:
        if self.path != "/v1/iphone/next":
            self._error(404)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/v1/iphone/ack":
            self._error(404)
            return
        super().do_POST()


class _PrivateIphoneHTTPSServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def __init__(
        self, bind: str, port: int, relay: Relay,
        tls: ssl.SSLContext, permitted_client: str,
        *, allow_test_loopback: bool = False,
    ) -> None:
        address = _safe_address(bind, allow_loopback=allow_test_loopback)
        client = _safe_address(permitted_client, allow_loopback=allow_test_loopback)
        if (not isinstance(tls, ssl.SSLContext)
                or type(port) is not int
                or not (port == 0 and allow_test_loopback
                        or 1024 <= port <= 65535)):
            raise ValueError("invalid HTTPS listener")
        self.relay = relay
        self._tls = tls
        self._permitted_client = client
        super().__init__((address, port), _PhoneOnlyHandler, bind_and_activate=True)

    def get_request(self) -> tuple[ssl.SSLSocket, tuple[str, int]]:
        accepted, peer = super().get_request()
        if peer[0] != self._permitted_client:
            accepted.close()
            # BaseServer catches OSError from get_request; no peer details
            # go to logs or responses, no TLS handshake with rejected peers.
            raise OSError("unapproved iPhone peer")
        try:
            accepted.settimeout(5)
            wrapped = self._tls.wrap_socket(accepted, server_side=True)
            wrapped.settimeout(5)
            return wrapped, peer
        except (OSError, ssl.SSLError):
            accepted.close()
            raise


def serve(
    admin_port: int, bind: str, phone_port: int, client: str,
    relay: Relay, tls: ssl.SSLContext,
) -> None:
    """Explicitly activated dual listeners; never executed on import."""
    if type(admin_port) is not int or not 1024 <= admin_port <= 65535:
        raise ValueError("invalid private operator port")
    # Build the phone-only gate before exposing any network socket.
    # A failure constructing HTTPS closes the loopback server and refuses.
    operator_server = _LoopbackOnly(("127.0.0.1", admin_port), relay)
    try:
        phone_server = _PrivateIphoneHTTPSServer(
            bind, phone_port, relay, tls, client)
    except Exception:
        operator_server.server_close()
        raise
    thread = threading.Thread(
        target=operator_server.serve_forever, daemon=True)
    try:
        thread.start()
        phone_server.serve_forever()
    finally:
        phone_server.shutdown()
        operator_server.shutdown()
        operator_server.server_close()
        phone_server.server_close()
        thread.join(timeout=3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Explicit iPhone-only FaceTime HTTPS ingress; not FaceTime")
    parser.add_argument("--serve-iphone-https", action="store_true")
    parser.add_argument("--acknowledge-private-lan-exposure", action="store_true")
    parser.add_argument("--operator-port", type=int)
    parser.add_argument("--phone-bind")
    parser.add_argument("--phone-port", type=int)
    parser.add_argument("--iphone-client-ip")
    parser.add_argument("--certificate-file")
    parser.add_argument("--private-key-file")
    parser.add_argument("--admin-token-file")
    parser.add_argument("--iphone-token-file")
    args = parser.parse_args(argv)
    if not (args.serve_iphone_https and args.acknowledge_private_lan_exposure):
        return 2
    try:
        bind = _safe_address(args.phone_bind)
        peer = _safe_address(args.iphone_client_ip)
        if (type(args.phone_port) is not int
                or not 1024 <= args.phone_port <= 65535
                or type(args.operator_port) is not int
                or not 1024 <= args.operator_port <= 65535):
            return 2
        tls = _tls_context(args.certificate_file, args.private_key_file)
        relay = Relay(_load_token(args.admin_token_file),
                      _load_token(args.iphone_token_file))
        serve(args.operator_port, bind, args.phone_port, peer, relay, tls)
    except (OSError, ValueError, TypeError, ssl.SSLError):
        # Never echo private paths, peer addresses or credentials.
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
