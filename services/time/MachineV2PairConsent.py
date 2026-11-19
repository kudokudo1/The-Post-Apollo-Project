"""MACHINE V2 external pairing + operator consent *verification*, CI-only.

Cryptographic admission is not proof of a real installed issuer, browser
identity, logind seat, trusted UI, or production execution permission. Keys
MUST be pinned by independent owner-controlled native services in a later
separately reviewed integration. This module contains no signing key,
signing function, environment-sourced trust key, Sway IPC or CLI.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid
from urllib.parse import quote

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from MachineV2GeometryJournal import (
    _safe_directory, _safe_file, _create_file, _summary,
)

PAIR_SCHEMA = "post-apollo.timew.external-window-pairing.v1"
CONSENT_SCHEMA = "post-apollo.timew.external-one-use-consent.v1"
AUDIENCE = "timew-machine-v2-disposable-floating-v1"
ACTION = "one-floating-window-size-and-position"
PAIR_DOMAIN = b"post-apollo.timew.pairing-proof.v1\x00"
CONSENT_DOMAIN = b"post-apollo.timew.consent-grant.v1\x00"
MAX_LEASE_MS = 10000
MAX_VALUE_BYTES = 4096
MAX_CLOCK_MS = 9007199254740991
MAX_FIELD = 128
SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
SIGNATURE = re.compile(r"[A-Za-z0-9_-]{86}\Z", re.ASCII)
PAIR_FIELDS = frozenset((
    "schema", "audience", "pair_id", "checkpoint_id", "window_key",
    "live_con_id", "app_id", "workspace", "output", "session_id",
    "browser_window_ref", "issued_ms", "expires_ms",
))
CONSENT_FIELDS = frozenset((
    "schema", "audience", "grant_id", "pair_sha256", "intent_sha256",
    "seat_id", "session_id", "issued_ms", "expires_ms",
    "single_use", "approved_action",
))
INTENT_FIELDS = frozenset((
    "checkpoint_id", "window_key", "live_con_id", "app_id",
    "output", "workspace", "before_rect", "target_rect", "session_id",
))
SPEND_NAME = "v2-one-use-consent-spends.db"


class AdmissionRefused(ValueError):
    pass


def refuse():
    raise AdmissionRefused("V2 PAIRING OR CONSENT REFUSED")


def _uuid(value, *, version=None):
    if not isinstance(value, str):
        refuse()
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        refuse()
    if str(parsed) != value or (version is not None and parsed.version != version):
        refuse()
    return value


def _field(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= MAX_FIELD
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)):
        refuse()
    return value


def _ms(value):
    if type(value) is not int or not 0 <= value <= MAX_CLOCK_MS:
        refuse()
    return value


def _period(payload, now_ms):
    issued, expires = _ms(payload["issued_ms"]), _ms(payload["expires_ms"])
    if (expires <= issued or expires - issued > MAX_LEASE_MS
            or not issued <= now_ms < expires):
        refuse()
    return issued, expires


def _json(obj):
    try:
        raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, allow_nan=False,
                         separators=(",", ":")).encode("ascii")
    except (ValueError, TypeError, UnicodeError):
        refuse()
    if len(raw) > MAX_VALUE_BYTES:
        refuse()
    return raw


def _digest(obj):
    return hashlib.sha256(_json(obj)).hexdigest()


def _verify(envelope, key, domain):
    if not isinstance(envelope, dict) or set(envelope) != {"payload", "signature"}:
        refuse()
    if not isinstance(key, Ed25519PublicKey):
        refuse()
    payload, signature = envelope["payload"], envelope["signature"]
    if (not isinstance(payload, dict) or not isinstance(signature, str)
            or SIGNATURE.fullmatch(signature) is None):
        refuse()
    try:
        sig = base64.urlsafe_b64decode(signature + "==")
        if len(sig) != 64 or base64.urlsafe_b64encode(sig).decode().rstrip("=") != signature:
            refuse()
        key.verify(sig, domain + _json(payload))
    except (ValueError, TypeError, InvalidSignature):
        refuse()
    return payload


def _intent(value):
    if not isinstance(value, dict) or set(value) != INTENT_FIELDS:
        refuse()
    core = {k: value[k] for k in (
        "checkpoint_id", "window_key", "app_id", "live_con_id",
        "before_rect", "target_rect")}
    try:
        core = _summary(core)
    except ValueError:
        refuse()
    return {
        **core, "output": _field(value["output"]),
        "workspace": _field(value["workspace"]),
        "session_id": _uuid(value["session_id"], version=4),
    }


def verify_pair_and_consent(*, pairing, consent, intent, pair_key,
                            consent_key, expected_session_id, expected_seat_id,
                            now_ms):
    """Only validate *externally* produced signed statements.

    A valid Ed25519 signature authenticates possession of a key, not that its
    issuer actually checked a Brave process or received user consent.
    Caller must separately pin independent production provenance, not present.
    """
    now_ms = _ms(now_ms)
    session_id = _uuid(expected_session_id, version=4)
    seat_id = _field(expected_seat_id)
    if not isinstance(pair_key, Ed25519PublicKey) or not isinstance(consent_key, Ed25519PublicKey):
        refuse()
    pair_pub = pair_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    consent_pub = consent_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    if hmac.compare_digest(pair_pub, consent_pub):
        refuse()

    plan = _intent(intent)
    if plan["session_id"] != session_id:
        refuse()
    pair = _verify(pairing, pair_key, PAIR_DOMAIN)
    if set(pair) != PAIR_FIELDS or pair["schema"] != PAIR_SCHEMA or pair["audience"] != AUDIENCE:
        refuse()
    _uuid(pair["pair_id"], version=4)
    _uuid(pair["browser_window_ref"], version=4)
    _uuid(pair["checkpoint_id"], version=4)
    _uuid(pair["window_key"])
    _uuid(pair["session_id"], version=4)
    if (type(pair["live_con_id"]) is not int
            or not 0 < pair["live_con_id"] <= 9007199254740991):
        refuse()
    _field(pair["app_id"])
    _field(pair["workspace"])
    _field(pair["output"])
    first_issued, first_expires = _period(pair, now_ms)
    if (pair["session_id"] != session_id
            or any(pair[k] != plan[k] for k in (
                "checkpoint_id", "window_key", "live_con_id",
                "app_id", "workspace", "output"))):
        refuse()

    approval = _verify(consent, consent_key, CONSENT_DOMAIN)
    if (set(approval) != CONSENT_FIELDS or approval["schema"] != CONSENT_SCHEMA
            or approval["audience"] != AUDIENCE
            or approval["single_use"] is not True
            or approval["approved_action"] != ACTION):
        refuse()
    _uuid(approval["grant_id"], version=4)
    _uuid(approval["session_id"], version=4)
    if SHA.fullmatch(str(approval["pair_sha256"])) is None or SHA.fullmatch(str(approval["intent_sha256"])) is None:
        refuse()
    second_issued, second_expires = _period(approval, now_ms)
    if (second_issued < first_issued or second_expires > first_expires
            or approval["seat_id"] != seat_id
            or approval["session_id"] != session_id
            or not hmac.compare_digest(approval["pair_sha256"], _digest(pair))
            or not hmac.compare_digest(approval["intent_sha256"], _digest(plan))):
        refuse()
    return {
        "grant_id": approval["grant_id"],
        "pair_sha256": _digest(pair),
        "intent_sha256": _digest(plan),
        "expires_ms": second_expires,
        "production_authorized": False,
        "persistent_brave_identity_verified": False,
        "browser_tabs_restorable": False,
        "requires_independent_issuer_provenance": True,
    }


def suggested_spend_path():
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    root = Path(xdg).expanduser() if xdg else Path.home() / ".local/share"
    return root / "post-apollo" / "machine" / SPEND_NAME


class OneUseSpendLedger:
    """Write-once per grant/pair/intent; a crash after spend burns permission.

    A future service must separately protect this path from a same-UID
    attacker, pin the two external issuer keys, and enforce a trusted seat.
    This class has no replay, clearing, issuance or authorization API.
    """

    def __init__(self, path):
        if not isinstance(path, (str, Path)):
            refuse()
        self.path = Path(path).expanduser()
        if (not self.path.is_absolute() or self.path.name != SPEND_NAME
                or self.path.parent.name != "machine"
                or self.path.parent.parent.name != "post-apollo"):
            refuse()

    def _connect(self, *, writable):
        if not writable and not self.path.exists() and not self.path.is_symlink():
            return None
        db = None
        try:
            _safe_directory(self.path.parent, create=writable)
            if writable:
                _create_file(self.path)
            elif not _safe_file(self.path):
                return None
            db = (sqlite3.connect(str(self.path), timeout=5.0)
                  if writable else sqlite3.connect(
                      "file:" + quote(str(self.path), safe="/") + "?mode=ro",
                      uri=True, timeout=5.0))
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("PRAGMA foreign_keys=ON")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in ((0, 1) if writable else (1,)):
                refuse()
            if writable:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute("PRAGMA synchronous=FULL")
                db.execute("BEGIN IMMEDIATE")
                try:
                    db.execute("""CREATE TABLE IF NOT EXISTS spends (
                        grant_id TEXT PRIMARY KEY,
                        pair_sha256 TEXT NOT NULL UNIQUE,
                        intent_sha256 TEXT NOT NULL UNIQUE,
                        spent_ms INTEGER NOT NULL
                    )""")
                    db.execute("PRAGMA user_version=1")
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
            else:
                db.execute("PRAGMA query_only=ON")
            return db
        except (OSError, ValueError, sqlite3.Error):
            if db is not None:
                db.close()
            refuse()

    def spend(self, verified, *, now_ms):
        """Durably spend prior to any geometry journal or Sway command."""
        if (not isinstance(verified, dict)
                or set(verified) != {
                    "grant_id", "pair_sha256", "intent_sha256", "expires_ms",
                    "production_authorized", "persistent_brave_identity_verified",
                    "browser_tabs_restorable", "requires_independent_issuer_provenance"}
                or verified["production_authorized"] is not False
                or verified["persistent_brave_identity_verified"] is not False
                or verified["browser_tabs_restorable"] is not False
                or verified["requires_independent_issuer_provenance"] is not True):
            refuse()
        grant_id = _uuid(verified["grant_id"], version=4)
        for field in ("pair_sha256", "intent_sha256"):
            value = verified[field]
            if not isinstance(value, str) or SHA.fullmatch(value) is None:
                refuse()
        now_ms = _ms(now_ms)
        if now_ms >= _ms(verified["expires_ms"]):
            refuse()
        db = self._connect(writable=True)
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""INSERT INTO spends
                (grant_id, pair_sha256, intent_sha256, spent_ms)
                VALUES (?,?,?,?)""",
                (grant_id, verified["pair_sha256"], verified["intent_sha256"], now_ms))
            db.commit()
        except (sqlite3.Error, ValueError):
            db.rollback()
            refuse()
        finally:
            db.close()
        return grant_id

    def lookup(self, grant_id):
        grant_id = _uuid(grant_id, version=4)
        db = self._connect(writable=False)
        if db is None:
            return None
        try:
            row = db.execute("""SELECT grant_id,pair_sha256,intent_sha256,spent_ms
                                FROM spends WHERE grant_id=?""", (grant_id,)).fetchone()
            return None if row is None else {
                "grant_id": _uuid(row["grant_id"], version=4),
                "pair_sha256": row["pair_sha256"],
                "intent_sha256": row["intent_sha256"],
                "spent_ms": row["spent_ms"],
                "spent": True,
                "replay_allowed": False,
                "production_authorized": False,
            }
        except (sqlite3.Error, ValueError):
            refuse()
        finally:
            db.close()
