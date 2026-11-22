✦︎✦︎✦︎ Meta Apollo Logos //

# FINANCEW // BANKING PROVIDER WORKSPACES & UNIFIED FINANCE

> **STATE // PROPOSED architecture and worker-continuity plan, documented at operator request, 2026-11-22.**
>
> **OWNER //** FinanceW Banking domain, `The-Post-Apollo-Project`.
>
> **AUTHORITY //** Operator chooses the final product design and implementation scope. This record preserves the discussion and intended direction; it does **not** authorize code changes to other Rooms, bank connections, credential collection, financial transactions, migrations, merges or host activation.
>
> **PROVENANCE //** Operator's Banking menu/icon request and subsequent discussion on whether Banking should host full Cash App/Chime/PayPal experiences, provider screens and a combined Post-Apollo view. Relevant source milestones: [Banking M1 PR #2174](../../pull/2174) and [bounded CSV picker M2 PR #2179](../../pull/2179) (use absolute GitHub URLs below for review; check current merge states).
>
> **STAFF //** Existing FinanceW Banking & Transfers lane, Hospital-compatible external DOC. No live Hospital Room/Assignment registration asserted.

## 1 // PRODUCT INTENT

**One unified Post-Apollo Banking control center plus a separate Post-Apollo-native workspace for each supported financial provider, then a detail page for each actual account or product.** The intent is to make existing providers usable from Post-Apollo, not to create a pooled or custodial Post-Apollo bank account and not merely to display a collection of links or balance cards.

Provider workspaces should reproduce useful functionality and fit the established Post-Apollo visual and interaction grammar, as far as authorized integration allows. They do **not** need to run the original mobile app binaries or imitate restricted proprietary code. When official provider capabilities are unavailable, show an honest state and a deliberate official-app/web handoff, not a nonfunctional payment/trade/loan button.

Use existing FinanceW chassis, `ActionButton`, `ModeButton`, shared text/scroll/keyboard primitives and in-place work area. Maintain resize continuity and avoid new unmanaged external windows. Keep the operator-selected **BANKING** as the **first main-menu item**, glyph **`₊˚⋆🏛⊹`** exactly.

## 2 // NAVIGATION MODEL

```text
FINANCE
  └── ₊˚⋆🏛⊹ BANKING
       ├── HOME / ALL ACCOUNTS
       │    ├── combined, correctly sourced financial overview
       │    ├── spending and cross-account transfer review
       │    ├── provider connection/status and alerts
       │    └── transfer workflow (only where allowed)
       ├── PROVIDERS
       │    ├── Cash App workspace
       │    ├── Chime workspace
       │    ├── PayPal workspace
       │    └── additional banks and supported services
       └── INDIVIDUAL ACCOUNT / PRODUCT
            ├── checking, savings, wallet/balance
            ├── payment or debit card
            ├── brokerage/portfolio (if offered and connected)
            └── debt/loan obligations (if offered and connected)
```

**Three scopes must remain distinct:** (1) universal summary, (2) provider workspace, (3) account/product details. A provider may have multiple accounts/products and people may have multiple separate provider logins. Never substitute a display label for verified account identity, ownership or authorization.

### Cash App example workspace, not a promise of API availability

- **Home / Money:** available balance, recent activity, deposits/withdrawals and funding paths.
- **Payments:** send/receive requests and transfer guidance.
- **Card:** Cash App Card status and controls, only where a supported API actually authorizes changes.
- **Stocks:** positions, holdings, research and market context; trading actions are a separately permissioned brokerage operation, not a feature enabled by transaction-read access.
- **Borrow:** information about eligible borrowing products, due dates, obligations and planning. Loan application/repayment actions depend on supported licensed endpoints and account eligibility.
- **Savings:** relevant savings features or reporting when available, never invented balances.
- **Activity:** posted/pending transactions, deduplication, transfer classification and audit provenance.
- **Security / Settings:** provider status and consent inspection, without copying credentials into FinanceW.

Chime and PayPal get their **own** appropriate product structures; do not mechanically copy all Cash App features to them. For example, Chime may have separate checking and savings details, while PayPal may have wallet and payment products. Treat product availability and integration capabilities as dynamic, per-region, per-account and versioned.

