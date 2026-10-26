# LINE for Chrome provider access

**Status:** provider-owned personal-account UI path, not a native Post-Apollo message adapter.

Post-Apollo uses LINE's official Chrome extension as the supported Linux access
surface. LY Corporation's current Help Center documents LINE for Chrome as a PC
option, including QR login from the user's main LINE device. The current Chrome
Web Store extension id is:

```text
ophjlpahpchlmihnnnihgmmeilfjmjjc
```

Official references:

- https://help.line.me/line/android/?contentId=50001182
- https://chromewebstore.google.com/detail/line/ophjlpahpchlmihnnnihgmmeilfjmjjc

## Post-Apollo behavior

1. LINE remains outside `SocialMessageRouter`; Post-Apollo does not read,
   normalize, scrape, or send LINE messages.
2. The Provider Access panel offers **SET UP LINE FOR CHROME**.
3. Setup opens the official Chrome Web Store listing in a dedicated
   `linechrome-browser` user-data directory. Post-Apollo does not download,
   side-load, or auto-approve the extension.
4. **CHECK LINE FOR CHROME** only checks whether the official extension id is
   installed under that isolated browser profile. It does not read cookies,
   account state, chat content, or credentials.
5. **OPEN LINE FOR CHROME** launches the extension's own
   `chrome-extension://.../index.html#popout` UI in an XWayland window class
   owned by the existing Social browser geometry system.
6. LINE itself owns QR/login/session state. The setup browser should be closed
   after installation before launching the managed LINE window, so Chromium
   starts the app surface with the intended Social window class.

## Security boundary

The extension profile is provider-scoped, not yet Post-Apollo-identity-scoped.
Do not claim identity switching until the Social Account Manager owns separate
per-identity browser profiles. No local installation or live login occurs from
this repository change.
