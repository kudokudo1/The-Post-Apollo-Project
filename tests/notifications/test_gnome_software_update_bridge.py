#!/usr/bin/env python3
"""No real updates: GNOME Software / Flatpak / fwupd update bridge contracts."""
from pathlib import Path
import importlib.util
from unittest.mock import patch
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
backend = ROOT / "scripts/updates/update_offers.py"
producer = (ROOT / "services/notifications/SoftwareUpdateOfferNotificationProducer.qml").read_text()
hub = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text()
workflow = (ROOT / ".github/workflows/notification-policy-contracts.yml").read_text()
spec = importlib.util.spec_from_file_location("update_offers_bridge", backend)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

assert mod.FLATPAK_REF.fullmatch("app/org.gnome.Calculator/x86_64/stable")
assert mod.FLATPAK_REF.fullmatch("runtime/org.gnome.Platform/x86_64/49")
assert not mod.FLATPAK_REF.fullmatch("../../bin/bash")
assert not mod.FLATPAK_REMOTE.fullmatch("flathub; reboot")
assert "gnome-software\", \"--mode=updates\"" in producer
assert "firmware" in producer and '"flatpak-user"' in producer
assert 'kind.startsWith("flatpak-")' in producer
assert "parsed.offers.slice(0, 6)" in producer
assert '? "OPEN UPDATES"' in hub
assert '? "DOWNLOAD" : "REVIEW"' in hub
assert "test_gnome_software_update_bridge.py" in workflow
assert "fwupdmgr update" not in backend.read_text()
assert "fwupdmgr install" not in backend.read_text()

ref = "app/org.gnome.Calculator/x86_64/stable"
remote = "flathub"
sha = "c"*64
cases = []
def check_run(argv, timeout=15):
    cases.append(tuple(argv))
    if "remote-ls" in argv:
        return 0, "Ref Origin\n" + ref + " " + remote + "\n"
    if "remote-info" in argv:
        return 0, sha + "\n"
    raise AssertionError(argv)

with patch.object(mod.shutil, "which", return_value="/usr/bin/flatpak"), \
     patch.object(mod, "run", side_effect=check_run):
    refs = mod.flatpak_targets("flatpak-user")
    assert refs == [(ref, remote, sha)]
    offered = mod.flatpak_offer("flatpak-user")
    assert offered["kind"] == "flatpak-user"
    assert offered["phase"] == "available"
    assert "DOWNLOAD" in offered["message"]
assert not any("update" in argv for argv in cases if "remote-ls" not in argv)
assert ("flatpak", "remote-info", "--user", "--show-commit", remote, ref) in cases

with patch.object(mod.shutil, "which", return_value="/usr/bin/flatpak"), \
     patch.object(mod, "run", side_effect=[
         (0, "Ref Origin\n" + ref + " " + remote + "\n"),
         (0, "d"*64+"\n")
     ]):
    change = mod.flatpak_offer("flatpak-user")
assert change["token"] != offered["token"]

# Unknown/unparseable refs may NEVER launch an update operation.
with patch.object(mod.shutil, "which", return_value="/usr/bin/flatpak"), \
     patch.object(mod, "run", return_value=(0, "Ref Origin\n../../oops flathub\n")):
    assert mod.flatpak_targets("flatpak-system") is None

devices = json.dumps({"Devices": [{
    "DeviceId": "abcdef012345",
    "Name": "Secure Boot dbx",
    "Releases": [{"Version": "20261001"}]
}]})
with patch.object(mod.shutil, "which", return_value="/usr/bin/fwupdmgr"), \
     patch.object(mod, "run", return_value=(0, devices)):
    firmware = mod.firmware()
assert firmware and firmware["kind"] == "firmware"
assert firmware["phase"] == "review"
assert "GNOME Software" in firmware["message"]
assert "abcdef012345" not in firmware["message"]

with patch.object(mod.shutil, "which", return_value="/usr/bin/fwupdmgr"), \
     patch.object(mod, "run", return_value=(0, "not json")):
    assert mod.firmware() is None

with patch.object(mod, "current_offer", return_value=firmware), \
     patch.object(mod.subprocess, "run") as run_mock, \
     patch("builtins.input") as input_mock:
    assert mod.review("firmware", firmware["token"]) == 0
    run_mock.assert_not_called()
    input_mock.assert_not_called()

# Existing review requires the exact offer both before and after typing.
with patch.object(mod, "current_offer", return_value=offered), \
     patch.object(mod, "flatpak_targets", return_value=refs), \
     patch("builtins.input", return_value="NO"), \
     patch.object(mod.subprocess, "run") as run_mock:
    assert mod.review("flatpak-user", offered["token"]) == 0
    run_mock.assert_not_called()

with patch.object(mod, "current_offer", return_value=offered), \
     patch.object(mod, "flatpak_targets", return_value=refs), \
     patch("builtins.input", return_value="DOWNLOAD"), \
     patch.object(mod.subprocess, "run") as run_mock:
    run_mock.return_value.returncode = 0
    assert mod.review("flatpak-user", offered["token"]) == 0
    run_mock.assert_called_once_with(
        ["flatpak", "update", "--user", "--assumeyes", "--noninteractive",
         "--no-deploy", "--commit="+sha, ref], check=False)

with patch.object(mod, "current_offer", return_value=offered), \
     patch.object(mod, "flatpak_targets", return_value=refs), \
     patch("builtins.input", return_value="APPLY"), \
     patch.object(mod.subprocess, "run") as run_mock:
    run_mock.return_value.returncode = 0
    assert mod.review("flatpak-user", offered["token"]) == 0
    run_mock.assert_called_once_with(
        ["flatpak", "update", "--user", "--assumeyes", "--noninteractive",
         "--commit="+sha, ref], check=False)

with patch.object(mod, "current_offer", side_effect=[offered, change]), \
     patch.object(mod, "flatpak_targets", return_value=refs), \
     patch("builtins.input", return_value="DOWNLOAD"), \
     patch.object(mod.subprocess, "run") as run_mock:
    assert mod.review("flatpak-user", offered["token"]) == 2
    run_mock.assert_not_called()

# Local installed Flatpaks, remote versions, firmware: the updater owns its
# records. No blanket "system is updated" assertions are implied by scan.
print("GNOME Software source bridge, Flatpak pinned download/apply, firmware review: PASS")
