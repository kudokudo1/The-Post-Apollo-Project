"""B5e: disposable installed host launcher, not production authority.

No caller-provided executable, arguments, UID, environment, storage path,
or FD. The launcher creates its own socketpair, passes only the child
endpoint, and reaps exactly that child. This is a CI-only same-UID
experiment; it cannot attest an enrolled host or private recipient.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import socket
import subprocess
import sys

HOST = "/usr/libexec/post-apollo/forest-ci/forest-host"
PYTHON = "/usr/bin/python3"
_CHILD_ENV = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LC_ALL": "C"}


def _require_disposable_context():
    if (not sys.platform.startswith("linux")
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or not Path("/.dockerenv").is_file()
            or os.getuid() == 0 or os.geteuid() != os.getuid()):
        raise RuntimeError("DISPOSABLE_NONROOT_CI_REQUIRED")


@contextmanager
def launch_disposable_host():
    """One on-demand child, no automatic retry or private operation.

    Yield the disposable requester endpoint and process for native tests.
    The caller receives no private storage capability or verified grant.
    """
    _require_disposable_context()
    requester, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    with requester, child:
        requester.settimeout(5)
        fd = child.fileno()
        inode = os.fstat(fd).st_ino
        proc = subprocess.Popen(
            [PYTHON, "-I", "-B", HOST, "--disposable-test-fd", str(fd)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True, pass_fds=(fd,),
            cwd="/", env=dict(_CHILD_ENV), restore_signals=True,
            umask=0o077,
        )
        try:
            child.close()
            yield requester, proc, fd, inode
        finally:
            requester.close()
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=4)
