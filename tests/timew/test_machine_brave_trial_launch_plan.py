#!/usr/bin/env python3
"""MACHINE // Read-only disposable Brave native launch preview checks."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))

from MachineBraveDisposableTrial import init_trial
from MachineBraveTrialLaunchPlan import plan_launch, LaunchPlanError


def refused(call):
    try:
        call()
    except (LaunchPlanError, OSError, TypeError, ValueError):
        return
    raise AssertionError("unsafe or unrecognized browser launch candidate accepted")


def files_in(root):
    return {str(p.relative_to(root)): p.read_bytes()
            for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


trial = Path(init_trial()["trial_root"])
external = Path(tempfile.mkdtemp(prefix="machine-brave-fake-binary-", dir="/tmp"))
try:
    binary = external / "brave-browser"
    binary.write_text("#!/bin/sh\nexit 42\n")  # never invoked
    binary.chmod(0o700)
    assert os.access(binary, os.X_OK)
    before = files_in(trial)
    result = plan_launch(str(trial), str(binary))
    assert files_in(trial) == before, "planning modified the trial profile"
    assert result["kind"] == "machine-brave-disposable-native-launch-preview-v1"
    assert result["status"] == "operator_review_required"
    assert result["candidate_native_binary"] == str(binary)
    assert result["candidate_argv"] == [
        str(binary),
        "--user-data-dir=" + str(trial / "profile"),
        "--no-first-run",
        "--no-default-browser-check",
    ]
    assert result["expected_user_data_dir"] == str(trial / "profile")
    assert result["manual_check_url"] == "brave://version"
    assert result["expected_profile_path_prefix"] == str(trial / "profile") + "/"
    for key in (
        "browser_launched_by_tool", "browser_identity_authenticated",
        "brave_package_verified", "profile_isolation_runtime_verified",
        "host_registration_used_by_browser_verified", "extension_loaded",
        "native_transport_tested", "browser_to_sway_identity_verified",
        "session_capture_allowed", "restore_allowed",
    ):
        assert result[key] is False, key
    assert result["safe_actions"] == []
    joined = json.dumps(result)
    for forbidden in ("--remote-debugging-port", "--profile-directory=",
                      "https://", "cookie", "tabs", "session_restore"):
        assert forbidden not in joined
    assert not (trial / "profile" / "Default").exists()

    # Real isolated CLI check. It prints a plan but cannot launch browser.
    cli = ROOT / "services/time/MachineBraveTrialLaunchPlan.py"
    run = subprocess.run(
        ["python3", "-B", "-I", str(cli), "plan", str(trial), str(binary)],
        capture_output=True, timeout=6,
    )
    assert run.returncode == 0 and not run.stderr
    assert json.loads(run.stdout) == result
    assert files_in(trial) == before
    assert not (trial / "profile" / "Default").exists()

    for candidate in ("/usr/bin/firefox", "brave-browser", "",
                      str(external / "brave-browser-untrusted"),
                      str(trial / "profile" / "brave"), "\n", 123, None):
        refused(lambda choice=candidate: plan_launch(str(trial), choice))

    # Reject a matching filename pointing to a non-Brave target.
    misleading = external / "brave"
    misleading.symlink_to("/usr/bin/env")
    refused(lambda: plan_launch(str(trial), str(misleading)))
    misleading.unlink()

    # Refuse binary without execute permission.
    binary.chmod(0o600)
    refused(lambda: plan_launch(str(trial), str(binary)))
    binary.chmod(0o700)

    # Mock path on a valid native-style name but symlinked into trial itself.
    inside = trial / "brave"
    inside.write_bytes(binary.read_bytes())
    inside.chmod(0o700)
    refused(lambda: plan_launch(str(trial), str(inside)))
    inside.unlink()

    # No registration is needed to print a preview; actual Brave usage is
    # explicitly unverified until a separate operator-approved UI inspection.
    assert plan_launch(str(trial), str(binary)) == result

    wrong = cli = ROOT / "services/time/MachineBraveTrialLaunchPlan.py"
    bad = subprocess.run(
        ["python3", "-B", "-I", str(wrong), "plan",
         "/home/example/.config/BraveSoftware/Brave-Browser", str(binary)],
        capture_output=True, timeout=6,
    )
    assert bad.returncode == 1 and not bad.stderr
    assert json.loads(bad.stdout) == {"status": "refused", "safe_actions": []}
finally:
    shutil.rmtree(trial)
    shutil.rmtree(external)

manifest = json.loads(
    (ROOT / "integrations/machine/brave-topology/manifest.json").read_text()
)
assert manifest["permissions"] == []
assert manifest["optional_permissions"] == ["nativeMessaging"]
assert manifest["host_permissions"] == []
assert manifest["incognito"] == "not_allowed"
assert "background" not in manifest
qml = (ROOT / "widgets/TimeW.qml").read_text()
assert "MachineBraveTrialLaunchPlan" not in qml
host = (ROOT / "services/time/MachineBraveNativeProbe.py").read_text()
assert "MachineBraveTrialLaunchPlan" not in host

code = (ROOT / "services/time/MachineBraveTrialLaunchPlan.py").read_text()
for blocked in ("subprocess.", "swaymsg", "sqlite3", "os.system(",
                "os.exec", "os.spawn", "Popen(", "chmod(", "write_text(",
                "write_bytes(", "mkdir(", "chrome.windows.update",
                "sendNativeMessage", "RESTORE_NOW", "shutil.rmtree"):
    assert blocked not in code, blocked

print("MACHINE Brave // native launch preview never starts browser or changes profile PASS")
