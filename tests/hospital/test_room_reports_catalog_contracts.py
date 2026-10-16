#!/usr/bin/env python3
"""Hospital-wide Reports must combine two different read-only sources.

Test the generated PX shell with a fake PX executable, not just source text.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
service = (ROOT / "services/hospital/HospitalRoomReportCatalogService.qml").read_text()
view = (ROOT / "widgets/HospitalReportsView.qml").read_text()
host = (ROOT / "widgets/HospitalW.qml").read_text()
for needle in (
    'catalogService: roomReportCatalogService',
    "HospitalRoomReportCatalogService {",
    "roomReportCatalogService.refresh();",
    "reportsView.teamFilter = requestedTeam;",
):
    assert needle in host, needle
for needle in ("readonly property var catalogEvents:", "readonly property var combinedEvents:",
               'eventType: "ROOM REPORT // " + kind', "root.historyService.events",
               "root.catalogService.reports", "NO REPORTS MATCH THE SELECTED FILTER"):
    assert needle in view, needle
assert 'NotificationsService.pushRich({' in host, "existing notifications must remain wired"

start = service.index("        const script = [")
end = service.index("        catalogProcess.exec([", start)
js_body = service[start:end] + "\nreturn script;\n"
node = ("const fn = new Function(" + json.dumps(js_body)
        + ");process.stdout.write(fn());")
cmd = subprocess.run(["node", "-e", node], capture_output=True, text=True, check=True).stdout
assert '\nwhile IFS= read -r room; do\n' in cmd
subprocess.run(["bash", "-n", "-c", cmd], capture_output=True, text=True, check=True)

with tempfile.TemporaryDirectory(prefix="hospital-reports-test-") as tmp:
    home = Path(tmp)
    px = home / ".local/share/post-apollo-dev-runtime/bin/px"
    px.parent.mkdir(parents=True)
    px.write_text(
        "#!/bin/bash\n"
        "if [[ \"$1\" == hospital && \"$2\" == rooms ]]; then\n"
        "  printf '%s\\n' '[{\"id\":\"room-1\",\"team\":\"T1\"},{\"id\":\"room-2\",\"team\":\"T2\"}]'\n"
        "elif [[ \"$1\" == hospital && \"$2\" == room-reports ]]; then\n"
        "  if [[ \"$3\" == room-1 ]]; then\n"
        "    printf '%s\\n' '[{\"id\":\"11\",\"roomId\":\"room-1\",\"kind\":\"DOCTOR_NOTE\",\"title\":\"T1 milestone\",\"body\":\"test evidence\",\"repository\":\"kudokudo1/example\",\"createdAt\":\"2026-10-16T08:00:00Z\"}]'\n"
        "  else printf '%s\\n' '[]'; fi\n"
        "else echo 'unexpected PX call' >&2; exit 31; fi\n"
    )
    px.chmod(0o755)
    env = dict(os.environ, HOME=str(home))
    result = subprocess.run(
        ["bash", "-lc", cmd, "hospital-report-catalog", "10", "10"],
        env=env, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, (result.stderr, result.stdout)
    data = json.loads(result.stdout)
    assert data["totalRooms"] == 2, data
    assert data["scannedRooms"] == 2, data
    assert data["failedRooms"] == 0, data
    assert len(data["reports"]) == 1, data
    assert data["reports"][0]["team"] == "T1", data
    assert data["reports"][0]["body"] == "test evidence", data

print("HOSPITAL REPORTS // PX CATALOG FAKE-ONLY CONTRACT PASS")
