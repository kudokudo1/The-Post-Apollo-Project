"""Social PHONE P43: strict untrusted editor intent at a future host boundary.

This parser is NOT an installed host, C5 consent checker, Secret Service
adapter, challenge issuer, or public save endpoint.  It only shapes a user's
unsaved UI edit for an independent protected host to reconsider from fresh
BlueFerry and encrypted-vault state.  No authorization bits accepted.
"""
from __future__ import annotations

from dataclasses import dataclass

import PhonePersonalContactIdentity as Identity

SCHEMA = "post-apollo.phone.personal-editor-intent.p43.v1"
ACTIONS = frozenset(("LINK", "UNLINK", "FAVORITE", "NOTE"))
BASE_FIELDS = frozenset(("schema", "action", "selectedContactId"))
MAX_SELECTOR = 256


class EditorIntentRefused(Exception):
    """Refuse without accidentally disclosing a private edit or selected row."""


def _deny() -> None:
    raise EditorIntentRefused("PHONE_EDITOR_INTENT_REFUSED")


@dataclass(frozen=True, slots=True, repr=False)
class StagedEditorIntent:
    """Ephemeral, untrusted input. NOT a C5 receipt or save approval."""

    action: str
    selected_contact_id: str
    favorite: bool | None = None
    note: str | None = None

    def __repr__(self) -> str:
        # Never display a private note or ephemeral selected row in diagnostics.
        return "<StagedEditorIntent UNSAVED_UNTRUSTED>"


def parse_untrusted_editor_intent(payload: object) -> StagedEditorIntent:
    """Accept one exact untrusted UI gesture, never a grant or trusted identity.

    A genuine host must independently re-resolve the current provider snapshot
    and stable local link, validate current revision, obtain one-use C5 intent,
    construct P41b editHmac under its own key, and enforce a protected commit
    lease.  This parser does NONE of that work.
    """
    try:
        if type(payload) is not dict:
            _deny()
        action = payload.get("action")
        if type(action) is not str or action not in ACTIONS:
            _deny()
        expected = BASE_FIELDS
        if action == "FAVORITE":
            expected = expected | {"favorite"}
        elif action == "NOTE":
            expected = expected | {"note"}
        if set(payload) != expected or payload.get("schema") != SCHEMA:
            _deny()
        selected = payload["selectedContactId"]
        if (type(selected) is not str or not 0 < len(selected) <= MAX_SELECTOR
                or any(ord(char) < 0x21 or ord(char) > 0x7e
                       for char in selected)):
            _deny()
        if action == "FAVORITE":
            favorite = payload["favorite"]
            if type(favorite) is not bool:
                _deny()
            return StagedEditorIntent(action, selected, favorite=favorite)
        if action == "NOTE":
            note = payload["note"]
            if (type(note) is not str or len(note) > Identity.MAX_NOTE
                    or "\x00" in note):
                _deny()
            # Reject lone surrogates and other malformed unencodable text.
            note.encode("utf-8", errors="strict")
            return StagedEditorIntent(action, selected, note=note)
        return StagedEditorIntent(action, selected)
    except EditorIntentRefused:
        raise
    except (KeyError, TypeError, ValueError, UnicodeError, OverflowError):
        _deny()


# No main, socket, IPC, filesystem, save, provider/phone edit, keyring or log.
