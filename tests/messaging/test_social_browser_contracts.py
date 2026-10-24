"""Offline contracts for the complete Social managed-browser family."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "widgets/messanger"
spec = importlib.util.spec_from_file_location("social_browser", BASE / "XBrowser.py")
browser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)

spec = importlib.util.spec_from_file_location("social_geometry", BASE / "DiscordGeometry.py")
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)

selector = (BASE / "AppSelector.qml").read_text()
social = (BASE / "MessagingW.qml").read_text()

for index, site in enumerate(("instagram", "facebook", "reddit", "threads", "pinterest"), start=4):
    url, window_class, profile = browser.site_config(site)
    assert f'name: "{site.upper()}"' in selector
    assert geometry.sway_criteria(site) == f'[class="{window_class}"]'
    with patch.dict(os.environ, {
        "POST_APOLLO_X_BROWSER": "/usr/bin/chromium",
        "XDG_DATA_HOME": "/tmp/social-browser-contract",
    }):
        with patch.object(browser.shutil, "which", return_value="/usr/bin/chromium"):
            cmd = browser.browser_command(site)
    assert f"--app={url}" in cmd
    assert f"--class={window_class}" in cmd
    assert f"--user-data-dir=/tmp/social-browser-contract/post-apollo/{profile}" in cmd
    assert "browserSite: browserSite" in social
    assert f'activeAppIndex === {index} ? "{site}"' in social

new_sites = (
    (9, "truthsocial", "TRUTH SOCIAL", "https://truthsocial.com/"),
    (10, "bluesky", "BLUESKY", "https://bsky.app/"),
    (11, "tumblr", "TUMBLR", "https://www.tumblr.com/"),
    (12, "tiktok", "TIKTOK", "https://www.tiktok.com/"),
    (13, "snapchat", "SNAPCHAT", "https://web.snapchat.com/"),
)
for index, site, label, url in new_sites:
    configured_url, window_class, profile = browser.site_config(site)
    assert configured_url == url
    assert f'name: "{label}"' in selector
    assert f'activeAppIndex === {index} ? "{site}"' in social
    assert window_class == f"post-apollo-{site}"
    assert profile == f"{site}-browser"
    assert geometry.sway_criteria(site) == f'[class="{window_class}"]'
    with patch.dict(os.environ, {
        "POST_APOLLO_X_BROWSER": "/usr/bin/chromium",
        "XDG_DATA_HOME": "/tmp/social-browser-contract",
    }):
        with patch.object(browser.shutil, "which", return_value="/usr/bin/chromium"):
            command = browser.browser_command(site)
    assert f"--app={url}" in command
    assert f"--class={window_class}" in command
    assert f"--user-data-dir=/tmp/social-browser-contract/post-apollo/{profile}" in command

# WhatsApp and Messenger use an explicit, unconnected native messaging slot.
for index, label in ((14, "WHATSAPP"), (15, "MESSENGER")):
    assert f'name: "{label}"' in selector
    assert label.lower() not in browser.SITES
    assert label.lower() not in geometry.BROWSER_SITES
    assert f'activeAppIndex === {index} ? "{label} // Native integration pending"' in social

# Keep all modes reachable in the fixed-height Social selector via scrolling.
assert "Flickable {" in selector
assert "function ensureSelectedVisible()" in selector
assert "onSelectedIndexChanged:" in selector
assert "flickableDirection: Flickable.VerticalFlick" in selector
assert "appScroll.contentY =" in selector
assert "activeAppIndex >= 3 && activeAppIndex <= 13" in social
assert "index >= 3 && index <= 13" in social

assert browser.site_config("threads")[0] == "https://www.threads.com/"
assert 'name: "REELS"' not in selector
assert "reels" not in browser.SITES
assert "reels" not in geometry.BROWSER_SITES
assert 'activeAppIndex === 7 ? "threads"' in social
assert browser.site_config("threads")[1] == "post-apollo-threads"
assert browser.site_config("pinterest")[0] == "https://www.pinterest.com/"
assert len({config[1] for config in browser.SITES.values()}) == len(browser.SITES)
assert len({config[2] for config in browser.SITES.values()}) == len(browser.SITES)
assert browser.site_config("threads")[2] != browser.site_config("instagram")[2]
assert "activeAppIndex >= 3 && activeAppIndex <= 13" in social
assert "index >= 3 && index <= 13" in social

commands = []
with patch.object(browser, "site_exists", side_effect=lambda site: site in ("x", "reddit")):
    with patch.object(browser, "sway_command", side_effect=commands.append):
        with patch.object(browser.subprocess, "Popen") as spawn:
            browser.show("reddit")
            spawn.assert_not_called()
assert commands == [
    '[class="post-apollo-x"] move scratchpad',
    '[class="post-apollo-reddit"] move scratchpad',
    '[class="post-apollo-reddit"] scratchpad show',
]

nodes = [
    {"visible": True, "name": "QS_SOCIAL_MENU", "rect": {"x": 0, "y": 0, "width": 800, "height": 700}},
]
for site in ("x", "instagram", "facebook", "reddit", "threads", "pinterest", "truthsocial", "bluesky", "tumblr", "tiktok", "snapchat"):
    nodes.append({
        "visible": True,
        "window_properties": {"class": f"post-apollo-{site}"},
        "rect": {"x": 120, "y": 1, "width": 680, "height": 700},
    })
sample = geometry.snapshot_from_tree({"visible": True, "nodes": nodes})
for site in ("x", "instagram", "facebook", "reddit", "threads", "pinterest", "truthsocial", "bluesky", "tumblr", "tiktok", "snapchat"):
    assert sample[site] and sample[site]["rect"]["width"] == 680
    bridge = geometry.Bridge(0.1)
    bridge.x_selected = True
    bridge.x_ready = True
    bridge.browser_site = site
    bridge.queue_sync = commands.append
    commands.clear()
    focused = {
        "social": {"rect": {"x": 0, "y": 0, "width": 800, "height": 700}, "focused": False},
        site: {"rect": {"x": 120, "y": 1, "width": 680, "height": 700}, "focused": True},
    }
    result = bridge.fast_follow(focused)
    assert result["fastLeader"] == site
    assert commands and commands[0]["target"] == "social"

# Existing sessions/Telegram are still in the native QML conversation lane.
assert "sessionAdapter.conversations" in social
assert "function showX()" in social
assert '"show", browserSite' in social
assert '"hide", "all"' in social
print("Social browser family source contracts: PASS")
