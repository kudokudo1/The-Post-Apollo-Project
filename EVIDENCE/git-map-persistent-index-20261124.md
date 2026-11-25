# DOC 3 G3a // Explicit full-history map integration

G1 #2566 and G2 #2567 merged, 5/5 exact-head workflows each.
Main preflight 83473371e9ee9f02de88db5a0a28982a686732a1; no open PRs
at preflight. Operator reported live installation, not native acceptance
of a full map (G1/G2 did not mount one). External Hospital-compatible DOC 3.

## Use after review, merge and explicit live apply

GitW > GIT > CONTROL > RECENT / FULL MAP / BUILD INDEX / OPEN // TOP.
RECENT is default. FULL MAP looks up matching local repository cache
without creating a file. BUILD INDEX explicitly creates a derived index
if missing, otherwise reuses it. OPEN // TOP explicitly adopts a completed
index; no silent jump when a new generation arrives. RECHECK compares
current local tip/shallow fingerprint. Returning from RECENT to an already
opened snapshot retains its position. A new index may be prepared while
the old snapshot is visible. While hidden no new page requests start
(one outstanding read may finish). No startup lookup/build.

The new 40px controls/status strip is confined to the Git control map;
legacy BranchMap remains mounted and is the fallback. Branches page
unchanged. GitW uses selected local repoPath, not delayed refresh repoRoot.
Repo epochs reject obsolete receipts including switch-away-and-back.
No mutation of Git data, journal, Undo or recovery.

## Cache

XDG_CACHE_HOME/post-apollo-git-map-v1 (fallback ~/.cache).
Private directory per common Git directory identity, fingerprint of
captured tip set plus shallow status and shallow boundary file digest.
Immutable index generations, nonblocking cooperative per-repo lock,
fresh candidate staging then rename and fsync. Lookup does not create
cache directories or traverse commit history. BUILD only by explicit
request; 120s timeout, lookup 20s; no periodic process. Existing matching
generation returned without rebuilding. Eight generation/staging entries
per repository; no automatic deletion, eviction, global byte quota or
cleanup UI yet. Failed staging may count toward cap. Cache is plaintext
derived display metadata, not authoritative evidence. Parent XDG path
trusted same-user; not a security boundary against same-UID modifications.
Git refs may change after lookup; map is explicitly frozen until recheck.
Initial full traversal may fail for very large or complex repositories.

## Verification

Tests: actual temporary Git repo, read-only missing lookup, matching
generation reuse without traversal, changed-tip new generation preserving
old, cap refusal, incomplete/symlink refusal, shallow deepen key change.
Native host fixture checks no startup work, hidden request rejection,
explicit lookup/build, hidden result does not adopt, explicit open,
RECENT fallback, same-session reopen, matching recheck. G1/G2 contracts
and native scrolling fixture rerun. CI pending, no live test performed.
Full GitW runtime integration, visual parity and actual performance
remain unverified. New generations require explicit OPEN // TOP in this
phase; exact SHA anchor adoption, search, incremental maintenance,
cleanup/quotas and broader Branches map integration follow later.
