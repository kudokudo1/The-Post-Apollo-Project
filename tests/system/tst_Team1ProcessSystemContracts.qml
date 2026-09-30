import QtQuick
import QtTest
import "../../services/system"
import "../../widgets/system"

TestCase {
    name: "Team1ProcessSystemContracts"

    ProcessIdentity {
        id: processIdentity
    }

    ProcessScope {
        id: processScope
    }

    ProcessSafety {
        id: processSafety
    }

    ProcessResourceScope {
        id: resourceScope
        processScope: processScope
        safetyService: processSafety
    }

    ProcessResourceState {
        id: resourceState
        processIdentity: processIdentity
        resourceScope: resourceScope
    }

    QtObject {
        id: fakeProcessControl

        property var calls: []
        property bool succeed: true

        function sendSignal(pid, signalName) {
            const next = calls.slice();
            next.push({
                kind: "single",
                pid: Number(pid || 0),
                signalName: String(signalName || "")
            });
            calls = next;
            return succeed;
        }

        function sendSignalMany(pids, signalName) {
            const next = calls.slice();
            next.push({
                kind: "many",
                pids: Array.isArray(pids) ? pids.slice() : [],
                signalName: String(signalName || "")
            });
            calls = next;
            return succeed;
        }

        function restart(pid) {
            const next = calls.slice();
            next.push({
                kind: "restart",
                pid: Number(pid || 0)
            });
            calls = next;
            return succeed;
        }
    }

    QtObject {
        id: fakeLimits

        property var remembered: []

        function hasSoftLimit(entry) {
            return false;
        }

        function minimumMiB(entry) {
            return 128;
        }

        function maximumMiB(entry) {
            return 8192;
        }

        function limitMiB(entry) {
            return 0;
        }

        function limitPercent(entry) {
            return 100;
        }

        function setLimitMiB(entry, mib) {
            const next = remembered.slice();
            next.push({
                pid: Number(entry && entry.pid || 0),
                mib: Number(mib || 0)
            });
            remembered = next;
        }
    }

    ProcessActionController {
        id: actionController
        safetyService: processSafety
        limitsService: fakeLimits
        controlService: fakeProcessControl
        processIdentity: processIdentity
    }

    QtObject {
        id: fakeLimitMutation

        signal batchFinished(int batchId, var context, bool ok, var results)

        property int serial: 0

        function requestLimitMany(pids, capBytes, context) {
            serial += 1;
            return serial;
        }
    }

    ProcessResourceController {
        id: resourceController
        resourceScope: resourceScope
        resourceState: resourceState
        processControl: fakeProcessControl
        limitMutation: fakeLimitMutation
    }

    ProcessPresentation {
        id: processPresentation
        processScope: processScope
    }

    SystemPresentation {
        id: systemPresentation
    }

    function cleanup() {
        processSafety.unlockedKeys = ({});
        processSafety.actionUnlockedKeys = ({});
        resourceState.memoryLimitPolicies = ({});
        resourceState.memoryLimitPidPolicies = ({});
        resourceState.frozenScopes = ({});
        resourceController.pendingLimitBatches = ({});
        resourceController.limitRequestSerial = 0;
        actionController.frozenOptimistic = ({});
        fakeProcessControl.calls = [];
        fakeProcessControl.succeed = true;
        fakeLimits.remembered = [];
        fakeLimitMutation.serial = 0;
    }

    function processRows() {
        return [
            {
                pid: 100,
                ppid: 2,
                comm: "demo",
                user: "user",
                state: "S",
                vsz: 262144,
                mem: 20
            },
            {
                pid: 101,
                ppid: 100,
                comm: "demo-child",
                user: "user",
                state: "S",
                vsz: 131072,
                mem: 10
            },
            {
                pid: 200,
                ppid: 2,
                comm: "other",
                user: "user",
                state: "S",
                vsz: 262144,
                mem: 15
            }
        ];
    }

    function test_processIdentityUnwrapsFavoriteRecord() {
        const source = {
            pid: 4242,
            comm: "Demo",
            args: "/usr/bin/demo --flag"
        };
        const wrapper = {
            _favoriteRecord: true,
            _sourceItem: source
        };

        compare(processIdentity.sourceEntry(wrapper), source);
        compare(processIdentity.persistentIdentity(wrapper), "demo");
        compare(processIdentity.pidPolicyKey(wrapper), "4242|demo");
    }

    function test_processIdentityRejectsPidReuseMismatch() {
        const captured = processIdentity.capturedIdentity({
            pid: 4242,
            comm: "demo",
            args: "/usr/bin/demo"
        });

        compare(
            processIdentity.matchesCaptured(
                { pid: 4242, comm: "demo", args: "/usr/bin/demo" },
                captured
            ),
            true
        );
        compare(
            processIdentity.matchesCaptured(
                { pid: 4242, comm: "other", args: "/usr/bin/other" },
                captured
            ),
            false
        );
        compare(
            processIdentity.matchesCaptured(
                { pid: 5000, comm: "demo", args: "/usr/bin/demo" },
                captured
            ),
            false
        );
    }

    function test_processScopeExpandsDescendantsWithoutDuplicates() {
        const rows = processRows();
        const scoped = processScope.treeRowsForRoots(
            rows,
            [100, "100", 0, 1, -5]
        );

        compare(scoped.length, 2);
        compare(scoped[0].pid, 100);
        compare(scoped[1].pid, 101);

        const pids = processScope.pidsForRoots(rows, [100, 100]);
        compare(pids.length, 2);
        compare(pids[0], 100);
        compare(pids[1], 101);
    }

    function test_protectedActionUnlockRelocksAfterCancel() {
        const entry = {
            pid: 6000,
            comm: "sway",
            user: "user"
        };

        compare(actionController.requestTerminate(entry), false);

        processSafety.toggleDangerActionUnlock(entry, "kill");
        compare(processSafety.dangerActionUnlocked(entry, "kill"), true);
        compare(actionController.requestTerminate(entry), true);

        const request = actionController.confirmationFor(
            entry,
            "terminate"
        );

        verify(request !== null);
        compare(actionController.cancelConfirmed(request, entry), true);
        compare(processSafety.dangerActionUnlocked(entry, "kill"), false);
        compare(fakeProcessControl.calls.length, 0);
    }

    function test_confirmedActionRevalidatesCapturedTarget() {
        const original = {
            pid: 7000,
            comm: "demo",
            user: "user",
            args: "/usr/bin/demo"
        };
        const request = actionController.confirmationFor(
            original,
            "terminate"
        );

        verify(request !== null);

        const reusedPid = {
            pid: 7000,
            comm: "other",
            user: "user",
            args: "/usr/bin/other"
        };

        compare(
            actionController.executeConfirmed(request, reusedPid),
            false
        );
        compare(fakeProcessControl.calls.length, 0);
    }

    function test_protectedFrozenProcessCanAlwaysResume() {
        const entry = {
            pid: 7050,
            comm: "sway",
            user: "user",
            state: "T",
            args: "/usr/bin/sway"
        };

        compare(
            processSafety.dangerActionUnlocked(entry, "freeze"),
            false
        );
        compare(actionController.isFrozen(entry), true);
        compare(actionController.requestToggleFreeze(entry), true);
        compare(actionController.isFrozen(entry), false);
        compare(fakeProcessControl.calls.length, 1);
        compare(fakeProcessControl.calls[0].signalName, "-CONT");
    }

    function test_failedResumePreservesOptimisticFrozenState() {
        const entry = {
            pid: 7100,
            comm: "demo",
            user: "user",
            state: "T",
            args: "/usr/bin/demo"
        };

        actionController.markFrozen(entry, true);
        compare(actionController.isFrozen(entry), true);

        fakeProcessControl.succeed = false;

        compare(actionController.requestToggleFreeze(entry), false);
        compare(actionController.isFrozen(entry), true);
        compare(fakeProcessControl.calls.length, 1);
        compare(fakeProcessControl.calls[0].signalName, "-CONT");
    }

    function test_resourceScopeBlocksProtectedProcesses() {
        const rows = [
            {
                pid: 8000,
                ppid: 2,
                comm: "demo",
                user: "user",
                state: "S",
                vsz: 262144
            },
            {
                pid: 8001,
                ppid: 8000,
                comm: "pipewire",
                user: "user",
                state: "S",
                vsz: 131072
            }
        ];

        compare(resourceScope.containsProtected(rows, [8000]), true);
        compare(resourceScope.limitAvailable(rows, [8000]), false);
    }

    function test_verifiedKernelResultsRemainPerPidAndMixed() {
        const rows = processRows();

        const summary = resourceState.noteMutationResults(
            rows,
            [
                {
                    ok: true,
                    pid: 100,
                    soft: 4096 * 1024 * 1024
                },
                {
                    ok: true,
                    pid: 200,
                    soft: 3072 * 1024 * 1024
                }
            ]
        );

        compare(summary.successCount, 2);
        compare(summary.failureCount, 0);

        const state = resourceState.rootLimitState(
            rows,
            [100, 200]
        );

        compare(state.known, 2);
        compare(state.mixed, true);
        compare(state.value, 3072);
    }

    function test_partialMutationKeepsSuccessfulKernelTruthOnly() {
        const rows = processRows();

        const summary = resourceState.noteMutationResults(
            rows,
            [
                {
                    ok: true,
                    pid: 100,
                    soft: 2048 * 1024 * 1024
                },
                {
                    ok: false,
                    pid: 200,
                    error: "denied"
                }
            ]
        );

        compare(summary.successCount, 1);
        compare(summary.failureCount, 1);
        compare(
            resourceState.memoryLimitPidPolicies["100|demo"],
            2048
        );
        verify(
            resourceState.memoryLimitPidPolicies["200|other"]
            === undefined
        );
    }

    function test_successfulBatchDoesNotOverwriteClampedPidTruth() {
        const rows = processRows();
        const context = {
            consumer: "process-resource",
            kind: "set",
            scopeKey: "app:demo",
            processRows: rows,
            rootPids: [100, 200],
            normalizedMiB: 4096
        };

        resourceController.finishLimitBatch(
            1,
            context,
            true,
            [
                {
                    ok: true,
                    pid: 100,
                    soft: 4096 * 1024 * 1024
                },
                {
                    ok: true,
                    pid: 200,
                    soft: 3072 * 1024 * 1024
                }
            ]
        );

        compare(
            resourceState.memoryLimitPolicies["app:demo"],
            4096
        );
        compare(
            resourceState.memoryLimitPidPolicies["100|demo"],
            4096
        );
        compare(
            resourceState.memoryLimitPidPolicies["200|other"],
            3072
        );
        compare(
            resourceState.limitMiB(
                "app:demo",
                rows,
                [100, 200]
            ),
            3072
        );
        compare(
            resourceState.limitMixed(rows, [100, 200]),
            true
        );
    }

    function test_freezeOptimismLesionRemainsExplicitCompatibility() {
        const rows = processRows();

        resourceState.markFrozen("app:demo", true);

        compare(
            resourceState.isFrozen(
                "app:demo",
                rows,
                [100]
            ),
            true
        );

        resourceState.markFrozen("app:demo", false);

        compare(
            resourceState.isFrozen(
                "app:demo",
                rows,
                [100]
            ),
            false
        );
    }

    function test_rssCriticalMetricPreservesDonorMemBehavior() {
        compare(
            processPresentation.metricIsCritical(
                { rss: 999999, mem: 10 },
                "rss"
            ),
            false
        );
        compare(
            processPresentation.metricIsCritical(
                { rss: 1, mem: 90 },
                "rss"
            ),
            true
        );
    }

    function test_systemRateMetricParsingRemainsPresentationOnly() {
        const parts = systemPresentation.systemRateMetricParts({
            metric: "↓ 12.5 MiB/s • ↑ 3.0 KiB/s"
        });

        compare(parts.length, 2);
        compare(parts[0].value, "↓ 12.5");
        compare(parts[0].unit, "MiB/s");
        compare(parts[1].value, "↑ 3.0");
        compare(parts[1].unit, "KiB/s");
    }
}
