# CPU++ DOC 3 // M3b.8 Storage observation, phase A

## Prior evidence and verification

Operator's completed 30s census: Quickshell PID 3049055 reported write
rates 54714.9, 9793.7 and 9862.5 B/s, zero storage reads in all three
returned intervals. Process-level kernel counters do not identify files,
SQL transactions, write syscalls or in-process service ownership.

PR #2535 merged, but exact-head diagnostic workflow 45487472221 failed:
contract job passed; native-continuity job 138776568374 could not load
CpuPlusMemoryActuatorPane.qml because the disposable fixture omitted
CpuPlusZramPolicyPane. This milestone adds the ZRAM pane and policy to
that fixture; native success remains unverified. No DOC 2 runtime edits.

## Fixed catalog from source inspected at main 2b81170a2292843694e099eac8688e986bb512a7

| Owner | Observed source paths / write mechanism |
|---|---|
| Notifications | services/notifications/NotificationsService.qml: history, favorites, policy and scroll files via Quickshell.dataPath; historyDocument() serializes retained history; 1000ms debounce; other saves 250ms |
| Weather | services/weather/WeatherPersistentCacheStore.qml, WeatherLiveHistoryStore.qml, WeatherEventArchiveStore.qml, WeatherPlaceCacheStore.qml, WeatherDossierArchiveStore.qml: fixed Quickshell.dataDir JSON files and setText; queued writes and atomic replacement |
| Hub | services/hub/ApolloHubStore.qml, ApolloHubNotesStore.qml, ApolloHubTodoStore.qml: three fixed JSON files; adapter and explicit document writers |
| Social | services/social/SocialIdentityStore.qml: identity document setText |
| Git | services/git/GitOperationJournalService.qml: journal and delta paths relative to shell |
| Forest | scripts/forest/ui_model_preferences.py: XDG data post-apollo/forest/ui-preferences/model-preferences-v1.json |
| Finance | scripts/finance/banking_manual_store.py: XDG data post-apollo/finance/banking-manual/manual-session.json |
| Company | services/company/CompanyHubDirectory.py: XDG data post-apollo/company/hubs-v1.json |

Eighteen fixed files, not an exhaustive storage inventory. These are
known JSON stores; experimental Tasks SQLite bridge expects an explicit
disposable candidate and is not evidence of production SQLite traffic.
Hospital, broader Finance, Social, Forest databases and any external
engines remain unmeasured. Source triggers do not prove actual workload
or duplicate persistence. Never inspect private payloads.

## Use

CPU++ > SYSTEM > MEMORY > DIAG > STORAGE OBSERVE // 30s.
Close menu, leave desktop idle for baseline, receive completion notice.
Repeat under comparable activity. Load HISTORY and choose completed
storage captures for before/after comparisons.

The external helper uses lstat only at fixed known paths, one baseline
and at most 30 observation intervals, nominal 1s spacing. Reports
cumulative metadata changes every 10 intervals and final completion.
Sample changes in existence, size, modification time or inode do not
count write syscalls or actual disk bytes. Same-size same-mtime writes,
multiple changes within one interval, transient files and other paths may
be missed; create/remove and metadata changes are included. Missing
or inaccessible observations are distinct from observed unchanged.
Final symlinks, foreign-owner and nonregular objects are unavailable.
No file contents, private path strings or inode values emitted. Parent
paths resolve normally; this is not an authorization or tamper boundary.
The observer does not start any other service. Actual elapsed time is
included. Current capture is archived after sampling, not inside it.

## Next

Measure native idle vs interactive captures. Identify frequent changed
targets; review exact service write triggers with their owners. If
needed, add bounded opt-in counters at verified commit points (no
payloads, no periodic writes) to measure real operation counts and
serialized bytes. GPU investigation must coordinate with Forest H4b
rather than duplicate its owner. No storage consolidation approved yet.
