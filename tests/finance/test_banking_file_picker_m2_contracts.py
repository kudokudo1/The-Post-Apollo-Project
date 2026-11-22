#!/usr/bin/env python3
"""Banking M2: only a user-picked, bounded, nofollow local CSV read is permitted."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
reader=(root/"scripts/finance/banking_csv_reader.py").read_text()
policy=(root/"widgets/FinanceBankingImportPolicy.js").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

assert "import QtQuick.Dialogs" in banking
assert "import Quickshell.Io" in banking
assert "FileDialog {" in banking
assert "fileMode: FileDialog.OpenFile" in banking
assert 'nameFilters: ["CSV statements (*.csv)"]' in banking
assert "options: FileDialog.ReadOnly" in banking
assert "statementPicker.open()" in banking
assert 'onAccepted: banking.beginFileRead(String(selectedFile),banking.pickerSource)' in banking
assert "Process {" in banking and banking.count("Process {")==1
assert "stdinEnabled: true" in banking
assert 'Quickshell.shellPath("scripts/finance/banking_csv_reader.py")' in banking
assert 'command:["/usr/bin/env","python3"' in banking
assert 'fileFrame=JSON.stringify({version:1,token:fileToken,fileUrl:fileUrl})+"\\n"' in banking
assert 'fileReader.write(banking.fileFrame)' in banking
assert 'onExited: function(exitCode,exitStatus)' in banking
assert 'banking.fileSource===banking.sourceId()' in banking
assert 'banking.fileEditorEpoch===banking.editorEpoch' in banking
assert 'banking.active && banking.selectedTool==="import"' in banking
assert 'payload.token!==banking.fileToken' in banking
assert 'banking.fileOutput.length>550000' in banking
assert 'payload.csv.length>65536' in banking
assert 'BankingPolicy.parseCsv(' in banking
assert 'banking.pending=result;' in banking
assert 'banking.fileFrame="";' in banking
assert 'banking.fileOutput="";' in banking
assert 'banking.fileToken="";' in banking
assert 'if(fileState==="pending")fileState="cancelled";' in banking
assert 'if(banking.fileState==="pending")' in banking
assert 'label: "PREVIEW PASTED CSV"' in banking
assert 'label: "IMPORT VERIFIED ROWS TO SESSION"' in banking
assert 'available: !!banking.pending&&banking.pending.ok' in banking
assert 'ledger=copy;' in banking and "ledger=copy;" not in reader
assert "No provider" not in reader or "CSV" in reader # no backend calls

# The picked file's content and path may only be consumed by the parser and
# controlled subprocess; never become logs, network, shell, or a stored record.
for forbidden in (
    "FileView {", "Process.startDetached", "Qt.openUrlExternally",
    "console.log(", "console.warn(", "console.error(", "WebSocket",
    "XMLHttpRequest", "actual-cli", "financeWrite", "FinanceServices.",
    "setText(", "setData(", "writeAdapter(", "localStorage"
):
    assert forbidden not in banking, forbidden
for forbidden in ("subprocess", "requests", "socket", "urllib.request", "Popen",
                  "os.system", "shell=True", "open(path, 'w'", "write_bytes("):
    assert forbidden not in reader, forbidden

assert "MAX_INPUT_BYTES = 4096" in reader
assert "MAX_FILE_BYTES = 65536" in reader
assert "os.O_NOFOLLOW" in reader
assert "os.O_NONBLOCK" in reader
assert "stat.S_ISREG" in reader
assert "first.st_uid != os.getuid()" in reader
assert "first.st_mtime_ns != last.st_mtime_ns" in reader
assert 'or received != last.st_size' in reader
assert 'errors="strict"' in reader
assert "sys.stdout.write(PREFIX" in reader
assert "sys.stderr.write" not in reader
assert "print(" not in reader
assert "MAX_IMPORT_ROWS=200" in policy
assert 'selectedMainMode === "banking" ? "MANUAL"' in finance
print("Banking M2: pinned file picker and fail-closed source contract PASS")
