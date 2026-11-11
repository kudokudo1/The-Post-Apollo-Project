# Social PHONE // P32 fixed snapshot search and magenta A-Z directory

> Status: GitHub-only review candidate. No live PHONE deployment or Hospital Session registration is claimed.
>
> Patient: \`kudokudo1/The-Post-Apollo-Project\`. Bounded assignment: existing PHONE → CONTACTS / MESSAGES list presentation. External Hospital-compatible development; exact Room and Staff-role assignment unverified.

## IMPLEMENTATION

- \`PhonePane.qml\` presents one fixed search header in the existing left sidebar, anchored **above** both scrolling list views. Contacts and Messages retain independent short, ephemeral search queries. Input text is magenta; cursor orange. No new global menu or popup.
- \`PhoneDirectorySearch.js\` performs **in-memory only** case-insensitive filtering of the approved projection:
  - CONTACTS: display name, organization and currently exposed primary contact value.
  - MESSAGES: conversation display name, nickname and four-line preview source (\`lastMessage\`), **not** every body in conversation history.
- CONTACTS renders a view-only, alphabetically sorted \`ListView\` with magenta A–Z letter headings and a magenta lower border. Non-letter names use \`#\`. Section headings are not selectable and scroll with the entries; the search header does not scroll.
- Existing \`PhoneContactDetail\` selection remains bound to a currently authorized card ID. Changing the search clears the selection. Message search resets the existing conversation selection. No new provider method, message send, call, write, permission, storage, or cross-provider join is introduced.
- Queries clear on view close and active Social identity change. The filtered models are empty whenever approval is absent, the active view was revoked, or the current Personal status is not \`LOCAL_SNAPSHOT\`.
- Preserve four-line message rows, orange/cyan contact colors, star scrollbars, the existing conversation/detail pane, Personal read-only permissions and existing CALLS action confirmation.

## WATCH OUT FOR // The 100-contact limit

This is a search of the **currently loaded** legacy BlueFerry 0.9.1 snapshot, currently bounded to 100 contact rows in the host projection. Search does not fetch another page or search the entire iPhone address book; \`NO MATCHES IN LOADED CONTACTS\` is deliberately distinct from a global "contact not found" claim. Full directory paging and provider-side search remain a separate authorized data-layer assignment. The current \`CONTACTS\` data does not yet provide every email, number label or durable contact ID.

## VERIFY

- Unit test executes pure JS search/section logic with synthetic contacts and conversations: alphabetical and # grouping, case-insensitive queries, search fields, unchanged provider arrays, and stable tie ordering.
- Source contract checks pinned input geometry, independent queries, consent constraints, magenta sections, existing item-selection behavior, and local-only no-match text.
- Existing PHONE tests for contact details, read-only permissions, HFP setup and four-line native Social lists remain in CI.
- Not verified: live Fedora/Quickshell appearance, keyboard input with a narrow sidebar, real private contact data, or completeness beyond the first page.

## HOW TO USE

After separate operator-approved merge and local deployment, open Social → PHONE → CONTACTS or MESSAGES and type into the field pinned above the list. CONTACTS sorts currently loaded rows under magenta letters; MESSAGES keeps provider ordering and four-line previews. Clear the query to restore all currently loaded rows.

## NEXT

Operator review of the draft PR, CI verification, separately approved desktop deployment, and screenshot acceptance. A subsequent provider assignment may add full pagination if a searched person is outside the legacy first page.

## DECISIONS

- No persistent search history or synchronization.
- Do not alter \`ContactList.qml\` shared across other native Social views or the global \`NeonScrollBar\` implementation.
- Search is never treated as new authorization or a durable contact identity. No local host changes were performed.
