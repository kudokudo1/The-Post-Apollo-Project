"""P34: pure fail-closed matching and private-metadata policy for PHONE contacts.

NO IO, no host auth, no key storage, no public persistence and no executable
CLI. A trusted future Personal vault supplies a >=32-byte secret, verifies
contacts.read on the *current* device/profile/session, and encrypts notes.
This policy intentionally never creates a durable identity from a BlueFerry
legacy-row-N or modern daemon-epoch ID. A digest is only a *candidate match*,
not evidence of a real person and not permission to access private notes.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import json
import re
import unicodedata
import uuid

SCHEMA = "post-apollo.phone.personal-contact-metadata.v0"
VERSION = 0
MAX_BINDINGS = 512
MAX_NOTE = 4096
MAX_DOCUMENT = 1024 * 1024
PROFILE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
PHONE = re.compile(r"^\+?[0-9 ()-]{3,32}$")
DIGITS = re.compile(r"^\+?[0-9]{3,18}$")
EMAIL = re.compile(r"^[^\s@\x00-\x1f\x7f]+@[^\s@\x00-\x1f\x7f]+$")
HEX = re.compile(r"^[a-f0-9]{64}$")
LOCAL_ID = re.compile(r"^[a-f0-9]{32}$")


def _refuse(reason: str = "INVALID") -> dict[str, object]:
    # No names, addresses, contact IDs, note bodies, secrets or digests
    # are included in failures or errors that could reach a public log.
    return {"ok": False, "reason": reason}


def empty_document() -> dict[str, object]:
    return {"schema": SCHEMA, "version": VERSION, "revision": 0, "entries": []}


def valid_document(document: object) -> bool:
    """Strict in-memory document shape. NOT permission to write plaintext."""
    if type(document) is not dict or set(document) != {
        "schema", "version", "revision", "entries"
    } or document["schema"] != SCHEMA or type(document["version"]) is not int \
            or document["version"] != VERSION:
        return False
    rev, entries = document["revision"], document["entries"]
    if type(rev) is not int or rev < 0 or rev >= 2**53 \
            or type(entries) is not list or len(entries) > MAX_BINDINGS:
        return False
    seen_ids: set[str] = set()
    seen_matches: set[tuple[str, str]] = set()
    for row in entries:
        if type(row) is not dict or set(row) != {
            "localId", "profileId", "matchProof", "favorite", "note"
        }:
            return False
        local = row["localId"]
        profile = row["profileId"]
        proof = row["matchProof"]
        note = row["note"]
        if (type(local) is not str or not LOCAL_ID.fullmatch(local)
                or type(profile) is not str or not PROFILE.fullmatch(profile)
                or type(proof) is not str or not HEX.fullmatch(proof)
                or type(row["favorite"]) is not bool
                or type(note) is not str or len(note) > MAX_NOTE
                or any(ord(c) == 0 for c in note)
                or local in seen_ids or (profile, proof) in seen_matches):
            return False
        seen_ids.add(local)
        seen_matches.add((profile, proof))
    # This limit is enforced even for a future encrypted-store integration.
    return len(json.dumps(document, ensure_ascii=False)) <= MAX_DOCUMENT


def _normalized_phone(value: object) -> str | None:
    if type(value) is not str or not PHONE.fullmatch(value):
        return None
    compact = re.sub(r"[ ()-]", "", value)
    return compact if DIGITS.fullmatch(compact) else None


def _normalized_email(value: object) -> str | None:
    if type(value) is not str or not 3 <= len(value) <= 254 \
            or not EMAIL.fullmatch(value):
        return None
    local, domain = value.rsplit("@", 1)
    if not local or not domain or domain.startswith(".") or domain.endswith("."):
        return None
    # Preserve the local part's case rather than risk merging accounts that
    # a provider considers distinct; only domains are case-insensitive.
    return local + "@" + domain.lower()


def _address_proof(card: object, profile: str, secret: bytes) -> str | None:
    if (type(profile) is not str or not PROFILE.fullmatch(profile)
            or type(secret) is not bytes or len(secret) < 32
            or type(card) is not dict or card.get("serviceId") != "blueferry"
            or card.get("deviceProfileId") != profile
            or card.get("hasAddressDetails") is not True):
        return None
    name = card.get("displayNameInProfile")
    phones = card.get("phoneNumbers")
    emails = card.get("emailAddresses")
    if (type(name) is not str or not name.strip() or len(name) > 256
            or type(phones) is not list or type(emails) is not list
            or len(phones) > 64 or len(emails) > 64
            or type(card.get("phoneCount")) is not int
            or type(card.get("emailCount")) is not int
            or card["phoneCount"] != len(phones)
            or card["emailCount"] != len(emails)):
        return None
    normalized_name = " ".join(unicodedata.normalize("NFC", name).split()).casefold()
    if not normalized_name:
        return None
    numbers = [_normalized_phone(value) for value in phones]
    addresses = [_normalized_email(value) for value in emails]
    if any(x is None for x in numbers + addresses):
        return None
    # Prevent hidden duplicate-row merges or partial normalization.
    if len(set(numbers)) != len(numbers) or len(set(addresses)) != len(addresses):
        return None
    if not numbers and not addresses:
        return None
    material = json.dumps({
        "kind": "CONTACT_MATCH_CANDIDATE_V1",
        "profileId": profile,
        "name": normalized_name,
        "phoneNumbers": sorted(numbers),
        "emailAddresses": sorted(addresses),
    }, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hmac.new(secret, material, hashlib.sha256).hexdigest()


def assess(card: object, cards: object, profile: str,
           secret: bytes) -> dict[str, object]:
    """One snapshot. An HMAC candidate is never an authenticated person ID."""
    proof = _address_proof(card, profile, secret)
    if proof is None:
        return _refuse("NO_UNAMBIGUOUS_ADDRESS")
    if type(cards) is not list or len(cards) > 100:
        return _refuse("INVALID_SNAPSHOT")
    equal = 0
    for other in cards:
        if _address_proof(other, profile, secret) == proof:
            equal += 1
            if equal > 1:
                return _refuse("AMBIGUOUS_CONTACT")
    if equal != 1:
        return _refuse("NOT_IN_CURRENT_SNAPSHOT")
    return {"ok": True, "matchProof": proof}


def resolve(document: object, card: object, cards: object, profile: str,
            secret: bytes) -> dict[str, object]:
    """Find an explicitly linked local record, no private note is returned."""
    if not valid_document(document):
        return _refuse("INVALID_DOCUMENT")
    matched = assess(card, cards, profile, secret)
    if matched.get("ok") is not True:
        return matched
    for entry in document["entries"]:
        if entry["profileId"] == profile and hmac.compare_digest(
            entry["matchProof"], matched["matchProof"]
        ):
            return {"ok": True, "status": "LINKED", "localId": entry["localId"]}
    return {"ok": True, "status": "NOT_LINKED"}


def link(document: object, card: object, cards: object, profile: str,
         secret: bytes, *, user_confirmed: bool,
         create_id=uuid.uuid4) -> dict[str, object]:
    """Requires a deliberate bind action. The caller must separately prove
    a current Personal grant and place the result only in an encrypted vault.
    """
    if user_confirmed is not True:
        return _refuse("CONFIRMATION_REQUIRED")
    if not valid_document(document):
        return _refuse("INVALID_DOCUMENT")
    result = resolve(document, card, cards, profile, secret)
    if result.get("ok") is not True:
        return result
    if result["status"] == "LINKED":
        return _refuse("ALREADY_LINKED")
    if len(document["entries"]) >= MAX_BINDINGS or document["revision"] >= 2**53 - 2:
        return _refuse("CAPACITY_REACHED")
    try:
        new_id = create_id().hex
    except Exception:
        return _refuse("IDENTITY_UNAVAILABLE")
    if type(new_id) is not str or not LOCAL_ID.fullmatch(new_id) \
            or any(item["localId"] == new_id for item in document["entries"]):
        return _refuse("IDENTITY_COLLISION")
    proof = assess(card, cards, profile, secret)["matchProof"]
    next_document = deepcopy(document)
    next_document["revision"] += 1
    next_document["entries"].append({
        "localId": new_id, "profileId": profile, "matchProof": proof,
        "favorite": False, "note": ""
    })
    if not valid_document(next_document):
        return _refuse("CAPACITY_REACHED")
    return {"ok": True, "localId": new_id, "document": next_document}


def edit(document: object, local_id: str, expected_revision: int,
         *, favorite: bool | None = None, note: str | None = None,
         user_confirmed: bool) -> dict[str, object]:
    """Pure, revision-checked mutation, NEVER persistence or provider write."""
    if user_confirmed is not True:
        return _refuse("CONFIRMATION_REQUIRED")
    if not valid_document(document) or type(expected_revision) is not int \
            or expected_revision != document["revision"]:
        return _refuse("STALE_OR_INVALID_DOCUMENT")
    if type(local_id) is not str or not LOCAL_ID.fullmatch(local_id):
        return _refuse("INVALID_LOCAL_ID")
    if (favorite is None and note is None
            or favorite is not None and type(favorite) is not bool
            or note is not None and (type(note) is not str or len(note) > MAX_NOTE
                                     or "\x00" in note)):
        return _refuse("INVALID_EDIT")
    next_document = deepcopy(document)
    for row in next_document["entries"]:
        if row["localId"] != local_id:
            continue
        if favorite is not None:
            row["favorite"] = favorite
        if note is not None:
            row["note"] = note
        if row == next(item for item in document["entries"]
                       if item["localId"] == local_id):
            return {"ok": True, "changed": False, "document": document}
        next_document["revision"] += 1
        if not valid_document(next_document):
            return _refuse("CAPACITY_REACHED")
        return {"ok": True, "changed": True, "document": next_document}
    return _refuse("NOT_LINKED")


def unlink(document: object, local_id: str, expected_revision: int,
           *, user_confirmed: bool) -> dict[str, object]:
    """Forget a local binding/notes only after explicit deletion confirmation."""
    if user_confirmed is not True:
        return _refuse("CONFIRMATION_REQUIRED")
    if not valid_document(document) or type(expected_revision) is not int \
            or expected_revision != document["revision"]:
        return _refuse("STALE_OR_INVALID_DOCUMENT")
    if type(local_id) is not str or not LOCAL_ID.fullmatch(local_id):
        return _refuse("INVALID_LOCAL_ID")
    next_document = deepcopy(document)
    original = len(next_document["entries"])
    next_document["entries"] = [
        row for row in next_document["entries"] if row["localId"] != local_id
    ]
    if len(next_document["entries"]) == original:
        return _refuse("NOT_LINKED")
    next_document["revision"] += 1
    if not valid_document(next_document):
        return _refuse("CAPACITY_REACHED")
    return {"ok": True, "document": next_document}
