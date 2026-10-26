#!/usr/bin/env python3
"""M2d3 Kitty actual documented ls JSON shape, no real terminal accessed."""
import copy
import json
import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "time"))
from MachineKittyRead import (
    KittyInventoryError, normalize_kitty_ls, read_existing_kitty_inventory,
)

SENSITIVE = "MY_PRIVATE_TEST_SENTINEL"
def pane(n):
    return {
        "id": n, "title": SENSITIVE, "cwd": "/secret/"+SENSITIVE,
        "pid": 12000+n, "cmdline": ["sh", SENSITIVE],
        "env": {"TOKEN": SENSITIVE}, "is_self": False,
    }
def kitty_os(n):
    return {"id": n, "title": SENSITIVE, "is_focused": False,
            "tabs": [
                {"id": n*100+1, "title": SENSITIVE, "layout": "splits",
                 "windows": [pane(n*1000+1), pane(n*1000+2)]},
                {"id": n*100+2, "title": SENSITIVE, "windows": [
                    pane(n*1000+3)]},
            ]}
payload = [kitty_os(n) for n in range(1,5)]
original = copy.deepcopy(payload)
read = normalize_kitty_ls(json.dumps(payload).encode())
assert read["kind"] == "machine-kitty-native-inventory-projection"
assert read["counts"] == {"os_windows": 4, "tabs": 8, "panes": 12}
assert [x["os_window_id"] for x in read["os_windows"]] == [1,2,3,4]
assert read["os_windows"][0]["tabs"][0]["pane_count"] == 2
assert [x["pane_id"] for x in read["os_windows"][0]["tabs"][0]["panes"]] == [1001,1002]
assert read["read_only"] and not read["executable"]
assert read["safe_actions"] == []
assert not read["capture_enabled"] and not read["restore_enabled"]
assert not read["input_origin_verified"] and not read["host_window_binding_verified"]
assert read["runtime_ids_ephemeral"] and not read["checkpoint_session_match"]
assert SENSITIVE not in json.dumps(read)
assert "pid" not in json.dumps(read).lower()
assert "cwd" not in json.dumps(read).lower()
assert "env" not in json.dumps(read).lower()
assert payload == original
assert read == normalize_kitty_ls(json.dumps(payload))
assert normalize_kitty_ls(b"[]")["counts"]["os_windows"] == 0

def rejects(data):
    try:
        normalize_kitty_ls(data)
    except KittyInventoryError:
        return
    raise AssertionError("bad or oversized Kitty response accepted")

rejects(None)
rejects(b"")
rejects(b"not json")
rejects(b'{"id":1}')
rejects(b"x"*2000001)
rejects({"private": 1})
rejects([[1]])
rejects([{"id": 1, "tabs": "private"}])
rejects([{"id": "1", "tabs": []}])
rejects([{"id": True, "tabs": []}])
rejects([{"id": -1, "tabs": []}])
rejects([{"id": 2**63, "tabs": []}])
rejects([{"id": 1, "tabs": []}, {"id": 1, "tabs": []}])
rejects([{"id": 1, "tabs": [{"id": 1, "windows": []}, {"id": 1, "windows": []}]}])
rejects([{"id": 1, "tabs": [{"id": 1, "windows": [{"id": 2}, {"id": 2}]}]}])
rejects([{"id": 1, "tabs": [{"id": 1, "windows": None}]}])
rejects([{"id": 1, "tabs": [{"id": True, "windows": []}]}])
rejects([{"id": 1, "tabs": [{"id": 1, "windows": [{"id": False}]}]}])
rejects([{"id": 1, "tabs": [{"id": 1, "windows": [{"id": 2}]}]},
         {"id": 2, "tabs": [{"id": 1, "windows": []}]}])
rejects([{"id": 1, "tabs": [{"id": 1, "windows": [{"id": 2}]}]},
         {"id": 2, "tabs": [{"id": 2, "windows": [{"id": 2}]}]}])
