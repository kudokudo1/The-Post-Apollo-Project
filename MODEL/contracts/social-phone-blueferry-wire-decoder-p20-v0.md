# Social PHONE P20 // BlueFerry D-Bus string decoding fix

> **STATE:** Isolated GitHub review change only. No local machine mutation, no Bluetooth/audio/pairing operations, no real iPhone content accessed.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`. **ROOM:** Social PHONE Personal read pilot / BlueFerry provider wire decoding. **PROVIDER:** OPEN AI // CHATGPT, external Hospital-compatible, no verified live Hospital room, staff role or attached assignment. **BASE:** `main` at `25add6078cb968982eb60992f67b53252da09d46`, PR #1396 merged.

## IMPLEMENTATION

User screenshot evidence on 2026-11-06 shows a paired/connected iPhone, BlueFerry MAP and PBAP **session reported active**, notifications of real SMS events, but zero Social conversations and contact cards. Screenshot message "Approve access in the new terminal, then select LOAD PERSONAL" does not demonstrate completed manual opt-in or a successful provider data read. BlueFerry notifications are a distinct event channel: they do not automatically supply the `ListThreads` or `ListContactCards` snapshot to the Social adapter.

A source-level defect was found in `services/phone/BlueFerryHostReadPort.py`: `UniqueOwnerBlueFerrySource._json` required `type(raw) is str`. **Python D-Bus method returns of signature `s` are ordinarily `dbus.String` (a subclass of `str`)**, so the guard rejects valid provider responses **before** the JSON is decoded. This can turn an actual read into `PROVIDER_UNAVAILABLE` or `READ_UNAVAILABLE` while fake tests that return built-in `str` pass.

Use `isinstance(raw, str)` instead, retaining byte-length bounds, JSON parsing, exact expected JSON object/list shape, bound unique D-Bus owner and profile checks, operation guard and release gating. Do **not** coerce arbitrary nontext objects with `str(raw)`. A new regression test wraps the fake `GetStatus`, `ListThreads` and `ListContactCards` results in a `str` subclass and separately rejects `bytes`, unrelated objects with deceptive `__str__`, overlong strings and wrong JSON shapes.

## HOW TO USE

After operator approval, merge and normal desktop update, the Personal read-only pilot still requires **PHONE → MESSAGES or CONTACTS → APPROVE READ**, typed terminal consent `ALLOW PERSONAL IPHONE READ`, explicit choice of message/contact capability, and **LOAD PERSONAL** within the 10-minute window. Clicking APPROVE READ merely requests the terminal: it does not confirm that consent was granted. If no terminal appears, check whether the `foot` terminal launched/was hidden before changing Bluetooth pairing.

To separate sources of failure **without exposing private content**, check the PHONE status text after `LOAD PERSONAL`. A `NOT_ACTIVE` state means the opt-in host is absent or no longer valid. `NOT_CONSENTED` means the current capability was not selected. `READ_UNAVAILABLE` means the BlueFerry read was refused/failed or the source content did not pass conversion. An empty validated snapshot means BlueFerry currently supplied no threads/cards. Do not share SMS bodies, phone numbers, contacts, profile IDs, tokens or private config values in logs.

## VERIFY

- Synthetic regression tests exercise `dbus.String`-like subclass wire responses through the real provider read source.
- Existing offline BlueFerry converter, Personal pilot, PHONE UI, calling and audio regressions remain in existing CI.
- Exact-head GitHub checks must pass before review. No physical iPhone, local Fedora, live Quickshell or BlueFerry daemon was inspected in this source fix.

## WATCH OUT FOR

**Not yet confirmed:** the installed BlueFerry version supports the contact-card API. In the screenshot, PBAP reports active but contact cache count is **not reported**. The read port requires valid `contact_card_epoch` and `contact_card_count`, so contacts can still refuse until the actual provider reports those fields. Similarly, MAP active is not proof a populated history is present. Notifications can exist with no discoverable thread history, and iMessage support may be provider/iOS-limited.

This fix does not grant phone data access or upgrade the Personal pilot to a production authenticated Identity Center/Account Broker host. The same-UID socket threat model and local-only purge limitations remain.

## CHECKLIST

- [x] Inspect user's DEVICE, MESSAGES, CONTACTS and notification screenshots.
- [x] Confirm PR #1396 merged and current GitHub ownership/HEAD.
- [x] Confirm D-Bus `dbus.String` inheritance using upstream library documentation.
- [x] Fix exact-type rejection and add tests that reproduce the real wire form.
- [ ] Exact-head CI.
- [ ] Operator review/merge and separately authorized desktop update.
- [ ] Complete manual Personal opt-in and verify live MAP/PBAP snapshot behavior.
- [ ] Address any additional provider API/consent issue using content-free diagnostics.

## NEXT

Review and merge the isolated patch under operator authority. Then reproduce Personal read on the live Fedora machine: confirm that a visible consent terminal remains running, `LOAD PERSONAL` reaches `SNAPSHOT`, and real iPhone threads/cards are returned in the existing PHONE UI. If `NOT_ACTIVE` persists, investigate native `foot` launch and socket lifecycle; if `READ_UNAVAILABLE`, diagnose the provider's API/status without leaking private data; if `SNAPSHOT` has empty arrays, investigate actual iPhone provider MAP/PBAP dataset availability. Preserve working A2DP and independent oFono/HFP calls.

## DECISIONS

No direct notification-to-chat shortcut: a notification event can be repeated, incomplete, out of order or duplicated and does not satisfy a historical conversation/contacts contract. This PR changes **only** the verified BlueFerry D-Bus string compatibility defect and tests, no automatic permission, no media/audio change, no merge, no production activation. Roll back by closing the draft PR or reverting its single commit if later merged.
