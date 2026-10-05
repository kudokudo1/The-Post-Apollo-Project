# Git / GitHub Evidence Contract

> STATE // active
>
> OWNER // Doc 3 — Git / Automation
>
> CONSUMER // Hospital surgery / certification lane

## Boundary

Git and GitHub report factual repository and automation state.

Hospital decides what those facts mean.

PX performs GitHub-facing operations.

This contract must not emit or infer Hospital policy states such as CANDIDATE,
VERIFIED, CERTIFIED, or IN MAIN.

## Provider

QML type:

`services/github/GitEvidenceProvider.qml`

Injected dependencies:

- `gitService` — `GitService`
- `githubService` — `GitHubService`

Current packet schema:

`schemaVersion: 1`

Provider identity:

`post-apollo.git-evidence`

## Request API

### Evidence for an exact commit

`requestEvidence(sha, "")`

Refreshes local Git state, refreshes normal GitHub telemetry, performs an exact-SHA
Actions run query, then emits `requestFinished(packet)`.

### Evidence for an exact commit and exact run

`requestEvidence(sha, runId)`

Performs the same exact-SHA request and also uses the shared GitHub run inspector
for the requested run. The finished packet can therefore include jobs, steps and
logs without Hospital owning another inspector implementation.

Only a run returned for the requested SHA is eligible for deep inspection.

### Snapshot only

`capture(sha)`

Builds a packet from currently loaded state without causing refresh/query work.
This is useful for display and diagnostics, but certification should normally use
the request API when fresh evidence is required.

## Exact identity

`GitService.head` remains the short display SHA.

`GitService.headFull` is the full commit identity used for provenance.

PX `runs` now returns `headSha`, and supports an optional exact SHA filter:

`px runs <repo> [limit] [sha]`

The evidence provider compares full local and GitHub SHAs. It does not certify
based on branch-name equality or short-SHA prefixes.

## Packet shape

Top-level fields currently include:

- `schemaVersion`
- `provider`
- `capturedAt`
- `target`
- `localGit`
- `facts`
- `github`
- `completeness`
- `request` for request-driven packets

### target

Factual requested identity:

- repository
- repoRoot
- origin
- branch at capture
- exact SHA

### localGit

Local repository facts:

- availability
- refresh state
- full HEAD at capture
- whether HEAD equals the requested SHA
- worktree
- upstream
- ahead / behind
- provider error

### github

Remote evidence:

- availability
- workflow inventory
- exact-SHA matching runs
- optional inspected run
- jobs
- steps
- logs
- provider error

### facts

Derived factual summaries only:

- whether requested SHA is the current local HEAD
- whether the worktree is dirty
- run status/conclusion counts
- staleness relationships between target SHA, local HEAD, exact run query and
  inspected run

These are observations, not certification decisions.

### completeness

Describes whether evidence exists and whether collection was complete:

- repository known
- target SHA known
- local HEAD known
- GitHub available
- exact run query completed for the requested SHA
- matching run count
- inspected run included
- inspector busy/error
- request error

Hospital may use these fields as inputs to its own policy.

## Workflow procedures

`WorkflowLibraryStore.qml` exposes saved workflow sets as named procedures.

Backend API:

- `procedureByName(name)`
- `procedures()`
- `runProcedure(name)`

A normalized procedure contains:

- schemaVersion
- repository
- name
- workflowCount
- missingCount
- runnable
- workflows[] with path, name and current availability

A procedure is an automation order. Successful execution is evidence; it is not
itself certification.

## Shared inspector rule

`RunInspectorDrawer.qml` remains a presentation surface.

The reusable evidence data comes from `GitHubService` and
`GitEvidenceProvider`.

Hospital should not parse the drawer or duplicate its GitHub queries.

## Canonical implementation status

Taskbars:

The Git/GitHub evidence provider and its service dependencies are integrated on
the repository's canonical `main` line. Historical Doc 3 feature branches are
not authoritative runtime baselines.

PX:

Canonical repository:

`kudokudo1/The-Post-Apollo-Dev-Exp`

The exact-SHA run contract is merged to PX `main`. PX now supports:

`px runs <repo> [limit] [sha]`

When `sha` is supplied, PX forwards it to GitHub Actions as an exact commit
filter and includes `headSha` in returned run summaries.

The exact-SHA restoration landed through PX merge commit:

`00d8016159c1304c3a7b313bd7ecfd6355488a3f`

Regression coverage for the run contract landed on PX `main` through:

`5b0e7f26e6ecd63f049273b3a3c68847af5c0013`

The PX smoke workflow now exercises the exact-SHA run contract on `main` and
pull requests.

Runtime note:

Taskbars invokes PX through `$HOME/.local/bin/px`. A workstation must have an
installed PX copy synchronized with canonical PX `main` for the exact-SHA
runtime behavior described by this contract.

## Deliberately outside this contract

Doc 3 does not decide:

- candidate state
- verification requirements
- certification requirements
- host-slot authority
- merge authorization
- post-op acceptance
- evidence retention policy

Those remain Hospital / certification responsibilities.
