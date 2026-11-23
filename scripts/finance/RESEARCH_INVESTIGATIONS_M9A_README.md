# FinanceW Research M9a // Memory-only scratch investigations

**PATIENT:** \`The-Post-Apollo-Project\`  
**STAFF ROLE:** External Hospital-compatible Research DOC (not live Hospital registered)  
**ROOM / ASSIGNMENT:** FinanceW Research · scratch case preview when M2 has no saved investigations  
**SCOPE:** Existing M3 InvestigationsPane, M9 candidate Review host, source/Quickshell tests. No shared FinanceW navigation, connection, writer or financial account changes.  
**RELEASE:** Draft GitHub implementation, native operator acceptance pending.

## IMPLEMENTATION

M9a resolves the operator's observed M9 gap: **LOAD CASES** returned zero saved investigations, leaving **PREPARE UNSAVED** unavailable.

Instead of enabling the M2 persistent-writer subsystem or inventing a parallel editor, M9a reuses the original \`FinanceResearchInvestigationsPane.qml\` title/question form:

- **NEW SCRATCH** opens the existing title and research-question fields even if no saved cases are loaded. A bounded **CREATE SCRATCH** action creates one M1-shaped object **only inside the running QML host**: \`schemaVersion:1\`, an ephemeral unique session ID, current UTC timestamp, title, question and an empty evidence list. The form refuses empty/overlong titles and questions and only allows one scratch case at a time.
- The editor's case list includes a clearly labeled **[UNSAVED]** entry. It does not present the scratch as saved or account-backed; the status explicitly says **MEMORY ONLY**.
- **PREPARE UNSAVED** uses the existing M9 read-only Node bridge and M6 \`prepareCandidateAttachDraft\` validation. The case is passed from memory and uses an in-memory revision marker rather than a persisted M2 revision.
- Existing citation title, URL and factual-note fields are populated for review. **ATTACH SOURCE, CREATE CASE and REMOVE SOURCE remain unwired and writer-disabled** via literal \`writeEnabled:false\`.
- **DISCARD SCRATCH**, leaving the case editor, changing source/issuer, or closing FinanceW clears the temporary case and prepared citation. No background retry, automatic saving, SEC fetch or provider call occurs.
- The existing explicit **LOAD CASES** reader continues to work for previously saved cases, without being required for scratch creation.

The temporary case and edits exist only while the corresponding Research review remains open. Do **not** type irreplaceable material into scratch; leaving the view discards it. This milestone does not provide persistence, encryption, backup, authenticated SEC provenance or a secure writer.

## HOW TO USE (after reviewed, authorized merge and local installation)

1. Finance → Research → SEC EDGAR, load the selected issuer's filings.
2. CANDIDATES → BUILD PREVIEW → select an SEC row → **REVIEW IN CASE EDITOR**.
3. Without needing a saved case, select **NEW SCRATCH**, enter a title and research question, then **CREATE SCRATCH**.
4. Select the temporary **[UNSAVED]** investigation (normally auto-selected), then **PREPARE UNSAVED**.
5. Review or edit the citation title, HTTPS source URL and factual note. Nothing is saved.
6. **DISCARD SCRATCH** removes it, or **BACK** leaves the editor and clears it.

The existing case reader remains independently available through **LOAD CASES**. The scratch case is never merged into the stored JSON file.

## VERIFY

- \`tests/finance/test_research_m9a_scratch_contract.py\` checks the original editor wiring, memory-only case lifecycle, compact form, explicit scratch/discard controls and hard writer HOLD.
- The existing M9 draft bridge Node test now validates an M1-shaped temporary investigation at revision 0 and refuses malformed title/question/ID/timestamp/evidence sets, without emitting an executable attach command.
- \`scripts/finance/verify_research_scratch_native_m9a.sh\` launches the actual QML components inside disposable Fedora/Quickshell/Xvfb with **empty XDG research storage**, verifies a synthetic SEC candidate → scratch creation → citation prefill → scratch discard → issuer-change invalidation, checks writer-disabled state and ensures **zero files were created in XDG_DATA_HOME**.
- Existing M9 saved-case native acceptance remains in its own workflow, so scratch does not replace or weaken that path.

This source/CI evidence does not substitute for the operator clicking through actual compact/wide FinanceW on the running desktop.

## WATCH OUT FOR

- M2 persistent-write **HOLD** remains in force. Nothing creates or attaches permanent investigations. Scratch creation is **not** a protected writer operation.
- Candidate citations still describe SEC submissions **index entries**, not content of filings actually inspected. No automatic claims about a company's finances are made.
- Scratch data is volatile and discarded on navigation/source change. An app crash also loses it. The UI labels this explicitly rather than promising preservation.
- Multiple FinanceW workers own neighboring menus; this PR only changes Research-owned editor and host components. GitHub merges, local machine updates and production activation remain operator-controlled.
- Existing diagnostics visual polish stays deferred.

## CHECKLIST / NEXT / DECISIONS

- [x] Inspect source, latest main and case reader; verify the zero-saved-case limitation
- [x] Reuse M3 title/question form and M9 read-only citation bridge
- [x] Create one ephemeral case, with explicit discard and source-change invalidation
- [x] Keep \`writeEnabled:false\`, no writer callbacks
- [x] Add Node, QML contract and empty-XDG native smoke
- [ ] Exact-head CI and actual native smoke
- [ ] FinanceW compatibility review and operator-authorized merge
- [ ] Operator desktop scratch-and-citation interaction acceptance

No claim of live Hospital registration, local workstation modifications, production writes, or final operator acceptance.
