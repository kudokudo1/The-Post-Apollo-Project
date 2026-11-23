# Finance Research // M2 crash and stranded-lock recovery

**Status: operator-only recovery procedure, not an automated recovery implementation.**
M2 is not connected to the FinanceW interface. Apply these instructions only if a reviewed local installation later uses the store. An apparently stale lock **must not** be discarded automatically.

## Why the lock can remain
A writer creates `investigations.lock` exclusively before reading a revision and making an atomic JSON replacement. On ordinary exit, it removes the lock. If the writer is forcibly terminated between creation and removal, the file remains, and future writes refuse with `WRITE_BUSY`. The JSON record might contain the **old** revision or the **new** revision. A successful file rename does not imply the caller saw confirmation.

## Read-only diagnosis
Run in a **private host terminal**, not in a public issue/CI log. Do not paste research records into chats.

```sh
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
case "$data_home" in /*) ;; *) data_home="$HOME/.local/share";; esac
research_dir="$data_home/post-apollo/finance/research-investigations"
stat -c '%F %a %U %n' -- "$research_dir" "$research_dir/investigations.lock"
pgrep -af '[r]esearch_investigation_store[.]mjs' || true
fuser -- "$research_dir/investigations.lock" 2>/dev/null || true
printf '{"action":"list"}\n' | node scripts/finance/research_investigation_store.mjs |
  python3 -c 'import json,sys; x=sys.stdin.read(); prefix="FINANCE_RESEARCH_STORE_RESULT "; assert x.startswith(prefix); d=json.loads(x[len(prefix):]); print("revision",d["revision"],"cases",len(d["investigations"]))'
```

The `list` action is read-only and leaves storage unchanged. If it reports corruption or unsafe permissions, **stop**: do not manufacture an empty record or overwrite the original file.

## Operator recovery gate
Only after all of these are independently established:

1. Research storage writing is disabled. No open Quickshell controller, pending command, helper, or second user session can write the same directory.
2. The lock is a regular, user-owned, non-symlink file with owner-only permissions. The directory is private (0700) and contains no suspicious entries.
3. There is no running research store process or open writer, including a suspended process or another login session. `pgrep`/`fuser` are useful clues, **not proof of absence**.
4. The current JSON document passes the store's read-only validation. Its revision and investigation/evidence counts are recorded privately.
5. The operator approves **one manual recovery**, based on the observed state. A reviewer verifies the ambiguity of the previous operation has been resolved to the extent possible.

The operator may then **quarantine** the old lock rather than deleting it. The following is an illustrative command to be run only after the gates above; it is **not executed by FinanceW**:

```sh
mv -n -- "$research_dir/investigations.lock" \
  "$research_dir/investigations.lock.recovered-$(date -u +%Y%m%dT%H%M%SZ)"
```

Read the document again with `list`, compare the revision with the recorded value, and re-open the interface only if the state is consistent. Never auto-retry the interrupted `create`, `attach`, or `remove` action. If the revision advanced, the mutation **may already be committed**. If it did not, inspect the record and decide manually whether to initiate a new action.

Keep the quarantined lock for investigation or authorized cleanup. Never place private investigation data in PR comments, CI logs or public reports.

## Acceptance evidence still needed
A disposable, isolated-profile crash test should kill a writer before and after atomic replacement and verify recovery safety, revision preservation and zero unintended retries. This recovery procedure is documented but **not independently tested or accepted**. Nurse 2 must review it before enabling persistence.
