#!/usr/bin/env python3
"""Banking M4p private archive contract: no UI activation or external authority."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
archive = (root/"scripts/finance/banking_manual_archive.py").read_text()
manual = (root/"scripts/finance/banking_manual_store.py").read_text()
ui = (root/"widgets/FinanceBankingAccountsPane.qml").read_text()
service = (root/"services/finance/FinanceBankingManualStore.qml").read_text()

for snippet in (
    'import banking_manual_store as manual',
    'PREFIX = "FINANCEW_BANKING_BACKUP_"',
    'MAX_BACKUPS = 8',
    'MAX_ARCHIVE_BYTES = manual.MAX_BYTES + 2048',
    'NAME_PATTERN = re.compile',
    'def validate_archive(archive, identifier):',
    'def archive_names(directory):',
    'def load_archive(directory, identifier):',
    'def store_new_archive(directory, archive):',
    'def with_store_lock(directory, action):',
    'def run(directory, command):',
    'manual.validate_doc(archive["document"])',
    'manual.read_doc(directory)',
    'manual.write_doc(directory, restored)',
    'archive["sha256"]',
    'digest(doc)',
    'expectedBackupSha256',
    'STALE_BACKUP_SELECTION',
    'STALE_REVISION',
    'BACKUP_CHECKSUM_MISMATCH',
    'BACKUP_MUST_BE_SAVED_MANUAL',
    'CONFIRM_RESTORE_REQUIRED',
    'CONFIRM_BACKUP_REQUIRED',
    'CONFIRM_DELETE_REQUIRED',
    'WRITE_BUSY',
    'UNSAFE_BACKUP',
    'os.O_NOFOLLOW',
    'os.O_NONBLOCK',
    'os.O_EXCL',
    'os.fsync(fd)',
    'os.fsync(dfd)',
    'os.link(temporary, final, follow_symlinks=False)',
    'os.unlink(temporary)',
    'fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)',
    '"encrypted": False',
    '"connected": False',
    '"bankVerified": False',
):
    assert snippet in archive, snippet

assert archive.count('manual.write_doc(directory, restored)')==1
assert 'manual.validate_session(' not in archive or \
       'manual.validate_doc(' in archive
assert 'os.replace(' not in archive, "Restore must use the existing secure M4o writer"
assert 'os.system' not in archive
assert 'eval(' not in archive
assert 'subprocess' not in archive
assert 'tempfile.NamedTemporaryFile' not in archive
assert 'def export_to_path(' not in archive
assert 'Path(command[' not in archive, "User-supplied filesystem paths are refused"

for forbidden in (
    'import requests', 'import urllib', 'import socket', 'import sqlite3',
    'HTTP', 'curl', 'bank_login', 'bankToken', 'access_token',
    'client_secret', 'ACTUAL_PASSWORD_FILE', 'ACTUAL_SERVER_URL',
    'paymentExecution', 'onPaymentSent', 'brokerageTrade',
    'financeWrite', 'actual-cli'
):
    assert forbidden not in archive, forbidden

# The directory privacy refusal is implemented in the shared M4o helper,
# which M4p calls rather than cloning filesystem ownership rules.
assert 'UNSAFE_DIRECTORY' in manual
assert 'manual.private_dir(directory, True)' in archive
assert 'manual.private_dir(directory, False)' in archive
assert 'FINANCEW_BANKING_MANUAL_' in manual
assert 'def validate_session(session)' in manual
assert 'def write_doc(directory: Path, doc)' in manual
assert 'manual-session.json' in manual
assert 'version": 1' in manual
assert 'FinanceBankingManualStorageControls {' in ui
assert 'Quickshell.shellPath("scripts/finance/banking_manual_store.py")' in service
assert 'banking_manual_archive.py' not in ui
assert 'banking_manual_archive.py' not in service
print("Banking M4p: no arbitrary export path, local-only private archive, CAS guarded explicit restore and no UI activation contract PASS")
