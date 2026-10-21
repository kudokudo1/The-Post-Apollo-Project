#!/usr/bin/env python3
"""Synthetic checks for consent-gated update notifications.

This test never queries remote update servers or executes updater commands.
"""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import importlib.util
import json
import os
import re
import stat
import tempfile
from unittest.mock import patch

# Keep updater-lock tests completely outside the operator's real state.
TEST_STATE = tempfile.TemporaryDirectory(prefix="apollo-update-tests-")
os.environ["XDG_STATE_HOME"] = TEST_STATE.name

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "scripts/updates/update_offers.py"
PRODUCER = (ROOT / "services/notifications/SoftwareUpdateOfferNotificationProducer.qml").read_text()
SHELL = (ROOT / "shell.qml").read_text()
HUB = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text()
QM = (ROOT / "services/notifications/qmldir").read_text()
WORKFLOW = (ROOT / ".github/workflows/notification-policy-contracts.yml").read_text()

spec = importlib.util.spec_from_file_location("post_apollo_update_offers", BACKEND)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.ALLOWED == {"silverblue", "oh-my-zsh", "powerlevel10k",
                       "flatpak-user", "flatpak-system", "firmware"}
assert mod.DEFER_SECONDS == 24 * 60 * 60
# Closing Kitty detaches the updater. A second review must not launch the
# same maintenance operation while the first detached process is still busy.
with mod.update_transaction_lock("flatpak-system") as primary:
    assert primary
    with mod.update_transaction_lock("flatpak-system") as duplicate:
        assert duplicate is False
with mod.update_transaction_lock("flatpak-system") as released:
    assert released
assert mod.fingerprint("silverblue", "old", "new") != mod.fingerprint("silverblue", "old", "newer")

# No auto-accept or arbitrary remote-code execution in Quickshell.
assert "SoftwareUpdateOfferNotificationProducer {" in SHELL
assert "updatesController: softwareUpdateOffers" in SHELL
assert "SoftwareUpdateOfferNotificationProducer 1.0 SoftwareUpdateOfferNotificationProducer.qml" in QM
assert "test_software_update_offers.py" in WORKFLOW
assert "6 * 60 * 60 * 1000" in PRODUCER
assert "NotificationsService.historyReady" in PRODUCER
assert 'sourceId": "apollo-update-monitor"' in PRODUCER
assert 'Quickshell.execDetached([' in PRODUCER
assert 'Quickshell.shellPath("scripts/updates/launch_review.py")' in PRODUCER
assert '"kitty", "--hold", "-e"' not in PRODUCER
assert "String(kind), String(token)" in PRODUCER
assert 'producer.script, "defer"' in PRODUCER
assert "producer.isCurrent(kind, token)" in PRODUCER
assert "onExited: function(code, exitStatus)" in PRODUCER
for forbidden in ["rpm-ostree upgrade", "systemctl reboot", "pkexec", "sudo",
                  "curl | sh", "git pull", "bash -lc"]:
    assert forbidden not in PRODUCER, forbidden

assert "property var updatesController: null" in HUB
assert 'updateKind": entry.sourceId === "apollo-update-monitor"' in HUB
assert 'updateToken": entry.sourceId === "apollo-update-monitor"' in HUB
assert "root.updatesController.isCurrent(updateKind, updateToken)" in HUB
assert '(notificationEntry.isUpdateOffer ? 32 : 0)' in HUB
assert 'label: notificationEntry.updateKind === "firmware"' in HUB
assert '? "OPEN UPDATES"' in HUB
assert '? "DOWNLOAD" : "REVIEW"' in HUB
assert 'label: "NOT NOW"' in HUB
assert "root.updatesController.review(" in HUB
assert "root.updatesController.defer(" in HUB
assert "&& !notificationEntry.isUpdateOffer" in HUB

# Status-only staged deployment; reboot is NEVER offered as a one-click action.
with patch.object(mod.shutil, "which", return_value="/usr/bin/rpm-ostree"), \
     patch.object(mod, "run", return_value=(0, json.dumps({
         "deployments": [
             {"checksum": "b"*64, "booted": False},
             {"checksum": "a"*64, "booted": True}
         ]
     }))):
    pending = mod.silverblue()
assert pending["kind"] == "silverblue"
assert pending["phase"] == "staged"
assert "REBOOT PENDING" in pending["title"]

status = json.dumps({"deployments": [{"checksum": "a"*64, "booted": True}]})
check = ("AvailableUpdate:\n  Version: 44.20261021\n"
         "  Commit: " + "c"*64 + "\n")
