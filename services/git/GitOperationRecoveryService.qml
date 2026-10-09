import QtQuick
import Quickshell
import Quickshell.Io

// Guarded executable recovery for the Universal Operation Journal.
//
// Undo is operation-specific, requires exact recorded transitions, and is
// itself snapshotted + journaled. Unsupported or stale states are refused.
Scope {
    id: root

    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null

    property bool busy: false
    property string pendingOperationId: ""
    property var pendingRecord: null
    property var pendingPlan: null

    property string pendingJournalId: ""
    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property bool pendingRecoverySuccess: false
    property string pendingRecoveryDetail: ""

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal recoveryStarted(string operationId)
    signal recoveryFinished(
        string operationId,
        bool success,
        string detail
    )

    function refSha(snapshot, refName) {
        const refs =
            snapshot && Array.isArray(snapshot.refs)
            ? snapshot.refs
            : [];

        for (let i = 0; i < refs.length; ++i) {
            const row = refs[i] || {};

            if (String(row.ref || "") === String(refName || ""))
                return String(row.sha || "");
        }

        return "";
    }

    function branchUpstream(snapshot, branchName) {
        const rows =
            snapshot && Array.isArray(snapshot.branchUpstreams)
            ? snapshot.branchUpstreams
            : [];
        const needle = String(branchName || "");

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};

            if (String(row.branch || "") === needle)
                return String(row.upstream || "");
        }

        return "";
    }

    function worktreeAt(snapshot, path) {
        const rows =
            snapshot && Array.isArray(snapshot.worktrees)
            ? snapshot.worktrees
            : [];
        const needle = String(path || "");

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};

            if (String(row.path || "") === needle)
                return row;
        }

        return null;
    }

    function argument(record, index) {
        const metadata = (record || {}).metadata || {};
        const args =
            Array.isArray(metadata.arguments)
            ? metadata.arguments
            : [];

        return index >= 0 && index < args.length
            ? String(args[index] || "")
            : "";
    }

    function hasFullStashStack(snapshot) {
        return snapshot && Array.isArray(snapshot.stashEntries);
    }

    function stashEntries(snapshot) {
        return hasFullStashStack(snapshot)
            ? snapshot.stashEntries
            : [];
    }

    function normalizedStashRef(value) {
        const ref = String(value || "");
        return !ref || ref === "refs/stash"
            ? "stash@{0}"
            : ref;
    }

    function stashEntry(snapshot, refName) {
        const rows = stashEntries(snapshot);
        const ref = normalizedStashRef(refName);

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            if (String(row.ref || "") === ref)
                return row;
        }

        return null;
    }

    function stashStackShas(snapshot) {
        return stashEntries(snapshot).map(function(row) {
            return String((row || {}).sha || "");
        }).filter(function(sha) {
            return sha.length > 0;
        });
    }

    function sameStringArray(first, second) {
        const a = Array.isArray(first) ? first : [];
        const b = Array.isArray(second) ? second : [];

        if (a.length !== b.length)
            return false;

        for (let i = 0; i < a.length; ++i) {
            if (String(a[i] || "") !== String(b[i] || ""))
                return false;
        }

        return true;
    }

    function stashStackAfterRemoving(snapshot, refName) {
        const rows = stashEntries(snapshot);
        const ref = normalizedStashRef(refName);
        const out = [];
        let removed = false;

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            if (!removed && String(row.ref || "") === ref) {
                removed = true;
                continue;
            }

            const sha = String(row.sha || "");
            if (sha)
                out.push(sha);
        }

        return removed ? out : null;
    }

    function refuse(reason) {
        return {
            allowed: false,
            strategy: "REFUSE",
            reason: String(reason || "UNDO REFUSED")
        };
    }

    function transferRecoveryPlan(record) {
        const row = record || {};
        const metadata = row.metadata || {};
        const kind = String(row.kind || "");
        const mode = String(metadata.mode || "").toLowerCase();
        const sourcePath = String(metadata.sourcePath || "");
        const destinationPath = String(metadata.destinationPath || "");
        const sourceHead = String(metadata.sourceHead || "");
        const destinationHead = String(metadata.destinationHead || "");
        const patchBase64 = String(metadata.patchBase64 || "");
        const fingerprint = String(metadata.fingerprint || "");
        const patchBytes = Number(metadata.patchBytes || 0);
        const layer =
            String(metadata.layer || "worktree").toLowerCase();

        if ([
                "CHANGES/TRANSFER",
                "CHANGES/TRANSFER_HUNK",
                "CHANGES/TRANSFER_LINE",
                "CHANGES/TRANSFER_STAGED",
                "CHANGES/TRANSFER_PARTIAL",
                "CHANGES/TRANSFER_CONFLICT_RESULT",
                "CHANGES/TRANSFER_UNTRACKED"
            ].indexOf(kind) < 0)
            return null;

        if (String(row.recoveryClass || "") !== "CONTENT_RECOVERABLE"
                || String((row.before || {}).recoveryClass || "")
                    !== "CONTENT_RECOVERABLE"
                || String((row.after || {}).recoveryClass || "")
                    !== "CONTENT_RECOVERABLE") {
            return refuse(
                "TRANSFER DOES NOT HAVE DURABLE CONTENT RECOVERY"
            );
        }

        if ((mode !== "copy" && mode !== "move")
                || !sourcePath
                || !destinationPath
                || sourcePath === destinationPath
                || !sourceHead
                || !destinationHead
                || !patchBase64
                || !fingerprint
                || patchBytes <= 0
                || (
                    layer !== "worktree"
                    && layer !== "staged"
                    && layer !== "partial"
                    && layer !== "conflict-result"
                    && layer !== "untracked"
                )
                || (
                    layer === "conflict-result"
                    && mode !== "copy"
                )) {
            return refuse("TRANSFER RECOVERY PAYLOAD IS INCOMPLETE");
        }

        return {
            allowed: true,
            strategy: "UNDO_TRANSFER_CONTENT",
            mode: mode,
            layer: layer,
            sourcePath: sourcePath,
            destinationPath: destinationPath,
            sourceHead: sourceHead,
            destinationHead: destinationHead,
            patchBase64: patchBase64,
            fingerprint: fingerprint,
            patchBytes: patchBytes,
            scope: String(metadata.scope || "file"),
            summary:
                "UNDO "
                + mode.toUpperCase()
                + (
                    layer === "staged"
                    ? " STAGED "
                    : layer === "partial"
                    ? " PARTIALLY STAGED "
                    : layer === "conflict-result"
                    ? " CONFLICT RESULT "
                    : layer === "untracked"
                    ? " UNTRACKED "
                    : " "
                  )
                + String(metadata.scope || "file").toUpperCase()
                + " TRANSFER"
        };
    }

    function absorbRecoveryPlan(record) {
        const row = record || {};
        const metadata = row.metadata || {};
        const kind = String(row.kind || "");

        if (kind !== "HISTORY/ABSORB_STAGED")
            return null;

        if (String(row.recoveryClass || "") !== "CONTENT_RECOVERABLE"
                || String((row.before || {}).recoveryClass || "")
                   !== "CONTENT_RECOVERABLE"
                || String((row.after || {}).recoveryClass || "")
                   !== "CONTENT_RECOVERABLE") {
            return refuse(
                "ABSORB DOES NOT HAVE DURABLE CONTENT RECOVERY"
            );
        }

        const branch = String(metadata.branch || "");
        const patchBase64 = String(metadata.patchBase64 || "");
        const fingerprint = String(metadata.fingerprint || "");
        const patchBytes = Number(metadata.patchBytes || 0);
        const before = row.before || {};
        const after = row.after || {};
        const beforeBranch = String(before.branch || "");
        const afterBranch = String(after.branch || "");
        const ref = "refs/heads/" + branch;
        const restoreSha = refSha(before, ref);
        const expectedSha = refSha(after, ref);

        if (!branch
                || beforeBranch !== branch
                || afterBranch !== branch
                || !restoreSha
                || !expectedSha
                || restoreSha === expectedSha
                || String(before.head || "") !== restoreSha
                || String(after.head || "") !== expectedSha
                || !patchBase64
                || !fingerprint
                || patchBytes <= 0) {
            return refuse("ABSORB RECOVERY PAYLOAD IS INCOMPLETE");
        }

        return {
            allowed: true,
            strategy: "UNDO_ABSORB_STAGED",
            branch: branch,
            restoreSha: restoreSha,
            expectedSha: expectedSha,
            patchBase64: patchBase64,
            fingerprint: fingerprint,
            patchBytes: patchBytes,
            summary:
                "RESTORE PRE-ABSORB HISTORY + STAGED PATCH // "
                + branch
        };
    }

    function commitRecoveryPlan(record) {
        const row = record || {};
        const metadata = row.metadata || {};

        if (String(row.kind || "") !== "CHANGES/COMMIT")
            return null;

        if (String(row.recoveryClass || "") !== "CONTENT_RECOVERABLE"
                || String((row.before || {}).recoveryClass || "")
                   !== "CONTENT_RECOVERABLE"
                || String((row.after || {}).recoveryClass || "")
                   !== "CONTENT_RECOVERABLE") {
            return refuse(
                "COMMIT/AMEND DOES NOT HAVE EXACT CONTENT RECOVERY"
            );
        }

        const before = row.before || {};
        const after = row.after || {};
        const beforeWorking = before.workingState || {};
        const afterWorking = after.workingState || {};
        const beforeIndex = before.index || {};
        const afterIndex = after.index || {};
        const branch = String(before.branch || "");
        const ref = "refs/heads/" + branch;
        const restoreSha = refSha(before, ref);
        const expectedSha = refSha(after, ref);
        const expectedIndexTree = String(afterIndex.tree || "");
        const expectedWorktreeHash =
            String(afterWorking.worktreePatchHash || "");
        const expectedUntrackedHash =
            String(afterWorking.untrackedListHash || "");

        if (!branch
                || String(after.branch || "") !== branch
                || !restoreSha
                || !expectedSha
                || restoreSha === expectedSha
                || String(before.head || "") !== restoreSha
                || String(after.head || "") !== expectedSha
                || !String(beforeIndex.tree || "")
                || String(beforeIndex.tree || "") !== expectedIndexTree
                || Number(afterWorking.stagedCount || 0) !== 0
                || Number(beforeWorking.conflictCount || 0) !== 0
                || Number(afterWorking.conflictCount || 0) !== 0
                || String(beforeWorking.worktreePatchHash || "")
                   !== expectedWorktreeHash
                || String(beforeWorking.untrackedListHash || "")
                   !== expectedUntrackedHash
                || Number(beforeWorking.unstagedCount || 0)
                   !== Number(afterWorking.unstagedCount || 0)
                || Number(beforeWorking.untrackedCount || 0)
                   !== Number(afterWorking.untrackedCount || 0)) {
            return refuse(
                "COMMIT/AMEND CONTENT TRANSITION IS NOT EXACT"
            );
        }

        const args =
            Array.isArray(metadata.arguments)
            ? metadata.arguments
            : [];
        const amended =
            args.length > 1
            && String(args[1] || "") === "1";

        return {
            allowed: true,
            strategy: "UNDO_COMMIT_TO_STAGED",
            branch: branch,
            restoreSha: restoreSha,
            expectedSha: expectedSha,
            expectedIndexTree: expectedIndexTree,
            expectedWorktreeHash: expectedWorktreeHash,
            expectedUntrackedHash: expectedUntrackedHash,
            summary:
                (amended ? "UNDO AMEND" : "UNDO COMMIT")
                + " // RESTORE "
                + restoreSha.slice(0, 12)
                + " + STAGED CONTENT"
        };
    }

    function stashCreateRecoveryPlan(record) {
        const row = record || {};
        const metadata = row.metadata || {};

        if (String(row.kind || "") !== "CHANGES/STASH")
            return null;

        const args =
            Array.isArray(metadata.arguments)
            ? metadata.arguments
            : [];
        const mode =
            args.length > 1
            ? String(args[1] || "all")
            : "all";

        if (["all", "keep-index", "staged"].indexOf(mode) < 0)
            return refuse("UNKNOWN STASH MODE CANNOT BE UNDONE");

        if (String(row.recoveryClass || "") !== "CONTENT_RECOVERABLE"
                || String((row.before || {}).recoveryClass || "")
                   !== "CONTENT_RECOVERABLE"
                || String((row.after || {}).recoveryClass || "")
                   !== "CONTENT_RECOVERABLE") {
            return refuse(
                "STASH CREATION DOES NOT HAVE EXACT CONTENT RECOVERY"
            );
        }

        const before = row.before || {};
        const after = row.after || {};
        const beforeWorking = before.workingState || {};
        const afterWorking = after.workingState || {};
        const beforeIndex = before.index || {};
        const afterIndex = after.index || {};
        const branch = String(before.branch || "");
        const branchRef = "refs/heads/" + branch;
        const head = String(before.head || "");
        const fullStackEvidence =
            hasFullStashStack(before)
            && hasFullStashStack(after);

        if (!fullStackEvidence) {
            if (mode !== "all")
                return refuse(
                    "OLDER JOURNAL RECORD LACKS FULL STASH-STACK EVIDENCE"
                );

            const stashSha = refSha(after, "refs/stash");
            const previousStashSha = refSha(before, "refs/stash");

            if (!branch
                    || !head
                    || String(after.branch || "") !== branch
                    || String(after.head || "") !== head
                    || refSha(before, branchRef) !== head
                    || refSha(after, branchRef) !== head
                    || !stashSha
                    || stashSha === previousStashSha
                    || !String(beforeIndex.tree || "")
                    || !String(afterIndex.tree || "")
                    || Number(afterWorking.stagedCount || 0) !== 0
                    || Number(afterWorking.unstagedCount || 0) !== 0
                    || Number(afterWorking.untrackedCount || 0) !== 0
                    || Number(afterWorking.conflictCount || 0) !== 0) {
                return refuse(
                    "LEGACY FULL-STASH TRANSITION IS NOT EXACT"
                );
            }

            return {
                allowed: true,
                strategy: "UNDO_STASH_CREATE_ALL",
                branch: branch,
                expectedHead: head,
                stashSha: stashSha,
                previousStashSha: previousStashSha,
                expectedAfterIndexTree: String(afterIndex.tree || ""),
                expectedAfterWorktreeHash:
                    String(afterWorking.worktreePatchHash || ""),
                expectedAfterUntrackedHash:
                    String(afterWorking.untrackedListHash || ""),
                restoreIndexTree: String(beforeIndex.tree || ""),
                restoreWorktreeHash:
                    String(beforeWorking.worktreePatchHash || ""),
                restoreUntrackedHash:
                    String(beforeWorking.untrackedListHash || ""),
                summary:
                    "UNDO LEGACY FULL STASH // RESTORE INDEX + WORKTREE + UNTRACKED"
            };
        }

        const beforeStack = stashStackShas(before);
        const afterStack = stashStackShas(after);
        const stashSha =
            afterStack.length > 0
            ? String(afterStack[0] || "")
            : "";
        const stackExact =
            stashSha
            && afterStack.length === beforeStack.length + 1
            && sameStringArray(
                afterStack.slice(1),
                beforeStack
            );

        let modeExact = false;

        if (mode === "all") {
            modeExact =
                Number(afterWorking.stagedCount || 0) === 0
                && Number(afterWorking.unstagedCount || 0) === 0
                && Number(afterWorking.untrackedCount || 0) === 0;
        } else if (mode === "keep-index") {
            modeExact =
                String(afterIndex.tree || "")
                   === String(beforeIndex.tree || "")
                && Number(afterWorking.unstagedCount || 0) === 0
                && Number(afterWorking.untrackedCount || 0) === 0
                && Number(afterWorking.stagedCount || 0)
                   === Number(beforeWorking.stagedCount || 0);
        } else {
            modeExact =
                Number(beforeWorking.unstagedCount || 0) === 0
                && Number(afterWorking.stagedCount || 0) === 0
                && Number(afterWorking.unstagedCount || 0) === 0
                && Number(afterWorking.untrackedCount || 0)
                   === Number(beforeWorking.untrackedCount || 0)
                && String(afterWorking.untrackedListHash || "")
                   === String(beforeWorking.untrackedListHash || "")
                && String(afterWorking.untrackedContentHash || "")
                   === String(beforeWorking.untrackedContentHash || "");
        }

        if (!branch
                || !head
                || String(after.branch || "") !== branch
                || String(after.head || "") !== head
                || refSha(before, branchRef) !== head
                || refSha(after, branchRef) !== head
                || !stackExact
                || !String(beforeIndex.tree || "")
                || !String(afterIndex.tree || "")
                || Number(beforeWorking.conflictCount || 0) !== 0
                || Number(afterWorking.conflictCount || 0) !== 0
                || !modeExact) {
            return refuse(
                "STASH CREATION CONTENT/STACK TRANSITION IS NOT EXACT"
            );
        }

        return {
            allowed: true,
            strategy: "UNDO_STASH_CREATE_EXACT",
            mode: mode,
            branch: branch,
            expectedHead: head,
            stashSha: stashSha,
            beforeStack: beforeStack,
            afterStack: afterStack,
            expectedAfterIndexTree: String(afterIndex.tree || ""),
            expectedAfterWorktreeHash:
                String(afterWorking.worktreePatchHash || ""),
            expectedAfterUntrackedHash:
                String(afterWorking.untrackedListHash || ""),
            expectedAfterUntrackedContentHash:
                String(afterWorking.untrackedContentHash || ""),
            restoreIndexTree: String(beforeIndex.tree || ""),
            restoreWorktreeHash:
                String(beforeWorking.worktreePatchHash || ""),
            restoreUntrackedHash:
                String(beforeWorking.untrackedListHash || ""),
            restoreUntrackedContentHash:
                String(beforeWorking.untrackedContentHash || ""),
            summary:
                "UNDO STASH "
                + mode.toUpperCase()
                + " // RESTORE EXACT PRE-STASH CONTENT + STACK"
        };
    }

    function stashMutationRecoveryPlan(record) {
        const row = record || {};
        const kind = String(row.kind || "");
        const metadata = row.metadata || {};

        if ([
                "CHANGES/STASH-APPLY",
                "CHANGES/STASH-POP",
                "CHANGES/STASH-DROP"
            ].indexOf(kind) < 0)
            return null;

        const args =
            Array.isArray(metadata.arguments)
            ? metadata.arguments
            : [];
        const ref =
            args.length > 0
            ? String(args[0] || "")
            : "";
        const normalizedRef = normalizedStashRef(ref);
        const useIndex =
            args.length > 1
            && String(args[1] || "") === "index";

        if (String(row.recoveryClass || "") !== "CONTENT_RECOVERABLE"
                || String((row.before || {}).recoveryClass || "")
                   !== "CONTENT_RECOVERABLE"
                || String((row.after || {}).recoveryClass || "")
                   !== "CONTENT_RECOVERABLE") {
            return refuse(
                "STASH MUTATION DOES NOT HAVE EXACT CONTENT RECOVERY"
            );
        }

        const before = row.before || {};
        const after = row.after || {};
        const beforeWorking = before.workingState || {};
        const afterWorking = after.workingState || {};
        const beforeIndex = before.index || {};
        const afterIndex = after.index || {};
        const branch = String(before.branch || "");
        const head = String(before.head || "");
        const branchRef = "refs/heads/" + branch;
        const fullStackEvidence =
            hasFullStashStack(before)
            && hasFullStashStack(after);

        if (!branch
                || !head
                || String(after.branch || "") !== branch
                || String(after.head || "") !== head
                || refSha(before, branchRef) !== head
                || refSha(after, branchRef) !== head
                || !String(beforeIndex.tree || "")
                || !String(afterIndex.tree || "")
                || Number(beforeWorking.conflictCount || 0) !== 0
                || Number(afterWorking.conflictCount || 0) !== 0) {
            return refuse(
                "STASH MUTATION CONTENT TRANSITION IS NOT EXACT"
            );
        }

        if (!fullStackEvidence) {
            const topRef =
                !ref
                || ref === "stash@{0}"
                || ref === "refs/stash";

            if (!topRef)
                return refuse(
                    "OLDER JOURNAL RECORD LACKS SELECTED-STASH STACK EVIDENCE"
                );

            const beforeStash = refSha(before, "refs/stash");
            const afterStash = refSha(after, "refs/stash");
            const common = {
                branch: branch,
                expectedHead: head,
                beforeStashSha: beforeStash,
                afterStashSha: afterStash,
                expectedAfterIndexTree: String(afterIndex.tree || ""),
                expectedAfterWorktreeHash:
                    String(afterWorking.worktreePatchHash || ""),
                expectedAfterUntrackedHash:
                    String(afterWorking.untrackedListHash || ""),
                restoreIndexTree: String(beforeIndex.tree || ""),
                restoreWorktreeHash:
                    String(beforeWorking.worktreePatchHash || ""),
                restoreUntrackedHash:
                    String(beforeWorking.untrackedListHash || ""),
                useIndex: useIndex
            };

            if (kind === "CHANGES/STASH-APPLY") {
                if (!beforeStash
                        || beforeStash !== afterStash
                        || Number(beforeWorking.stagedCount || 0) !== 0
                        || Number(beforeWorking.unstagedCount || 0) !== 0
                        || Number(beforeWorking.untrackedCount || 0) !== 0) {
                    return refuse(
                        "LEGACY STASH APPLY TRANSITION IS NOT EXACT"
                    );
                }
                common.allowed = true;
                common.strategy = "UNDO_STASH_APPLY_CLEAN";
                common.summary = "UNDO LEGACY TOP-STASH APPLY";
                return common;
            }

            if (kind === "CHANGES/STASH-POP") {
                if (!beforeStash
                        || beforeStash === afterStash
                        || Number(beforeWorking.stagedCount || 0) !== 0
                        || Number(beforeWorking.unstagedCount || 0) !== 0
                        || Number(beforeWorking.untrackedCount || 0) !== 0) {
                    return refuse(
                        "LEGACY STASH POP TRANSITION IS NOT EXACT"
                    );
                }
                common.allowed = true;
                common.strategy = "UNDO_STASH_POP_TOP";
                common.summary = "UNDO LEGACY TOP-STASH POP";
                return common;
            }

            if (!beforeStash || beforeStash === afterStash)
                return refuse(
                    "LEGACY STASH DROP TRANSITION IS NOT EXACT"
                );

            common.allowed = true;
            common.strategy = "UNDO_STASH_DROP_TOP";
            common.summary = "UNDO LEGACY TOP-STASH DROP";
            return common;
        }

        const selected = stashEntry(before, normalizedRef);
        const beforeStack = stashStackShas(before);
        const afterStack = stashStackShas(after);
        const expectedAfterStack =
            kind === "CHANGES/STASH-APPLY"
            ? beforeStack
            : stashStackAfterRemoving(before, normalizedRef);

        if (!selected
                || expectedAfterStack === null
                || !sameStringArray(
                    expectedAfterStack,
                    afterStack
                )) {
            return refuse(
                "SELECTED STASH STACK TRANSITION IS NOT EXACT"
            );
        }

        if ((kind === "CHANGES/STASH-APPLY"
                    || kind === "CHANGES/STASH-POP")
                && (
                    Number(beforeWorking.stagedCount || 0) !== 0
                    || Number(beforeWorking.unstagedCount || 0) !== 0
                    || Number(beforeWorking.untrackedCount || 0) !== 0
                )) {
            return refuse(
                "STASH APPLY/POP DID NOT START FROM AN EXACT CLEAN STATE"
            );
        }

        const common = {
            branch: branch,
            expectedHead: head,
            selectedRef: normalizedRef,
            selectedStashSha: String(selected.sha || ""),
            beforeStack: beforeStack,
            afterStack: afterStack,
            expectedAfterIndexTree: String(afterIndex.tree || ""),
            expectedAfterWorktreeHash:
                String(afterWorking.worktreePatchHash || ""),
            expectedAfterUntrackedHash:
                String(afterWorking.untrackedListHash || ""),
            expectedAfterUntrackedContentHash:
                String(afterWorking.untrackedContentHash || ""),
            restoreIndexTree: String(beforeIndex.tree || ""),
            restoreWorktreeHash:
                String(beforeWorking.worktreePatchHash || ""),
            restoreUntrackedHash:
                String(beforeWorking.untrackedListHash || ""),
            restoreUntrackedContentHash:
                String(beforeWorking.untrackedContentHash || ""),
            useIndex: useIndex
        };

        common.allowed = true;

        if (kind === "CHANGES/STASH-APPLY") {
            common.strategy = "UNDO_STASH_APPLY_REF";
            common.summary =
                "UNDO " + normalizedRef + " APPLY // RESTORE CLEAN PRE-APPLY STATE";
        } else if (kind === "CHANGES/STASH-POP") {
            common.strategy = "UNDO_STASH_POP_REF";
            common.summary =
                "UNDO " + normalizedRef + " POP // RESTORE CONTENT + EXACT STACK ORDER";
        } else {
            common.strategy = "UNDO_STASH_DROP_REF";
            common.summary =
                "UNDO " + normalizedRef + " DROP // RESTORE EXACT STACK ORDER";
        }

        return common;
    }

    function controlPullRecoveryPlan(record) {
        const row = record || {};
        const metadata = row.metadata || {};

        if (String(row.kind || "") !== "CONTROL/PULL")
            return null;

        if (String(row.recoveryClass || "") !== "REF_RECOVERABLE"
                || String((row.before || {}).recoveryClass || "")
                   !== "REF_RECOVERABLE"
                || String((row.after || {}).recoveryClass || "")
                   !== "REF_RECOVERABLE") {
            return refuse(
                "PULL DOES NOT HAVE CLEAN REF-RECOVERABLE EVIDENCE"
            );
        }

        const before = row.before || {};
        const after = row.after || {};
        const localTarget = String(metadata.localTarget || "");
        const pullMode = String(metadata.pullMode || "");
        const targetRef = "refs/heads/" + localTarget;
        const beforeSha = refSha(before, targetRef);
        const afterSha = refSha(after, targetRef);
        const beforeBranch = String(before.branch || "");
        const afterBranch = String(after.branch || "");
        const beforeHead = String(before.head || "");
        const afterHead = String(after.head || "");

        if (!localTarget
                || !beforeSha
                || !afterSha
                || beforeSha === afterSha) {
            return refuse(
                "PULL DID NOT RECORD AN EXACT LOCAL BRANCH TRANSITION"
            );
        }

        if (beforeBranch === localTarget) {
            if (afterBranch !== localTarget
                    || beforeHead !== beforeSha
                    || afterHead !== afterSha) {
                return refuse(
                    "CHECKED-OUT PULL HEAD TRANSITION IS NOT EXACT"
                );
            }

            return {
                allowed: true,
                strategy: "RESTORE_PULLED_BRANCH",
                branch: localTarget,
                restoreSha: beforeSha,
                expectedSha: afterSha,
                pullMode: pullMode,
                target: String(metadata.target || ""),
                summary:
                    "UNDO "
                    + (pullMode === "merge" ? "MERGE" : "FF")
                    + " PULL // RESTORE "
                    + localTarget
                    + " TO "
                    + beforeSha.slice(0, 12)
                    + " // KEEP FETCHED REMOTE REFS"
            };
        }

        if (pullMode !== "ff-only")
            return refuse(
                "BACKGROUND MERGE PULL IS NOT A SUPPORTED SUCCESS STATE"
            );

        if (!beforeBranch
                || afterBranch !== beforeBranch
                || !beforeHead
                || afterHead !== beforeHead) {
            return refuse(
                "BACKGROUND PULL CHANGED THE CHECKED-OUT HEAD"
            );
        }

        return {
            allowed: true,
            strategy: "RESTORE_BACKGROUND_PULL_REF",
            branch: localTarget,
            restoreSha: beforeSha,
            expectedSha: afterSha,
            currentBranch: beforeBranch,
            expectedCurrentHead: beforeHead,
            target: String(metadata.target || ""),
            summary:
                "UNDO BACKGROUND FF PULL // RESTORE "
                + localTarget
                + " TO "
                + beforeSha.slice(0, 12)
                + " // KEEP FETCHED REMOTE REFS"
        };
    }

    function cloneRecoveryPlan(record) {
        const row = record || {};
        const metadata = row.metadata || {};
        const before = row.before || {};
        const after = row.after || {};

        if (String(row.kind || "") !== "CONTROL/CLONE")
            return null;

        const destinationPath =
            String(
                after.destinationPath
                || metadata.destinationPath
                || ""
            );
        const beforePath =
            String(before.destinationPath || "");
        const expectedHead = String(after.head || "");
        const expectedBranch = String(after.branch || "");
        const expectedOrigin = String(after.origin || "");
        const expectedFingerprint =
            String(after.filesystemFingerprint || "");

        if (String(row.recoveryClass || "")
                    !== "EXTERNAL_RECOVERABLE"
                || String(before.recoveryClass || "")
                    !== "EXTERNAL_RECOVERABLE"
                || String(after.recoveryClass || "")
                    !== "EXTERNAL_RECOVERABLE"
                || !Boolean(before.destinationRequiredAbsent)
                || !Boolean(after.cloneCreated)
                || !destinationPath
                || beforePath !== destinationPath
                || !expectedHead
                || !expectedOrigin
                || !expectedFingerprint) {
            return refuse(
                "CLONE DOES NOT HAVE EXACT EXTERNAL RECOVERY EVIDENCE"
            );
        }

        return {
            allowed: true,
            strategy: "DELETE_EXACT_CLONE",
            destinationPath: destinationPath,
            expectedHead: expectedHead,
            expectedBranch: expectedBranch,
            expectedOrigin: expectedOrigin,
            expectedFingerprint: expectedFingerprint,
            summary:
                "UNDO CLONE // DELETE EXACT UNCHANGED CHECKOUT // "
                + destinationPath
        };
    }

    function resetRecoveryPlan(record) {
        const row = record || {};

        if (String(row.kind || "") !== "HISTORY/RESET")
            return null;

        const mode = String(argument(row, 1) || "").toLowerCase();

        if (mode === "hard")
            return null;

        if (mode !== "soft" && mode !== "mixed")
            return refuse("RESET MODE DOES NOT HAVE EXACT AUTOMATIC UNDO");

        const before = row.before || {};
        const after = row.after || {};
        const beforeIndex = before.index || {};
        const afterIndex = after.index || {};
        const afterWorking = after.workingState || {};
        const beforeBranch = String(before.branch || "");
        const afterBranch = String(after.branch || "");
        const ref = "refs/heads/" + beforeBranch;
        const restoreSha = refSha(before, ref);
        const expectedSha = refSha(after, ref);
        const expectedIndexTree = String(afterIndex.tree || "");
        const beforeIndexTree = String(beforeIndex.tree || "");

        if (String(before.recoveryClass || "") !== "REF_RECOVERABLE"
                || !beforeBranch
                || afterBranch !== beforeBranch
                || !restoreSha
                || !expectedSha
                || restoreSha === expectedSha
                || String(before.head || "") !== restoreSha
                || String(after.head || "") !== expectedSha
                || !beforeIndexTree
                || !expectedIndexTree
                || Number(afterWorking.conflictCount || 0) !== 0
                || String(((before.operationState || {}).state) || "NONE")
                   !== "NONE"
                || String(((after.operationState || {}).state) || "NONE")
                   !== "NONE") {
            return refuse(
                "SOFT/MIXED RESET TRANSITION IS NOT EXACT"
            );
        }

        if (mode === "soft"
                && expectedIndexTree !== beforeIndexTree) {
            return refuse(
                "SOFT RESET DID NOT PRESERVE THE PRE-RESET INDEX"
            );
        }

        return {
            allowed: true,
            strategy: "UNDO_RESET_SOFT_OR_MIXED",
            mode: mode,
            branch: beforeBranch,
            restoreSha: restoreSha,
            expectedSha: expectedSha,
            expectedIndexTree: expectedIndexTree,
            expectedStatusBase64:
                String(afterWorking.statusBase64 || ""),
            expectedWorktreeHash:
                String(afterWorking.worktreePatchHash || ""),
            expectedUntrackedHash:
                String(afterWorking.untrackedListHash || ""),
            summary:
                "UNDO RESET "
                + mode.toUpperCase()
                + " // RESTORE "
                + beforeBranch
                + " TO "
                + restoreSha.slice(0, 12)
                + " WITHOUT DISCARDING VERIFIED CONTENT"
        };
    }

    function preview(record) {
        const row = record || {};
        const kind = String(row.kind || "");
        const status = String(row.status || "");
        const recoveryClass = String(row.recoveryClass || "");
        const before = row.before || {};
        const after = row.after || {};

        if (status !== "COMPLETE")
            return refuse("ONLY COMPLETE OPERATIONS CAN BE UNDONE");

        if (String(row.undoState || "") === "UNDONE")
            return refuse("OPERATION IS ALREADY UNDONE");

        const resetPlan = resetRecoveryPlan(row);
        if (resetPlan)
            return resetPlan;

        const clonePlan = cloneRecoveryPlan(row);
        if (clonePlan)
            return clonePlan;

        const transferPlan = transferRecoveryPlan(row);
        if (transferPlan)
            return transferPlan;

        const absorbPlan = absorbRecoveryPlan(row);
        if (absorbPlan)
            return absorbPlan;

        const commitPlan = commitRecoveryPlan(row);
        if (commitPlan)
            return commitPlan;

        const stashPlan = stashCreateRecoveryPlan(row);
        if (stashPlan)
            return stashPlan;

        const stashMutationPlan = stashMutationRecoveryPlan(row);
        if (stashMutationPlan)
            return stashMutationPlan;

        const pullPlan = controlPullRecoveryPlan(row);
        if (pullPlan)
            return pullPlan;

        if (recoveryClass !== "REF_RECOVERABLE"
                || String(before.recoveryClass || "") !== "REF_RECOVERABLE"
                || String(after.recoveryClass || "") !== "REF_RECOVERABLE") {
            return refuse("OPERATION IS NOT CLEAN REF-RECOVERABLE");
        }

        const historyRewrite =
            kind === "HISTORY/INTERACTIVE_REBASE"
            || kind === "HISTORY/INTERACTIVE_REBASE_SESSION"
            || kind === "HISTORY/FOLD_COMMITS"
            || kind === "HISTORY/SPLIT_COMMIT"
            || kind === "HISTORY/SPLIT_COMMIT_HUNK"
            || kind === "HISTORY/SPLIT_COMMIT_LINE"
            || kind === "HISTORY/MERGE"
            || kind === "HISTORY/CHERRY-PICK"
            || kind === "HISTORY/REVERT"
            || kind === "HISTORY/RESET";

        if (historyRewrite) {
            const beforeBranch = String(before.branch || "");
            const afterBranch = String(after.branch || "");

            if (!beforeBranch
                    || beforeBranch !== afterBranch) {
                return refuse(
                    "HISTORY REWRITE BRANCH IDENTITY CHANGED"
                );
            }

            const ref = "refs/heads/" + beforeBranch;
            const beforeSha = refSha(before, ref);
            const afterSha = refSha(after, ref);

            if (!beforeSha
                    || !afterSha
                    || beforeSha === afterSha
                    || String(before.head || "") !== beforeSha
                    || String(after.head || "") !== afterSha) {
                return refuse(
                    "HISTORY REWRITE REF TRANSITION IS NOT EXACT"
                );
            }

            return {
                allowed: true,
                strategy: "RESTORE_REWRITTEN_BRANCH",
                branch: beforeBranch,
                expectedSha: afterSha,
                restoreSha: beforeSha,
                summary:
                    "RESTORE "
                    + beforeBranch
                    + " // "
                    + afterSha.slice(0, 12)
                    + " -> "
                    + beforeSha.slice(0, 12)
            };
        }

        if (kind === "HISTORY/DETACH") {
            const previousBranch = String(before.branch || "");
            const afterBranch = String(after.branch || "");
            const previousRef = "refs/heads/" + previousBranch;
            const previousSha = refSha(before, previousRef);
            const afterPreviousSha = refSha(after, previousRef);
            const detachedSha = String(after.head || "");
            const targetSha = argument(row, 0);

            if (!previousBranch
                    || afterBranch
                    || !previousSha
                    || afterPreviousSha !== previousSha
                    || String(before.head || "") !== previousSha
                    || !detachedSha
                    || (targetSha && detachedSha !== targetSha)) {
                return refuse(
                    "DETACH TRANSITION IS NOT EXACT"
                );
            }

            return {
                allowed: true,
                strategy: "SWITCH_BACK_FROM_DETACHED",
                previousBranch: previousBranch,
                expectedPreviousSha: previousSha,
                expectedDetachedSha: detachedSha,
                summary:
                    "SWITCH BACK FROM DETACHED "
                    + detachedSha.slice(0, 12)
                    + " TO "
                    + previousBranch
            };
        }

        if (kind === "HISTORY/TAG") {
            const name = argument(row, 0);
            const ref = "refs/tags/" + name;
            const beforeSha = refSha(before, ref);
            const afterSha = refSha(after, ref);

            if (!name || beforeSha || !afterSha)
                return refuse("TAG CREATE REF TRANSITION IS NOT EXACT");

            return {
                allowed: true,
                strategy: "DELETE_CREATED_TAG",
                tag: name,
                expectedSha: afterSha,
                summary:
                    "DELETE CREATED TAG "
                    + name
                    + " @ "
                    + afterSha.slice(0, 12)
            };
        }

        if (kind === "BRANCH_WORKSPACE/CREATE"
                || kind === "HISTORY/BRANCH") {
            const name = argument(row, 0);
            const ref = "refs/heads/" + name;
            const beforeSha = refSha(before, ref);
            const afterSha = refSha(after, ref);

            if (!name || beforeSha || !afterSha)
                return refuse("CREATE REF TRANSITION IS NOT EXACT");

            return {
                allowed: true,
                strategy: "DELETE_CREATED_BRANCH",
                branch: name,
                expectedSha: afterSha,
                summary:
                    "DELETE CREATED BRANCH "
                    + name
                    + " @ "
                    + afterSha.slice(0, 12)
            };
        }

        if (kind === "BRANCH_WORKSPACE/RENAME") {
            const oldName = argument(row, 0);
            const newName = argument(row, 1);
            const oldRef = "refs/heads/" + oldName;
            const newRef = "refs/heads/" + newName;
            const beforeOld = refSha(before, oldRef);
            const beforeNew = refSha(before, newRef);
            const afterOld = refSha(after, oldRef);
            const afterNew = refSha(after, newRef);

            if (!oldName
                    || !newName
                    || !beforeOld
                    || beforeNew
                    || afterOld
                    || afterNew !== beforeOld) {
                return refuse("RENAME REF TRANSITION IS NOT EXACT");
            }

            return {
                allowed: true,
                strategy: "RENAME_BRANCH_BACK",
                oldName: oldName,
                newName: newName,
                expectedSha: afterNew,
                summary:
                    "RENAME "
                    + newName
                    + " BACK TO "
                    + oldName
            };
        }

        if (kind === "BRANCH_WORKSPACE/DELETE") {
            const name = argument(row, 0);
            const ref = "refs/heads/" + name;
            const beforeSha = refSha(before, ref);
            const afterSha = refSha(after, ref);

            if (!name || !beforeSha || afterSha)
                return refuse("DELETE REF TRANSITION IS NOT EXACT");

            return {
                allowed: true,
                strategy: "RESTORE_DELETED_BRANCH",
                branch: name,
                restoreSha: beforeSha,
                restoreUpstream: branchUpstream(before, name),
                summary:
                    "RESTORE DELETED BRANCH "
                    + name
                    + " @ "
                    + beforeSha.slice(0, 12)
            };
        }

        if (kind === "BRANCH_WORKSPACE/SWITCH") {
            const previousBranch = String(before.branch || "");
            const currentBranch = String(after.branch || "");

            if (!previousBranch
                    || !currentBranch
                    || previousBranch === currentBranch) {
                return refuse("SWITCH BRANCH TRANSITION IS NOT EXACT");
            }

            const previousRef = "refs/heads/" + previousBranch;
            const currentRef = "refs/heads/" + currentBranch;
            const beforePrevious = refSha(before, previousRef);
            const afterPrevious = refSha(after, previousRef);
            const beforeCurrent = refSha(before, currentRef);
            const afterCurrent = refSha(after, currentRef);

            // Refuse switches that created a new local tracking branch.
            if (!beforePrevious
                    || !beforeCurrent
                    || beforePrevious !== afterPrevious
                    || beforeCurrent !== afterCurrent
                    || String(before.head || "") !== beforePrevious
                    || String(after.head || "") !== afterCurrent) {
                return refuse(
                    "SWITCH CHANGED OR CREATED REFS // EXPLICIT STRATEGY REQUIRED"
                );
            }

            return {
                allowed: true,
                strategy: "SWITCH_BACK",
                currentBranch: currentBranch,
                previousBranch: previousBranch,
                expectedCurrentSha: afterCurrent,
                expectedPreviousSha: afterPrevious,
                summary:
                    "SWITCH BACK "
                    + currentBranch
                    + " -> "
                    + previousBranch
            };
        }

        if (kind === "BRANCH_WORKSPACE/SET-UPSTREAM"
                || kind === "BRANCH_WORKSPACE/CLEAR-UPSTREAM") {
            const branch = argument(row, 0);
            const ref = "refs/heads/" + branch;
            const beforeSha = refSha(before, ref);
            const afterSha = refSha(after, ref);
            const beforeUpstream = branchUpstream(before, branch);
            const afterUpstream = branchUpstream(after, branch);

            if (!branch || !beforeSha || beforeSha !== afterSha)
                return refuse("UPSTREAM BRANCH REF CHANGED");

            if (kind === "BRANCH_WORKSPACE/SET-UPSTREAM") {
                const requested = argument(row, 1);

                if (!requested || afterUpstream !== requested)
                    return refuse("SET-UPSTREAM TRANSITION IS NOT EXACT");
            } else if (!beforeUpstream || afterUpstream) {
                return refuse("CLEAR-UPSTREAM TRANSITION IS NOT EXACT");
            }

            return {
                allowed: true,
                strategy: "RESTORE_UPSTREAM",
                branch: branch,
                expectedSha: afterSha,
                expectedUpstream: afterUpstream,
                restoreUpstream: beforeUpstream,
                summary:
                    "RESTORE UPSTREAM // "
                    + branch
                    + " -> "
                    + (beforeUpstream || "NONE")
            };
        }

        if (kind === "BRANCH_WORKSPACE/ADD-WORKTREE") {
            const path = argument(row, 0);
            const branch = argument(row, 1);
            const beforeTree = worktreeAt(before, path);
            const afterTree = worktreeAt(after, path);
            const ref = "refs/heads/" + branch;
            const beforeSha = refSha(before, ref);
            const afterSha = refSha(after, ref);

            if (!path
                    || !branch
                    || beforeTree
                    || !afterTree
                    || String(afterTree.branch || "") !== branch
                    || Number(afterTree.dirtyCount || 0) !== 0
                    || !beforeSha
                    || beforeSha !== afterSha
                    || String(afterTree.head || "") !== afterSha) {
                return refuse("ADD-WORKTREE TRANSITION IS NOT EXACT");
            }

            return {
                allowed: true,
                strategy: "REMOVE_ADDED_WORKTREE",
                path: path,
                branch: branch,
                expectedSha: afterSha,
                summary: "REMOVE ADDED WORKTREE // " + path
            };
        }

        if (kind === "BRANCH_WORKSPACE/NEW-WORKTREE") {
            const path = argument(row, 0);
            const branch = argument(row, 1);
            const beforeTree = worktreeAt(before, path);
            const afterTree = worktreeAt(after, path);
            const ref = "refs/heads/" + branch;
            const beforeSha = refSha(before, ref);
            const afterSha = refSha(after, ref);

            if (!path
                    || !branch
                    || beforeTree
                    || !afterTree
                    || beforeSha
                    || !afterSha
                    || String(afterTree.branch || "") !== branch
                    || String(afterTree.head || "") !== afterSha
                    || Number(afterTree.dirtyCount || 0) !== 0) {
                return refuse("NEW-WORKTREE TRANSITION IS NOT EXACT");
            }

            return {
                allowed: true,
                strategy: "REMOVE_NEW_WORKTREE_AND_BRANCH",
                path: path,
                branch: branch,
                expectedSha: afterSha,
                summary:
                    "REMOVE NEW WORKTREE + BRANCH // "
                    + path
            };
        }

        if (kind === "BRANCH_WORKSPACE/REMOVE-WORKTREE") {
            const path = argument(row, 0);
            const beforeTree = worktreeAt(before, path);
            const afterTree = worktreeAt(after, path);

            if (!path
                    || !beforeTree
                    || afterTree
                    || Number(beforeTree.dirtyCount || 0) !== 0
                    || !String(beforeTree.head || "")) {
                return refuse("REMOVE-WORKTREE TRANSITION IS NOT EXACT");
            }

            const treeBranch = String(beforeTree.branch || "");
            const expectedSha = String(beforeTree.head || "");

            if (treeBranch) {
                const ref = "refs/heads/" + treeBranch;
                const beforeSha = refSha(before, ref);
                const afterSha = refSha(after, ref);

                if (!beforeSha
                        || beforeSha !== expectedSha
                        || afterSha !== expectedSha) {
                    return refuse(
                        "REMOVED WORKTREE BRANCH MOVED DURING OPERATION"
                    );
                }
            }

            return {
                allowed: true,
                strategy: "RESTORE_REMOVED_WORKTREE",
                path: path,
                branch: treeBranch,
                expectedSha: expectedSha,
                detached: !treeBranch,
                summary: "RESTORE REMOVED WORKTREE // " + path
            };
        }

        return refuse(
            "UNDO STRATEGY NOT IMPLEMENTED FOR "
            + (kind || "UNKNOWN OPERATION")
        );
    }

    function clearPending() {
        pendingOperationId = "";
        pendingRecord = null;
        pendingPlan = null;
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        pendingRecoverySuccess = false;
        pendingRecoveryDetail = "";
    }

    function recoveryContext() {
        return {
            source: "GitOperationRecoveryService",
            originalOperationId: pendingOperationId,
            originalKind: String((pendingRecord || {}).kind || ""),
            strategy: String((pendingPlan || {}).strategy || ""),
            summary: String((pendingPlan || {}).summary || "")
        };
    }

    function failBeforeSnapshot(detail) {
        const operationId = pendingOperationId;
        const message =
            "UNDO BEFORE SNAPSHOT FAILED // "
            + String(detail || "SNAPSHOT UNAVAILABLE");

        busy = false;
        clearPending();
        recoveryFinished(operationId, false, message);
    }

    function execute(operationId, record) {
        if (busy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const plan = preview(record);

        if (!repo) {
            recoveryFinished(
                String(operationId || ""),
                false,
                "NO REPOSITORY"
            );
            return false;
        }

        if (!operationJournal || !snapshotService) {
            recoveryFinished(
                String(operationId || ""),
                false,
                "UNDO REQUIRES JOURNAL + SNAPSHOT SERVICES"
            );
            return false;
        }

        if (!plan.allowed) {
            recoveryFinished(
                String(operationId || ""),
                false,
                String(plan.reason || "UNDO REFUSED")
            );
            return false;
        }

        busy = true;
        pendingOperationId = String(operationId || "");
        pendingRecord = record || {};
        pendingPlan = plan;
        pendingJournalId = "";
        pendingRecoverySuccess = false;
        pendingRecoveryDetail = "";

        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        recoveryStarted(pendingOperationId);

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "UNDO BEFORE // " + String(plan.strategy || ""),
            recoveryContext()
        );

        if (!pendingSnapshotRequest) {
            failBeforeSnapshot("SNAPSHOT SERVICE BUSY OR UNAVAILABLE");
            return false;
        }

        return true;
    }

    function executeRecoveryProcess() {
        const repo = String(repositoryPath || "").trim();
        const plan = pendingPlan || {};
        const strategy = String(plan.strategy || "");

        if (!repo || !strategy) {
            finalizeRecovery(
                null,
                "RECOVERY IDENTITY LOST BEFORE EXECUTION"
            );
            return false;
        }

        let a = "";
        let b = "";
        let c = "";
        let d = "";
        let e = "";
        let f = "";
        let g = "";

        if (strategy === "DELETE_EXACT_CLONE") {
            a = String(plan.destinationPath || "");
            b = String(plan.expectedHead || "");
            c = String(plan.expectedBranch || "");
            d = String(plan.expectedOrigin || "");
            e = String(plan.expectedFingerprint || "");
        } else if (strategy === "DELETE_CREATED_BRANCH") {
            a = String(plan.branch || "");
            c = String(plan.expectedSha || "");
        } else if (strategy === "DELETE_CREATED_TAG") {
            a = String(plan.tag || "");
            c = String(plan.expectedSha || "");
        } else if (strategy === "SWITCH_BACK_FROM_DETACHED") {
            a = String(plan.previousBranch || "");
            b = String(plan.expectedPreviousSha || "");
            c = String(plan.expectedDetachedSha || "");
        } else if (strategy === "RENAME_BRANCH_BACK") {
            a = String(plan.oldName || "");
            b = String(plan.newName || "");
            c = String(plan.expectedSha || "");
        } else if (strategy === "RESTORE_DELETED_BRANCH") {
            a = String(plan.branch || "");
            b = String(plan.restoreSha || "");
            c = String(plan.restoreUpstream || "");
        } else if (strategy === "SWITCH_BACK") {
            a = String(plan.currentBranch || "");
            b = String(plan.previousBranch || "");
            c = String(plan.expectedCurrentSha || "");
            d = String(plan.expectedPreviousSha || "");
        } else if (strategy === "RESTORE_UPSTREAM") {
            a = String(plan.branch || "");
            b = String(plan.expectedUpstream || "");
            c = String(plan.restoreUpstream || "");
            d = String(plan.expectedSha || "");
        } else if (strategy === "REMOVE_ADDED_WORKTREE"
                || strategy === "REMOVE_NEW_WORKTREE_AND_BRANCH") {
            a = String(plan.path || "");
            b = String(plan.branch || "");
            c = String(plan.expectedSha || "");
        } else if (strategy === "RESTORE_REMOVED_WORKTREE") {
            a = String(plan.path || "");
            b = String(plan.branch || "");
            c = String(plan.expectedSha || "");
            d = plan.detached ? "1" : "0";
        } else if (strategy === "RESTORE_PULLED_BRANCH") {
            a = String(plan.branch || "");
            b = String(plan.restoreSha || "");
            c = String(plan.expectedSha || "");
        } else if (strategy === "RESTORE_BACKGROUND_PULL_REF") {
            a = String(plan.branch || "");
            b = String(plan.restoreSha || "");
            c = String(plan.expectedSha || "");
            d = String(plan.currentBranch || "");
            e = String(plan.expectedCurrentHead || "");
        } else if (strategy === "RESTORE_REWRITTEN_BRANCH") {
            a = String(plan.branch || "");
            b = String(plan.restoreSha || "");
            c = String(plan.expectedSha || "");
        } else if (strategy === "UNDO_RESET_SOFT_OR_MIXED") {
            a = String(plan.branch || "");
            b = String(plan.restoreSha || "");
            c = String(plan.expectedSha || "");
            d = String(plan.mode || "");
            e = String(plan.expectedIndexTree || "");
            f = String(plan.expectedWorktreeHash || "");
            g =
                String(plan.expectedStatusBase64 || "")
                + "\t"
                + String(plan.expectedUntrackedHash || "");
        } else if (strategy === "UNDO_COMMIT_TO_STAGED") {
            a = String(plan.branch || "");
            b = String(plan.restoreSha || "");
            c = String(plan.expectedSha || "");
            d = String(plan.expectedIndexTree || "");
            e = String(plan.expectedWorktreeHash || "");
            f = String(plan.expectedUntrackedHash || "");
        } else if (strategy === "UNDO_STASH_CREATE_EXACT") {
            a = String(plan.branch || "");
            b = String(plan.expectedHead || "");
            c = String(plan.stashSha || "");
            d = String(plan.mode || "");
            e = String(plan.expectedAfterIndexTree || "");
            f = String(plan.expectedAfterWorktreeHash || "");
            g =
                String(plan.expectedAfterUntrackedHash || "")
                + "\t"
                + String(plan.expectedAfterUntrackedContentHash || "")
                + "\t"
                + String(plan.restoreIndexTree || "")
                + "\t"
                + String(plan.restoreWorktreeHash || "")
                + "\t"
                + String(plan.restoreUntrackedHash || "")
                + "\t"
                + String(plan.restoreUntrackedContentHash || "")
                + "\t"
                + (
                    Array.isArray(plan.beforeStack)
                    ? plan.beforeStack.join(",")
                    : ""
                  )
                + "\t"
                + (
                    Array.isArray(plan.afterStack)
                    ? plan.afterStack.join(",")
                    : ""
                  );
        } else if (strategy === "UNDO_STASH_APPLY_REF"
                || strategy === "UNDO_STASH_POP_REF"
                || strategy === "UNDO_STASH_DROP_REF") {
            a = String(plan.branch || "");
            b = String(plan.expectedHead || "");
            c = String(plan.selectedStashSha || "");
            d = String(plan.selectedRef || "");
            e = String(plan.expectedAfterIndexTree || "");
            f = String(plan.expectedAfterWorktreeHash || "");
            g =
                String(plan.expectedAfterUntrackedHash || "")
                + "\t"
                + String(plan.expectedAfterUntrackedContentHash || "")
                + "\t"
                + String(plan.restoreIndexTree || "")
                + "\t"
                + String(plan.restoreWorktreeHash || "")
                + "\t"
                + String(plan.restoreUntrackedHash || "")
                + "\t"
                + String(plan.restoreUntrackedContentHash || "")
                + "\t"
                + (
                    Array.isArray(plan.beforeStack)
                    ? plan.beforeStack.join(",")
                    : ""
                  )
                + "\t"
                + (
                    Array.isArray(plan.afterStack)
                    ? plan.afterStack.join(",")
                    : ""
                  )
                + "\t"
                + (plan.useIndex ? "1" : "0");
        } else if (strategy === "UNDO_STASH_APPLY_CLEAN"
                || strategy === "UNDO_STASH_POP_TOP"
                || strategy === "UNDO_STASH_DROP_TOP") {
            a = String(plan.branch || "");
            b = String(plan.expectedHead || "");
            c = String(plan.beforeStashSha || "");
            d = String(plan.afterStashSha || "");
            e = String(plan.expectedAfterIndexTree || "");
            f = String(plan.expectedAfterWorktreeHash || "");
            g =
                String(plan.expectedAfterUntrackedHash || "")
                + "\t"
                + String(plan.restoreIndexTree || "")
                + "\t"
                + String(plan.restoreWorktreeHash || "")
                + "\t"
                + String(plan.restoreUntrackedHash || "")
                + "\t"
                + (plan.useIndex ? "1" : "0");
        } else if (strategy === "UNDO_STASH_CREATE_ALL") {
            a = String(plan.branch || "");
            b = String(plan.expectedHead || "");
            c = String(plan.stashSha || "");
            d = String(plan.previousStashSha || "");
            e = String(plan.expectedAfterIndexTree || "");
            f = String(plan.expectedAfterWorktreeHash || "");
            g =
                String(plan.expectedAfterUntrackedHash || "")
                + "\t"
                + String(plan.restoreIndexTree || "")
                + "\t"
                + String(plan.restoreWorktreeHash || "")
                + "\t"
                + String(plan.restoreUntrackedHash || "");
        } else if (strategy === "UNDO_ABSORB_STAGED") {
            a = String(plan.branch || "");
            b = String(plan.restoreSha || "");
            c = String(plan.expectedSha || "");
            d = String(plan.patchBase64 || "");
            e = String(plan.fingerprint || "");
            f = String(plan.patchBytes || "");
        } else if (strategy === "UNDO_TRANSFER_CONTENT") {
            a = String(plan.sourcePath || "");
            b = String(plan.destinationPath || "");
            c =
                String(plan.mode || "")
                + "\t"
                + String(plan.layer || "worktree");
            d = String(plan.patchBase64 || "");
            e = String(plan.sourceHead || "");
            f = String(plan.destinationHead || "");
            g = String(plan.fingerprint || "");
        }

        recoveryProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'strategy="$2"',
                'a="$3"',
                'b="$4"',
                'c="$5"',
                'd="$6"',
                'e="$7"',
                'f="$8"',
                'g="$9"',
                'fingerprint_tree() {',
                '  python3 - "$1" <<\'PY\'',
                'import hashlib, os, stat, sys',
                'root = os.path.realpath(sys.argv[1])',
                'h = hashlib.sha256()',
                'for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):',
                '    dirnames.sort(); filenames.sort()',
                '    for name in list(dirnames) + list(filenames):',
                '        path = os.path.join(dirpath, name)',
                '        rel = os.path.relpath(path, root)',
                '        st = os.lstat(path)',
                '        h.update(rel.encode("utf-8", "surrogateescape") + b"\\0")',
                '        h.update(str(stat.S_IFMT(st.st_mode)).encode() + b":" + str(stat.S_IMODE(st.st_mode)).encode() + b"\\0")',
                '        if stat.S_ISLNK(st.st_mode):',
                '            h.update(os.readlink(path).encode("utf-8", "surrogateescape"))',
                '        elif stat.S_ISREG(st.st_mode):',
                '            with open(path, "rb") as handle:',
                '                while True:',
                '                    chunk = handle.read(1024 * 1024)',
                '                    if not chunk:',
                '                        break',
                '                    h.update(chunk)',
                '        h.update(b"\\0")',
                'print(h.hexdigest())',
                'PY',
                '}',
                'untracked_content_hash() {',
                '  local target="$1"',
                '  git -C "$target" ls-files --others --exclude-standard -z 2>/dev/null | while IFS= read -r -d "" p; do printf "%s\\0" "$p"; git -C "$target" hash-object -- "$p" 2>/dev/null || true; done | git -C "$target" hash-object --stdin 2>/dev/null || true',
                '}',
                'stash_stack() {',
                '  git -C "$1" stash list --format="%H" 2>/dev/null | paste -sd, -',
                '}',
                'stash_stack_objects_exist() {',
                '  local target="$1" csv="$2" sha',
                '  [ -z "$csv" ] && return 0',
                '  IFS="," read -ra stack_rows <<<"$csv"',
                '  for sha in "${stack_rows[@]}"; do',
                '    [ -n "$sha" ] || continue',
                '    git -C "$target" cat-file -e "$sha^{commit}" 2>/dev/null || return 1',
                '  done',
                '}',
                'rebuild_stash_stack() {',
                '  local target="$1" csv="$2" sha message i',
                '  stash_stack_objects_exist "$target" "$csv" || return 1',
                '  git -C "$target" update-ref -d refs/stash >/dev/null 2>&1 || true',
                '  [ -z "$csv" ] && return 0',
                '  IFS="," read -ra stack_rows <<<"$csv"',
                '  for ((i=${#stack_rows[@]}-1; i>=0; i--)); do',
                '    sha="${stack_rows[$i]}"',
                '    [ -n "$sha" ] || continue',
                '    message="$(git -C "$target" log -1 --format=%s "$sha" 2>/dev/null || printf "Post-Apollo restored stash")"',
                '    git -C "$target" stash store -m "$message" "$sha" >/dev/null 2>&1 || return 1',
                '  done',
                '}',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "REFUSED\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'if [ "$strategy" != "UNDO_TRANSFER_CONTENT" ] && [ "$strategy" != "UNDO_COMMIT_TO_STAGED" ] && [ "$strategy" != "UNDO_RESET_SOFT_OR_MIXED" ] && [ "$strategy" != "UNDO_STASH_CREATE_ALL" ] && [ "$strategy" != "UNDO_STASH_CREATE_EXACT" ] && [ "$strategy" != "UNDO_STASH_APPLY_CLEAN" ] && [ "$strategy" != "UNDO_STASH_POP_TOP" ] && [ "$strategy" != "UNDO_STASH_DROP_TOP" ] && [ "$strategy" != "UNDO_STASH_APPLY_REF" ] && [ "$strategy" != "UNDO_STASH_POP_REF" ] && [ "$strategy" != "UNDO_STASH_DROP_REF" ]; then',
                '  while IFS= read -r wt; do',
                '    [ -n "$wt" ] || continue',
                '    if [ -n "$(git -C "$wt" status --porcelain=v1 --untracked-files=all 2>/dev/null)" ]; then',
                '      printf "REFUSED\\tWORKTREE DIRTY // UNDO WILL NOT DISCARD CONTENT\\n"',
                '      exit 22',
                '    fi',
                '  done < <(git -C "$repo" worktree list --porcelain 2>/dev/null | sed -n "s/^worktree //p")',
                'fi',
                'zeros="0000000000000000000000000000000000000000"',
                'case "$strategy" in',
                '  DELETE_EXACT_CLONE)',
                '    clone_path="$a"',
                '    expected_head="$b"',
                '    expected_branch="$c"',
                '    expected_origin="$d"',
                '    expected_fingerprint="$e"',
                '    [ -n "$clone_path" ] && [ -n "$expected_head" ] && [ -n "$expected_fingerprint" ] || { printf "REFUSED\\tCLONE RECOVERY IDENTITY MISSING\\n"; exit 23; }',
                '    [ -d "$clone_path" ] && [ ! -L "$clone_path" ] || { printf "REFUSED\\tCLONE DESTINATION IS MISSING OR NOT A REAL DIRECTORY\\n"; exit 24; }',
                '    clone_path="$(realpath "$clone_path" 2>/dev/null || true)"',
                '    repo_top="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null || true)"',
                '    repo_top="$(realpath "$repo_top" 2>/dev/null || true)"',
                '    [ -n "$clone_path" ] && [ "$repo_top" = "$clone_path" ] || { printf "REFUSED\\tCURRENT REPOSITORY IS NOT THE RECORDED CLONE\\n"; exit 25; }',
                '    projects="$(realpath "$HOME/Projects" 2>/dev/null || true)"',
                '    [ -n "$projects" ] || { printf "REFUSED\\tPROJECTS ROOT CANNOT BE RESOLVED\\n"; exit 26; }',
                '    case "$clone_path" in "$projects"/*) ;; *) printf "REFUSED\\tCLONE DESTINATION IS OUTSIDE PROJECTS ROOT\\n"; exit 27 ;; esac',
                '    actual_head="$(git -C "$clone_path" rev-parse HEAD 2>/dev/null || true)"',
                '    actual_branch="$(git -C "$clone_path" branch --show-current 2>/dev/null || true)"',
                '    actual_origin="$(git -C "$clone_path" remote get-url origin 2>/dev/null || true)"',
                '    [ "$actual_head" = "$expected_head" ] || { printf "REFUSED\\tCLONE HEAD CHANGED SINCE CREATION\\n"; exit 28; }',
                '    [ "$actual_branch" = "$expected_branch" ] || { printf "REFUSED\\tCLONE BRANCH CHANGED SINCE CREATION\\n"; exit 29; }',
                '    [ "$actual_origin" = "$expected_origin" ] || { printf "REFUSED\\tCLONE ORIGIN CHANGED SINCE CREATION\\n"; exit 30; }',
                '    worktree_count="$(git -C "$clone_path" worktree list --porcelain 2>/dev/null | grep -c "^worktree " || true)"',
                '    [ "$worktree_count" = "1" ] || { printf "REFUSED\\tCLONE HAS ADDITIONAL WORKTREES\\n"; exit 31; }',
                '    actual_fingerprint="$(fingerprint_tree "$clone_path" 2>/dev/null || true)"',
                '    [ -n "$actual_fingerprint" ] && [ "$actual_fingerprint" = "$expected_fingerprint" ] || { printf "REFUSED\\tCLONE DIRECTORY CHANGED SINCE CREATION\\n"; exit 32; }',
                '    python3 - "$clone_path" <<\'PY\'',
                'import os, shutil, sys',
                'path = os.path.realpath(sys.argv[1])',
                'if not os.path.isdir(path) or os.path.islink(path):',
                '    raise SystemExit(1)',
                'shutil.rmtree(path)',
                'PY',
                '    rc=$?',
                '    [ "$rc" -eq 0 ] && [ ! -e "$clone_path" ] && [ ! -L "$clone_path" ] || { printf "REFUSED\\tEXACT CLONE DELETE FAILED\\n"; exit 33; }',
                '    printf "OK\\tUNDID CLONE // EXACT CREATED REPOSITORY REMOVED\\n"',
                '    ;;',
                '  DELETE_CREATED_BRANCH)',
                '    branch="$a"',
                '    expected="$c"',
                '    ref="refs/heads/$branch"',
                '    current="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$current" != "$ref" ] || { printf "REFUSED\\tCREATED BRANCH IS CURRENTLY CHECKED OUT\\n"; exit 31; }',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tBRANCH MOVED SINCE RECORDED OPERATION\\n"; exit 32; }',
                '    if git -C "$repo" worktree list --porcelain 2>/dev/null | grep -Fqx "branch $ref"; then',
                '      printf "REFUSED\\tBRANCH IS CHECKED OUT IN A WORKTREE\\n"',
                '      exit 33',
                '    fi',
                '    git -C "$repo" update-ref -d "$ref" "$expected" || { printf "REFUSED\\tGUARDED REF DELETE FAILED\\n"; exit 34; }',
                '    printf "OK\\tDELETED CREATED BRANCH // %s\\n" "$branch"',
                '    ;;',
                '  DELETE_CREATED_TAG)',
                '    tag="$a"',
                '    expected="$c"',
                '    ref="refs/tags/$tag"',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tTAG MOVED SINCE RECORDED OPERATION\\n"; exit 35; }',
                '    git -C "$repo" update-ref -d "$ref" "$expected" || { printf "REFUSED\\tGUARDED TAG DELETE FAILED\\n"; exit 36; }',
                '    printf "OK\\tDELETED CREATED TAG // %s\\n" "$tag"',
                '    ;;',
                '  SWITCH_BACK_FROM_DETACHED)',
                '    previous="$a"',
                '    expected_previous="$b"',
                '    expected_detached="$c"',
                '    previous_ref="refs/heads/$previous"',
                '    current_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ -z "$current_ref" ] || { printf "REFUSED\\tHEAD IS NO LONGER DETACHED\\n"; exit 37; }',
                '    actual_head="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                '    [ "$actual_head" = "$expected_detached" ] || { printf "REFUSED\\tDETACHED HEAD MOVED SINCE OPERATION\\n"; exit 38; }',
                '    actual_previous="$(git -C "$repo" rev-parse -q --verify "$previous_ref" 2>/dev/null || true)"',
                '    [ "$actual_previous" = "$expected_previous" ] || { printf "REFUSED\\tPREVIOUS BRANCH MOVED SINCE DETACH\\n"; exit 39; }',
                '    if git -C "$repo" worktree list --porcelain 2>/dev/null | grep -Fqx "branch $previous_ref"; then',
                '      printf "REFUSED\\tPREVIOUS BRANCH IS CHECKED OUT ELSEWHERE\\n"',
                '      exit 40',
                '    fi',
                '    git -C "$repo" switch "$previous" >/dev/null 2>&1 || { printf "REFUSED\\tSWITCH BACK FROM DETACHED FAILED\\n"; exit 41; }',
                '    printf "OK\\tSWITCHED BACK FROM DETACHED // %s\\n" "$previous"',
                '    ;;',
                '  RENAME_BRANCH_BACK)',
                '    old="$a"',
                '    new="$b"',
                '    expected="$c"',
                '    oldref="refs/heads/$old"',
                '    newref="refs/heads/$new"',
                '    git -C "$repo" show-ref --verify --quiet "$oldref" && { printf "REFUSED\\tORIGINAL BRANCH NAME NOW EXISTS\\n"; exit 41; }',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$newref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tRENAMED BRANCH MOVED SINCE RECORDED OPERATION\\n"; exit 42; }',
                '    git -C "$repo" branch -m "$new" "$old" >/dev/null 2>&1 || { printf "REFUSED\\tGUARDED RENAME BACK FAILED\\n"; exit 43; }',
                '    printf "OK\\tRENAMED %s BACK TO %s\\n" "$new" "$old"',
                '    ;;',
                '  RESTORE_DELETED_BRANCH)',
                '    branch="$a"',
                '    restore="$b"',
                '    upstream="$c"',
                '    ref="refs/heads/$branch"',
                '    git -C "$repo" show-ref --verify --quiet "$ref" && { printf "REFUSED\\tBRANCH NAME NOW EXISTS\\n"; exit 51; }',
                '    git -C "$repo" cat-file -e "$restore^{commit}" 2>/dev/null || { printf "REFUSED\\tRECOVERY COMMIT MISSING\\n"; exit 52; }',
                '    git -C "$repo" update-ref "$ref" "$restore" "$zeros" || { printf "REFUSED\\tGUARDED REF RESTORE FAILED\\n"; exit 53; }',
                '    if [ -n "$upstream" ]; then',
                '      git -C "$repo" branch --set-upstream-to="$upstream" "$branch" >/dev/null 2>&1 || {',
                '        git -C "$repo" update-ref -d "$ref" "$restore" >/dev/null 2>&1 || true',
                '        printf "REFUSED\\tUPSTREAM RESTORE FAILED // BRANCH ROLLED BACK\\n"',
                '        exit 54',
                '      }',
                '    fi',
                '    printf "OK\\tRESTORED DELETED BRANCH // %s\\n" "$branch"',
                '    ;;',
                '  SWITCH_BACK)',
                '    current="$a"',
                '    previous="$b"',
                '    expected_current="$c"',
                '    expected_previous="$d"',
                '    current_ref="refs/heads/$current"',
                '    previous_ref="refs/heads/$previous"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$current_ref" ] || { printf "REFUSED\\tCURRENT BRANCH CHANGED SINCE RECORDED SWITCH\\n"; exit 61; }',
                '    actual_current="$(git -C "$repo" rev-parse -q --verify "$current_ref" 2>/dev/null || true)"',
                '    actual_previous="$(git -C "$repo" rev-parse -q --verify "$previous_ref" 2>/dev/null || true)"',
                '    [ "$actual_current" = "$expected_current" ] || { printf "REFUSED\\tCURRENT BRANCH MOVED SINCE RECORDED SWITCH\\n"; exit 62; }',
                '    [ "$actual_previous" = "$expected_previous" ] || { printf "REFUSED\\tPREVIOUS BRANCH MOVED SINCE RECORDED SWITCH\\n"; exit 63; }',
                '    if git -C "$repo" worktree list --porcelain 2>/dev/null | grep -Fqx "branch $previous_ref"; then',
                '      printf "REFUSED\\tPREVIOUS BRANCH IS CHECKED OUT ELSEWHERE\\n"',
                '      exit 64',
                '    fi',
                '    git -C "$repo" switch "$previous" >/dev/null 2>&1 || { printf "REFUSED\\tSWITCH BACK FAILED\\n"; exit 65; }',
                '    printf "OK\\tSWITCHED BACK // %s -> %s\\n" "$current" "$previous"',
                '    ;;',
                '  RESTORE_UPSTREAM)',
                '    branch="$a"',
                '    expected_upstream="$b"',
                '    restore_upstream="$c"',
                '    expected_sha="$d"',
                '    ref="refs/heads/$branch"',
                '    actual_sha="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '    [ "$actual_sha" = "$expected_sha" ] || { printf "REFUSED\\tBRANCH MOVED SINCE UPSTREAM OPERATION\\n"; exit 71; }',
                '    actual_upstream="$(git -C "$repo" for-each-ref --format="%(upstream:short)" "$ref" 2>/dev/null)"',
                '    [ "$actual_upstream" = "$expected_upstream" ] || { printf "REFUSED\\tUPSTREAM CHANGED SINCE RECORDED OPERATION\\n"; exit 72; }',
                '    if [ -n "$restore_upstream" ]; then',
                '      git -C "$repo" branch --set-upstream-to="$restore_upstream" "$branch" >/dev/null 2>&1 || { printf "REFUSED\\tRESTORE UPSTREAM FAILED\\n"; exit 73; }',
                '    else',
                '      git -C "$repo" branch --unset-upstream "$branch" >/dev/null 2>&1 || { printf "REFUSED\\tCLEAR RESTORED UPSTREAM FAILED\\n"; exit 74; }',
                '    fi',
                '    printf "OK\\tRESTORED UPSTREAM // %s\\n" "$branch"',
                '    ;;',
                '  REMOVE_ADDED_WORKTREE|REMOVE_NEW_WORKTREE_AND_BRANCH)',
                '    path="$a"',
                '    branch="$b"',
                '    expected="$c"',
                '    [ -n "$path" ] && [ -n "$branch" ] || { printf "REFUSED\\tWORKTREE IDENTITY MISSING\\n"; exit 81; }',
                '    wt_head="$(git -C "$path" rev-parse HEAD 2>/dev/null || true)"',
                '    wt_branch="$(git -C "$path" branch --show-current 2>/dev/null || true)"',
                '    [ "$wt_head" = "$expected" ] && [ "$wt_branch" = "$branch" ] || { printf "REFUSED\\tWORKTREE CHANGED SINCE RECORDED OPERATION\\n"; exit 82; }',
                '    git -C "$repo" worktree remove "$path" >/dev/null 2>&1 || { printf "REFUSED\\tWORKTREE REMOVE FAILED\\n"; exit 83; }',
                '    if [ "$strategy" = "REMOVE_NEW_WORKTREE_AND_BRANCH" ]; then',
                '      ref="refs/heads/$branch"',
                '      actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '      [ "$actual" = "$expected" ] || { printf "REFUSED\\tNEW BRANCH MOVED BEFORE DELETE\\n"; exit 84; }',
                '      if git -C "$repo" worktree list --porcelain 2>/dev/null | grep -Fqx "branch $ref"; then',
                '        printf "REFUSED\\tNEW BRANCH CHECKED OUT ELSEWHERE\\n"',
                '        exit 85',
                '      fi',
                '      git -C "$repo" update-ref -d "$ref" "$expected" || { printf "REFUSED\\tNEW BRANCH DELETE FAILED\\n"; exit 86; }',
                '    fi',
                '    printf "OK\\tREMOVED RECORDED WORKTREE // %s\\n" "$path"',
                '    ;;',
                '  RESTORE_REMOVED_WORKTREE)',
                '    path="$a"',
                '    branch="$b"',
                '    expected="$c"',
                '    detached="$d"',
                '    [ ! -e "$path" ] || { printf "REFUSED\\tWORKTREE PATH NOW EXISTS\\n"; exit 91; }',
                '    if [ "$detached" = "1" ]; then',
                '      git -C "$repo" cat-file -e "$expected^{commit}" 2>/dev/null || { printf "REFUSED\\tDETACHED RECOVERY COMMIT MISSING\\n"; exit 92; }',
                '      git -C "$repo" worktree add --detach "$path" "$expected" >/dev/null 2>&1 || { printf "REFUSED\\tDETACHED WORKTREE RESTORE FAILED\\n"; exit 93; }',
                '    else',
                '      ref="refs/heads/$branch"',
                '      actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '      [ "$actual" = "$expected" ] || { printf "REFUSED\\tWORKTREE BRANCH MOVED SINCE REMOVAL\\n"; exit 94; }',
                '      if git -C "$repo" worktree list --porcelain 2>/dev/null | grep -Fqx "branch $ref"; then',
                '        printf "REFUSED\\tWORKTREE BRANCH CHECKED OUT ELSEWHERE\\n"',
                '        exit 95',
                '      fi',
                '      git -C "$repo" worktree add "$path" "$branch" >/dev/null 2>&1 || { printf "REFUSED\\tWORKTREE RESTORE FAILED\\n"; exit 96; }',
                '    fi',
                '    printf "OK\\tRESTORED REMOVED WORKTREE // %s\\n" "$path"',
                '    ;;',
                '  RESTORE_PULLED_BRANCH)',
                '    branch="$a"',
                '    restore="$b"',
                '    expected="$c"',
                '    ref="refs/heads/$branch"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$ref" ] || { printf "REFUSED\\tPULLED BRANCH IS NOT CURRENTLY CHECKED OUT\\n"; exit 179; }',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tPULLED BRANCH MOVED SINCE OPERATION\\n"; exit 180; }',
                '    git -C "$repo" cat-file -e "$restore^{commit}" 2>/dev/null || { printf "REFUSED\\tPRE-PULL COMMIT MISSING\\n"; exit 181; }',
                '    git -C "$repo" update-ref ORIG_HEAD "$expected" >/dev/null 2>&1 || true',
                '    git -C "$repo" update-ref "$ref" "$restore" "$expected" || { printf "REFUSED\\tGUARDED PULL REF RESTORE FAILED\\n"; exit 182; }',
                '    if ! git -C "$repo" reset --hard "$restore" >/dev/null 2>&1; then',
                '      git -C "$repo" update-ref "$ref" "$expected" "$restore" >/dev/null 2>&1 || { printf "REFUSED\\tPULL WORKTREE REALIGN FAILED // REF ROLLBACK FAILED\\n"; exit 183; }',
                '      git -C "$repo" reset --hard "$expected" >/dev/null 2>&1 || true',
                '      printf "REFUSED\\tPULL WORKTREE REALIGN FAILED // REF ROLLED BACK\\n"',
                '      exit 184',
                '    fi',
                '    printf "OK\\tRESTORED PRE-PULL LOCAL BRANCH // FETCHED REMOTE REFS RETAINED // %s\\n" "$branch"',
                '    ;;',
                '  RESTORE_BACKGROUND_PULL_REF)',
                '    branch="$a"',
                '    restore="$b"',
                '    expected="$c"',
                '    current_branch="$d"',
                '    expected_current_head="$e"',
                '    ref="refs/heads/$branch"',
                '    current_ref="refs/heads/$current_branch"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$current_ref" ] || { printf "REFUSED\\tCHECKED-OUT BRANCH CHANGED SINCE BACKGROUND PULL\\n"; exit 185; }',
                '    actual_current_head="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                '    [ "$actual_current_head" = "$expected_current_head" ] || { printf "REFUSED\\tCHECKED-OUT HEAD MOVED SINCE BACKGROUND PULL\\n"; exit 186; }',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tBACKGROUND PULL TARGET MOVED SINCE OPERATION\\n"; exit 187; }',
                '    git -C "$repo" cat-file -e "$restore^{commit}" 2>/dev/null || { printf "REFUSED\\tPRE-PULL TARGET COMMIT MISSING\\n"; exit 188; }',
                '    if git -C "$repo" worktree list --porcelain 2>/dev/null | grep -Fqx "branch $ref"; then',
                '      printf "REFUSED\\tBACKGROUND PULL TARGET IS NOW CHECKED OUT IN A WORKTREE\\n"',
                '      exit 189',
                '    fi',
                '    git -C "$repo" update-ref "$ref" "$restore" "$expected" || { printf "REFUSED\\tGUARDED BACKGROUND PULL REF RESTORE FAILED\\n"; exit 190; }',
                '    printf "OK\\tRESTORED PRE-PULL BACKGROUND BRANCH // FETCHED REMOTE REFS RETAINED // %s\\n" "$branch"',
                '    ;;',
                '  UNDO_RESET_SOFT_OR_MIXED)',
                '    branch="$a"',
                '    restore="$b"',
                '    expected="$c"',
                '    mode="$d"',
                '    expected_index_tree="$e"',
                '    expected_worktree_hash="$f"',
                '    IFS="$(printf "\t")" read -r expected_status64 expected_untracked_hash <<<"$g"',
                '    case "$mode" in soft|mixed) ;; *) printf "REFUSED\tINVALID RECORDED RESET MODE\n"; exit 191 ;; esac',
                '    ref="refs/heads/$branch"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$ref" ] || { printf "REFUSED\tRESET BRANCH IS NOT CURRENTLY CHECKED OUT\n"; exit 192; }',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\tRESET BRANCH MOVED SINCE OPERATION\n"; exit 193; }',
                '    git -C "$repo" cat-file -e "$restore^{commit}" 2>/dev/null || { printf "REFUSED\tPRE-RESET COMMIT MISSING\n"; exit 194; }',
                '    [ -z "$(git -C "$repo" ls-files -u 2>/dev/null)" ] || { printf "REFUSED\tCURRENT INDEX HAS CONFLICTS\n"; exit 195; }',
                '    actual_index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                '    [ "$actual_index_tree" = "$expected_index_tree" ] || { printf "REFUSED\tINDEX CHANGED SINCE RESET\n"; exit 196; }',
                '    actual_worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_worktree_hash" = "$expected_worktree_hash" ] || { printf "REFUSED\tTRACKED WORKTREE CHANGED SINCE RESET\n"; exit 197; }',
                '    actual_status64="$(git -C "$repo" status --porcelain=v1 --untracked-files=all 2>/dev/null | base64 -w0 2>/dev/null || true)"',
                '    [ "$actual_status64" = "$expected_status64" ] || { printf "REFUSED\tWORKTREE STATUS CHANGED SINCE RESET\n"; exit 198; }',
                '    actual_untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_untracked_hash" = "$expected_untracked_hash" ] || { printf "REFUSED\tUNTRACKED SET CHANGED SINCE RESET\n"; exit 199; }',
                '    expected_tree="$(git -C "$repo" rev-parse "$expected^{tree}" 2>/dev/null || true)"',
                '    restore_tree="$(git -C "$repo" rev-parse "$restore^{tree}" 2>/dev/null || true)"',
                '    [ -n "$expected_tree" ] && [ -n "$restore_tree" ] || { printf "REFUSED\tRESET TREE IDENTITY MISSING\n"; exit 200; }',
                '    if [ "$mode" = "soft" ]; then',
                '      [ "$expected_index_tree" = "$restore_tree" ] || { printf "REFUSED\tSOFT RESET INDEX NO LONGER MATCHES PRE-RESET TREE\n"; exit 201; }',
                '    else',
                '      [ "$expected_index_tree" = "$expected_tree" ] || { printf "REFUSED\tMIXED RESET INDEX NO LONGER MATCHES RESET TARGET TREE\n"; exit 202; }',
                '    fi',
                '    repo_top="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null || true)"',
                '    while IFS= read -r wt; do',
                '      [ -n "$wt" ] || continue',
                '      [ "$(realpath "$wt" 2>/dev/null || printf %s "$wt")" = "$(realpath "$repo_top" 2>/dev/null || printf %s "$repo_top")" ] && continue',
                '      [ -z "$(git -C "$wt" status --porcelain=v1 --untracked-files=all 2>/dev/null)" ] || { printf "REFUSED\tANOTHER WORKTREE CHANGED SINCE RESET\n"; exit 203; }',
                '    done < <(git -C "$repo" worktree list --porcelain 2>/dev/null | sed -n "s/^worktree //p")',
                '    tmp_index="$(mktemp)"',
                '    rm -f "$tmp_index"',
                '    GIT_INDEX_FILE="$tmp_index" git -C "$repo" read-tree "$restore" >/dev/null 2>&1 || { rm -f "$tmp_index"; printf "REFUSED\tRESET WORKTREE PREFLIGHT INDEX CREATE FAILED\n"; exit 204; }',
                '    GIT_INDEX_FILE="$tmp_index" git -C "$repo" add -A -- . >/dev/null 2>&1 || { rm -f "$tmp_index"; printf "REFUSED\tRESET WORKTREE PREFLIGHT MATERIALIZATION FAILED\n"; exit 205; }',
                '    worktree_tree="$(GIT_INDEX_FILE="$tmp_index" git -C "$repo" write-tree 2>/dev/null || true)"',
                '    rm -f "$tmp_index"',
                '    [ "$worktree_tree" = "$restore_tree" ] || { printf "REFUSED\tWORKTREE CONTENT NO LONGER MATCHES PRE-RESET TREE\n"; exit 206; }',
                '    git -C "$repo" update-ref "$ref" "$restore" "$expected" || { printf "REFUSED\tGUARDED RESET HEAD RESTORE FAILED\n"; exit 207; }',
                '    if [ "$mode" = "mixed" ]; then',
                '      if ! git -C "$repo" reset --mixed "$restore" >/dev/null 2>&1; then',
                '        git -C "$repo" update-ref "$ref" "$expected" "$restore" >/dev/null 2>&1 || { printf "REFUSED\tMIXED RESET UNDO FAILED // REF ROLLBACK FAILED\n"; exit 208; }',
                '        git -C "$repo" read-tree "$expected" >/dev/null 2>&1 || true',
                '        printf "REFUSED\tMIXED RESET UNDO FAILED // OPERATION ROLLED BACK\n"',
                '        exit 209',
                '      fi',
                '    fi',
                '    if [ -n "$(git -C "$repo" status --porcelain=v1 --untracked-files=all 2>/dev/null)" ]; then',
                '      git -C "$repo" update-ref "$ref" "$expected" "$restore" >/dev/null 2>&1 || { printf "REFUSED\tRESET UNDO VERIFICATION FAILED // REF ROLLBACK FAILED\n"; exit 210; }',
                '      if [ "$mode" = "mixed" ]; then git -C "$repo" read-tree "$expected" >/dev/null 2>&1 || true; fi',
                '      printf "REFUSED\tRESET UNDO VERIFICATION FAILED // OPERATION ROLLED BACK\n"',
                '      exit 211',
                '    fi',
                '    git -C "$repo" update-ref ORIG_HEAD "$expected" >/dev/null 2>&1 || true',
                '    printf "OK\tRESTORED PRE-RESET HEAD + INDEX/WORKTREE // %s // %s\n" "$mode" "$branch"',
                '    ;;',
                '  RESTORE_REWRITTEN_BRANCH)',
                '    branch="$a"',
                '    restore="$b"',
                '    expected="$c"',
                '    ref="refs/heads/$branch"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$ref" ] || { printf "REFUSED\\tREWRITTEN BRANCH IS NOT CURRENTLY CHECKED OUT\\n"; exit 97; }',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tREWRITTEN BRANCH MOVED SINCE OPERATION\\n"; exit 98; }',
                '    git -C "$repo" cat-file -e "$restore^{commit}" 2>/dev/null || { printf "REFUSED\\tPRE-REWRITE COMMIT MISSING\\n"; exit 99; }',
                '    git -C "$repo" update-ref ORIG_HEAD "$expected" >/dev/null 2>&1 || true',
                '    git -C "$repo" update-ref "$ref" "$restore" "$expected" || { printf "REFUSED\\tGUARDED REWRITE RESTORE FAILED\\n"; exit 122; }',
                '    if ! git -C "$repo" reset --hard "$restore" >/dev/null 2>&1; then',
                '      git -C "$repo" update-ref "$ref" "$expected" "$restore" >/dev/null 2>&1 || { printf "REFUSED\\tREWRITE WORKTREE REALIGN FAILED // REF ROLLBACK FAILED\\n"; exit 123; }',
                '      git -C "$repo" reset --hard "$expected" >/dev/null 2>&1 || true',
                '      printf "REFUSED\\tREWRITE WORKTREE REALIGN FAILED // REF ROLLED BACK\\n"',
                '      exit 124',
                '    fi',
                '    printf "OK\\tRESTORED PRE-OPERATION HEAD // %s\\n" "$branch"',
                '    ;;',
                '  UNDO_COMMIT_TO_STAGED)',
                '    branch="$a"',
                '    restore="$b"',
                '    expected="$c"',
                '    expected_index_tree="$d"',
                '    expected_worktree_hash="$e"',
                '    expected_untracked_hash="$f"',
                '    ref="refs/heads/$branch"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$ref" ] || { printf "REFUSED\\tCOMMIT BRANCH IS NOT CURRENTLY CHECKED OUT\\n"; exit 141; }',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tCOMMIT BRANCH MOVED SINCE OPERATION\\n"; exit 142; }',
                '    git -C "$repo" cat-file -e "$restore^{commit}" 2>/dev/null || { printf "REFUSED\\tPRE-COMMIT HEAD MISSING\\n"; exit 143; }',
                '    [ -z "$(git -C "$repo" ls-files -u 2>/dev/null)" ] || { printf "REFUSED\\tCURRENT INDEX HAS CONFLICTS\\n"; exit 144; }',
                '    actual_index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                '    [ "$actual_index_tree" = "$expected_index_tree" ] || { printf "REFUSED\\tINDEX CHANGED SINCE COMMIT\\n"; exit 145; }',
                '    expected_head_tree="$(git -C "$repo" rev-parse "$expected^{tree}" 2>/dev/null || true)"',
                '    [ "$expected_head_tree" = "$expected_index_tree" ] || { printf "REFUSED\\tRECORDED COMMIT INDEX NO LONGER MATCHES HEAD TREE\\n"; exit 146; }',
                '    actual_worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_worktree_hash" = "$expected_worktree_hash" ] || { printf "REFUSED\\tWORKTREE CHANGED SINCE COMMIT\\n"; exit 147; }',
                '    actual_untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_untracked_hash" = "$expected_untracked_hash" ] || { printf "REFUSED\\tUNTRACKED FILE SET CHANGED SINCE COMMIT\\n"; exit 148; }',
                '    git -C "$repo" update-ref ORIG_HEAD "$expected" >/dev/null 2>&1 || true',
                '    git -C "$repo" update-ref "$ref" "$restore" "$expected" || { printf "REFUSED\\tGUARDED COMMIT UNDO REF RESTORE FAILED\\n"; exit 149; }',
                '    printf "OK\\tRESTORED PRE-COMMIT HEAD + STAGED CONTENT // %s\\n" "$branch"',
                '    ;;',
                '  UNDO_STASH_CREATE_EXACT)',
                '    branch="$a"',
                '    expected_head="$b"',
                '    stash_sha="$c"',
                '    mode="$d"',
                '    expected_index_tree="$e"',
                '    expected_worktree_hash="$f"',
                '    IFS="$(printf "\\t")" read -r expected_untracked_hash expected_untracked_content_hash restore_index_tree restore_worktree_hash restore_untracked_hash restore_untracked_content_hash before_stack after_stack <<<"$g"',
                '    ref="refs/heads/$branch"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$ref" ] || { printf "REFUSED\\tSTASH BRANCH IS NOT CURRENTLY CHECKED OUT\\n"; exit 212; }',
                '    actual_head="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                '    [ "$actual_head" = "$expected_head" ] || { printf "REFUSED\\tHEAD CHANGED SINCE STASH CREATION\\n"; exit 213; }',
                '    [ "$(stash_stack "$repo")" = "$after_stack" ] || { printf "REFUSED\\tSTASH STACK CHANGED SINCE CREATION\\n"; exit 214; }',
                '    stash_stack_objects_exist "$repo" "$before_stack" || { printf "REFUSED\\tPRE-STASH STACK OBJECT MISSING\\n"; exit 215; }',
                '    git -C "$repo" cat-file -e "$stash_sha^{commit}" 2>/dev/null || { printf "REFUSED\\tCREATED STASH OBJECT MISSING\\n"; exit 216; }',
                '    [ -z "$(git -C "$repo" ls-files -u 2>/dev/null)" ] || { printf "REFUSED\\tCURRENT INDEX HAS CONFLICTS\\n"; exit 217; }',
                '    actual_index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                '    [ "$actual_index_tree" = "$expected_index_tree" ] || { printf "REFUSED\\tINDEX CHANGED SINCE STASH CREATION\\n"; exit 218; }',
                '    actual_worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_worktree_hash" = "$expected_worktree_hash" ] || { printf "REFUSED\\tWORKTREE CHANGED SINCE STASH CREATION\\n"; exit 219; }',
                '    actual_untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_untracked_hash" = "$expected_untracked_hash" ] || { printf "REFUSED\\tUNTRACKED SET CHANGED SINCE STASH CREATION\\n"; exit 220; }',
                '    actual_untracked_content_hash="$(untracked_content_hash "$repo")"',
                '    [ "$actual_untracked_content_hash" = "$expected_untracked_content_hash" ] || { printf "REFUSED\\tUNTRACKED CONTENT CHANGED SINCE STASH CREATION\\n"; exit 221; }',
                '    case "$mode" in all|keep-index|staged) ;; *) printf "REFUSED\\tINVALID RECORDED STASH MODE\\n"; exit 222 ;; esac',
                '    restore_post_creation() {',
                '      git -C "$repo" reset --hard "$expected_head" >/dev/null 2>&1 || return 1',
                '      git -C "$repo" read-tree "$expected_index_tree" >/dev/null 2>&1 || return 1',
                '      git -C "$repo" checkout-index -a -f >/dev/null 2>&1 || return 1',
                '      if [ "$mode" != "staged" ]; then git -C "$repo" clean -fd >/dev/null 2>&1 || return 1; fi',
                '      rebuild_stash_stack "$repo" "$after_stack" || return 1',
                '    }',
                '    if [ "$mode" != "staged" ]; then',
                '      git -C "$repo" reset --hard "$expected_head" >/dev/null 2>&1 || { printf "REFUSED\\tSTASH UNDO CLEAN RESET FAILED\\n"; exit 223; }',
                '      git -C "$repo" clean -fd >/dev/null 2>&1 || { printf "REFUSED\\tSTASH UNDO CLEAN FAILED\\n"; exit 224; }',
                '    fi',
                '    if ! git -C "$repo" stash apply --index "$stash_sha" >/dev/null 2>&1; then',
                '      restore_post_creation >/dev/null 2>&1 || { printf "REFUSED\\tSTASH RESTORE FAILED // POST-STATE ROLLBACK FAILED\\n"; exit 225; }',
                '      printf "REFUSED\\tSTASH RESTORE FAILED // POST-STATE RESTORED\\n"',
                '      exit 226',
                '    fi',
                '    if ! rebuild_stash_stack "$repo" "$before_stack"; then',
                '      restore_post_creation >/dev/null 2>&1 || { printf "REFUSED\\tSTASH STACK RESTORE FAILED // POST-STATE ROLLBACK FAILED\\n"; exit 227; }',
                '      printf "REFUSED\\tSTASH STACK RESTORE FAILED // POST-STATE RESTORED\\n"',
                '      exit 228',
                '    fi',
                '    restored_index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                '    restored_worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    restored_untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    restored_untracked_content_hash="$(untracked_content_hash "$repo")"',
                '    restored_stack="$(stash_stack "$repo")"',
                '    if [ "$restored_index_tree" != "$restore_index_tree" ] || [ "$restored_worktree_hash" != "$restore_worktree_hash" ] || [ "$restored_untracked_hash" != "$restore_untracked_hash" ] || [ "$restored_untracked_content_hash" != "$restore_untracked_content_hash" ] || [ "$restored_stack" != "$before_stack" ]; then',
                '      restore_post_creation >/dev/null 2>&1 || { printf "REFUSED\\tSTASH RESTORE EVIDENCE MISMATCH // POST-STATE ROLLBACK FAILED\\n"; exit 229; }',
                '      printf "REFUSED\\tSTASH RESTORE EVIDENCE MISMATCH // POST-STATE RESTORED\\n"',
                '      exit 230',
                '    fi',
                '    printf "OK\\tRESTORED PRE-STASH CONTENT + STACK // %s\\n" "$mode"',
                '    ;;',
                '  UNDO_STASH_APPLY_REF|UNDO_STASH_POP_REF|UNDO_STASH_DROP_REF)',
                '    branch="$a"',
                '    expected_head="$b"',
                '    selected_stash="$c"',
                '    selected_ref="$d"',
                '    expected_index_tree="$e"',
                '    expected_worktree_hash="$f"',
                '    IFS="$(printf "\\t")" read -r expected_untracked_hash expected_untracked_content_hash restore_index_tree restore_worktree_hash restore_untracked_hash restore_untracked_content_hash before_stack after_stack use_index <<<"$g"',
                '    ref="refs/heads/$branch"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$ref" ] || { printf "REFUSED\\tSTASH MUTATION BRANCH IS NOT CURRENTLY CHECKED OUT\\n"; exit 231; }',
                '    actual_head="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                '    [ "$actual_head" = "$expected_head" ] || { printf "REFUSED\\tHEAD CHANGED SINCE STASH MUTATION\\n"; exit 232; }',
                '    [ "$(stash_stack "$repo")" = "$after_stack" ] || { printf "REFUSED\\tSTASH STACK CHANGED SINCE MUTATION\\n"; exit 233; }',
                '    stash_stack_objects_exist "$repo" "$before_stack" || { printf "REFUSED\\tRECORDED PRE-MUTATION STASH OBJECT MISSING\\n"; exit 234; }',
                '    git -C "$repo" cat-file -e "$selected_stash^{commit}" 2>/dev/null || { printf "REFUSED\\tSELECTED STASH OBJECT MISSING\\n"; exit 235; }',
                '    [ -z "$(git -C "$repo" ls-files -u 2>/dev/null)" ] || { printf "REFUSED\\tCURRENT INDEX HAS CONFLICTS\\n"; exit 236; }',
                '    actual_index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                '    [ "$actual_index_tree" = "$expected_index_tree" ] || { printf "REFUSED\\tINDEX CHANGED SINCE STASH MUTATION\\n"; exit 237; }',
                '    actual_worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_worktree_hash" = "$expected_worktree_hash" ] || { printf "REFUSED\\tWORKTREE CHANGED SINCE STASH MUTATION\\n"; exit 238; }',
                '    actual_untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_untracked_hash" = "$expected_untracked_hash" ] || { printf "REFUSED\\tUNTRACKED SET CHANGED SINCE STASH MUTATION\\n"; exit 239; }',
                '    actual_untracked_content_hash="$(untracked_content_hash "$repo")"',
                '    [ "$actual_untracked_content_hash" = "$expected_untracked_content_hash" ] || { printf "REFUSED\\tUNTRACKED CONTENT CHANGED SINCE STASH MUTATION\\n"; exit 240; }',
                '    reapply_selected() {',
                '      git -C "$repo" reset --hard "$expected_head" >/dev/null 2>&1 || return 1',
                '      git -C "$repo" clean -fd >/dev/null 2>&1 || return 1',
                '      if [ "$use_index" = "1" ]; then git -C "$repo" stash apply --index "$selected_stash" >/dev/null 2>&1; else git -C "$repo" stash apply "$selected_stash" >/dev/null 2>&1; fi',
                '    }',
                '    rollback_stash_mutation() {',
                '      rebuild_stash_stack "$repo" "$after_stack" >/dev/null 2>&1 || return 1',
                '      if [ "$strategy" = "UNDO_STASH_APPLY_REF" ] || [ "$strategy" = "UNDO_STASH_POP_REF" ]; then reapply_selected || return 1; fi',
                '    }',
                '    case "$strategy" in',
                '      UNDO_STASH_APPLY_REF)',
                '        git -C "$repo" reset --hard "$expected_head" >/dev/null 2>&1 || { printf "REFUSED\\tSTASH APPLY UNDO RESET FAILED\\n"; exit 241; }',
                '        git -C "$repo" clean -fd >/dev/null 2>&1 || { printf "REFUSED\\tSTASH APPLY UNDO CLEAN FAILED\\n"; exit 242; }',
                '        ;;',
                '      UNDO_STASH_POP_REF)',
                '        git -C "$repo" reset --hard "$expected_head" >/dev/null 2>&1 || { printf "REFUSED\\tSTASH POP UNDO RESET FAILED\\n"; exit 243; }',
                '        git -C "$repo" clean -fd >/dev/null 2>&1 || { printf "REFUSED\\tSTASH POP UNDO CLEAN FAILED\\n"; exit 244; }',
                '        rebuild_stash_stack "$repo" "$before_stack" || { rollback_stash_mutation >/dev/null 2>&1 || true; printf "REFUSED\\tSTASH POP STACK RESTORE FAILED\\n"; exit 245; }',
                '        ;;',
                '      UNDO_STASH_DROP_REF)',
                '        rebuild_stash_stack "$repo" "$before_stack" || { rollback_stash_mutation >/dev/null 2>&1 || true; printf "REFUSED\\tSTASH DROP STACK RESTORE FAILED\\n"; exit 246; }',
                '        ;;',
                '    esac',
                '    restored_index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                '    restored_worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    restored_untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    restored_untracked_content_hash="$(untracked_content_hash "$repo")"',
                '    restored_stack="$(stash_stack "$repo")"',
                '    if [ "$restored_index_tree" != "$restore_index_tree" ] || [ "$restored_worktree_hash" != "$restore_worktree_hash" ] || [ "$restored_untracked_hash" != "$restore_untracked_hash" ] || [ "$restored_untracked_content_hash" != "$restore_untracked_content_hash" ] || [ "$restored_stack" != "$before_stack" ]; then',
                '      rollback_stash_mutation >/dev/null 2>&1 || { printf "REFUSED\\tSTASH MUTATION UNDO EVIDENCE MISMATCH // ROLLBACK FAILED\\n"; exit 247; }',
                '      printf "REFUSED\\tSTASH MUTATION UNDO EVIDENCE MISMATCH // POST-STATE RESTORED\\n"',
                '      exit 248',
                '    fi',
                '    printf "OK\\tRESTORED PRE-STASH-MUTATION CONTENT + STACK // %s\\n" "$selected_ref"',
                '    ;;',
                '  UNDO_STASH_APPLY_CLEAN|UNDO_STASH_POP_TOP|UNDO_STASH_DROP_TOP)',
                '    branch="$a"',
                '    expected_head="$b"',
                '    before_stash="$c"',
                '    after_stash="$d"',
                '    expected_index_tree="$e"',
                '    expected_worktree_hash="$f"',
                '    IFS="$(printf "\\t")" read -r expected_untracked_hash restore_index_tree restore_worktree_hash restore_untracked_hash use_index <<<"$g"',
                '    ref="refs/heads/$branch"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$ref" ] || { printf "REFUSED\\tSTASH MUTATION BRANCH IS NOT CURRENTLY CHECKED OUT\\n"; exit 160; }',
                '    actual_head="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                '    [ "$actual_head" = "$expected_head" ] || { printf "REFUSED\\tHEAD CHANGED SINCE STASH MUTATION\\n"; exit 161; }',
                '    current_stash="$(git -C "$repo" rev-parse -q --verify refs/stash 2>/dev/null || true)"',
                '    [ "$current_stash" = "$after_stash" ] || { printf "REFUSED\\tSTASH STACK CHANGED SINCE MUTATION\\n"; exit 162; }',
                '    [ -z "$(git -C "$repo" ls-files -u 2>/dev/null)" ] || { printf "REFUSED\\tCURRENT INDEX HAS CONFLICTS\\n"; exit 163; }',
                '    actual_index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                '    [ "$actual_index_tree" = "$expected_index_tree" ] || { printf "REFUSED\\tINDEX CHANGED SINCE STASH MUTATION\\n"; exit 164; }',
                '    actual_worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_worktree_hash" = "$expected_worktree_hash" ] || { printf "REFUSED\\tWORKTREE CHANGED SINCE STASH MUTATION\\n"; exit 165; }',
                '    actual_untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_untracked_hash" = "$expected_untracked_hash" ] || { printf "REFUSED\\tUNTRACKED SET CHANGED SINCE STASH MUTATION\\n"; exit 166; }',
                '    case "$strategy" in',
                '      UNDO_STASH_APPLY_CLEAN)',
                '        git -C "$repo" reset --hard "$expected_head" >/dev/null 2>&1 || { printf "REFUSED\\tSTASH APPLY UNDO RESET FAILED\\n"; exit 167; }',
                '        git -C "$repo" clean -fd >/dev/null 2>&1 || { printf "REFUSED\\tSTASH APPLY UNDO CLEAN FAILED\\n"; exit 168; }',
                '        ;;',
                '      UNDO_STASH_POP_TOP)',
                '        git -C "$repo" cat-file -e "$before_stash^{commit}" 2>/dev/null || { printf "REFUSED\\tPOPPED STASH OBJECT MISSING\\n"; exit 169; }',
                '        git -C "$repo" reset --hard "$expected_head" >/dev/null 2>&1 || { printf "REFUSED\\tSTASH POP UNDO RESET FAILED\\n"; exit 170; }',
                '        git -C "$repo" clean -fd >/dev/null 2>&1 || { printf "REFUSED\\tSTASH POP UNDO CLEAN FAILED\\n"; exit 171; }',
                '        stash_message="$(git -C "$repo" log -1 --format=%s "$before_stash" 2>/dev/null || printf "Post-Apollo restored stash")"',
                '        git -C "$repo" stash store -m "$stash_message" "$before_stash" >/dev/null 2>&1 || { printf "REFUSED\\tPOPPED STASH OBJECT RESTORE FAILED\\n"; exit 172; }',
                '        ;;',
                '      UNDO_STASH_DROP_TOP)',
                '        git -C "$repo" cat-file -e "$before_stash^{commit}" 2>/dev/null || { printf "REFUSED\\tDROPPED STASH OBJECT MISSING\\n"; exit 173; }',
                '        stash_message="$(git -C "$repo" log -1 --format=%s "$before_stash" 2>/dev/null || printf "Post-Apollo restored stash")"',
                '        git -C "$repo" stash store -m "$stash_message" "$before_stash" >/dev/null 2>&1 || { printf "REFUSED\\tDROPPED STASH OBJECT RESTORE FAILED\\n"; exit 174; }',
                '        ;;',
                '    esac',
                '    restored_index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                '    restored_worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    restored_untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$restored_index_tree" = "$restore_index_tree" ] || { printf "REFUSED\\tRESTORED STASH INDEX EVIDENCE MISMATCH\\n"; exit 175; }',
                '    [ "$restored_worktree_hash" = "$restore_worktree_hash" ] || { printf "REFUSED\\tRESTORED STASH WORKTREE EVIDENCE MISMATCH\\n"; exit 176; }',
                '    [ "$restored_untracked_hash" = "$restore_untracked_hash" ] || { printf "REFUSED\\tRESTORED STASH UNTRACKED EVIDENCE MISMATCH\\n"; exit 177; }',
                '    restored_stash="$(git -C "$repo" rev-parse -q --verify refs/stash 2>/dev/null || true)"',
                '    [ "$restored_stash" = "$before_stash" ] || { printf "REFUSED\\tSTASH STACK DID NOT RETURN TO RECORDED PRE-MUTATION HEAD\\n"; exit 178; }',
                '    printf "OK\\tRESTORED PRE-STASH-MUTATION STATE // %s\\n" "$strategy"',
                '    ;;',
                '  UNDO_STASH_CREATE_ALL)',
                '    branch="$a"',
                '    expected_head="$b"',
                '    stash_sha="$c"',
                '    previous_stash_sha="$d"',
                '    expected_index_tree="$e"',
                '    expected_worktree_hash="$f"',
                '    IFS="$(printf "\\t")" read -r expected_untracked_hash restore_index_tree restore_worktree_hash restore_untracked_hash <<<"$g"',
                '    ref="refs/heads/$branch"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$ref" ] || { printf "REFUSED\\tSTASH BRANCH IS NOT CURRENTLY CHECKED OUT\\n"; exit 150; }',
                '    actual_head="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                '    [ "$actual_head" = "$expected_head" ] || { printf "REFUSED\\tHEAD CHANGED SINCE STASH CREATION\\n"; exit 151; }',
                '    actual_stash="$(git -C "$repo" rev-parse -q --verify refs/stash 2>/dev/null || true)"',
                '    [ "$actual_stash" = "$stash_sha" ] || { printf "REFUSED\\tSTASH STACK CHANGED SINCE CREATION\\n"; exit 152; }',
                '    [ -z "$(git -C "$repo" ls-files -u 2>/dev/null)" ] || { printf "REFUSED\\tCURRENT INDEX HAS CONFLICTS\\n"; exit 153; }',
                '    actual_index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                '    [ "$actual_index_tree" = "$expected_index_tree" ] || { printf "REFUSED\\tINDEX CHANGED SINCE STASH CREATION\\n"; exit 154; }',
                '    actual_worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_worktree_hash" = "$expected_worktree_hash" ] || { printf "REFUSED\\tWORKTREE CHANGED SINCE STASH CREATION\\n"; exit 155; }',
                '    actual_untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    [ "$actual_untracked_hash" = "$expected_untracked_hash" ] || { printf "REFUSED\\tUNTRACKED SET CHANGED SINCE STASH CREATION\\n"; exit 156; }',
                '    if ! git -C "$repo" stash pop --index "stash@{0}" >/dev/null 2>&1; then',
                '      git -C "$repo" reset --hard "$expected_head" >/dev/null 2>&1 || true',
                '      git -C "$repo" clean -fd >/dev/null 2>&1 || true',
                '      printf "REFUSED\\tSTASH RESTORE FAILED // POST-STASH CLEAN STATE RESTORED\\n"',
                '      exit 157',
                '    fi',
                '    restored_index_tree="$(git -C "$repo" write-tree 2>/dev/null || true)"',
                '    restored_worktree_hash="$(git -C "$repo" diff --binary 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    restored_untracked_hash="$(git -C "$repo" ls-files --others --exclude-standard -z 2>/dev/null | git -C "$repo" hash-object --stdin 2>/dev/null || true)"',
                '    if [ "$restored_index_tree" != "$restore_index_tree" ] || [ "$restored_worktree_hash" != "$restore_worktree_hash" ] || [ "$restored_untracked_hash" != "$restore_untracked_hash" ]; then',
                '      git -C "$repo" reset --hard "$expected_head" >/dev/null 2>&1 || true',
                '      git -C "$repo" clean -fd >/dev/null 2>&1 || true',
                '      current_stash="$(git -C "$repo" rev-parse -q --verify refs/stash 2>/dev/null || true)"',
                '      if [ "$current_stash" != "$stash_sha" ]; then git -C "$repo" stash store -m "Post-Apollo stash Undo rollback" "$stash_sha" >/dev/null 2>&1 || true; fi',
                '      printf "REFUSED\\tSTASH RESTORE EVIDENCE MISMATCH // OPERATION ROLLED BACK\\n"',
                '      exit 158',
                '    fi',
                '    current_stash="$(git -C "$repo" rev-parse -q --verify refs/stash 2>/dev/null || true)"',
                '    [ "$current_stash" = "$previous_stash_sha" ] || {',
                '      git -C "$repo" reset --hard "$expected_head" >/dev/null 2>&1 || true',
                '      git -C "$repo" clean -fd >/dev/null 2>&1 || true',
                '      git -C "$repo" stash store -m "Post-Apollo stash Undo rollback" "$stash_sha" >/dev/null 2>&1 || true',
                '      printf "REFUSED\\tSTASH STACK DID NOT RETURN TO RECORDED PREVIOUS HEAD\\n"',
                '      exit 159',
                '    }',
                '    printf "OK\\tRESTORED PRE-STASH INDEX + WORKTREE + UNTRACKED CONTENT // %s\\n" "$branch"',
                '    ;;',
                '  UNDO_ABSORB_STAGED)',
                '    branch="$a"',
                '    restore="$b"',
                '    expected="$c"',
                '    payload="$d"',
                '    expected_fingerprint="$e"',
                '    expected_bytes="$f"',
                '    ref="refs/heads/$branch"',
                '    head_ref="$(git -C "$repo" symbolic-ref -q HEAD 2>/dev/null || true)"',
                '    [ "$head_ref" = "$ref" ] || { printf "REFUSED\\tABSORB BRANCH IS NOT CURRENTLY CHECKED OUT\\n"; exit 125; }',
                '    actual="$(git -C "$repo" rev-parse -q --verify "$ref" 2>/dev/null || true)"',
                '    [ "$actual" = "$expected" ] || { printf "REFUSED\\tABSORB BRANCH MOVED SINCE OPERATION\\n"; exit 126; }',
                '    git -C "$repo" cat-file -e "$restore^{commit}" 2>/dev/null || { printf "REFUSED\\tPRE-ABSORB COMMIT MISSING\\n"; exit 127; }',
                '    patch="$(mktemp "${TMPDIR:-/tmp}/pa-absorb-undo.XXXXXX")" || { printf "REFUSED\\tABSORB RECOVERY PATCH TEMPFILE FAILED\\n"; exit 128; }',
                '    tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/pa-absorb-preflight.XXXXXX")" || { rm -f "$patch"; printf "REFUSED\\tABSORB PREFLIGHT TEMP DIR FAILED\\n"; exit 129; }',
                '    trap \'git -C "$repo" worktree remove --force "$tmpdir/wt" >/dev/null 2>&1 || true; rm -rf "$tmpdir" "$patch"\' EXIT INT TERM',
                '    printf "%s" "$payload" | base64 -d >"$patch" 2>/dev/null || { printf "REFUSED\\tABSORB RECOVERY PATCH DECODE FAILED\\n"; exit 130; }',
                '    actual_fingerprint="$(sha256sum "$patch" | awk "{print \\$1}")"',
                '    [ "$actual_fingerprint" = "$expected_fingerprint" ] || { printf "REFUSED\\tABSORB RECOVERY PATCH FINGERPRINT MISMATCH\\n"; exit 131; }',
                '    actual_bytes="$(wc -c <"$patch" | tr -d " ")"',
                '    [ -z "$expected_bytes" ] || [ "$actual_bytes" = "$expected_bytes" ] || { printf "REFUSED\\tABSORB RECOVERY PATCH SIZE MISMATCH\\n"; exit 132; }',
                '    git -C "$repo" worktree add --detach "$tmpdir/wt" "$restore" >/dev/null 2>&1 || { printf "REFUSED\\tABSORB PREFLIGHT WORKTREE FAILED\\n"; exit 133; }',
                '    git -C "$tmpdir/wt" apply --check --index --binary --whitespace=nowarn "$patch" >/dev/null 2>&1 || { printf "REFUSED\\tPRE-ABSORB STAGED PATCH NO LONGER APPLIES\\n"; exit 134; }',
                '    git -C "$repo" worktree remove --force "$tmpdir/wt" >/dev/null 2>&1 || { printf "REFUSED\\tABSORB PREFLIGHT CLEANUP FAILED\\n"; exit 135; }',
                '    git -C "$repo" update-ref ORIG_HEAD "$expected" >/dev/null 2>&1 || true',
                '    git -C "$repo" update-ref "$ref" "$restore" "$expected" || { printf "REFUSED\\tGUARDED ABSORB HISTORY RESTORE FAILED\\n"; exit 136; }',
                '    if ! git -C "$repo" reset --hard "$restore" >/dev/null 2>&1; then',
                '      git -C "$repo" update-ref "$ref" "$expected" "$restore" >/dev/null 2>&1 || { printf "REFUSED\\tABSORB HISTORY REALIGN FAILED // REF ROLLBACK FAILED\\n"; exit 137; }',
                '      git -C "$repo" reset --hard "$expected" >/dev/null 2>&1 || true',
                '      printf "REFUSED\\tABSORB HISTORY REALIGN FAILED // REF ROLLED BACK\\n"',
                '      exit 138',
                '    fi',
                '    if ! git -C "$repo" apply --index --binary --whitespace=nowarn "$patch"; then',
                '      git -C "$repo" reset --hard "$restore" >/dev/null 2>&1 || true',
                '      git -C "$repo" update-ref "$ref" "$expected" "$restore" >/dev/null 2>&1 || { printf "REFUSED\\tABSORB PATCH RESTORE FAILED // HISTORY ROLLBACK FAILED\\n"; exit 139; }',
                '      git -C "$repo" reset --hard "$expected" >/dev/null 2>&1 || true',
                '      printf "REFUSED\\tABSORB PATCH RESTORE FAILED // HISTORY ROLLED BACK\\n"',
                '      exit 140',
                '    fi',
                '    printf "OK\\tRESTORED PRE-ABSORB HISTORY + STAGED PATCH // %s\\n" "$branch"',
                '    ;;',
                '  UNDO_TRANSFER_CONTENT)',
                '    source="$a"',
                '    destination="$b"',
                '    IFS="$(printf "\\t")" read -r mode layer <<<"$c"',
                '    [ -n "$layer" ] || layer="worktree"',
                '    payload="$d"',
                '    expected_source_head="$e"',
                '    expected_destination_head="$f"',
                '    expected_fingerprint="$g"',
                '    [ "$mode" = "copy" ] || [ "$mode" = "move" ] || { printf "REFUSED\\tTRANSFER MODE INVALID\\n"; exit 101; }',
                '    source="$(realpath "$source" 2>/dev/null || true)"',
                '    destination="$(realpath "$destination" 2>/dev/null || true)"',
                '    [ -n "$source" ] && [ -n "$destination" ] || { printf "REFUSED\\tTRANSFER WORKTREE PATH MISSING\\n"; exit 102; }',
                '    [ "$source" != "$destination" ] || { printf "REFUSED\\tTRANSFER WORKTREES COLLAPSED TO SAME PATH\\n"; exit 103; }',
                '    git -C "$source" rev-parse --is-inside-work-tree >/dev/null 2>&1 || { printf "REFUSED\\tSOURCE WORKTREE MISSING\\n"; exit 104; }',
                '    git -C "$destination" rev-parse --is-inside-work-tree >/dev/null 2>&1 || { printf "REFUSED\\tDESTINATION WORKTREE MISSING\\n"; exit 105; }',
                '    common_source="$(git -C "$source" rev-parse --git-common-dir 2>/dev/null || true)"',
                '    common_destination="$(git -C "$destination" rev-parse --git-common-dir 2>/dev/null || true)"',
                '    case "$common_source" in /*) ;; *) common_source="$source/$common_source" ;; esac',
                '    case "$common_destination" in /*) ;; *) common_destination="$destination/$common_destination" ;; esac',
                '    common_source="$(realpath "$common_source" 2>/dev/null || true)"',
                '    common_destination="$(realpath "$common_destination" 2>/dev/null || true)"',
                '    [ -n "$common_source" ] && [ "$common_source" = "$common_destination" ] || { printf "REFUSED\\tTRANSFER WORKTREES NO LONGER SHARE A REPOSITORY\\n"; exit 106; }',
                '    actual_source_head="$(git -C "$source" rev-parse HEAD 2>/dev/null || true)"',
                '    actual_destination_head="$(git -C "$destination" rev-parse HEAD 2>/dev/null || true)"',
                '    if [ "$layer" != "conflict-result" ]; then',
                '      [ "$actual_source_head" = "$expected_source_head" ] || { printf "REFUSED\\tSOURCE HEAD CHANGED SINCE TRANSFER\\n"; exit 107; }',
                '      [ -z "$(git -C "$source" ls-files -u 2>/dev/null)" ] || { printf "REFUSED\\tSOURCE HAS CONFLICTS\\n"; exit 109; }',
                '    fi',
                '    [ "$actual_destination_head" = "$expected_destination_head" ] || { printf "REFUSED\\tDESTINATION HEAD CHANGED SINCE TRANSFER\\n"; exit 108; }',
                '    [ -z "$(git -C "$destination" ls-files -u 2>/dev/null)" ] || { printf "REFUSED\\tDESTINATION HAS CONFLICTS\\n"; exit 110; }',
                '    if [ "$layer" = "conflict-result" ]; then',
                '      git -C "$destination" diff --cached --quiet || { printf "REFUSED\\tDESTINATION HAS STAGED DRIFT AFTER CONFLICT RESULT COPY\\n"; exit 111; }',
                '    elif [ "$layer" = "staged" ]; then',
                '      git -C "$source" diff --quiet || { printf "REFUSED\\tSOURCE HAS UNSTAGED DRIFT AFTER STAGED TRANSFER\\n"; exit 111; }',
                '      git -C "$destination" diff --quiet || { printf "REFUSED\\tDESTINATION HAS UNSTAGED DRIFT AFTER STAGED TRANSFER\\n"; exit 112; }',
                '    elif [ "$layer" = "partial" ]; then',
                '      :',
                '    else',
                '      git -C "$source" diff --cached --quiet || { printf "REFUSED\\tSOURCE HAS STAGED CHANGES\\n"; exit 111; }',
                '      git -C "$destination" diff --cached --quiet || { printf "REFUSED\\tDESTINATION HAS STAGED CHANGES\\n"; exit 112; }',
                '    fi',
                '    patch="$(mktemp "${TMPDIR:-/tmp}/pa-transfer-undo.XXXXXX")" || { printf "REFUSED\\tRECOVERY PATCH TEMPFILE FAILED\\n"; exit 113; }',
                '    partial_staged=""',
                '    partial_worktree=""',
                '    cleanup_transfer_undo() { rm -f "$patch"; [ -z "$partial_staged" ] || rm -f "$partial_staged"; [ -z "$partial_worktree" ] || rm -f "$partial_worktree"; }',
                '    trap cleanup_transfer_undo EXIT INT TERM',
                '    printf "%s" "$payload" | base64 -d >"$patch" 2>/dev/null || { printf "REFUSED\\tRECOVERY PATCH DECODE FAILED\\n"; exit 114; }',
                '    actual_fingerprint="$(sha256sum "$patch" | awk "{print \\$1}")"',
                '    [ "$actual_fingerprint" = "$expected_fingerprint" ] || { printf "REFUSED\\tRECOVERY PATCH FINGERPRINT MISMATCH\\n"; exit 115; }',
                '    if [ "$layer" = "partial" ]; then',
                '      partial_staged="$(mktemp "${TMPDIR:-/tmp}/pa-transfer-undo-staged.XXXXXX")" || { printf "REFUSED\\tPARTIAL STAGED RECOVERY TEMPFILE FAILED\\n"; exit 116; }',
                '      partial_worktree="$(mktemp "${TMPDIR:-/tmp}/pa-transfer-undo-worktree.XXXXXX")" || { printf "REFUSED\\tPARTIAL WORKTREE RECOVERY TEMPFILE FAILED\\n"; exit 117; }',
                '      staged64="$(sed -n "s/^STAGED64$(printf \'\\t\')//p" "$patch" | head -n1)"',
                '      worktree64="$(sed -n "s/^WORKTREE64$(printf \'\\t\')//p" "$patch" | head -n1)"',
                '      [ -n "$staged64" ] && [ -n "$worktree64" ] || { printf "REFUSED\\tPARTIAL RECOVERY BUNDLE IS INCOMPLETE\\n"; exit 118; }',
                '      printf "%s" "$staged64" | base64 -d >"$partial_staged" 2>/dev/null || { printf "REFUSED\\tPARTIAL STAGED RECOVERY DECODE FAILED\\n"; exit 119; }',
                '      printf "%s" "$worktree64" | base64 -d >"$partial_worktree" 2>/dev/null || { printf "REFUSED\\tPARTIAL WORKTREE RECOVERY DECODE FAILED\\n"; exit 120; }',
                '      [ -s "$partial_staged" ] && [ -s "$partial_worktree" ] || { printf "REFUSED\\tPARTIAL RECOVERY PATCH IS EMPTY\\n"; exit 121; }',
                '    fi',
                '    if [ "$layer" = "staged" ]; then',
                '      git -C "$destination" apply -R --check --index --binary --whitespace=nowarn "$patch" >/dev/null 2>&1 || { printf "REFUSED\\tDESTINATION NO LONGER CONTAINS EXACT STAGED TRANSFER\\n"; exit 116; }',
                '      if [ "$mode" = "move" ]; then',
                '        git -C "$source" apply --check --index --binary --whitespace=nowarn "$patch" >/dev/null 2>&1 || { printf "REFUSED\\tSOURCE CAN NO LONGER RECEIVE STAGED TRANSFERRED CONTENT\\n"; exit 117; }',
                '        git -C "$source" apply --index --binary --whitespace=nowarn "$patch" || { printf "REFUSED\\tSOURCE STAGED RESTORE FAILED\\n"; exit 118; }',
                '        if ! git -C "$destination" apply -R --index --binary --whitespace=nowarn "$patch"; then',
                '          git -C "$source" apply -R --index --binary --whitespace=nowarn "$patch" >/dev/null 2>&1 || { printf "REFUSED\\tDESTINATION STAGED REMOVE FAILED // SOURCE ROLLBACK FAILED\\n"; exit 119; }',
                '          printf "REFUSED\\tDESTINATION STAGED REMOVE FAILED // SOURCE ROLLED BACK\\n"',
                '          exit 120',
                '        fi',
                '        printf "OK\\tUNDID STAGED MOVE TRANSFER // STAGED CONTENT RESTORED TO SOURCE\\n"',
                '      else',
                '        git -C "$destination" apply -R --index --binary --whitespace=nowarn "$patch" || { printf "REFUSED\\tSTAGED COPY TRANSFER REMOVE FAILED\\n"; exit 121; }',
                '        printf "OK\\tUNDID STAGED COPY TRANSFER // DESTINATION STAGED CONTENT REMOVED\\n"',
                '      fi',
                '    elif [ "$layer" = "conflict-result" ]; then',
                '      git -C "$destination" apply -R --check --binary --whitespace=nowarn "$patch" >/dev/null 2>&1 || { printf "REFUSED\\tDESTINATION NO LONGER CONTAINS EXACT CONFLICT RESULT COPY\\n"; exit 122; }',
                '      git -C "$destination" apply -R --binary --whitespace=nowarn "$patch" || { printf "REFUSED\\tCONFLICT RESULT COPY REMOVE FAILED\\n"; exit 123; }',
                '      printf "OK\\tUNDID CONFLICT RESULT COPY // SOURCE CONFLICT LEFT UNTOUCHED\\n"',
                '    elif [ "$layer" = "partial" ]; then',
                '      partial_apply() {',
                '        local repo="$1"',
                '        git -C "$repo" apply --cached --binary --whitespace=nowarn "$partial_staged" || return 1',
                '        if ! git -C "$repo" apply --binary --whitespace=nowarn "$partial_staged"; then',
                '          git -C "$repo" apply -R --cached --binary --whitespace=nowarn "$partial_staged" >/dev/null 2>&1 || true',
                '          return 1',
                '        fi',
                '        if ! git -C "$repo" apply --binary --whitespace=nowarn "$partial_worktree"; then',
                '          git -C "$repo" apply -R --binary --whitespace=nowarn "$partial_staged" >/dev/null 2>&1 || true',
                '          git -C "$repo" apply -R --cached --binary --whitespace=nowarn "$partial_staged" >/dev/null 2>&1 || true',
                '          return 1',
                '        fi',
                '      }',
                '      partial_remove() {',
                '        local repo="$1"',
                '        git -C "$repo" apply -R --binary --whitespace=nowarn "$partial_worktree" || return 1',
                '        if ! git -C "$repo" apply -R --binary --whitespace=nowarn "$partial_staged"; then',
                '          git -C "$repo" apply --binary --whitespace=nowarn "$partial_worktree" >/dev/null 2>&1 || true',
                '          return 1',
                '        fi',
                '        if ! git -C "$repo" apply -R --cached --binary --whitespace=nowarn "$partial_staged"; then',
                '          git -C "$repo" apply --binary --whitespace=nowarn "$partial_staged" >/dev/null 2>&1 || true',
                '          git -C "$repo" apply --binary --whitespace=nowarn "$partial_worktree" >/dev/null 2>&1 || true',
                '          return 1',
                '        fi',
                '      }',
                '      if [ "$mode" = "move" ]; then',
                '        partial_apply "$source" || { printf "REFUSED\\tSOURCE PARTIAL TWO-LAYER RESTORE FAILED\\n"; exit 123; }',
                '        if ! partial_remove "$destination"; then',
                '          partial_remove "$source" >/dev/null 2>&1 || { printf "REFUSED\\tDESTINATION PARTIAL REMOVE FAILED // SOURCE ROLLBACK FAILED\\n"; exit 124; }',
                '          printf "REFUSED\\tDESTINATION PARTIAL REMOVE FAILED // SOURCE ROLLED BACK\\n"',
                '          exit 125',
                '        fi',
                '        printf "OK\\tUNDID PARTIALLY STAGED MOVE TRANSFER // TWO LAYERS RESTORED TO SOURCE\\n"',
                '      else',
                '        partial_remove "$destination" || { printf "REFUSED\\tPARTIAL COPY TWO-LAYER REMOVE FAILED\\n"; exit 126; }',
                '        printf "OK\\tUNDID PARTIALLY STAGED COPY TRANSFER // DESTINATION TWO-LAYER CONTENT REMOVED\\n"',
                '      fi',
                '    else',
                '      git -C "$destination" apply -R --check --binary --whitespace=nowarn "$patch" >/dev/null 2>&1 || { printf "REFUSED\\tDESTINATION NO LONGER CONTAINS EXACT TRANSFER\\n"; exit 116; }',
                '      if [ "$mode" = "move" ]; then',
                '        git -C "$source" apply --check --binary --whitespace=nowarn "$patch" >/dev/null 2>&1 || { printf "REFUSED\\tSOURCE CAN NO LONGER RECEIVE TRANSFERRED CONTENT\\n"; exit 117; }',
                '        git -C "$source" apply --binary --whitespace=nowarn "$patch" || { printf "REFUSED\\tSOURCE RESTORE FAILED\\n"; exit 118; }',
                '        if ! git -C "$destination" apply -R --binary --whitespace=nowarn "$patch"; then',
                '          git -C "$source" apply -R --binary --whitespace=nowarn "$patch" >/dev/null 2>&1 || { printf "REFUSED\\tDESTINATION REMOVE FAILED // SOURCE ROLLBACK FAILED\\n"; exit 119; }',
                '          printf "REFUSED\\tDESTINATION REMOVE FAILED // SOURCE ROLLED BACK\\n"',
                '          exit 120',
                '        fi',
                '        printf "OK\\tUNDID MOVE TRANSFER // CONTENT RESTORED TO SOURCE\\n"',
                '      else',
                '        git -C "$destination" apply -R --binary --whitespace=nowarn "$patch" || { printf "REFUSED\\tCOPY TRANSFER REMOVE FAILED\\n"; exit 121; }',
                '        printf "OK\\tUNDID COPY TRANSFER // DESTINATION CONTENT REMOVED\\n"',
                '      fi',
                '    fi',
                '    ;;',
                '  *)',
                '    printf "REFUSED\\tUNKNOWN RECOVERY STRATEGY\\n"',
                '    exit 100',
                '    ;;',
                'esac'
            ].join("\n"),
            "git-operation-recovery",
            repo,
            strategy,
            a,
            b,
            c,
            d,
            e,
            f,
            g
        ]);

        return true;
    }

    function cloneUndoAfterSnapshot() {
        const plan = pendingPlan || {};

        return {
            snapshotVersion: 1,
            repository: String(plan.destinationPath || repositoryPath || ""),
            capturedAt: new Date().toISOString(),
            externalBoundary: "CLONE_UNDO",
            destinationPath: String(plan.destinationPath || ""),
            destinationPresent: false,
            recoveryClass: "EXTERNAL_RECOVERABLE",
            recoveryReason:
                "EXACT CREATED CLONE DIRECTORY REMOVED"
        };
    }

    function maybeFinish() {
        if (!busy || !exitSeen || !stdoutSeen || !stderrSeen)
            return;

        const out = String(stdoutText || "").trim();
        const err = String(stderrText || "").trim();
        const line = out.split("\n")[0] || "";
        const parts = line.split("\t");
        const kind = parts.length > 0 ? parts[0] : "";
        const detail =
            parts.length > 1
            ? parts.slice(1).join("\t")
            : String(err || out || ("EXIT " + exitCode)).trim();

        pendingRecoverySuccess =
            exitCode === 0
            && kind === "OK";
        pendingRecoveryDetail =
            detail
            || (
                pendingRecoverySuccess
                ? "UNDO COMPLETE"
                : "UNDO REFUSED"
            );

        if (pendingRecoverySuccess
                && String((pendingPlan || {}).strategy || "")
                    === "DELETE_EXACT_CLONE") {
            finalizeRecovery(
                cloneUndoAfterSnapshot(),
                ""
            );
            return;
        }

        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "UNDO AFTER // " + String((pendingPlan || {}).strategy || ""),
            recoveryContext()
        );

        if (!pendingSnapshotRequest) {
            finalizeRecovery(
                null,
                "UNDO AFTER SNAPSHOT COULD NOT START"
            );
        }
    }

    function finalizeRecovery(afterSnapshot, snapshotWarning) {
        const originalId = pendingOperationId;
        const undoId = pendingJournalId;
        const success = pendingRecoverySuccess;
        const detail = String(pendingRecoveryDetail || "");
        const warning = String(snapshotWarning || "");
        const snapshot =
            afterSnapshot
            || {
                snapshotVersion: 1,
                repository: String(repositoryPath || ""),
                capturedAt: new Date().toISOString(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason:
                    warning
                    || "UNDO AFTER SNAPSHOT UNAVAILABLE"
            };
        const finalDetail =
            warning
            ? detail + " // " + warning
            : detail;

        if (undoId && operationJournal) {
            if (success)
                operationJournal.completeOperation(
                    undoId,
                    snapshot,
                    finalDetail
                );
            else
                operationJournal.failOperation(
                    undoId,
                    snapshot,
                    finalDetail
                );

            operationJournal.markUndoResult(
                originalId,
                undoId,
                success,
                finalDetail
            );
        }

        busy = false;
        clearPending();
        recoveryFinished(
            originalId,
            success,
            finalDetail || (success ? "UNDO COMPLETE" : "UNDO REFUSED")
        );
    }

    Connections {
        target: root.snapshotService
        enabled: root.snapshotService !== null
        ignoreUnknownSignals: true

        function onSnapshotReady(requestId, snapshot) {
            if (String(requestId || "")
                    !== String(root.pendingSnapshotRequest || ""))
                return;

            root.pendingSnapshotRequest = "";

            if (root.snapshotPhase === "BEFORE") {
                root.snapshotPhase = "";

                const strategy =
                    String((root.pendingPlan || {}).strategy || "");
                const snapshotClass =
                    String((snapshot || {}).recoveryClass || "");

                if (strategy !== "UNDO_TRANSFER_CONTENT"
                        && strategy !== "UNDO_COMMIT_TO_STAGED"
                        && strategy !== "UNDO_RESET_SOFT_OR_MIXED"
                        && strategy.indexOf("UNDO_STASH_") !== 0
                        && snapshotClass !== "REF_RECOVERABLE") {
                    root.failBeforeSnapshot(
                        "CURRENT REPOSITORY STATE IS NOT CLEAN REF-RECOVERABLE"
                    );
                    return;
                }

                root.pendingJournalId =
                    root.operationJournal.beginOperation(
                        "UNDO/"
                            + String((root.pendingRecord || {}).kind || ""),
                        snapshot,
                        root.recoveryContext()
                    );

                if (!root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "UNDO JOURNAL RECORD COULD NOT START"
                    );
                    return;
                }

                root.executeRecoveryProcess();
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeRecovery(snapshot, "");
            }
        }

        function onSnapshotFailed(requestId, detail) {
            if (String(requestId || "")
                    !== String(root.pendingSnapshotRequest || ""))
                return;

            root.pendingSnapshotRequest = "";

            if (root.snapshotPhase === "BEFORE") {
                root.snapshotPhase = "";
                root.failBeforeSnapshot(detail);
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeRecovery(
                    null,
                    "UNDO AFTER SNAPSHOT FAILED // "
                        + String(detail || "UNKNOWN ERROR")
                );
            }
        }
    }

    Process {
        id: recoveryProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.stdoutText = this.text;
                root.stdoutSeen = true;
                root.maybeFinish();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.stderrText = this.text;
                root.stderrSeen = true;
                root.maybeFinish();
            }
        }

        onExited: function(code, exitStatus) {
            root.exitCode = Number(code);
            root.exitSeen = true;
            root.maybeFinish();
        }
    }
}
