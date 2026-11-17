#!/usr/bin/env python3
"""W28 // Guarded hotkey startup installer contracts, no live Sway writes."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import os
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location(
    "ensure_post_apollo_widget_hotkeys",
    ROOT/"scripts/ensure_post_apollo_widget_hotkeys.py")
assert spec and spec.loader
installer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

for chord in installer.CHORDS:
    assert installer.normalize_chord(chord) in installer.EXPECTED
assert len(installer.EXPECTED)==8

with tempfile.TemporaryDirectory() as root:
    home=Path(root)
    swaydir=home/".config/sway"
    swaydir.mkdir(parents=True)
    main=swaydir/"config"
    include=home/"post-apollo-widget-hotkeys.conf"
    include.write_text((ROOT/"config/sway/post-apollo-widget-hotkeys.conf").read_text())
    original="set $mod Mod1\nbindsym $mod+t exec original-command\n"
    main.write_text(original)
    with patch.object(installer.Path,"home",return_value=home), \
         patch.object(installer,"INCLUDE",include), \
         patch.object(installer,"resolve_validator",return_value=("swaypx","test-swaypx")), \
         patch.object(installer,"checked_config",return_value=(True,"valid")) as check:
        # Check mode is read-only, never creates a config/backup.
        ready,msg=installer.enable(main,sway="swaypx",dry_run=True)
        assert ready and "READY" in msg
        assert main.read_text()==original
        assert not list(swaydir.glob("config.before-widget-hotkeys-*.bak"))

        # Successful install only appends a managed include, preserving bytes,
        # old bindings, original mode and symlink topology.
        main.chmod(0o640)
        ok,msg=installer.enable(main,sway="swaypx")
        assert ok and "INSTALLED" in msg, msg
        check.assert_called_once()
        written=main.read_text()
        assert written.startswith(original)
        assert ('include "' + str(include.resolve()) + '"') in written
        assert written.count("include ")==1
        assert (main.stat().st_mode & 0o777)==0o640
        backups=list(swaydir.glob("config.before-widget-hotkeys-*.bak"))
        assert len(backups)==1 and backups[0].read_text()==original

        # Idempotence is essential when Quickshell is restarted repeatedly.
        check.reset_mock()
        ok,msg=installer.enable(main,sway="swaypx")
        assert ok and "ALREADY" in msg
        assert main.read_text()==written
        assert len(list(swaydir.glob("config.before-widget-hotkeys-*.bak")))==1
        check.assert_not_called()

        # Preserve a symlink into a separate dotfiles checkout and replace
        # the real file only, never the symlink itself.
        dotfiles=home/"dotfiles"
        dotfiles.mkdir()
        target=dotfiles/"sway-user.conf"
        target.write_text(original)
        alias=swaydir/"linked-config"
        alias.symlink_to("../../dotfiles/sway-user.conf")
        link_before=alias.readlink()
        ok,msg=installer.enable(alias,sway="swaypx")
        assert ok and "INSTALLED" in msg
        assert alias.is_symlink() and alias.readlink()==link_before
        assert alias.resolve()==target
        assert target.read_text().startswith(original)
        assert len(list(dotfiles.glob("sway-user.conf.before-widget-hotkeys-*.bak")))==1

        # A collision must preserve the file byte-for-byte, and no new
        # backups or validation calls should be attempted.
        for bad in (
            "bindsym Mod4+t exec my-app\n",
            "set $mod Mod4\nbindsym $mod+Shift+w exec another-app\n",
            "bindcode Mod4+42 exec custom-code\n",
            "bindsym Mod4+T exec uppercase-shifted-key\n",
            "include $unknown/folder.conf\n",
            "include /this/path/cannot/exist.conf\n",
        ):
            main.write_text(bad)
            check.reset_mock()
            before=len(list(swaydir.glob("config.before-widget-hotkeys-*.bak")))
            ok,msg=installer.enable(main,sway="swaypx")
            assert not ok and "SKIPPED" in msg, (bad,msg)
            assert main.read_text()==bad
            assert len(list(swaydir.glob("config.before-widget-hotkeys-*.bak")))==before
            check.assert_not_called()

        # Recursive includes, not just the visible main config, are checked.
        nested=swaydir/"custom.conf"
        nested.write_text("set $owner Mod4\nbindsym $owner+n exec notes\n")
        main.write_text('include "' + str(nested) + '"\n')
        ok,msg=installer.enable(main,sway="swaypx")
        assert not ok and "user shortcuts" in msg
        assert main.read_text()=='include "'+str(nested)+'"\n'

        included_dir=swaydir/"config.d"
        included_dir.mkdir()
        (included_dir/"01-user.conf").write_text(
            "bindsym Mod4+Shift+m exec my-finances\n")
        main.write_text("include "+str(included_dir)+"/*.conf\n")
        ok,msg=installer.enable(main,sway="swaypx")
        assert not ok and "user shortcuts" in msg

        # A broken config must not be replaced, even if all chords are free.
        main.write_text(original)
        with patch.object(installer,"checked_config",
                          return_value=(False,"config parse error")):
            ok,msg=installer.enable(main,sway="swaypx")
            assert not ok and "validation failed" in msg
        assert main.read_text()==original

        # If another worker changes any file while validation runs, abort.
        def concurrent_edit(config, candidate, binary):
            nested.write_text("bindsym Mod4+r exec changed\n")
            return True, "valid"
        main.write_text('include "' + str(nested) + '"\n')
        nested.write_text("bindsym Mod1+v exec harmless\n")
        with patch.object(installer,"checked_config",side_effect=concurrent_edit):
            ok,msg=installer.enable(main,sway="swaypx")
            assert not ok and "changed during validation" in msg
        assert main.read_text()=='include "'+str(nested)+'"\n'

        # The helper never creates a missing Sway config.
        missing=swaydir/"missing"
        ok,msg=installer.enable(missing,sway="swaypx")
        assert not ok and not missing.exists()

        # Without an explicitly verified running compositor, no changes.
        main.write_text(original)
        with patch.object(installer,"correct_live_config",return_value=False):
            ok,msg=installer.enable(main)
            assert not ok and "not positively identified" in msg
        assert main.read_text()==original

# The active config cannot be reloaded automatically because this operator's
# Sway exec_always chain kills/restarts Quickshell.
shell=(ROOT/"shell.qml").read_text()
bootstrap=(ROOT/"services/system/SwayWidgetHotkeyBootstrap.qml").read_text()
assert "SwayWidgetHotkeyBootstrap {" in shell
assert "Process {" not in shell
assert "POST_APOLLO_AUTO_WIDGET_HOTKEYS" in bootstrap
assert "ensure_post_apollo_widget_hotkeys.py" in bootstrap
assert "StdioCollector" in bootstrap
assert "swaymsg reload" not in bootstrap
assert 'Quickshell.watchFiles = false' in shell
print("W28 SAFE AUTO-WIDGET-HOTKEY INSTALL // PASS")
