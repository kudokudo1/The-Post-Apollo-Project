"""Session-bound public-HTTPS-to-loopback relay for MPD radio playback.

This module is only started by the existing media-controller service after an
explicit LOAD. Untrusted directory URLs are never supplied directly to MPD.
Outbound TLS is pinned to an independently checked public IP; HTTP redirects
are never followed. The relay is a transport, not a new audio player.
"""
from __future__ import annotations

import http.client
import ipaddress
import secrets
import socket
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from direct_stream_source import validate_https_audio_url
from headless_mpd import MediaBackendError

_MAX_ACTIVE_STREAMS = 2
_MAX_REGISTERED_STATIONS = 256
_TOKEN_LIFETIME_SECONDS = 12 * 60 * 60
_ALLOWED_MIME = {"audio/mpeg", "audio/mp3", "audio/x-mpeg"}


def public_endpoint(hostname: str, resolve=socket.getaddrinfo) -> str:
    """Refuse DNS answers containing ANY non-global address; pin the chosen IP."""
    try:
        answers = resolve(hostname, 443, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError, ValueError):
        raise MediaBackendError("STREAM_DNS", "Station DNS lookup failed") from None
    addresses: list[str] = []
    for family, _, _, _, sockaddr in answers:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        try:
            address = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            raise MediaBackendError("STREAM_DNS", "Invalid station DNS answer") from None
        # ipaddress.is_global alone counts multicast destinations as global.
        # Public unicast is the only permissible remote audio endpoint.
        if (not address.is_global or address.is_multicast
                or address.is_unspecified or address.is_reserved):
            raise MediaBackendError("STREAM_DNS_BLOCKED",
                                    "Station DNS resolved to a restricted address")
        addresses.append(str(address))
    if not addresses:
        raise MediaBackendError("STREAM_DNS", "No public station address found")
    return addresses[0]


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, pinned_ip: str, timeout: float = 6.0):
        super().__init__(hostname, 443, timeout=timeout, context=ssl.create_default_context())
        self._pinned_ip = pinned_ip

    def connect(self):
        # Using the numeric destination here prevents a second DNS resolution
        # between validation and TLS. SNI and certificate validation retain
        # the original hostname, NOT the numeric address.
        raw = socket.create_connection((self._pinned_ip, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def open_public_mp3_stream(uri: str, resolver=public_endpoint):
    """Create a single TLS-pinned MP3 response. Never honor redirects."""
    uri = validate_https_audio_url(uri)
    parsed = urlsplit(uri)
    hostname = parsed.hostname
    if not hostname:
        raise MediaBackendError("INVALID_REF", "Stream hostname absent")
    destination = resolver(hostname)
    connection = _PinnedHTTPSConnection(hostname, destination)
    try:
        target = parsed.path or "/"
        connection.request("GET", target,
                           headers={"Host": hostname, "Accept": "audio/mpeg",
                                    "Icy-MetaData": "0", "User-Agent": "Post-Apollo-HiFi/0.1"})
        response = connection.getresponse()
        if response.status != 200:
            raise MediaBackendError("STREAM_HTTP",
                                    "Station did not return an HTTP 200 audio stream")
        media_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
        if media_type not in _ALLOWED_MIME:
            raise MediaBackendError("STREAM_FORMAT", "Station did not return MP3 audio")
        return connection, response
    except BaseException:
        connection.close()
        raise


class RadioStreamRelay:
    """One existing controller-owned loopback relay, started lazily on LOAD."""

    def __init__(self, opener=open_public_mp3_stream, now=time.monotonic):
        self._opener = opener
        self._now = now
        self._entries: dict[str, tuple[str, float]] = {}
        self._lock = threading.RLock()
        self._capacity = threading.BoundedSemaphore(_MAX_ACTIVE_STREAMS)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def _start(self):
        if self._server is not None:
            return
        relay = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, fmt, *args):
                # Never log token or stream URL.
                return

            def do_GET(self):
                if not relay._capacity.acquire(blocking=False):
                    self.send_error(503, "Audio relay busy")
                    return
                connection = None
                try:
                    uri = relay._resolve(self.path)
                    if uri is None:
                        self.send_error(404, "Unknown or expired audio token")
                        return
                    connection, response = relay._opener(uri)
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/mpeg")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    while True:
                        frame = response.read(16_384)
                        if not frame:
                            break
                        self.wfile.write(frame)
                except (OSError, ssl.SSLError, BrokenPipeError, ConnectionResetError,
                        MediaBackendError, http.client.HTTPException):
                    # No destination details are sent back to MPD or logged.
                    if not self.wfile.closed:
                        try:
                            if connection is None:
                                self.send_error(502, "Audio stream unavailable")
                        except (BrokenPipeError, OSError):
                            pass
                finally:
                    if connection is not None:
                        connection.close()
                    relay._capacity.release()

        class Server(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = False

        self._server = Server(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="post-apollo-radio-relay", daemon=True)
        self._thread.start()

    def _resolve(self, path: str) -> str | None:
        if not path.startswith("/radio/"):
            return None
        token = path[len("/radio/"):]
        if len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
            return None
        with self._lock:
            item = self._entries.get(token)
            if item is None or self._now() - item[1] > _TOKEN_LIFETIME_SECONDS:
                self._entries.pop(token, None)
                return None
            return item[0]

    def register(self, uri: str) -> str:
        uri = validate_https_audio_url(uri)
        with self._lock:
            # Bounded in-memory capabilities. Expired entries never persist.
            self._entries = {
                token: item for token, item in self._entries.items()
                if self._now() - item[1] <= _TOKEN_LIFETIME_SECONDS
            }
            if len(self._entries) >= _MAX_REGISTERED_STATIONS:
                raise MediaBackendError("RELAY_FULL", "Radio relay requires cleanup")
            self._start()
            token = secrets.token_hex(32)
            self._entries[token] = (uri, self._now())
            assert self._server is not None
            return f"http://127.0.0.1:{self._server.server_port}/radio/{token}"

    def owns(self, uri: str) -> bool:
        with self._lock:
            if self._server is None or not isinstance(uri, str):
                return False
            prefix = f"http://127.0.0.1:{self._server.server_port}"
            if not uri.startswith(prefix + "/radio/"):
                return False
            return self._resolve(uri[len(prefix):]) is not None

    def revoke(self, uri: str):
        """Release an unused token if MPD rejected its queue addition."""
        with self._lock:
            if not isinstance(uri, str) or not self.owns(uri):
                return
            token = uri.rsplit("/", 1)[-1]
            self._entries.pop(token, None)

    def close(self):
        with self._lock:
            server, thread = self._server, self._thread
            self._server = None
            self._thread = None
            self._entries.clear()
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=2)
