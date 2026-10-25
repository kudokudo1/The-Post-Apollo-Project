# Social Hub // Provider desktop and web fallback integration

**STATUS //** GitHub draft integration; no operator-desktop activation or live provider authentication  
**SOURCE //** 2026-10-24 operator request to connect Worker B/C native and desktop parts in Social  
**OWNER //** Social shared integration, not the individual provider adapter workers  
**PARENT //** [Adapter Contract v1.0](./ADAPTER-CONTRACT.md)  
**COORDINATION //** issue #733

## What this implements

Select Signal, Viber, WeChat, LINE, KakaoTalk, WhatsApp, Messenger or BeReal
from the *existing* Social selector. The chat region shows a truthful
`ProviderAccessPanel.qml` instead of an empty conversation feed.

- **Signal, Viber:** Read the merged Worker B service adapter's actual
  `UNSUPPORTED` native status. A separate **OPEN DESKTOP CLIENT** control is
  enabled only if `DesktopServiceLauncher.py probe` discovers an installed
  `signal-desktop` / `viber` executable. These are provider-owned desktop
  applications; messages are never extracted into Post-Apollo's native feed.
- **WeChat:** A supported Linux desktop application exists. The panel can
  launch an already-installed `wechat` or `weixin` executable, with no
  native message adapter attached. Installation and QR linking are still
  performed through Tencent's official client.
- **Messenger:** Its former desktop app and `messenger.com` standalone
  website were discontinued. The **OPEN OFFICIAL WEB MESSAGING** button uses
  `https://www.facebook.com/messages/` in an isolated Post-Apollo browser
  profile and the existing Sway managed-window geometry. The merged Messenger
  native `UNSUPPORTED` adapter remains honest.
- **WhatsApp:** The same explicit web button opens
  `https://web.whatsapp.com/` with its own profile and managed window. There
  is no personal-inbox Cloud API. The native adapter is still research-blocked.
- **LINE:** The official Chrome extension supports Linux but is a separate
  install/account linking step. We do not silently side-load it or try to
  masquerade as the extension; this service stays an explanatory panel.
- **KakaoTalk:** No supported Linux-native client or verified native
  personal-inbox adapter was found for this scope. No fake launch action.
- **BeReal:** Mobile-oriented placeholder, no unsupported automation.

The B adapters remain `UNSUPPORTED`, inactive unless their exact Social index
is selected, with no polling, login, transport calls or fabricated messages.
The shared router continues to send *native* messages only through Sessions
(index 0) and Telegram (index 2). The C service states are sourced from the
research gate, not invented adapter files.

## Native desktop behavior

`DesktopServiceLauncher.py probe signal|viber|wechat` is read-only and
returns JSON with `desktopInstalled`, `backendMode: UNSUPPORTED` and
`launched: false`. `open` is initiated only after a direct click, executes
an allowlisted installed binary **without a shell**, reports **launch
requested**, and never reports an authenticated account. It does not install
packages, locate arbitrary user binaries or access app data.

Desktop clients may appear in their own native windows. Unlike Chromium
fallbacks, their windows are **not yet geometrically docked inside the
Social backing surface**: that needs real Sway window-class inspection and
desktop acceptance on the operator's computer. The Social menu itself retains
the status/explanation panel.

## Web fallback behavior

The 21 pre-existing service sites in `XBrowser.py.SITES` remain unchanged.
`WEB_FALLBACK_SITES` adds only `whatsappweb` and `messengerweb` with
separate profiles and Sway window classes. These stay dormant until the user
selects that service and clicks **OPEN OFFICIAL WEB MESSAGING**. The profile is
provider-specific but is **not yet Post-Apollo identity-specific**; the
separately owned Account Manager must implement profile isolation before
multi-identity switching can be considered safe.

Neither native desktop nor web fallback supplies provider-confirmed login
status or extends the adapter's `capabilities` or send success serial.

## Verification and limitations

Offline tests cover native launcher allowlists, no spawn from probes, no
credential or script execution, web URL/profile isolation, Sway class
integration, source routing, and inert Worker B adapters. Existing Social
browser/Session/Telegram tests must remain green. These are source and
mock tests **not** real Sway window / account / login acceptance.

The operator must separately authorize local deployment and account pairing.
Never collect phone codes, passwords, browser cookies, Chromium profiles or
desktop session files in GitHub reports. Stop if any unsupported service is
presented as `READY` native chat, if another provider's conversations appear
under it, or if switching Post-Apollo identities reuses the wrong profile.

### Evidence links (provider-owned)

- Signal Linux: https://signal.org/download/linux/
- Viber Linux/desktop: https://www.viber.com/en/download/
- WeChat Linux: https://linux.weixin.qq.com/
- WhatsApp Web: https://web.whatsapp.com/
- Messenger website fallback: https://www.facebook.com/messages/
- LINE Chrome extension: https://chromewebstore.google.com/detail/line/ophjlpahpchlmihnnnihgmmeilfjmjjc
- KakaoTalk service: https://www.kakaocorp.com/page/service/service/KakaoTalk/?lang=ENG

**No merge, local machine change, native personal-backend certification,
provider login or live Hospital registration is conferred by this document.**
