#!/usr/bin/env python3
"""Run the exact inline QML Git probe against a disposable worktree."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "services" / "hospital" / "HospitalFirstBedProbeService.qml"


def command(*cmd, env=None, ok=True):
    result = subprocess.run(cmd, capture_output=True, text=True,
                            env=env, timeout=16)
    if ok and result.returncode:
        raise AssertionError(f"Command failed: {cmd}: {result.stderr}")
    if not ok and result.returncode == 0:
        raise AssertionError(f"Expected refusal: {cmd}: {result.stdout}")
    return result


def code_from_qml():
    source = QML.read_text()
    start = source.split("const inspect = [", 1)[1]
    body = start.split('].join("\\n");', 1)[0]
    lines = []
    for raw in body.splitlines():
        value = raw.strip().rstrip(",")
        if value.startswith('"') and value.endswith('"'):
            lines.append(json.loads(value))
    assert len(lines) >= 18, "Failed to recover the QML process script"
    return "\n".join(lines)


def inspect(code, bed, env=None, ok=True):
    result = command("python3", "-c", code, str(bed), env=env, ok=ok)
    return json.loads(result.stdout)


def main():
    source = code_from_qml()
    compile(source, "<Hospital Git Probe>", "exec")
    with tempfile.TemporaryDirectory(prefix="hospital-git-probe-") as base:
        root = Path(base)
        path = root / "test working tree"
        command("git", "init", "-q", "-b", "fixture/main", str(path))
        command("git", "-C", str(path), "config", "user.name", "Hospital Test")
        command("git", "-C", str(path), "config", "user.email",
                "hospital-test@example.invalid")
        (path / "file.txt").write_text("fixture\n")
        command("git", "-C", str(path), "add", "file.txt")
        command("git", "-C", str(path), "commit", "-qm", "fixture")
        command("git", "-C", str(path), "remote", "add", "origin",
                "git@github.com:owner/example.git")
        head = command("git", "-C", str(path), "rev-parse", "HEAD").stdout.strip()
        result = inspect(source, path)
        assert result["path"] == str(path)
        assert result["topLevel"] == str(path)
        assert result["origin"] == "git@github.com:owner/example.git"
        assert result["branch"] == "fixture/main"
        assert result["head"] == head
        assert result["clean"] is True

        # The inspection is still read-only when a worktree is dirty;
        # its evidence must say dirty, so the policy refuses registration.
        (path / "untracked.txt").write_text("unsaved\n")
        assert inspect(source, path)["clean"] is False
        (path / "untracked.txt").unlink()

        alias = root / "alias"
        alias.symlink_to(path, target_is_directory=True)
        assert "canonical" in inspect(source, alias, ok=False)["error"]
        subdir = path / "subdir"
        subdir.mkdir()
        assert "worktree root" in inspect(source, subdir, ok=False)["error"]
        assert "metadata unavailable" in inspect(source, root / "none",
                                                  ok=False)["error"]

        # Fake HOME to verify the live Quickshell path refusal without ever
        # reading the user's actual desktop.
        fake_home = root / "fake-home"
        live = fake_home / ".config" / "quickshell"
        live.parent.mkdir(parents=True)
        live.symlink_to(path, target_is_directory=True)
        env = dict(os.environ, HOME=str(fake_home))
        assert "Live Quickshell" in inspect(source, path, env=env, ok=False)["error"]
        assert command("git", "-C", str(path), "rev-parse", "HEAD").stdout.strip() == head
        assert command("git", "-C", str(path), "symbolic-ref", "--short",
                       "HEAD").stdout.strip() == "fixture/main"
    print("HOSPITAL GIT PROBE FIXTURE // PASS // no writes, correct origin, branch, HEAD and path refusals")


if __name__ == "__main__":
    main()
