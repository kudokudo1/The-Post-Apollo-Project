#!/usr/bin/env python3
"""FP1k source and Quickshell boundary contracts (no bank permission)."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
py = (root / "scripts/finance/household_reserve_preference_store.py").read_text()
qml = (root / "services/finance/FinanceHouseholdReservePreferenceStore.qml").read_text()
ui = (root / "widgets/FinanceHouseholdTimelinePane.qml").read_text()
policy = (root / "widgets/FinanceHouseholdReservePolicy.js").read_text()
plan = (root / "scripts/finance/household_plan_store.py").read_text()
schedule = (root / "scripts/finance/household_schedule_store.py").read_text()

for token in ('CONTEXTS = frozenset(("mine", "shared", "mom", "granny", "family"))',
              'PERCENTAGES = frozenset((100, 110, 125))',
              'household-reserve-preferences',
              'def read_doc(directory, context):',
              'def write_doc(directory, doc):',
              'def apply(doc, command):',
              'def run(directory, command):',
              'def valid_context(value):',
              'STALE_REVISION',
              'UNSAFE_DIRECTORY',
              'UNSAFE_RECORD',
              'UNSAFE_LOCK',
              'WRITE_BUSY',
              'os.O_NOFOLLOW',
              'os.O_NONBLOCK',
              'fcntl.flock',
              'os.replace',
              'os.fsync',
              'mode=0o700',
              '0o600',
              '"reset"',
              '"save"',
              '"list"',
              '"identityVerified": False',
              '"bankVerified": False'):
    assert token in py, token

assert 'return empty(context)' in py
assert '"marginPercent": 100' in py
assert 'not 0 <= doc["revision"] < MAX_REVISION' in py
assert 'type(percent) is not int' in py
assert 'doc["version"] != 1' in py
assert 'if action == "list" and exact(command, ("action", "contextId")):' in py

for token in (
    'contextId: timeline.contextId',
    'monitoring: timeline.active',
    'onPreferenceLoaded: timeline.reserveMarginPercent=reservePreferenceStore.marginPercent',
    'onPreferenceSaved: timeline.reserveMarginPercent=reservePreferenceStore.marginPercent',
    'onPreferenceReset: timeline.reserveMarginPercent=reservePreferenceStore.marginPercent',
    'reservePreferenceStore.state==="ready"',
    'reservePreferenceStore.save(timeline.reserveMarginPercent)',
    'reservePreferenceStore.reset()',
    'reservePreferenceStore.refresh()',
    'SAVE FOR ',
    'CONFIRM RESET 100%',
    'PREVIEW NOT SAVED UNTIL SAVE',
    'SAVED LOCAL PREFERENCE',
    'SAME LINUX LOGIN; NOT A HOUSEHOLD IDENTITY GRANT',
    'onContextIdChanged: {',
    'reserveMarginPercent=100;',
    'armedPreferenceReset=false;',
    'Reserves.annotate(sourceRows,scheduleRows,projection,reserveMarginPercent)'
):
    assert token in ui, token

for token in (
    'FINANCEW_RESERVE_PREF_RESULT ',
    'LOCAL_OPERATOR_RESERVE_PREFS',
    'doc.bankVerified===false',
    'doc.identityVerified===false',
    'doc.contextId===store.contextId',
    'store.submittedContext===store.contextId',
    'doc.version===1',
    'doc.marginPercent',
    'Number.isSafeInteger(doc.revision)',
    'state="failed"',
    'pendingReload=true',
    'onContextIdChanged:',
    'onMonitoringChanged:',
    'function save(percent)',
    'function reset()',
    'function refresh()',
    'Quickshell.shellPath("scripts/finance/household_reserve_preference_store.py")',
    'ACTUAL_PASSWORD_FILE:null'):
    assert token in qml, token

for s in (py, qml, ui):
    for forbidden in ('FinanceTransactionWriteService',
                      'FinanceFundingWriteService',
                      'ConnectionsBroker',
                      'SocialIdentityStore',
                      'FinanceStockHistoryReadService'):
        assert forbidden not in s, forbidden
for forbidden in ('sqlite3','requests','urllib.request','subprocess',
                  'ACTUAL_PASSWORD','ACTUAL_SYNC_ID','SOCIAL_','@actual-app',
                  'FinanceHouseholdPlanStore','FinanceHouseholdScheduleStore'):
    assert forbidden not in py, forbidden
assert 'function annotate(rows,schedules,projection,marginPercent)' in policy
assert 'doc["version"] not in (1, 2, 3, 4)' in schedule
assert 'doc["version"] not in (1, 2)' in plan
print("FinanceW FP1k private preference UI/storage separation: PASS")
