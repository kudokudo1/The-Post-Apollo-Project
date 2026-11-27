"""Stage 1: pinned PUBLIC artifact verification only. Never run downloaded code.

Manual GitHub-hosted job only. No model/service invocation, credentials, model
pull, retry, artifact publishing or native admission. Fail closed on unknowns.
"""
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import shutil
import ssl
import stat
import subprocess
import sys
import tarfile
import time
from urllib.parse import urlsplit, parse_qs

GIB = 1024**3
ARCHIVE_SIZE = 1421191399
ARCHIVE_SHA = "c620917a71e146ab3a7f893084f066069c4c65d144ef8379a91c3cbe8b27de8f"
MANIFEST_SHA = "07bd1f170855240f9e162bf54ea494a8bc1c73d8cbd1365d7fccbeb7d2504947"
RELEASE = "https://github.com/ollama/ollama/releases/download/v0.32.14/ollama-linux-amd64.tar.zst"
RELEASE_REPO_ID = 658928958
RELEASE_ASSET_ID = 517039292
RELEASE_FILENAME = "ollama-linux-amd64.tar.zst"
RELEASE_CDN_PATH = re.compile(
    r"/github-production-release-asset/658928958/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z", re.ASCII)
REGISTRY = "https://registry.ollama.ai/v2/library/granite3.3/"
R2 = "dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
MODEL_LIMIT = 1560000000
MANIFEST_LIMIT = 65536
EXTRACT_LIMIT = 6 * GIB
DISK_RESERVE = 2 * GIB
TOTAL_SECONDS = 660
CHUNK = 1024 * 1024
MAX_MEMBERS = 30000


class Hold(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise Hold(code)


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, "DUPLICATE_JSON_KEY")
        result[k] = v
    return result


def parse_manifest(raw):
    require(0 < len(raw) <= MANIFEST_LIMIT and digest_bytes(raw) == MANIFEST_SHA,
            "MANIFEST_DIGEST")
    obj = json.loads(raw, object_pairs_hook=unique_pairs)
    require(type(obj) is dict and obj.get("schemaVersion") == 2
            and type(obj.get("layers")) is list and 1 <= len(obj["layers"]) <= 16,
            "MANIFEST_SHAPE")
    entries = [obj.get("config")] + obj["layers"]
    blobs = {}
    for entry in entries:
        require(type(entry) is dict and set(entry) == {"mediaType", "digest", "size"}
                and type(entry["mediaType"]) is str
                and type(entry["digest"]) is str and DIGEST.fullmatch(entry["digest"])
                and type(entry["size"]) is int and 0 < entry["size"] <= MODEL_LIMIT,
                "BLOB_DESCRIPTOR")
        require(entry["digest"] not in blobs, "DUPLICATE_BLOB")
        blobs[entry["digest"]] = entry["size"]
    require(entries[0]["size"] <= CHUNK and sum(blobs.values()) <= MODEL_LIMIT,
            "MODEL_BYTE_LIMIT")
    return blobs


def target(url, kind, digest=None, redirected=False):
    require(type(url) is str and len(url) <= 16384, "URL_INVALID")
    p = urlsplit(url)
    require(p.scheme == "https" and p.username is None and p.password is None
            and p.port is None and not p.fragment and p.hostname
            and not any(c in url for c in ("\r", "\n", "\\"))
            and p.netloc == p.hostname, "URL_INVALID")
    if not redirected:
        expected = (RELEASE if kind == "archive" else
                    REGISTRY + "manifests/2b" if kind == "manifest" else
                    REGISTRY + "blobs/" + digest)
        require(url == expected, "SOURCE_REFUSED")
    elif kind == "archive":
        # Public release metadata independently identifies repo, asset ID,
        # filename, size and digest. CDN storage UUID is not the API asset ID.
        # This narrows the CDN namespace and verifies the signed filename;
        # the initial exact release URL and final bytes remain essential.
        query = parse_qs(p.query, strict_parsing=True, max_num_fields=32)
        require(p.hostname == "release-assets.githubusercontent.com"
                and RELEASE_CDN_PATH.fullmatch(p.path)
                and query.get("response-content-disposition") in (
                    ["attachment; filename=" + RELEASE_FILENAME],
                    ['attachment; filename="' + RELEASE_FILENAME + '"'])
                and len(query.get("sig", [])) == 1
                and bool(query["sig"][0]), "REDIRECT_REFUSED")
    elif kind == "blob":
        require(type(digest) is str and DIGEST.fullmatch(digest), "BLOB_DESCRIPTOR")
        hexval = digest[7:]
        require(p.hostname == R2
                and p.path == "/ollama/docker/registry/v2/blobs/sha256/"
                + hexval[:2] + "/" + hexval + "/data"
                and bool(p.query), "REDIRECT_REFUSED")
    else:
        raise Hold("REDIRECT_REFUSED")
    return p


