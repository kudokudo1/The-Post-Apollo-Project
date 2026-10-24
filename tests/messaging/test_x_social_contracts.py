"""Isolated X Social contracts: no browser, login or Sway session required."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "widgets/messanger/XBrowser.py"
GEOMETRY = ROOT / "widgets/messanger/DiscordGeometry.py"
SOCIAL = ROOT / "widgets/messanger/MessagingW.qml"
SELECTOR = ROOT / "widgets/messanger/AppSelector.qml"

for path in (LAUNCHER, GEOMETRY):
    compile(path.read_text(), str(path), "exec")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


browser = load(LAUNCHER, "x_social_browser")
geometry = load(GEOMETRY, "x_social_geometry")

# The user signs into real X in a persistent, distinct browser profile.
with patch.dict(os.environ, {
    "POST_APOLLO_X_BROWSER": "/usr/bin/chromium",
    "XDG_DATA_HOME": "/tmp/post-apollo-contract-test",
}):
    with patch.object(browser.shutil, "which", return_value="/usr/bin/chromium"):
        command = browser.browser_command()
assert "--app=https://x.com" in command
assert "--ozone-platform=x11" in command
assert "--class=post-apollo-x" in command
assert any(
    part.startswith("--user-data-dir=/tmp/post-apollo-contract-test/post-apollo/x-browser")
    for part in command
)

# Flatpak apps must not receive a profile path outside their sandbox.
with patch.object(browser, "browser_prefix", return_value=["flatpak", "run", "com.brave.Browser"]):
    flatpak_command = browser.browser_command()
assert any(
    ".var/app/com.brave.Browser/data/post-apollo/x-browser" in part
    for part in flatpak_command
)

# The launcher never opens a new process if the X application already exists.
commands = []
with patch.object(browser, "site_exists", side_effect=lambda site: site == "x"):
    with patch.object(browser, "sway_command", side_effect=commands.append):
        with patch.object(browser.subprocess, "Popen") as spawn:
            browser.show()
            spawn.assert_not_called()
assert commands == [
    '[class="post-apollo-x"] move scratchpad',
    '[class="post-apollo-x"] scratchpad show',
]

# Hiding X does not destroy the browser or its authenticated profile.
commands.clear()
with patch.object(browser, "x_exists", return_value=True):
    with patch.object(browser, "sway_command", side_effect=commands.append):
        browser.hide()
assert commands == ['[class="post-apollo-x"] move scratchpad']

# Sway XWayland class matching must identify ONLY the isolated X window.
tree = {
    "visible": True,
    "nodes": [
        {"visible": True, "name": "QS_SOCIAL_MENU",
         "rect": {"x": 0, "y": 0, "width": 800, "height": 700}},
        {"visible": True, "app_id": "vesktop",
         "rect": {"x": 1, "y": 1, "width": 300, "height": 300}},
        {"visible": True, "window_properties": {"class": "post-apollo-x"},
         "rect": {"x": 120, "y": 1, "width": 680, "height": 700}},
        {"visible": True, "window_properties": {"class": "Chromium"},
         "rect": {"x": 0, "y": 0, "width": 900, "height": 800}},
    ],
}
snapshot = geometry.snapshot_from_tree(tree)
assert snapshot["social"]["rect"]["width"] == 800
assert snapshot["discord"]["rect"]["width"] == 300
assert snapshot["x"]["rect"]["width"] == 680
assert geometry.sway_criteria("discord") == '[app_id="vesktop"]'
assert geometry.sway_criteria("x") == '[class="post-apollo-x"]'
assert '[class="post-apollo-x"]' in geometry.build_sync_command({
    "target": "x", "x": 1, "y": 2, "width": 300, "height": 400,
})

bridge = geometry.Bridge(0.1)
bridge.x_selected = True
bridge.x_ready = True
commands = []
bridge.queue_sync = commands.append
sample = {
    "social": {"rect": {"x": 0, "y": 0, "width": 800, "height": 700},
               "focused": False},
    "x": {"rect": {"x": 120, "y": 1, "width": 700, "height": 690},
          "focused": True},
}
result = bridge.fast_follow(sample)
assert result["fastLeader"] == "x"
assert commands[0]["target"] == "social"
assert result["shared"]["width"] >= 800

# Discord remains a valid standalone guest and cannot select the X class.
bridge.x_selected = False
bridge.discord_selected = True
bridge.discord_ready = True
commands.clear()
sample["discord"] = sample.pop("x")
result = bridge.fast_follow(sample)
assert result["fastLeader"] == "discord"
assert commands[0]["target"] == "social"

# Source-level contracts: existing Session/Discord paths are still present.
social = SOCIAL.read_text()
selector = SELECTOR.read_text()
assert 'name: "SESSIONS"' in selector
assert 'name: "DISCORD"' in selector
assert 'name: "TELEGRAM"' in selector
assert 'name: "X"' in selector
# The X browser remains index 3, even though the browser lane is now a range.
assert 'activeAppIndex >= 3 && activeAppIndex <= 13' in social
assert 'activeAppIndex === 4 ? "instagram"' in social
assert ': "x"' in social
assert "readonly property bool externalSelected" in social
assert "function showX()" in social
assert "function hideX()" in social
assert "function syncXGeometry(focusWindow)" in social
assert 'Quickshell.shellPath("widgets/messanger/XBrowser.py")' in social
assert "messagingWindow.externalSelected" in social
assert "sessionAdapter.sendMessage(conversationId, text);" in social
assert 'target: "messaging"' in social

print("Social X browser/geometry source contracts: PASS")
