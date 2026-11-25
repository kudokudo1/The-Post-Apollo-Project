#!/usr/bin/python3 -I
"""Real external privileged change after durable intent; disposable guest only."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

PIN = "6bac8be7b1de6883f480a95944d6ba1130852270"
RECOVERY = Path("/usr/local/libexec/postapollo-memory-ci-fault.py")
MARKER = Path("/etc/postapollo-memory-native-interference-ci-only")

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def stage(message):
    print("CPU_MEM_INTERFERENCE_STAGE // " + message, flush=True)

def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

def guarded():
    require(os.geteuid() == 0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    guard = load("interference_guard", RECOVERY)
    require(guard.protected_bytes(MARKER).strip() ==
            b"DISPOSABLE_CPU_MEMORY_INTERFERENCE_V1", "interference marker absent")
    guard.PIN = PIN
    guard.guard()
    return guard

def signature(guard):
    return {path: (kind, size, priority)
            for path, (kind, size, used, priority) in guard.rows().items()}

def run(guard):
    guard.verify_swap(True)
    history = guard.history()
    require(len(history) == 2, "normal cycle evidence absent")
    require(not any(os.path.lexists(guard.EXT / name) for name in guard.RECORD_NAMES)
            and not os.path.lexists(guard.PENDING), "prior recovery records exist")
    before = signature(guard)
    ids = [guard.identity(guard.BASE), guard.identity(guard.EXTRA)]
    expected = dict(before)
    del expected[str(guard.EXTRA)]
    candidate = load("interference_candidate", guard.HELPER)
    target = str(guard.EXTRA)
    intent_path = guard.EXT / guard.RECORD_NAMES[0]
    outcome_path = guard.EXT / guard.RECORD_NAMES[1]
    original_record = candidate.durable_withdrawal_record
    original_run = candidate.run
    effects = []
    prepared = []

    def observe_candidate_run(*argv):
        # Observe the candidate's real command invocations; do not substitute
        # results or change the production decision path.
        if argv and Path(argv[0]).name in ("swapon", "swapoff"):
            effects.append(tuple(argv))
        return original_run(*argv)

    def external_after_intent(data, *, initial=False):
        original_record(data, initial=initial)
        if not initial:
            return
        require(not prepared and data["state"] == "PREPARED",
                "unexpected repeated intent")
        intent = guard.protected_bytes(intent_path)
        require(json.loads(intent) == json.loads(json.dumps(data))
                and not os.path.lexists(outcome_path),
                "durable intent not observed")
        # A cooperating privileged helper must refuse while the current
        # candidate holds its lock. No mutation is requested by the probe.
        busy = guard.helper("persist-authorized")
        require(busy.returncode == 2 and '"code": "OPERATION_BUSY"' in busy.stdout,
                "cooperating lock contention not observed")
        # Fresh actual readiness checks BEFORE any fixture swapoff. Do not
        # force occupied withdrawal or reduce physical memory headroom.
        now = candidate.reduction_preflight(4)
        require(now["state"] == "READY_ADVISORY"
                and now["evidence"]["extensionUsedKiB"] == 0
                and signature(guard) == before,
                "external fixture safety gate unavailable")
        # Deliberately independent util-linux actor, not a helper command.
        # No inherited helper lock descriptor; fixed managed extension only.
        # This is a native interference test, not a new supported operation.
        command = subprocess.run(["/usr/sbin/swapoff", "--", target],
                                 check=False, text=True, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 cwd="/", close_fds=True)
        require(command.returncode == 0, "external swapoff did not complete")
        guard.verify_swap(False)
        require(signature(guard) == expected and
                [guard.identity(guard.BASE), guard.identity(guard.EXTRA)] == ids
                and guard.protected_bytes(intent_path) == intent,
                "unexpected external state")
        prepared.append(intent)
        stage("EXTERNAL_REAL_SWAPOFF_AFTER_DURABLE_INTENT")
    candidate.run = observe_candidate_run
    candidate.durable_withdrawal_record = external_after_intent
    # The real candidate's main acquires its ordinary lock, persists intent,
    # and performs its own final live check. No synthetic proc snapshots.
    rc = candidate.main(["withdraw-authorized", "4"])
    require(rc == 3 and len(prepared) == 1,
            "expected recovery-required result")
    require(not effects, "candidate attempted its own swap command")
    outcome = json.loads(guard.protected_bytes(outcome_path))
    require(outcome == {"state":"NOT_STARTED", "code":"BASE_OR_EXTENSION_INACTIVE"},
            "candidate falsely claimed completion")
    require(guard.protected_bytes(intent_path) == prepared[0]
            and signature(guard) == expected and guard.history() == history
            and [guard.identity(guard.BASE), guard.identity(guard.EXTRA)] == ids,
            "candidate changed retained evidence")
    guard.fence()
    observed = guard.success("inspect-recovery-authorized", prefix="RECOVERY INSPECTION: ")
    require(observed["code"] == "RESULT_CONTRADICTS_KERNEL"
            and observed["mutationAllowed"] is False and observed["recordCleared"] is False,
            "external effect incorrectly attributed to candidate")
    require(signature(guard) == expected and guard.history() == history
            and guard.protected_bytes(intent_path) == prepared[0]
            and json.loads(guard.protected_bytes(outcome_path)) == outcome,
            "inspection or refusal changed evidence")
    print("CPU_MEM_INTERFERENCE_PASS // EXTERNAL_EFFECT_NOT_ATTRIBUTED_NO_CANDIDATE_SWAP_COMMAND", flush=True)
    print("CPU_MEM_INTERFERENCE_PASS // CONTRADICTORY_KERNEL_RESULT_RETAINED_AND_FENCED", flush=True)
    # No recovery clearance, reactivation, compensating action or retry.

def main():
    guard = guarded()
    require(len(sys.argv) == 2, "phase required")
    if sys.argv[1] == "guard":
        stage("EXACT_CANDIDATE " + PIN)
    elif sys.argv[1] == "run":
        run(guard)
    else:
        raise RuntimeError("invalid phase")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print("CPU_MEM_INTERFERENCE_FAIL // " + type(exc).__name__ + ": " + str(exc), flush=True)
        raise SystemExit(2)
