# Social PHONE P17 // Local nickname for an observed iPhone

**Status:** GitHub-only review candidate. No host deployment, BlueFerry configuration changes or live PHONE visual acceptance.

**Patient:** `kudokudo1/The-Post-Apollo-Project`
**Room:** P17 bounded continuation of Social Phone Bridge (Hospital-compatible, live Room/Assignment registration unverified).
**Staff:** External DOC-compatible ChatGPT worker; no independent global Social/Identity owner claim.
**Starting main:** `11786e4a260f2233e6f2cbee8e2bc37a587eba1d`, with P16 PR #1360 merged and no colliding open PHONE PR at preflight.

## IMPLEMENTATION

The existing **Social → PHONE → DEVICE** overlay gets a small **PERSONAL DEVICE LABEL** display and a collapsible **MANAGE PHONE NAME** editor. SAVE NAME is standard green, CLEAR NAME red/destructive, text input magenta with an orange caret. Only an explicitly clicked SAVE or CLEAR writes local display metadata; CONNECT PHONE continues to do a read-only device check.

`services/phone/PhoneNickname.py` accepts `--read <profile_uuid>`, `--save <profile_uuid> <name>` and `--clear <profile_uuid>`. Every command re-observes the configured BlueFerry profile through the previously merged `PhoneDeviceObservation.observe()` and requires a matching **paired** BlueZ device (connected or paired-offline). The write checks the active profile a second time while holding a file lock to refuse an intervening phone change.

Optional names are keyed by BlueFerry's opaque version-4 profile ID, not by a Bluetooth MAC, phone number, account label or organization name. They live in an owner-only, atomic JSON file at `$XDG_STATE_HOME/post-apollo/social-phone-nicknames.json`, or `~/.local/state/post-apollo/social-phone-nicknames.json` if XDG_STATE_HOME is unset. Reading creates no file; only explicit SAVE/CLEAR may create the private storage directory. Existing malformed, public or symlinked storage is refused, not silently replaced. Up to 8 names, 1 to 40 printable characters each. The file does not contain contacts, messages, device addresses or permission tokens.

This is **presentation only**. A local label never grants user/organization ownership, access to a phone line, private content, or carrier call control. The existing P16 Bluetooth display still shows the physical device name and link status separately. Calls/music controls, oFono setup, Stage Director, pairing and the empty message/contact feed remain untouched.

## HOW TO USE

After operator review/merge and separately approved Fedora deployment: open **Social → PHONE → CONNECT PHONE → DEVICE → MANAGE PHONE NAME**. Enter an optional friendly label, then SAVE NAME. CLEAR NAME removes only that label, **not** the Bluetooth pairing or actual BlueFerry device. The existing provider setup is still OPEN IPHONE; it is not a multi-phone selector.

## VERIFY

- New `tests/phone/test_phone_nickname.py` exercises no-write read, save/replace/clear, paired-offline, profile mismatch, unsafe labels and storage, owner-only permissions, symlink refusal, eight-profile cap, and mid-operation device changes.
- New `tests/messaging/test_social_phone_nickname_ui.py` checks the one-button observation flow, explicit edit controls, correct semantics, false-grant refusal and unchanged disabled conversation feed.
- Existing Social PHONE workflow includes both modules/tests. CI and real Fedora rendering are independently checked.
- No actual operator iPhone or host was inspected, modified, paired or renamed.

## WATCH OUT FOR

**BlueFerry upstream currently exposes one active configured iPhone profile, not a verified safe multi-active-phone switching interface.** This P17 increment must not imply that a second connected iPhone can be selected simply by changing a UI label. No arbitrary new pairing wizard is activated by a nickname save. Also the Personal label is UI wording, **not** an Identity Center principal, legal owner, organization grant or trusted content authorization. Same-UID desktop code still needs a security owner to accept the private message/contact release boundary.

The user's working audio remains as-is. Do not assume that installing oFono will synchronize messages or route arbitrary FaceTime/media by application.

## CHECKLIST

- [x] Reconstruct P16 merged state, current main, Syntagma and no active PHONE PR conflict.
- [x] Inspect upstream provider's current one-profile setup.
- [x] Add safe local display names for the verified profile only.
- [x] Keep save and clear explicit, avoid re-pairing.
- [x] Protect state file and reject stale/wrong-device operations.
- [x] Add unit + UI regression tests and CI workflow.
- [ ] Exact-head CI.
- [ ] Operator review and merge approval.
- [ ] Separately approved Fedora/Quickshell runtime test.
- [ ] True multi-device list/switch support, if provider/API verified.
- [ ] Authorized BlueFerry message/contact feed release.
- [ ] oFono/HFP independent host verification.

## NEXT

P18 should address the **actual Social conversation data bridge** under an agreed Identity/Account Broker host owner and verified BlueFerry permission model. Native BlueFerry `ListThreads`, `ListContacts`, and send APIs exist, but provider D-Bus availability alone cannot authorize Social data release. In parallel, investigate genuine provider-supported device inventory/explicit switching, with a non-destructive path for existing pairing. Continue oFono/HFP installer verification separately.

## DECISIONS

Use one existing Social PHONE surface, one primary Connect Phone action, and a collapsible name editor. Preserve network-first per capability, Bluetooth as consented fallback, data protection and operator final acceptance. This PR does not merge or deploy itself. Recovery: close draft PR or revert its bounded commit after a separately authorized merge.
