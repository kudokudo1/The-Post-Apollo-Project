#!/usr/bin/env python3
"""FP1k.N1 source contracts for truthful persisted-preference presentation."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
store=(root/"scripts/finance/household_reserve_preference_store.py").read_text()
bridge=(root/"services/finance/FinanceHouseholdReservePreferenceStore.qml").read_text()
ui=(root/"widgets/FinanceHouseholdTimelinePane.qml").read_text()
previous=(root/"tests/finance/test_household_reserve_preferences_fp1k.py").read_text()

for token in (
    'if saved["revision"] == 0:',
    'fail("INVALID_STORE")',
    '"savedOnDisk": doc["revision"] > 0,',
    'def validate(doc, context):',
    'return empty(context)',
    'os.O_NOFOLLOW',
    'fcntl.flock',
    'os.fsync',
    'os.replace',
):
    assert token in store, token
for token in (
    'property bool savedOnDisk: false',
    'savedOnDisk=false;',
    'typeof doc.savedOnDisk==="boolean"',
    'doc.savedOnDisk===(doc.revision>0)',
    'store.savedOnDisk=doc.savedOnDisk;',
    'store.submittedContext===store.contextId',
    'store.preferenceUnavailable();',
):
    assert token in bridge, token
for token in (
    '!reservePreferenceStore.savedOnDisk',
    'DEFAULT 100% // NO SAVED FILE',
    'PREVIEW NOT SAVED UNTIL SAVE',
    'SAVED LOCAL PREFERENCE FOR ',
    'available: timeline.preferenceReady && timeline.preferenceDirty',
    'reservePreferenceStore.save(timeline.reserveMarginPercent)',
    'onPreferenceUnavailable:',
    'reserveMarginPercent=100;',
):
    assert token in ui, token
# Preserve all prior hostile input tests and re-check the absence of bank IO.
assert "test_symlink_record_and_lock_refused" in previous
for source in (store,bridge,ui):
    for forbidden in ("FinanceTransactionWriteService","FinanceFundingWriteService",
                      "ConnectionsBroker","SocialIdentityStore"):
        assert forbidden not in source, forbidden
for forbidden in ("sqlite3","requests","urllib.request","subprocess",
                  "ACTUAL_PASSWORD","ACTUAL_SYNC_ID","SOCIAL_","@actual-app"):
    assert forbidden not in store, forbidden
print("FinanceW FP1k.N1 saved provenance and source isolation: PASS")
