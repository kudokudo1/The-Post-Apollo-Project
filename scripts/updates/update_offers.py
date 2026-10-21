#!/usr/bin/env python3
"""Post-Apollo update offers, not an unattended package manager.

scan: read-only deployment + managed Git checkout observations.
defer: explicitly requested suppression of one unchanged offer for 24 hours.
review: fresh-check the offer in Kitty and require typed APPLY before mutation.

No sudo, reboot, shell interpolation, arbitrary paths or auto-updates.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ALLOWED = {"silverblue", "oh-my-zsh", "powerlevel10k",
           "flatpak-user", "flatpak-system", "firmware"}
FLATPAK_REF = re.compile(r"(?:app|runtime)/[A-Za-z0-9_.-]+/[A-Za-z0-9_]+/[A-Za-z0-9_.-]+")
FLATPAK_REMOTE = re.compile(r"[A-Za-z0-9_.-]{1,100}")
REVISION = re.compile(r"[a-f0-9]{40,64}")
DEFER_SECONDS = 24 * 60 * 60


def home() -> Path:
    return Path.home()


def state_file() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or home() / ".local/state")
    return base / "post-apollo" / "update-offer-deferrals.json"


def run(argv: list[str], timeout: int = 15) -> tuple[int, str]:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["LC_ALL"] = "C"
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                           env=env, check=False)
        return p.returncode, p.stdout[:32000]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return 127, ""


def fingerprint(kind: str, current: str, target: str) -> str:
    return hashlib.sha256(f"{kind}\0{current}\0{target}".encode()).hexdigest()[:24]


def offer(kind: str, current: str, target: str, title: str,
          message: str, phase: str) -> dict[str, str]:
    return {"kind": kind, "token": fingerprint(kind, current, target),
            "title": title, "message": message, "phase": phase}


def silverblue() -> dict[str, str] | None:
    if not shutil.which("rpm-ostree"):
        return None
    rc, raw = run(["rpm-ostree", "status", "--json"], timeout=15)
    if rc != 0:
        return None
    try:
        deployments = json.loads(raw).get("deployments", [])
        if not isinstance(deployments, list):
            return None
        booted = next((d for d in deployments if d.get("booted") is True), None)
        pending = deployments[0] if deployments else None
        current = str((booted or {}).get("checksum", "")).strip()
        target = str((pending or {}).get("checksum", "")).strip()
        if pending and not pending.get("booted", False) and booted and target and current != target:
            return offer("silverblue", current, target, "SILVERBLUE // REBOOT PENDING",
                         "A newer OS deployment is already staged. It becomes active on "
                         "a separate reboot. Review it in Updates before restarting.", "staged")
    except (ValueError, TypeError, AttributeError):
        return None

    # rpm-ostree --check examines remote metadata; it does NOT create a
    # deployment. Avoid guessing from arbitrary error/transaction output.
    rc, result = run(["rpm-ostree", "upgrade", "--check"], timeout=90)
    if rc != 0 or not re.search(r"(?m)^\s*AvailableUpdate:\s*$", result):
        return None
    match = re.search(r"(?m)^\s*Commit:\s*([a-fA-F0-9]{40,64})\s*$", result)
    if not match:
        return None
    target = match.group(1).lower()
    if target == current:
        return None
    version = re.search(r"(?m)^\s*Version:\s*(.{1,100})$", result)
    label = version.group(1).strip() if version else "new deployment"
    return offer("silverblue", current, target, "SILVERBLUE // UPDATE AVAILABLE",
                 "A new OS deployment is offered (" + label + "). Apply stages it "
                 "for the next reboot; it will not reboot automatically.", "available")


def managed_checkout(kind: str) -> dict[str, str] | None:
    if kind == "oh-my-zsh":
        folder = home() / ".oh-my-zsh"
    elif kind == "powerlevel10k":
        choices = [home() / ".oh-my-zsh/custom/themes/powerlevel10k",
                   home() / "powerlevel10k"]
        folder = next((p for p in choices if (p / ".git").exists()), choices[0])
    else:
        return None
    if not (folder / ".git").exists() or not shutil.which("git"):
        return None
    rc, local = run(["git", "-C", str(folder), "rev-parse", "--verify", "HEAD"])
    if rc or not re.fullmatch("[a-f0-9]{40,64}", local.strip()):
        return None
    rc, tracking = run(["git", "-C", str(folder),
                        "rev-parse", "--abbrev-ref", "--symbolic-full-name",
                        "@{upstream}"])
    upstream = tracking.strip()
    if rc or "/" not in upstream:
        return None
    remote, branch = upstream.split("/", 1)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", remote):
        return None
    if not re.fullmatch(r"[A-Za-z0-9_./-]{1,150}", branch) or ".." in branch:
        return None
    rc, latest = run(["git", "-C", str(folder), "ls-remote", "--exit-code",
                      remote, "refs/heads/" + branch], timeout=20)
    if rc:
        return None
    match = re.fullmatch(r"([a-f0-9]{40,64})\s+refs/heads/[^\s]+\s*", latest)
    if not match:
        return None
    current, target = local.strip(), match.group(1)
    if current == target:
        return None

    # A changed remote HEAD is an offer to REVIEW, not proven FF eligibility.
    label = "OH MY ZSH" if kind == "oh-my-zsh" else "POWERLEVEL10K"
    return offer(kind, current, target, label + " // REMOTE CHANGE FOUND",
                 "The tracked remote revision differs from the local checkout. "
                 "Review the changes and local Git state before updating.", "review")


def flatpak_targets(kind: str) -> list[tuple[str, str, str]] | None:
    """Refs, remotes and pinned upstream commits, or None on unreliable evidence."""
    if kind not in ("flatpak-user", "flatpak-system") or not shutil.which("flatpak"):
        return None
    scope = "--user" if kind == "flatpak-user" else "--system"
    rc, raw = run(["flatpak", "remote-ls", scope, "--updates",
                   "--columns=ref,origin"], timeout=45)
    if rc:
        return None
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    # A bounded complete result prevents partial notices or mass operations.
    if len(lines) > 30:
        return None
    found = []
    for line in lines:
        fields = line.split()
        if [part.lower() for part in fields] == ["ref", "origin"]:
            continue
        if len(fields) != 2 or not FLATPAK_REF.fullmatch(fields[0]) or not FLATPAK_REMOTE.fullmatch(fields[1]):
            return None
        ref, remote = fields
        rc, text = run(["flatpak", "remote-info", scope, "--show-commit",
                        remote, ref], timeout=20)
        commit = text.strip().lower()
        if rc or not REVISION.fullmatch(commit):
            return None
        found.append((ref, remote, commit))
    return sorted(set(found))


def flatpak_offer(kind: str) -> dict[str, str] | None:
    rows = flatpak_targets(kind)
    if not rows:
        return None
    # This token is derived from the exact refs, remotes and upstream commits,
    # NOT solely from app names or last-known installed versions.
    target = "\n".join("\t".join(row) for row in rows)
    label = "USER" if kind == "flatpak-user" else "SYSTEM"
    return offer(kind, label, target,
                 "FLATPAK // " + label + " UPDATES AVAILABLE",
                 str(len(rows)) + " Flatpak ref(s) have upstream changes. "
                 "DOWNLOAD caches pinned versions without deployment; APPLY installs. "
                 "Review the exact refs and confirm separately in Kitty.",
                 "available")


def firmware() -> dict[str, str] | None:
    """Observe fwupd JSON, but never install/flash firmware from this program."""
    if not shutil.which("fwupdmgr"):
        return None
    rc, raw = run(["fwupdmgr", "get-updates", "--json"], timeout=45)
    if rc != 0:
        return None
    try:
        data = json.loads(raw)
        devices = data.get("Devices", [])
        if not isinstance(devices, list):
            return None
        found = []
        for device in devices[:40]:
            if not isinstance(device, dict):
                continue
            device_id = str(device.get("DeviceId", ""))
            releases = device.get("Releases", [])
            if not isinstance(releases, list) or not releases:
                continue
            for release in releases[:2]:
                if not isinstance(release, dict):
                    continue
                version = str(release.get("Version", "")).strip()
                if device_id and version and len(device_id) < 256 and len(version) < 120:
                    found.append((device_id, version))
        if not found:
            return None
        found.sort()
        return offer("firmware", "fwupd", repr(found),
                     "FIRMWARE // UPDATE NEEDS REVIEW",
                     str(len(found)) + " firmware release(s) reported by fwupd. "
                     "Review the devices, warnings and restart requirements in "
                     "GNOME Software before making any firmware changes.",
                     "review")
    except (ValueError, TypeError, AttributeError):
        return None


def current_offer(kind: str) -> dict[str, str] | None:
    if kind == "silverblue":
        return silverblue()
    if kind.startswith("flatpak-"):
        return flatpak_offer(kind)
    if kind == "firmware":
        return firmware()
    if kind in ("oh-my-zsh", "powerlevel10k"):
        return managed_checkout(kind)
    return None


def saved_deferrals() -> dict[str, float]:
    try:
        obj = json.loads(state_file().read_text())
        return {str(k): float(v) for k, v in obj.items()
                if isinstance(k, str) and isinstance(v, (int, float))}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def defer(kind: str, token: str) -> bool:
    if kind not in ALLOWED or not re.fullmatch(r"[0-9a-f]{24}", token):
        return False
    # Persist a 24-hour decision, scoped to the exact offer fingerprint.
    path = state_file()
    data = {k: v for k, v in saved_deferrals().items() if v > time.time()}
    data[kind + ":" + token] = time.time() + DEFER_SECONDS
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".updates-", text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, separators=(",", ":"))
            stream.write("\n")
        os.replace(temp, path)
        return True
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def scan() -> None:
    until = saved_deferrals()
    now = time.time()
    rows = []
    for kind in ("silverblue", "flatpak-user", "flatpak-system",
                 "firmware", "oh-my-zsh", "powerlevel10k"):
        item = current_offer(kind)
        if item and until.get(kind + ":" + item["token"], 0) <= now:
            rows.append(item)
    print(json.dumps({"schema": 1, "offers": rows}, separators=(",", ":")))


def fresh_checkout_is_clean(kind: str) -> bool:
    paths = {"oh-my-zsh": home() / ".oh-my-zsh",
             "powerlevel10k": next(
                (p for p in [home() / ".oh-my-zsh/custom/themes/powerlevel10k",
                             home() / "powerlevel10k"] if (p / ".git").exists()),
                home() / "powerlevel10k")}
    path = paths[kind]
    rc, dirty = run(["git", "-C", str(path), "status",
                     "--porcelain", "--untracked-files=normal"])
    if rc or dirty.strip():
        print("UPDATE REFUSED // Working tree contains local changes.")
        return False
    return True


def review(kind: str, token: str) -> int:
    if kind not in ALLOWED or not re.fullmatch(r"[0-9a-f]{24}", token):
        print("UPDATE REFUSED // Unknown offer.")
        return 2
    item = current_offer(kind)
    if not item or item["token"] != token:
        print("UPDATE REFUSED // Offer changed or no longer available. Scan again.")
        return 2
    print(item["title"])
    print(item["message"])
    print("\nThis is a separate terminal authorization, NOT automatic installation.")
    if item["phase"] == "staged":
        print("The Silverblue deployment is already staged. No update is needed.")
        print("Review with: rpm-ostree status")
        print("Reboot separately when ready. This tool will never reboot.")
        return 0
    if kind == "firmware":
        print("Firmware installation is managed only through GNOME Software/fwupd.")
        print("No firmware updater command is available through this script.")
        return 0
    if kind.startswith("flatpak-"):
        rows = flatpak_targets(kind)
        if not rows:
            print("UPDATE REFUSED // Flatpak target list changed.")
            return 2
        scope = "--user" if kind == "flatpak-user" else "--system"
        print("\nFlatpak scope: " + scope)
        for ref, remote, commit in rows:
            print(" ", ref, "//", remote, "//", commit[:12])
        print("\nDOWNLOAD caches pinned versions without installing.")
        print("APPLY downloads and deploys each pinned version.")
        print("Existing GNOME Software auto-update preferences are unchanged.")
        try:
            answer = input("\nType DOWNLOAD, APPLY, or anything else to cancel: ")
        except (EOFError, KeyboardInterrupt):
            print("\nCANCELLED // No Flatpak command executed.")
            return 0
        if answer not in ("DOWNLOAD", "APPLY"):
            print("CANCELLED // No Flatpak command executed.")
            return 0
        fresh = current_offer(kind)
        if not fresh or fresh["token"] != token or flatpak_targets(kind) != rows:
            print("UPDATE REFUSED // Flatpak targets changed during review.")
            return 2
        for ref, remote, commit in rows:
            argv = ["flatpak", "update", scope,
                    "--assumeyes", "--noninteractive"]
            if answer == "DOWNLOAD":
                argv.append("--no-deploy")
            argv.extend(["--commit=" + commit, ref])
            print("\nRUNNING //", " ".join(argv))
            result = subprocess.run(argv, check=False)
            if result.returncode != 0:
                print("UPDATE INCOMPLETE // Stop at first failure.")
                return result.returncode
        print("\nCOMPLETE //", "Downloads cached." if answer == "DOWNLOAD"
              else "Pinned Flatpak updates applied.")
        return 0
    if kind in ("oh-my-zsh", "powerlevel10k") and not fresh_checkout_is_clean(kind):
        return 2
    if kind == "silverblue":
        command = ["rpm-ostree", "upgrade"]
        print("This stages a deployment, not a live OS replacement.")
    elif kind == "oh-my-zsh":
        updater = home() / ".oh-my-zsh/tools/upgrade.sh"
        if not updater.is_file() or not shutil.which("zsh"):
            print("UPDATE REFUSED // Official Oh My Zsh updater unavailable.")
            return 2
        command = ["zsh", str(updater)]
        print("Runs the official Oh My Zsh update script.")
    elif kind == "powerlevel10k":
        folder = next((p for p in [home() / ".oh-my-zsh/custom/themes/powerlevel10k",
                                  home() / "powerlevel10k"] if (p / ".git").exists()), None)
        if not folder:
            return 2
        command = ["git", "-C", str(folder), "pull", "--ff-only"]
        print("Uses a fast-forward-only Git pull. Restart Zsh afterward.")
    print("Command:", " ".join(command))
    try:
        answer = input("\nType APPLY to authorize, or anything else to cancel: ")
    except (EOFError, KeyboardInterrupt):
        print("\nCANCELLED // No update command executed.")
        return 0
    if answer != "APPLY":
        print("CANCELLED // No update command executed.")
        return 0
    # The exact fingerprint must still refer to the same offered version,
    # including after the operator has spent time reading this terminal.
    fresh = current_offer(kind)
    if not fresh or fresh["token"] != token or fresh["phase"] != item["phase"]:
        print("UPDATE REFUSED // Offer changed during confirmation.")
        return 2
    if kind in ("oh-my-zsh", "powerlevel10k") and not fresh_checkout_is_clean(kind):
        return 2
    return subprocess.run(command, check=False).returncode


def main() -> int:
    args = sys.argv[1:]
    if args == ["scan"]:
        scan()
        return 0
    if len(args) == 3 and args[0] == "defer":
        return 0 if defer(args[1], args[2]) else 2
    if len(args) == 3 and args[0] == "review":
        return review(args[1], args[2])
    print("Usage: update_offers.py scan | defer KIND TOKEN | review KIND TOKEN",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
