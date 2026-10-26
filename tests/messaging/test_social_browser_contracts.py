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

# The two official web fallbacks are opt-in, not native inbox adapters.
for index, label, key, url in (
    (14, "WHATSAPP", "whatsappweb", "https://web.whatsapp.com/"),
    (15, "MESSENGER", "messengerweb", "https://www.facebook.com/messages/"),
):
    assert f'name: "{label}"' in selector
    assert label.lower() not in browser.SITES
    assert key not in browser.SITES  # 21 ordinary browser-profile slots remain.
    assert browser.site_config(key)[0] == url
    assert geometry.sway_criteria(key) == f'[class="post-apollo-{key}"]'
    assert f'activeAppIndex === {index}' in social
assert 'providerWebOpen = true;' in social
assert 'onBrowserRequested: function(serviceId)' in social

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

# Expanded social/network apps with actual desktop browser entry points.
additional_web_modes = (
    (16, "linkedin", "LINKEDIN", "https://www.linkedin.com/"),
    (17, "mastodon", "MASTODON", "https://mastodon.social/"),
    (18, "nextdoor", "NEXTDOOR", "https://nextdoor.com/"),
    (19, "steamchat", "STEAM CHAT", "https://steamcommunity.com/chat/"),
    (20, "element", "ELEMENT", "https://app.element.io/"),
    (21, "groupme", "GROUPME", "https://web.groupme.com/"),
    (22, "lemon8", "LEMON8", "https://www.lemon8-app.com/"),
    (23, "quora", "QUORA", "https://www.quora.com/"),
    (24, "pixelfed", "PIXELFED", "https://pixelfed.social/"),
    (25, "zalo", "ZALO", "https://chat.zalo.me/"),
)
for index, key, label, url in additional_web_modes:
    assert f'name: "{label}"' in selector
    assert f'activeAppIndex === {index} ? "{key}"' in social
    assert browser.site_config(key) == (
        url, f"post-apollo-{key}", f"{key}-browser"
    )
    assert geometry.sway_criteria(key) == f'[class="post-apollo-{key}"]'
    with patch.dict(os.environ, {
        "POST_APOLLO_X_BROWSER": "/usr/bin/chromium",
        "XDG_DATA_HOME": "/tmp/social-browser-contract",
    }):
        with patch.object(browser.shutil, "which", return_value="/usr/bin/chromium"):
            command = browser.browser_command(key)
    assert f"--app={url}" in command
    assert f"--class=post-apollo-{key}" in command
    assert f"--user-data-dir=/tmp/social-browser-contract/post-apollo/{key}-browser" in command

# LINE now has an explicit provider-owned Chrome extension path. It remains
# outside browser.SITES because it is not an ordinary website.
assert 'name: "LINE"' in selector
assert "linechrome" in browser.EXTENSION_SITES
assert browser.site_config("linechrome")[0] == browser.LINE_EXTENSION_URL
assert geometry.sway_criteria("linechrome") == '[class="post-apollo-linechrome"]'
assert 'activeAppIndex === 28 && providerWebOpen ? "linechrome"' in social

# Remaining mobile/native-oriented services keep truthful provider states.
pending_modes = (
    (26, "SIGNAL", "Native integration pending"),
    (27, "WECHAT", "Native integration pending"),
    (29, "VIBER", "Native integration pending"),
    (30, "KAKAOTALK", "Desktop integration pending"),
    (31, "BEREAL", "Mobile integration pending"),
)
for index, label, detail in pending_modes:
    assert f'name: "{label}"' in selector
    assert label.lower() not in browser.SITES
    assert label.lower() not in geometry.BROWSER_SITES
    assert "ProviderAccessPanel {" in social
    assert "messageRouter.accessBackendMode" in social

# Twitch and YouTube remain in the streaming/media category, not Social.
assert 'name: "TWITCH"' not in selector
assert 'name: "YOUTUBE"' not in selector
assert len(browser.SITES) == 21
assert set(browser.ALL_SITES) == set(geometry.BROWSER_SITES)
assert set(browser.WEB_FALLBACK_SITES) == {"whatsappweb", "messengerweb"}
assert set(browser.EXTENSION_SITES) == {"linechrome"}
assert len({config[1] for config in browser.SITES.values()}) == len(browser.SITES)
assert len({config[2] for config in browser.SITES.values()}) == len(browser.SITES)
assert "activeAppIndex >= 16 && activeAppIndex <= 25" in social
assert "index >= 16 && index <= 25" in social
assert 'readonly property bool providerAccessSelected:' in social
assert 'messageRouter.accessBackendDetail' in social
assert "function ensureSelectedVisible()" in selector
assert "Flickable {" in selector

# Existing sessions/Telegram are still in the native QML conversation lane.
assert "messageRouter.conversations" in social
assert "function showX()" in social
assert '"show", browserSite' in social
assert '"hide", "all"' in social
print("Social browser family source contracts: PASS")