def remaining(deadline):
    left = deadline - time.monotonic()
    require(left > 0, "DEADLINE")
    return left


def fetch(url, kind, output, deadline, *, size=None, sha=None, digest=None):
    """Direct TLS, no proxy, cookies, authorization, retries or broad redirects."""
    cap = MANIFEST_LIMIT if size is None else size
    for redirected in (False, True):
        p = target(url, kind, digest, redirected)
        conn = http.client.HTTPSConnection(p.hostname, timeout=min(15, remaining(deadline)),
                                           context=ssl.create_default_context())
        try:
            request = p.path + ("?" + p.query if p.query else "")
            conn.request("GET", request, headers={
                "Accept": "application/vnd.docker.distribution.manifest.v2+json"
                if kind == "manifest" else "application/octet-stream",
                "Accept-Encoding": "identity", "User-Agent": "Forest-Stage1-public-verifier"})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                require(not redirected, "REDIRECT_LIMIT")
                url = response.getheader("Location")
                # Do not echo signed URLs, server text or headers.
                target(url, kind, digest, True)
                continue
            require(response.status == 200, "HTTP_REFUSED")
            require(response.getheader("Content-Encoding") in (None, "identity"),
                    "CONTENT_ENCODING")
            length = response.getheader("Content-Length")
            if length is not None:
                require(length.isascii() and length.isdecimal()
                        and 0 < int(length) <= cap
                        and (size is None or int(length) == size), "CONTENT_LENGTH")
            h = hashlib.sha256()
            count = 0
            with output.open("xb") as out:
                while True:
                    remaining(deadline)
                    chunk = response.read(min(CHUNK, cap - count + 1))
                    if not chunk:
                        break
                    count += len(chunk)
                    require(count <= cap, "TRANSFER_LIMIT")
                    out.write(chunk)
                    h.update(chunk)
            require(count > 0 and (size is None or count == size)
                    and h.hexdigest() == sha, "TRANSFER_DIGEST")
            return count
        finally:
            conn.close()
    raise Hold("REDIRECT_LIMIT")


def member_path(name):
    require(type(name) is str and len(name) <= 512 and "\\" not in name
            and not name.startswith("/") and all(32 <= ord(c) < 127 for c in name),
            "ARCHIVE_PATH")
    parts = PurePosixPath(name).parts
    require(".." not in parts and len(parts) <= 32, "ARCHIVE_PATH")
    return "/".join(parts)


def link_target(name, link):
    require(type(link) is str and 0 < len(link) <= 512
            and not link.startswith("/") and "\\" not in link
            and all(32 <= ord(c) < 127 for c in link), "ARCHIVE_LINK")
    stack = name.split("/")[:-1]
    for part in PurePosixPath(link).parts:
        if part == "..":
            require(bool(stack), "ARCHIVE_LINK")
            stack.pop()
        elif part != ".":
            stack.append(part)
    require(bool(stack) and len(stack) <= 32, "ARCHIVE_LINK")
    return "/".join(stack)


def validate_tar_tail(source, end, size, deadline):
    # tarfile may buffer or silently stop on invalid headers. The physical
    # seekable decompressed bytes, not its buffered stream, prove the tail.
    require(type(end) is int and end >= 0 and end % 512 == 0
            and size % 512 == 0 and size - end >= 1024, "ARCHIVE_TERMINATOR")
    source.seek(end)
    remaining_bytes = size - end
    require(remaining_bytes <= CHUNK, "ARCHIVE_TRAILING")
    while remaining_bytes:
        remaining(deadline)
        block = source.read(min(CHUNK, remaining_bytes))
        require(bool(block) and not any(block), "ARCHIVE_TRAILING")
        remaining_bytes -= len(block)


