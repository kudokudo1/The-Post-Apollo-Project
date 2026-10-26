# BeReal desktop/personal-message integration feasibility

**Status:** BLOCKED / RESEARCH.

**Reviewed:** 2026-10-26.

BeReal's current public material confirms that the service has chat data, but
the supported product experience remains app-oriented. No official desktop
client, web personal inbox, or public developer messaging API was verified.

Official references:

- https://bereal.com/
- https://bereal.com/privacy
- https://bereal.com/community-standards

BeReal's September 2026 Community Standards explicitly prohibit automated
accounts/bots and coordinated automated behavior. Post-Apollo must therefore
not use private mobile endpoints, reverse-engineered sessions, emulators,
credential capture, or UI automation to manufacture a desktop messenger.

## Post-Apollo decision

No `BeRealAdapter.qml` should be created without a provider-supported
personal-account interface. Opening the public marketing website would not
provide account chat functionality and would be a decorative launcher rather
than a connection, so the Social slot stays an explicit mobile/provider
blocker.

Revisit only if BeReal publishes a supported desktop/web personal-account
client or developer messaging interface whose terms permit this use.