with patch.object(mod.shutil, "which", return_value="/usr/bin/rpm-ostree"), \
     patch.object(mod, "run", side_effect=[(0, status), (0, check)]):
    offered = mod.silverblue()
assert offered["phase"] == "available"
assert offered["token"] == mod.fingerprint("silverblue", "a"*64, "c"*64)

# Don't announce updates based on command errors, garbage or no complete sha.
with patch.object(mod.shutil, "which", return_value="/usr/bin/rpm-ostree"), \
     patch.object(mod, "run", side_effect=[(0, status), (1, "error")]):
    assert mod.silverblue() is None
with patch.object(mod.shutil, "which", return_value="/usr/bin/rpm-ostree"), \
     patch.object(mod, "run", side_effect=[(0, status), (0, "AvailableUpdate:\nVersion: 44\n")]):
    assert mod.silverblue() is None

with tempfile.TemporaryDirectory() as td:
    fake_home = Path(td)
    omz = fake_home / ".oh-my-zsh"
    (omz / ".git").mkdir(parents=True)
    (omz / "tools").mkdir()
    (omz / "tools/upgrade.sh").write_text("#!/bin/sh\nexit 0\n")
    p10k = fake_home / ".oh-my-zsh/custom/themes/powerlevel10k"
    (p10k / ".git").mkdir(parents=True)
    calls = []
    def git_run(argv, timeout=15):
        calls.append(tuple(argv))
        if "rev-parse" in argv and "HEAD" in argv:
            return 0, "1"*40+"\n"
        if "rev-parse" in argv:
            return 0, "origin/master\n"
        if "ls-remote" in argv:
            return 0, "2"*40+"\trefs/heads/master\n"
        if "status" in argv:
            return 0, ""
        return 127, ""
    with patch.object(mod, "home", return_value=fake_home), \
         patch.object(mod.shutil, "which", return_value="/usr/bin/git"), \
         patch.object(mod, "run", side_effect=git_run):
        omz_offer = mod.managed_checkout("oh-my-zsh")
        p10k_offer = mod.managed_checkout("powerlevel10k")
    assert omz_offer["phase"] == "review"
    assert p10k_offer["phase"] == "review"
    assert len([x for x in calls if "ls-remote" in x]) == 2
    assert not any("pull" in x for x in calls)

    with patch.object(mod, "home", return_value=fake_home), \
         patch.dict(os.environ, {"XDG_STATE_HOME": str(fake_home / ".local/state")}), \
         patch.object(mod, "current_offer", return_value=offered):
        assert not mod.defer("invalid-kind", offered["token"])
        assert not mod.defer("silverblue", "../../etc")
        assert mod.defer("silverblue", offered["token"])
        file = mod.state_file()
        assert (stat.S_IMODE(file.stat().st_mode)) == 0o600
        assert mod.saved_deferrals()["silverblue:" + offered["token"]] > mod.time.time()
        output = StringIO()
        with patch.object(mod, "current_offer", side_effect=lambda k: offered if k == "silverblue" else None), \
             redirect_stdout(output):
            mod.scan()
        assert json.loads(output.getvalue()) == {"schema": 1, "offers": []}

    # No action at all from absent/stale tokens or declined terminal consent.
    with patch.object(mod, "current_offer", return_value=offered), \
         patch("builtins.input", return_value="NO"), \
         patch.object(mod.subprocess, "run") as fake_update:
        assert mod.review("silverblue", "0"*24) == 2
        assert mod.review("silverblue", offered["token"]) == 0
        fake_update.assert_not_called()

    # A changed offer while the user reads the terminal must not be applied.
    changed = dict(offered, token="f"*24)
    with patch.object(mod, "current_offer", side_effect=[offered, changed]), \
         patch("builtins.input", return_value="APPLY"), \
         patch.object(mod.subprocess, "run") as fake_update:
        assert mod.review("silverblue", offered["token"]) == 2
        fake_update.assert_not_called()

    # Only a separate terminal, exact fingerprint and typed APPLY can stage.
    with patch.object(mod, "current_offer", return_value=offered), \
         patch("builtins.input", return_value="APPLY"), \
         patch.object(mod.subprocess, "run") as fake_update:
        fake_update.return_value.returncode = 0
        assert mod.review("silverblue", offered["token"]) == 0
        fake_update.assert_called_once_with(["rpm-ostree", "upgrade"], check=False)

    with patch.object(mod, "current_offer", return_value=pending), \
         patch.object(mod.subprocess, "run") as fake_update:
        assert mod.review("silverblue", pending["token"]) == 0
        fake_update.assert_not_called()

print("Software update offers, 24h defer and double-authorization: PASS")