def unpack(source, deadline):
    """Hash data-only tar members in a bounded, seekable spool.

    No materialized files, symlinks, executables, devices or duplicate
    extraction disk allocation. Full decompressed tail checked by offset.
    """
    records, dirs, links, names = {}, {""}, {}, set()
    count = total = 0
    source.seek(0, os.SEEK_END)
    size = source.tell()
    require(0 < size <= EXTRACT_LIMIT, "ARCHIVE_STREAM_LIMIT")
    source.seek(0)
    with tarfile.open(fileobj=source, mode="r:") as archive:
        for member in archive:
            remaining(deadline)
            count += 1
            require(count <= MAX_MEMBERS, "ARCHIVE_MEMBER_LIMIT")
            name = member_path(member.name)
            require(name not in names, "ARCHIVE_DUPLICATE")
            names.add(name)
            require(not member.sparse and not any(k.startswith("GNU.sparse")
                    for k in member.pax_headers), "ARCHIVE_SPARSE")
            require(0 <= member.offset < member.offset_data <= size
                    and 0 <= member.size <= size - member.offset_data,
                    "ARCHIVE_TRUNCATED")
            if not name:
                require(member.isdir() and member.size == 0, "ARCHIVE_PATH")
                continue
            parents = [str(p) for p in PurePosixPath(name).parents if str(p) != "."]
            require(not any(p in records or p in links for p in parents), "ARCHIVE_PARENT")
            if member.isdir():
                require(member.size == 0, "ARCHIVE_DIRECTORY")
                dirs.add(name)
                dirs.update(parents)
                continue
            require(name not in dirs, "ARCHIVE_DUPLICATE")
            dirs.update(parents)
            if member.issym():
                require(member.size == 0, "ARCHIVE_LINK")
                links[name] = link_target(name, member.linkname)
                continue
            require(member.isfile() and 0 <= member.size <= EXTRACT_LIMIT - total,
                    "ARCHIVE_MEMBER_TYPE_OR_SIZE")
            h = hashlib.sha256()
            with archive.extractfile(member) as data:
                left = member.size
                while left:
                    remaining(deadline)
                    block = data.read(min(CHUNK, left))
                    require(bool(block), "ARCHIVE_TRUNCATED")
                    h.update(block)
                    left -= len(block)
            total += member.size
            records[name] = (member.size, h.hexdigest())
        end = archive.offset
    validate_tar_tail(source, end, size, deadline)
    for name, dest in links.items():
        seen = {name}
        while dest in links:
            require(dest not in seen and len(seen) < 32, "ARCHIVE_LINK_CYCLE")
            seen.add(dest)
            dest = links[dest]
        require(dest in records or dest in dirs, "ARCHIVE_LINK_TARGET")
    require("bin/ollama" in records, "RUNTIME_BINARY_MISSING")
    return records, links, total


def extract_archive(path, root, deadline):
    # One bounded spool replaces materialized extraction, within existing
    # 6GiB disk budget. Never execute, chmod or create archive members.
    require(Path("/usr/bin/zstd").is_file(), "DECOMPRESSOR_MISSING")
    spool = root / "runtime.tar"
    with subprocess.Popen(["/usr/bin/zstd", "-dc", "--", str(path)],
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, close_fds=True) as proc:
        try:
            count = 0
            with spool.open("xb") as out:
                while True:
                    remaining(deadline)
                    block = proc.stdout.read(min(CHUNK, EXTRACT_LIMIT - count + 1))
                    if not block:
                        break
                    count += len(block)
                    require(count <= EXTRACT_LIMIT, "ARCHIVE_STREAM_LIMIT")
                    require(shutil.disk_usage(root).free >= len(block) + DISK_RESERVE,
                            "DISK_RESERVE")
                    out.write(block)
            require(proc.wait(timeout=min(15, remaining(deadline))) == 0,
                    "DECOMPRESSOR_FAILED")
            with spool.open("rb") as source:
                return unpack(source, deadline)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


