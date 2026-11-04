# Social Organization Manager / Semantic Action Colors v1

PATIENT // kudokudo1/The-Post-Apollo-Project
PROVIDER // OPEN AI // CHATGPT, external Hospital-compatible, no verified live Room, Role or Assignment
SCOPE // Operator-authorized Organization Settings color pass only; user will later choose exact hues/glow and pixel harmonization
STATE // Draft PR; source tests and operator live acceptance separate

## IMPLEMENTATION

The operator uses area plus **semantic control color** to navigate without reading every label. Existing CYAN-everywhere text, button borders, and fields made direct manipulation difficult. Preserve existing one-page Organizations menu and exact button width, height, type size and click behavior. **Do not edit the shared components/ActionButton.qml or components/Colors.qml** and avoid affecting unrelated Post-Apollo widgets.

Add IdentityCenterLocalActionButton.qml, a local subclass of the *existing* ActionButton. Its only new input is role, which sets idle/hover/pressed/selected foreground, translucent fill, borders, and existing glow properties; it adds no handlers or dimensions.

Local roles:
- Danger **RED**: remove from portfolio, unlink, clear search/session, Restore's still-locked danger affordance.
- Refresh **GREEN**: reload directory, refresh all seven stores, validate a backup, and confirm positive results.
- Manage **YELLOW**: save/rename, archive, show archived, create backup.
- Primary **ORANGE**: create organization/portfolio/unit/branch, apply modifier, focus a chosen company record.
- Navigation **BLUE**: choose organization/branch/modifier context, search scopes, list backups, show events.
- Neutral **WHITE**: passive backup filename selection and background labels.
- Immediate intentional pressed/selected/focused controls **MAGENTA**: selected button outline/fill/glow, pressed action (except intentionally RED destructive press), and actively editable text input borders/translucent fills/selection highlights.

Section headings now vary by function (orange Directory/Modifier, white Portfolio/History, blue Search/Structure, yellow Save/Backup, green Refresh). Status text is green for confirmed success, yellow for saving, red for failed, and neutral for informational output. Keep the text labels, explicit status and safe disabled states so color is not the sole meaning. All typed inputs retain the original width, height, maximum length, validation and storage binding.

The new local component reuses ActionButton's existing soft/wide glow, 0.16 hover-fill transparency, pressed/selected states and existing disabled alpha. Global theme values, geometry and animation timings remain operator-adjustable in a later approved design pass. This phase applies the semantic roles only.

## HOW TO USE

After operator-authorized merge and separately approved desktop code update: Social → USER → SETTINGS → ORGANIZATIONS. Read color first: green for Refresh/Validate, yellow Save/Archive/Back Up, red Remove/Clear, orange Add/Apply, blue selectors and white passive controls. Currently selected or actively typed controls become magenta. No changes to where a button leads or the original record stores.

## VERIFY

Dedicated static contracts confirm all 47 original editor buttons plus two inline edit-context selectors use local roles, no modifications to shared theme, 10 focused text inputs, explicit Restore locked state and original Save/Refresh/Backups/History structure. Genuine offscreen Qt6 Settings test confirms real instantiated button role/accent values, selected magenta state, input focus style and that original workflows still load. Existing 1–7 control regressions and native Quickshell smoke workflows rerun.

## WATCH OUT FOR

This is a local style pass only. Global Post-Apollo color or pixel normalization, exact shade selection and glow fine-tuning remain separate operator decisions. Do not imply buttons have been manually visually accepted: only Backup Now/List/Validate were operator-tested. Nothing about color affects revision conflicts, duplicate-click locks, restore safety, private records or verified Identity Center grants.

## CHECKLIST

- [x] Verify Activity PR #1185 merged, current main, Syntagma rules and absence of competing Social editor PR
- [x] Inspect original ActionButton styles and all in-page actions
- [x] Apply local semantic roles, text focus and status colors without resizing
- [x] Preserve all original action handlers and source-store contracts
- [x] Add exact source and genuine Qt testing
- [ ] Exact-head GitHub CI green
- [ ] Operator review/merge
- [ ] Live visual acceptance deferred to operator

## NEXT

Review the resulting live page when operator chooses, adjust hues/glows selectively with evidence. A later wider Post-Apollo color treatment must coordinate other component owners; this PR does not silently style globally. Multi-file Restore remains locked until separately reviewed transaction safety.

## DECISIONS

One semantic language, applied only to Social Organizations. No global theme changes, different sizes, new menus, new backend writes or auth permissions. Magenta denotes direct focus/selection and press; it is not a bypass of safety confirmations.


---

## REFINEMENT v1.1 // operator clarification, 2026-11-04

This section supersedes only the conflicting visual behavior described earlier in v1. All record-operation, geometry, backend and permission decisions are preserved.

1. **Already open/selected controls keep the original shared ActionButton open-state rules**. The Organizations-local wrapper no longer overrides selected or keyboard-selected fill, border, foreground, content glow or wide glow. The base component remains the canonical source of these states. The underlying selected state is *not* recolored to magenta merely for being open.
2. **Add and + buttons are magenta** in their ordinary idle role. In particular, `+ ORGANIZATION`, `+ BRANCH`, `+ PORTFOLIO`, `+ ADD UNIT`, and the `+ <organization>` portfolio-association buttons now use local role `add` (magenta). This overrides v1's orange role only for these five creation/add controls. Other primary Apply/Focus actions remain orange.
3. **User-entered text is magenta**, even when not focused, in the ten existing editable Organizations TextInput controls. The **insertion cursor is orange** via the QtQuick TextInput `cursorDelegate`; its appearance does not change the typed text color or input size. Focused field border/translucent fill remains magenta and idle border blue.
4. **Direct press remains magenta** for non-destructive buttons (red for destructive ones). An open-state and a press-state are different: being open is not a new press.

Both the shared `components/ActionButton.qml` and `components/Colors.qml` remain untouched. No button dimensions, action handlers, saved records, Restore lock, or Quickshell session are changed.

**Verification:** dedicated contract checks confirm all five magenta Add buttons, all ten magenta text/orange cursor delegates, no local selected-state override; offscreen Qt tests check instantiated Add role/accent, inherited selected colors, typed text color, cursor delegate existence, and focus. Live visual acceptance is deferred unless separately confirmed by the operator.

**Hospital checkpoint:** Patient `kudokudo1/The-Post-Apollo-Project`, external ChatGPT worker, live Room/Assignment unverified. Preserve the earlier user-confirmed Backup Now / List / Validate passes and all other deferred tests. Merge and desktop update remain operator-owned.
