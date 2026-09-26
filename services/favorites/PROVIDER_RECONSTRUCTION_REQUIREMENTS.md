# Favorites provider reconstruction requirements

Status: Team 2 consumer requirements. This document is NOT a semantic identity schema and does not supersede Team 7.

Favorites persists interest. Providers own semantic identity and domain behavior.

For any persistable favorite, Team 2 needs a provider-owned persistent key, reconstruction reference, provider resolver, provider activation path, and resolved provider record.

A provider resolver must distinguish resolved, missing/unavailable, ambiguous, and invalid. Favorites must not convert ambiguity into first-match-wins.

Resolved objects should be normal provider records. Favorites wrappers may add Favorites metadata but must not become a second provider implementation.

After reconstruction, activation routes back through provider/domain behavior. Favorites should not duplicate provider mutations.

Legacy migration is split:
- provider adapter recognizes old identity and proposes old -> new;
- FavoritesService owns replacement, deduplication, ordering and persistence.

This does not authorize AppControlW changes, FAVORITES/COMBI insertion, provider lifetime integration, or navigation/detail/result rewiring.