def preflight(root):
    require(sys.platform == "linux" and os.uname().machine == "x86_64"
            and os.getuid() != 0 and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
            and os.environ.get("RUNNER_ARCH") == "X64"
            and os.environ.get("ImageOS") == "ubuntu24"
            and re.fullmatch(r"[0-9.]+", os.environ.get("ImageVersion", "")) is not None
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
            and os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "RUNNER_SCOPE")
    osinfo = Path("/etc/os-release").read_text(encoding="utf-8")
    require('VERSION_ID="24.04"' in osinfo and "ID=ubuntu" in osinfo, "RUNNER_OS")
    st = root.lstat()
    require(stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid()
            and stat.S_IMODE(st.st_mode) == 0o700 and not any(root.iterdir()),
            "OWNED_STAGE_DIRECTORY")
    require(shutil.disk_usage(root).free >= ARCHIVE_SIZE + MODEL_LIMIT
            + EXTRACT_LIMIT + DISK_RESERVE, "DISK_PREFLIGHT")
    require(Path("/usr/bin/zstd").is_file(), "DECOMPRESSOR_MISSING")
    # No inherited open files other than stdio; listing fd may have closed.
    for name in os.listdir("/proc/self/fd"):
        if int(name) > 2:
            try:
                os.fstat(int(name))
            except OSError:
                continue
            raise Hold("INHERITED_FD")
    cgroup = Path("/proc/self/cgroup").read_text().splitlines()
    require(len(cgroup) == 1 and cgroup[0].startswith("0::/"), "CGROUP_UNKNOWN")
    relative = cgroup[0][4:]
    require(".." not in PurePosixPath(relative).parts, "CGROUP_UNKNOWN")
    mount = Path("/sys/fs/cgroup")
    group = mount / relative
    # Root controller limit files need not exist on cgroup v2. Verify
    # the actual unified mount exposes hierarchy root, not a subtree.
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    roots = [line.split() for line in mounts if " - cgroup2 " in line]
    require(len(roots) == 1 and roots[0][3] == "/"
            and roots[0][4] == str(mount), "CGROUP_MOUNT_UNKNOWN")
    require(group.is_dir() and group != mount, "CGROUP_SCOPE_UNKNOWN")
    limits = []
    while group != mount:
        # Read-only visible non-root ancestry, not a demand proof.
        values = {}
        for key in ("memory.max", "memory.current", "memory.swap.max",
                    "cpu.max", "pids.max", "pids.current"):
            raw = (group / key).read_text().strip()
            pattern = (r"(?:max|[0-9]+) [0-9]+" if key == "cpu.max"
                       else r"[0-9]+" if key.endswith(".current")
                       else r"(?:max|[0-9]+)")
            require(re.fullmatch(pattern, raw) is not None, "CGROUP_UNKNOWN")
            values[key] = raw
        limits.append(values)
        require(mount in group.parents and len(limits) < 32, "CGROUP_UNKNOWN")
        group = group.parent
    # Explicitly distinguish root from a measured finite controller limit.
    limits.append({"scope": "visible_hierarchy_root_no_limit_claim"})
    mem = Path("/proc/meminfo").read_text()
    available = re.search(r"^MemAvailable:\s+([0-9]+) kB$", mem, re.M)
    require(available is not None, "MEMORY_UNKNOWN")
    return {"image_os": "ubuntu24", "image_version": os.environ["ImageVersion"],
            "arch": "x64", "disk_free_bytes": shutil.disk_usage(root).free,
            "memory_available_kib": int(available[1]), "cgroup_limits": limits}


def run(root):
    # Bound verifier memory and individual output file size. Neither is an
    # approved model containment profile or a provider demand measurement.
    resource.setrlimit(resource.RLIMIT_AS, (GIB, GIB))
    resource.setrlimit(resource.RLIMIT_FSIZE, (EXTRACT_LIMIT, EXTRACT_LIMIT))
    os.umask(0o077)
    deadline = time.monotonic() + TOTAL_SECONDS
    evidence = preflight(root)
    manifest = root / "manifest.json"
    fetch(REGISTRY + "manifests/2b", "manifest", manifest, deadline, sha=MANIFEST_SHA)
    blobs = parse_manifest(manifest.read_bytes())
    for digest, size in blobs.items():
        fetch(REGISTRY + "blobs/" + digest, "blob", root / digest[7:],
              deadline, size=size, sha=digest[7:], digest=digest)
    runtime = root / "ollama.tar.zst"
    fetch(RELEASE, "archive", runtime, deadline, size=ARCHIVE_SIZE, sha=ARCHIVE_SHA)
    records, links, extracted = extract_archive(runtime, root, deadline)
    inventory = json.dumps({"regular": records, "links": links}, sort_keys=True,
                           separators=(",", ":")).encode("ascii")
    # Derive exact member hashes and aggregate inventory digest; there are
    # no independent per-member reference pins other than archive digest.
    evidence.update({"stage": "STAGED_PUBLIC_ONLY", "manifest_sha256": MANIFEST_SHA,
                     "archive_sha256": ARCHIVE_SHA, "blob_count": len(blobs),
                     "blob_bytes": sum(blobs.values()), "hashed_member_bytes": extracted,
                     "regular_count": len(records), "link_count": len(links),
                     "runtime_inventory_sha256": digest_bytes(inventory),
                     "ollama_binary_sha256": records["bin/ollama"][1],
                     "native_inference": False, "native_qualified": False})
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    try:
        require(len(sys.argv) == 2, "ARGUMENTS")
        run(Path(sys.argv[1]))
    except Hold as exc:
        print("STAGE1_HOLD " + str(exc), flush=True)
        sys.exit(2)
    except Exception:
        # No upstream signed URL, credentials, path or untrusted text.
        print("STAGE1_HOLD UNEXPECTED_REFUSAL", flush=True)
        sys.exit(2)
