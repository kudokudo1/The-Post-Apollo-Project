"""P41b // Exact PHONE Personal metadata edit commitment, in-memory only.

This prepares P37's editHmac field from the *exact* locally proposed change
and all other P37 request fields. The caller supplies a protected in-memory
P35 master key. The master is never returned, stored, fetched or logged.

THIS IS NOT C5 CONSENT, AN IDENTITY GRANT OR A PRODUCTION SAVE HOST.
There is no UI, keyring, CLI, IPC, storage or real provider interaction.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import PhonePersonalContactIdentity as Identity
import PhonePersonalSignedTrustP37 as P37

SCHEMA = "post-apollo.phone.personal-contact-edit-commitment.p41b.v1"
KEY_DOMAIN = b"post-apollo:phone:personal:v1:edit-commitment\x00"
VALUE_DOMAIN = b"post-apollo.phone.p41b.exact-edit\x00"
DRAFT_FIELDS = P37.REQ_FIELDS - {"editHmac"}
MAX_ENCODED = 32 * 1024


class CommitmentRefused(Exception):
    """One fixed refusal; never exposes note, identifier, key or request."""


def _deny() -> None:
    raise CommitmentRefused("PHONE_EDIT_COMMITMENT_REFUSED")


def _strict_action(action: str, local_id: object,
                   favorite: object, note: object) -> bool:
    if action == "LINK":
        # The local UUID is created at link commit, not guessed from a
        # temporary BlueFerry row. Selection is bound by selectedCardHmac.
        return local_id is None and favorite is None and note is None
    if (type(local_id) is not str
            or Identity.LOCAL_ID.fullmatch(local_id) is None):
        return False
    if action == "UNLINK":
        return favorite is None and note is None
    if action == "FAVORITE":
        return type(favorite) is bool and note is None
    if action == "NOTE":
        # Empty string is an explicit note clear, not an omitted edit.
        return (favorite is None and type(note) is str
                and len(note) <= Identity.MAX_NOTE and "\x00" not in note)
    return False


def bind_exact_edit(
    *, master_key: object, request_draft: object,
    local_id: object = None, favorite: object = None, note: object = None,
) -> dict[str, object]:
    """Return a P37-shaped request with a deterministic, secret-keyed editHmac.

    Every permitted request field (including selected card proof, profile,
    owner, session, epoch, revision, challenge, release floor and nonce) and
    the exact edit value are committed. This is a binding, not proof that the
    user approved the edit or that the selected candidate is a real person.
    """
    try:
        if type(master_key) is not bytes or len(master_key) != 32:
            _deny()
        if (type(request_draft) is not dict
                or set(request_draft) != DRAFT_FIELDS):
            _deny()
        # Reuse the exact existing P37 shape validator with a placeholder.
        # No P37 security flags are ever converted into an authorization.
        candidate = {**request_draft, "editHmac": "0" * 64}
        if not P37._valid_request(candidate):
            _deny()
        if not _strict_action(request_draft["action"], local_id, favorite, note):
            _deny()
        frame: dict[str, Any] = {
            "schema": SCHEMA,
            "request": request_draft,
            "localId": local_id,
            "favorite": favorite,
            "note": note,
        }
        raw = json.dumps(
            frame, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        if len(raw) > MAX_ENCODED:
            _deny()
        key = hmac.new(master_key, KEY_DOMAIN, hashlib.sha256).digest()
        digest = hmac.new(key, VALUE_DOMAIN + raw, hashlib.sha256).hexdigest()
        result = {**request_draft, "editHmac": digest}
        if not P37._valid_request(result):
            _deny()
        return result
    except CommitmentRefused:
        raise
    except (KeyError, TypeError, ValueError, UnicodeError,
            OverflowError, RecursionError):
        _deny()


# No main(), production switch, network, filesystem, signer, C5 issuer,
# Secret Service, phone save, P35 commit call or QML entry point.
