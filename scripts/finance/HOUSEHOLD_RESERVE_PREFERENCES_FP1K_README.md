# FinanceW FP1k // Persisted manual reserve-cushion preference

## Status and scope

Source-only FP1k development from application main after PR #2110 (FP1j)
merged. The operator previously approved the FP1i interface, not an
independent financial security review, host installation, or permission
to merge/activate FP1k.

FP1k adds an **optional persisted UI preference per existing local
planning context**. It stores only the selected 100%, 110% or 125%
reserve-cushion percentage. There are no stored account numbers,
transaction records, financial balances, secret tokens, actual money
transfers, provider calls, or edits to the FP1a–j plan/schedule stores.

Five labels (\`mine\`, \`shared\`, \`mom\`, \`granny\`, \`family\`) remain
accessible to the same Unix user. This preference **does not authenticate
household members or grant any financial-data permissions**.

## Operator path after review and authorized installation

Finance → STRATEGIES → PLANS → TIMELINE:

1. Select a context and ensure the local preference reports READY.
   Initially, the UI uses 100% until the selected context's saved
   preference is independently loaded; the context name must match.
   If storage fails, the UI continues to show only a default preview,
   with save and cushion choices disabled rather than guessing.
2. Preview the **100% / 110% / 125%** reserve strategy. The selection
   does **not** save any file.
3. Choose **SAVE FOR [CONTEXT]** explicitly to persist this percentage
   under the current context only. The button is enabled only when
   the preview differs from the loaded saved value. The guarded Python
   writer checks the expected revision under a per-context lock.
4. To return to the default, choose **RESET SAVED TO 100%**, then
   **CONFIRM RESET 100%**. This is a deliberate revisioned write;
   it does not delete files or alter any budget/planning records.
5. **REFRESH SAVED** re-reads the current local preference. Switching
   context resets the preview to 100% immediately, then loads only the
   stored value for that context. A late result from another context
   is refused. All settings remain local to one Linux login.

Selection buttons follow the existing Post-Apollo ActionButton
hover/click behavior. No new shared button types or global settings
were invented.

## Format, security, and recovery

Storage:
\`$XDG_DATA_HOME/post-apollo/finance/household-reserve-preferences/<context>.json\`
(or XDG fallback under the operator's home directory).

Minimal schema v1:

    {"version":1,"contextId":"mine","revision":1,"marginPercent":110}

- No file or directory is created on a missing-file read. A missing
  preference always returns revision 0, 100% by default.
- Explicit SAVE and RESET are the **only writes**. Unknown commands,
  invalid percentages (including bool, strings and floats), forged
  contexts, arbitrary fields, stale revisions, unsafe permissions,
  symlinks, malformed JSON and unknown future schema refuse.
- Directory 0700; document/lock/temp files 0600. Read via nofollow
  fd with bounded size and regular-file/owner checks. Writes take an
  advisory lock, create exclusive nofollow temp files, fsync, atomically
  replace and fsync the directory.
- A concurrent or stale writer fails without silently overwriting the
  current value. UI reports an unavailable preference and requests a
  refresh rather than falling back to a fabricated persisted value.
- Back up this minimal file if preserving a saved UI preference across
  code rollback matters. Rolling back to FP1j will simply not load
  FP1k's separate preference file; it does not need to alter the
  prior FP1g/FP1h v3/v4 schedule database.
- The previous v3/v4 schedule rollback requirement still applies
  separately; do not delete or convert it automatically.

The file is owner-only **plaintext**, not encrypted. Separate Unix user
identities or a future verified Hospital/Connections identity gate would
require a new, independently approved security contract.

## Financial semantics unchanged

FP1j's pure \`FinanceHouseholdReservePolicy.js\` remains unchanged.
All existing income, goal, bill, charge, exception, deferral and
sinking-fund math retain the same behavior. The preference merely
selects which of those existing in-memory scenarios is displayed.
No local money, bank money or actual reserve is set aside. A modeled
unreserved change is **not verified available cash**.

## Verification

python3 tests/finance/test_household_reserve_preferences_fp1k.py
python3 tests/finance/test_household_reserve_preferences_fp1k_contracts.py
node tests/finance/test_household_reserve_cushion_fp1j.mjs
node tests/finance/test_household_reserves_fp1i.mjs

All inherited FinanceW FP1a–j, protected Actual and Market CI must
remain green at exact commit. Native Quickshell UI acceptance, crash
recovery and interprocess context-switch testing are not established
by source-only CI and require separate verification and operator approval.

## Scope boundaries

Do not merge this source branch or change desktop application files
without the operator's scoped authorization. Do not use this preference
store as a substitute for verified per-member household permissions.