## 3 // HOW REAL FUNCTIONS CAN WORK

**Three capability modes, visible per screen and action:**

1. **POST-APOLLO NATIVE + AUTHORIZED:** FinanceW renders data or invokes an action using an explicitly scoped, vetted provider integration, after identity/consent checks and permission gates.
2. **OFFICIAL PROVIDER HANDOFF:** the button explains what will happen and opens the real provider app/site for unavailable or restricted operations. Never imply Post-Apollo executed a transfer/trade/card action when it merely handed off.
3. **SIMULATION / MANUAL:** synthetic accounts and explicitly manual data while real connections are unavailable. Fake balances and demo transactions must be unmistakably marked; manually entered transactions are not provider-verified.

A provider's *read* connection does **not** grant *money movement*, *stock trading*, *loan origination*, *card administration*, or *credential access*. Merchant checkout/payout APIs are not assumed to provide consumer P2P APIs. **Each capability must be verified with current provider documentation and separate consent/authorization before implementation.** No scraping login pages, passwords, bypassing MFA, covert automation of consumer apps or undocumented transfer methods.

## 4 // SHARED FINANCEW INTEROPERABILITY

A unified home may combine data returned from independently authorized provider adapters, but retains the original provider/account/product identity, timestamp, currency, connection status, permission source and freshness for each record.

- **Balance totals:** separate cash and cash-like balances from liabilities, credit availability and investment value. Exclude duplicate representations of the same funds and clearly mark incomplete/stale feeds.
- **Transfers:** recognize paired debit and credit events across **owned/authorized accounts**, respecting posting delays, fees, reversals, mismatches and ambiguous matches. Do not count a transfer as spending only after an evidenced/user-confirmed classification. Never infer income simply from a credit.
- **Stocks / Market:** a provider's holdings can feed the universal stock portfolio/research view without handing market research permission to a trading service.
- **Budget / Strategies / Plans:** provider transactions and debt obligations can inform the universal money-planning tools only with clear data lineage and approved linkage; retain existing functional ownership.
- **Accounts:** canonical account IDs and granular product IDs remain separate from display names, provider keys and profile scopes. No implicit consolidation across family members or business entities.

Any user-specific or household data must remain under **real** identity/permissions, not a UI-only `mom`, `shared` or other label. The user's mother's accounts require her explicit consent and the relevant provider authorization. A profile switch does not itself grant access or transaction rights. Reuse the Universal Connections and Identity/Permissions owners rather than implementing another provider credential store inside Banking.

## 5 // PHASES & PARALLEL OWNERSHIP

| Stage | Goal | Owner / boundary | Completion evidence |
| --- | --- | --- | --- |
| **M1 / M2** | Existing first-menu Banking, fictional transfer guidance, CSV paste/import, and local CSV picker | Banking only | Source on application `main` observed 2026-11-22; CI history in PRs #2174/#2179. **Native UI or user acceptance does not follow from source presence.** |
| **M3: account manager** | One-person, explicit demo/manual accounts, provider tiles, per-account detail, editable manual transaction entry, review/undo | Banking; no connections/profile writes | CI + native Quickshell navigation and resize tests; no false "connected" state |
| **M4: provider workspaces** | Cash App, Chime, PayPal mini-app screens with independent product sections (money/card/stocks/borrow/etc. as applicable), capability status and reversible official handoff | Banking UI; coordinate Stocks, Budget, Strategies owners | UI/contract tests for empty, fictional, unsupported, stale and revoked capabilities |
| **M5: read-only real connections** | Provider authorization, consent, account discovery, balances and supported transaction access | **Universal Connections + Sign-In/Profile/Permissions owners** supply the security layer; Banking consumes approved adapter interfaces | Real eligible provider authorization, provenance, revocation and disconnect tests; no write authority |
| **M6: money actions** | Authorized transfer initiation where a permitted payment rail truly exists; official-app fallback elsewhere | Separate protected permissions + payment executor; requires operator assignment and financial/security review | Explicit source/target/amount/fees/ETA, consent, replay/refusal, audit, actual provider confirmation; never mark success on handoff |
| **M7: cross-product integration** | Reconcile universal spending, holdings, liabilities and family/organization switching | Coordinated cross-Room work, possibly mass surgery | End-to-end permission-isolated tests, user acceptance and recovery |

