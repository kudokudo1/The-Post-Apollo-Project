#!/usr/bin/env python3
"""Shared Post-Apollo date component: one Tasks-backed date editor and Banking adoption."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
stepper=(root/"widgets/PostApolloDateStepper.qml").read_text()
segment=(root/"widgets/tasks/TaskDateSegment.qml").read_text()
segments=(root/"widgets/tasks/TaskDateSegments.js").read_text()
bank=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
finance=(root/"widgets/FinanceDateInput.qml").read_text()
weather=(root/"widgets/weather/StationMagickUtcDateField.qml").read_text()
github=(root/"widgets/GitHubProjectsDateInput.qml").read_text()

# Shared wrapper does not copy Tasks' arrow QML or independent date math.
assert 'import "tasks" as TaskFields' in stepper
assert 'import "tasks/TaskDateSegments.js" as Segments' in stepper
assert stepper.count("TaskFields.TaskDateSegment {")==3
assert 'Keys.onUpPressed:' in segment and 'Keys.onDownPressed:' in segment
assert 'stepRequested(segment.part, modelData)' in segment
assert 'function step(date, kind, direction, referenceDate)' in segments
assert 'function setPart(date, kind, raw, referenceDate)' in segments
assert 'function daysInMonth(year, month)' in segments
assert 'new Date(0)' in segments
assert 'Segments.setPart(base,part,value)' in stepper
assert 'Segments.step(base,part,direction)' in stepper
assert 'if(dateWithinBounds(dateValue))return dateValue;' in stepper
assert 'if(dateWithinBounds(fallbackDate))return fallbackDate;' in stepper
assert 'return dateWithinBounds(minDate) ? minDate : "";' in stepper
assert 'useUtcToday ? now.getUTCFullYear() : now.getFullYear()' in stepper
assert 'dateEdited(candidate)' in stepper
assert 'dateEdited("")' in stepper
assert 'onLeftClicked: picker.setToday()' in stepper
assert 'onLeftClicked: picker.clearDate()' in stepper
assert "Component.onCompleted" not in stepper
assert "Timer {" not in stepper
assert "↑" not in stepper and "↓" not in stepper

# Banking uses TWO copies of the same component, with local civil date and
# the same allowed 1900..2100 range as its existing journal policy.
assert bank.count("PostApolloDateStepper {")==2
assert 'id: fromDateStepper' in bank and 'id: toDateStepper' in bank
assert 'dateValue: providerPane.activityFromDate' in bank
assert 'dateValue: providerPane.activityToDate' in bank
assert bank.count('minDate: "1900-01-01"')==2
assert bank.count('maxDate: "2100-12-31"')==2
assert bank.count('useUtcToday: false')==2
assert bank.count('showToday: true')==2
assert bank.count('allowClear: true')==2
assert 'property string activityFromDate: ""' in bank
assert 'property string activityToDate: ""' in bank
assert 'fromDate:activityFromDate,toDate:activityToDate' in bank
assert 'onActivityFromDateChanged: {' in bank
assert 'onActivityToDateChanged: {' in bank
assert 'activityPageIndex=0;' in bank
assert 'clearSelectedEntry();' in bank
assert 'providerPane.activityFromDate=isoDate;' in bank
assert 'providerPane.activityToDate=isoDate;' in bank
assert 'providerPane.activityFromDate="";' in bank
assert 'providerPane.activityToDate="";' in bank
assert 'CLEAR ACTIVITY DATE RANGE' in bank
assert 'SESSION DATE RANGE // INCLUSIVE' in bank
assert 'fromDate=opts.fromDate===undefined?"":opts.fromDate' in journal
assert 'toDate=opts.toDate===undefined?"":opts.toDate' in journal
assert 'INVALID DATE RANGE // USE YYYY-MM-DD AND FROM <= TO' in journal
assert 'signal manualCorrectionRequested(var draft)' in bank
assert 'signal manualDeletionRequested(var draft)' in bank
assert 'Accounts.correctEntry(session,draft)' in manager
assert 'Accounts.deleteEntry(session,draft)' in manager

# Previous users continue using their current wrappers without any edits.
assert 'TaskFields.TaskDateSegment {' in finance
assert 'TasksFields.TaskDateSegment {' in weather
assert 'component DatePart: Item {' in github

# Shared visual control must not acquire domain write/network/clock authority.
for text in (stepper,bank):
    for forbidden in (
        "Process {","FileView {","FileDialog {","XMLHttpRequest",
        "fetch(","WebSocket","localStorage","FinanceServices.",
        "financeWrite","actual-cli","ACTUAL_PASSWORD","ACTUAL_SYNC",
        "access_token","client_secret","onPaymentSent","openDatabase",
        "writeFile(","paymentExecution","onTraderOrder","Quickshell.Io",
        "Qt.openUrlExternally"
    ):
        assert forbidden not in text,forbidden
print("Shared date stepper: canonical Tasks arrows/logic, two Banking bounds, no domain writers or duplicate control PASS")
