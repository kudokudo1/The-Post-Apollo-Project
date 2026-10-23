# Social Email // read-only account inventory prototype

GitHub Issue #603. **Not installed, registered or activated.** This prototype
does not add an Email mode in QML and does not read message bodies or send mail.

## Proposed data path

Thunderbird MailExtension (`extension/`) -> native messaging host
(`EmailAccountHost.py`) -> user-only JSON snapshot at
`$XDG_STATE_HOME/post-apollo/social-email/accounts.json`
(default `~/.local/state/post-apollo/social-email/accounts.json`).

The host writes through an atomic replacement and enforces mode 0600 on the
snapshot and 0700 on its immediate directory. Thunderbird retains ownership of
credentials and provider synchronization. The extension asks for
`accountsRead` and `nativeMessaging` only.

## Later operator-approved setup

1. Verify installed Thunderbird version and the extension API / background
   lifetime behavior against that actual build.
2. Package `extension/` as a MailExtension and install in Thunderbird.
3. Register a native-messaging host named `post_apollo_social_email` using
   Thunderbird's documented native messaging host manifest location. The host
   manifest must point to an executable wrapper for `EmailAccountHost.py` and
   authorize only `social-email-bridge@post-apollo.local`.
4. Verify an account snapshot with a throwaway/test mailbox, and then read it
   through a separately developed read-only Quickshell adapter.
5. Only after that prototype works should email mode UI work start.

No installer is provided intentionally. Registering the host or extension
would mutate the operator's local machine and needs separate explicit approval.

## Constraints

- No credentials, messages, message bodies or attachment data in snapshot.
- Do not assume `accounts.list()` returns folders uniformly across Thunderbird
  versions or mail providers. Validate against live API results first.
- The snapshot describes the most recent successful read and is not a live
  connection-health signal; any UI must label stale data as such.
- No mailbox API mutation or send permission.
- Confirm local native-messaging host location, Flatpak sandbox access and
  executable resolution before any deployment.
- Discover, X and existing Session/Discord code remain unchanged.

## Rollback

Since this is repository-only, discard the feature branch or close its draft
PR. No local runtime state is created by repository commits.