rejects([{"id": 1, "tabs": [{"id": n, "windows": []} for n in range(1,2050)]}])
rejects([{"id": n, "tabs": []} for n in range(1,258)])
rejects([{"id": 1, "tabs": [{"id": 1, "windows": [{"id": n} for n in range(1,8194)]}]}])

# The runner is injected. Tests NEVER contact a real socket or run kitten.
cmds = []
def runner(argv, **options):
    cmds.append((list(argv), dict(options)))
    return SimpleNamespace(returncode=0, stdout=json.dumps(payload).encode(),
                           stderr=b"PRIVATE ERROR")

runtime = "/run/user/"+str(os.geteuid())
sock = runtime+"/kitty-probe"
def inspector(path):
    if path == runtime:
        return SimpleNamespace(st_uid=os.geteuid(), st_mode=stat.S_IFDIR|0o700)
    if path == sock:
        return SimpleNamespace(st_uid=os.geteuid(), st_mode=stat.S_IFSOCK|0o600)
    raise OSError("path not found")

def capture(**kwargs):
    return read_existing_kitty_inventory(
        target="unix:"+sock, runtime_directory=runtime,
        opt_in="explicit_read_only_kitty_inventory",
        runner=runner, inspector=inspector, **kwargs)

assert capture() == read
assert len(cmds)==1
assert cmds[0][0] == ["kitten","@","--to","unix:"+sock,"ls"]
assert cmds[0][1] == {
    "check":True, "capture_output":True, "timeout":3, "shell":False}
assert SENSITIVE not in str(cmds)

def refuses(*, target="unix:"+sock, root=runtime,
            choice="explicit_read_only_kitty_inventory", fake_inspector=inspector):
    before = len(cmds)
    try:
        read_existing_kitty_inventory(
            target=target, runtime_directory=root, opt_in=choice,
            runner=runner, inspector=fake_inspector)
    except KittyInventoryError:
        assert len(cmds)==before, "invalid request reached executable"
        return
    raise AssertionError("unsafe target or consent passed")
refuses(choice=False)
refuses(choice="yes")
refuses(choice=None)
refuses(target="tcp:localhost:9999")
refuses(target="unix:/tmp/kitty")
refuses(target="unix:/")
refuses(target="unix:"+runtime+"/../kitty")
refuses(target="unix:"+runtime+"//kitty")
refuses(target="unix:"+runtime+"/kitty/too/many/parts")
refuses(target="unix:"+runtime+"/kitty/../../private")
refuses(root="/")
refuses(root="")
refuses(root=runtime+"/")
refuses(target="unix:@kitty")
refuses(target="unix:relative")
refuses(target="unix:"+runtime+"/symlink")
def insecure(mode):
    def inspect(path):
        if path==runtime:
            return SimpleNamespace(st_uid=os.geteuid(),st_mode=stat.S_IFDIR|0o700)
        return SimpleNamespace(st_uid=os.geteuid(),st_mode=mode)
    return inspect
refuses(fake_inspector=insecure(stat.S_IFREG|0o600))
refuses(fake_inspector=insecure(stat.S_IFLNK|0o700))
refuses(fake_inspector=insecure(stat.S_IFSOCK|0o666))
def other_owner(path):
    v=inspector(path)
    return SimpleNamespace(st_uid=os.geteuid()+1,st_mode=v.st_mode)
refuses(fake_inspector=other_owner)
def bad_runner(argv,**kw):
    raise subprocess.TimeoutExpired(argv,3)
try:
    read_existing_kitty_inventory(target="unix:"+sock,runtime_directory=runtime,
        opt_in="explicit_read_only_kitty_inventory",
        runner=bad_runner, inspector=inspector)
except KittyInventoryError as e:
    assert "PRIVATE" not in str(e)
else:
    raise AssertionError("timeout unexpectedly accepted")
print("MACHINE M2D3: KITTY NATIVE INVENTORY FIELDS REDACTED / READ TRIAL PASS")
