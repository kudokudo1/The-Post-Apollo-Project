#!/usr/bin/env python3
"""Isolated cooperative reader-custody candidate. No deletion or UI activation.

Linux flock on the generation directory inode, held for the lifetime of an
explicit reader. Future cooperating reclamation must acquire the repository
build lock AND an exclusive generation lock, revalidate the named inode, and
refuse legacy/unregistered readers. This module alone does not prove that
all current readers participate. No persistent lease files are created.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import git_map_index_manager as manager
import git_map_history_index as index

SCHEMA = "post-apollo-git-map-reader-candidate-v1"


def same_directory(path, fd):
    named, opened = path.lstat(), os.fstat(fd)
    return (stat.S_ISDIR(named.st_mode) and stat.S_ISDIR(opened.st_mode)
            and named.st_uid == opened.st_uid == os.getuid()
            and not (named.st_mode | opened.st_mode) & 0o077
            and (named.st_dev, named.st_ino) == (opened.st_dev, opened.st_ino))


class Reader:
    def __init__(self, root, repo_id, key, snapshot):
        self.fd = None
        if (not isinstance(repo_id, str) or not manager.HEX.fullmatch(repo_id)
                or not isinstance(key, str) or not manager.HEX.fullmatch(key)
                or not isinstance(snapshot, str) or not index.SNAPSHOT.fullmatch(snapshot)):
            raise ValueError("invalid reader identity")
        root = Path(root)
        if not root.is_absolute():
            raise ValueError("absolute cache root required")
        manager.private_dir(root)
        folder = manager.private_dir(root / repo_id)
        self.path = folder / key
        manager.private_dir(self.path)
        fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            if not same_directory(self.path, fd):
                raise ValueError("generation replaced before reader acquisition")
            conn = index.open_index(self.path)
            try:
                m = index.manifest_for(conn, snapshot)
            finally:
                conn.close()
            digest = m.get("rootsDigest")
            if (m.get("repoId") != repo_id or not isinstance(digest, str)
                    or not manager.HEX.fullmatch(digest)
                    or type(m.get("shallow")) is not bool
                    or type(m.get("maxLane")) is not int
                    or not 0 <= m["maxLane"] < index.MAX_LANES):
                raise ValueError("generation manifest mismatch")
            if not m["shallow"]:
                expected = hashlib.sha256((digest+":False:").encode("ascii")).hexdigest()
                if expected != key:
                    raise ValueError("generation key mismatch")
            else:
                # v1 cannot reconstruct the historical shallow boundary key.
                raise ValueError("shallow reader candidate not qualified")
            if not same_directory(self.path, fd):
                raise ValueError("generation replaced during acquisition")
            info = os.fstat(fd)
            self.receipt = {"schema":SCHEMA,"status":"HELD","repoId":repo_id,
                            "key":key,"snapshot":snapshot,"device":str(info.st_dev),
                            "inode":str(info.st_ino),"reclamationAllowed":False}
            self.fd = fd
        except BaseException:
            os.close(fd)
            raise

    def close(self):
        if self.fd is not None:
            # Do not explicitly unlock a possibly shared open-file description.
            # The final descriptor close releases its kernel lock.
            fd, self.fd = self.fd, None
            os.close(fd)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_id")
    parser.add_argument("key")
    parser.add_argument("snapshot")
    args = parser.parse_args(argv)
    try:
        # An explicit pipe is the test owner's lifetime channel. EOF releases
        # custody; a byte is not a valid command. No heartbeat or polling.
        # Native QML process-pipe custody is deliberately not assumed.
        if not stat.S_ISFIFO(os.fstat(sys.stdin.fileno()).st_mode):
            raise ValueError("reader lifetime pipe required")
        with Reader(manager.cache_root(),args.repo_id,args.key,args.snapshot) as reader:
            print(json.dumps(reader.receipt,separators=(",",":")),flush=True)
            if sys.stdin.buffer.read(1):
                raise ValueError("unexpected lifetime channel data")
        return 0
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error,subprocess.SubprocessError):
        print("Reader custody unavailable or terminated.",file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
