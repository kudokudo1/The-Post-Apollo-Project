"""M4s3 source-only cooperative lifetime lease for manual Banking recovery.

No CLI, no live mount, no service discovery or authority claim. Every future
client MUST acquire the shared lease before reading and hold it until its
in-memory session and all children are discarded. Existing M4o clients and
direct legacy helper calls are NOT participants; never activate on that basis.
"""
from contextlib import contextmanager
import fcntl
import os
import stat

import banking_manual_store as manual
import banking_manual_archive as archive
import banking_manual_recovery as recovery
import banking_manual_portable as portable

LOCK_NAME = "manual-client-lifetime.lock"
MAX_REVISION = 2147483646

def fail(code):
    raise manual.Refusal(code)

@contextmanager
def _lease(directory, exclusive):
    # Distinct from the short-duration writer lock. Always acquire lifetime
    # lease first; existing helpers acquire the writer lock inside it.
    if not manual.private_dir(directory, not exclusive):
        fail("RECOVERY_DIRECTORY_NOT_READY")
    path = directory / LOCK_NAME
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW |
                     os.O_NONBLOCK | os.O_CLOEXEC, 0o600)
    except OSError:
        fail("UNSAFE_CLIENT_LEASE")
    try:
        def checked():
            info = os.fstat(fd)
            named = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o077 or info.st_nlink != 1
                    or (info.st_dev, info.st_ino) != (named.st_dev, named.st_ino)):
                fail("UNSAFE_CLIENT_LEASE")
        try:
            checked()
            fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                        | fcntl.LOCK_NB)
            checked()
        except BlockingIOError:
            fail("CLIENT_LEASE_BUSY")
        except OSError:
            fail("UNSAFE_CLIENT_LEASE")
        yield
    finally:
        # Never unlink the lock: a new inode would split the exclusion domain.
        os.close(fd)

@contextmanager
def client_lifetime(directory):
    """Future client integration contract, not a live client implementation."""
    with _lease(directory, False):
        yield

def guarded_recovery(directory, command, *, confirm_clients_closed=False):
    """Internal candidate only; explicit operator attestation still required.

    The exclusive lease establishes absence of cooperating lease holders, NOT
    absence of legacy clients, other processes, or hostile same-UID writers.
    The existing backend rechecks selection and revision under its writer lock.
    """
    if confirm_clients_closed is not True:
        fail("EXPLICIT_CLOSED_CLIENTS_REQUIRED")
    if type(command) is not dict:
        fail("INVALID_RECOVERY_HANDOFF")
    action = command.get("action")
    if action == "restore":
        if not manual.exact(command, ("action", "backupId", "expectedRevision",
                                      "expectedBackupSha256", "confirmRestore")):
            fail("INVALID_RECOVERY_HANDOFF")
        revision = command["expectedRevision"]
        if type(revision) is not int or not 0 <= revision < MAX_REVISION:
            fail("INVALID_REVISION")
        executor = archive.run
    elif action == "recover":
        if not manual.exact(command, ("action", "backupId", "expectedPrimarySha256",
                                      "expectedBackupSha256", "lastKnownRevision",
                                      "confirmRecovery", "confirmClientsClosed")):
            fail("INVALID_RECOVERY_HANDOFF")
        executor = recovery.run
    elif action == "import":
        if not manual.exact(command, ("action", "portableId", "password",
                                      "expectedSha256", "expectedRevision",
                                      "confirmImport", "confirmClientsClosed")):
            fail("INVALID_RECOVERY_HANDOFF")
        executor = portable.run
    else:
        fail("INVALID_RECOVERY_HANDOFF")
    # Do not synthesize any missing confirmation or automatically retry.
    with _lease(directory, True):
        return executor(directory, command)