Stages can progress in parallel only when files, contracts, owners and authority do not collide. Prefer useful manual/simulated screens **now**, without waiting for the entire Identity/Connections implementation. Do not pre-build a privileged bank connection just because a UI mock exists.

## 6 // CURRENT SOURCE ANCHORS / RECOVERY

**Patient:** `kudokudo1/The-Post-Apollo-Project`. Recheck `main`, open PRs, merge status, exact HEAD and current Hospital assignments before doing anything. Snapshot descriptions below are **not** claims of live runtime installation.

- `widgets/FinanceW.qml` — first BANKING main-mode entry and Banking pane mounting.
- `widgets/FinanceBankingPane.qml` — Banking transfer/import workspace; local file-selection lifecycle.
- `widgets/FinanceTransferGuidePane.qml` and `widgets/FinanceTransferGuidePolicy.js` — offline provider guidance and fictional cases.
- `widgets/FinanceBankingImportPolicy.js` — manual CSV parsing and conservative cross-account reconciliation policy.
- `scripts/finance/banking_csv_reader.py` — bounded read-only, local CSV selection. **Not a bank connector or data store.**
- `tests/finance/test_banking_import_m1.mjs`, `tests/finance/test_banking_file_picker_m2.py` and related source-contract tests.
- **History:** [Banking M1 PR #2174](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2174), [CSV picker M2 PR #2179](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2179).
- **Neighbor contracts:** [Social + PostWallet account/org management roadmap](./social-postwallet-management-connectivity-roadmap-v0.md) and the working [Syntagma rules](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/AGENTS.md). These remain independently owned; this Banking document is not their approval or replacement.

As of 2026-11-22, application `main` contains the M1/M2 file paths. Prior M1 12/12 and M2 4/4 GitHub workflow checkpoints were reported. The exact live desktop deployment, tested dialog interaction, provider APIs, security/custody arrangements, and final operator acceptance are **not independently established by this document**.

## 7 // WATCH OUT FOR / UNRESOLVED DECISIONS

- Which providers and actual product capabilities offer documented, authorized read/write APIs? Verify current official terms individually before assigning real tasks.
- Should the provider workspace use a fixed provider-specific inner navigation rail, dynamic tabs, or an existing specialized pane? Choose after live chassis/resize inspection.
- How should manual statements be stored securely, if at all? No assumption of safe durable storage, encryption, backup or family sharing.
- What normalized domain schemas and freshness/settlement semantics will avoid counting the same dollars twice?
- What status is appropriate for a disabled/unsupported operation? Prefer clearly stated unsupported/handoff over a simulated action disguised as live.
- How will read-only financial data from multiple providers be scoped to real persons/business entities? Obtain Identity/Connections owner contracts before integration.
- Real card controls, lending, brokerage and money movement are **high-authority, separate product scopes**; do not infer authorization from view-only banking connections.

## 8 // HANDOFF TO NEXT BANKING WORKER

**Role on recovery:** ordinary external DOC unless the operator/live Hospital assigns a different role. **Do not claim live Room registration.**

1. Read [Syntagma AGENTS](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/AGENTS.md), Hospital Agent/Report protocols, and current assignment/permissions.
2. Reconcile the **Patient, Room, Assignment, owners, PRs, branch/head, CI, host state and latest checkpoints**. Check other workers' active STRATEGIES, Universal Connections and Sign-In/Profile lanes.
3. Treat this roadmap as **proposed future architecture**, preserving the user's requested three-level model and exact Banking icon without treating every feature as approved or feasible.
4. The next safe Banking milestone is **M3 manual/demo account management with provider/account/product navigation**, using fictional examples and no provider calls. Draft and test in isolation, then request native verification and operator acceptance.
5. Report meaningful boundaries using **IMPLEMENTATION, HOW TO USE, VERIFY, WATCH OUT FOR, CHECKLIST, NEXT, DECISIONS**. Keep GitHub code/CI, live desktop, and Hospital assignment evidence separate. Do not merge or activate without authorization.

**DECISIONS //** Documentation and requested future direction recorded, not executed. The complete provider-workspace design and integration details remain **PROPOSED** until accepted in the appropriate assignment and security review.
