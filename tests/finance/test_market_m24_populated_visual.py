#!/usr/bin/env python3
"""M24: disposable SQLite-backed rendering of the actual Market quota pane.

--ci: Qt offscreen test: M20 reserve -> temp DB -> M21 read -> real QML.
--visual: an isolated native Qt window with conspicuous TEST/NOT LIVE banners.

No provider requests, normal Quickshell process, canonical M20 file, real
quota reservation, credential, live configuration or host package install.
Only a temporary 0700 directory and its disposable fixture DBs are written.
"""
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

# Do not populate Python compiled-code caches in the operator checkout.
sys.dont_write_bytecode = True
os.environ["QML_DISABLE_DISK_CACHE"] = "1"
if "--ci" in sys.argv:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_QUICK_BACKEND"] = "software"

ROOT = Path(__file__).resolve().parents[2]
MARKET = ROOT / "scripts" / "finance"
sys.path.insert(0, str(MARKET))

from market_shared_quota import reserve, LIMITS, DB_NAME  # noqa: E402
from market_quota_status import quota_status  # noqa: E402

try:
    from PySide6.QtCore import QObject, QMetaObject, Q_ARG, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine
except ImportError as exc:
    raise SystemExit(
        "M24 requires existing PySide6 (Qt6). No package installed. "
        "Run via the dedicated GitHub CI job or use a host with PySide6."
    ) from exc

DAY = dt.datetime.now(dt.timezone.utc).date().isoformat()
OTHER_DAY = (dt.date.fromisoformat(DAY) - dt.timedelta(days=1)).isoformat()
KNOWN_CASES = ("LOW", "FULL", "ZERO", "ABSENT", "UNAVAILABLE")
PATH = Path(__file__).resolve().with_name(
    "finance_market_m24_populated_visual_harness.qml"
)


def snapshot(db, day=DAY):
    """Exercise M21's *test-only database override*, never canonical path."""
    result = quota_status(database=db, utc_day=day)
    assert result["noProviderCalls"] is True
    assert result["notAccountBalance"] is True
    assert result["readOnly"] is True
    assert result["utcDay"] == day
    return result


def safe_digest(path):
    """Observe disposable file bytes only; never touch canonical user DB."""
    return (
        hashlib.sha256(path.read_bytes()).hexdigest(),
        path.stat().st_mtime_ns,
        path.stat().st_size,
    )


def build_fixture(temp):
    """Use real M20 quotas in temp files and read with the real M21 parser."""
    temp = Path(temp).resolve(strict=True)
    assert temp != Path.home() and temp.is_dir()
    db = temp / DB_NAME
    zero = temp / "zero-previous-day.sqlite3"
    corrupt = temp / "corrupt-test.sqlite3"
    absent = temp / "absent-test.sqlite3"
    assert all(p.parent == temp for p in (db, zero, corrupt, absent))
    assert not any(p.exists() for p in (db, zero, corrupt, absent))

    # Canonical writer first. No network operations: reserve() solely updates
    # an explicit disposable test database and never calls price providers.
    db.touch(mode=0o600)
    for _ in range(3):
        reserve("eodhd", utc_day=DAY, database=db)
    for _ in range(9):
        reserve("alpha-vantage", utc_day=DAY, database=db)
    before = safe_digest(db)
    low = snapshot(db)
    assert safe_digest(db) == before, "M21 changed temporary low DB"
    assert low["ledgerState"] == "ready"
    assert [x["reserved"] for x in low["providers"]] == [3, 9]

    for _ in range(LIMITS["eodhd"] - 3):
        reserve("eodhd", utc_day=DAY, database=db)
    for _ in range(LIMITS["alpha-vantage"] - 9):
        reserve("alpha-vantage", utc_day=DAY, database=db)
    before = safe_digest(db)
    full = snapshot(db)
    assert safe_digest(db) == before, "M21 changed temporary full DB"
    assert [x["reserved"] for x in full["providers"]] == [20, 25]

    zero.touch(mode=0o600)
    reserve("eodhd", utc_day=OTHER_DAY, database=zero)
    before = safe_digest(zero)
    empty_today = snapshot(zero)
    assert safe_digest(zero) == before, "M21 changed temporary zero DB"
    assert empty_today["ledgerState"] == "ready"
    assert [x["reserved"] for x in empty_today["providers"]] == [0, 0]

    missing = snapshot(absent)
    assert missing["ledgerState"] == "absent"
    assert all(x["reserved"] is None for x in missing["providers"])
    assert not absent.exists(), "M21 created missing test ledger"

    corrupt.write_bytes(b"disposable M24 invalid SQLite")
    bad_before = safe_digest(corrupt)
    broken = snapshot(corrupt)
    assert safe_digest(corrupt) == bad_before, "M21 modified corrupt DB"
    assert broken["ledgerState"] == "unavailable"
    assert all(x["reserved"] is None for x in broken["providers"])

    expected = {
        "LOW": low,
        "FULL": full,
        "ZERO": empty_today,
        "ABSENT": missing,
        "UNAVAILABLE": broken,
    }
    assert set(expected) == set(KNOWN_CASES)
    assert {key: x["ledgerState"] for key, x in expected.items()} == {
        "LOW": "ready", "FULL": "ready", "ZERO": "ready",
        "ABSENT": "absent", "UNAVAILABLE": "unavailable",
    }
    return expected, {p: safe_digest(p) for p in (db, zero, corrupt)}


def make_fake_quickshell(temp):
    """This QML module NEVER executes a process. Only temp test imports."""
    stub = Path(temp) / "Quickshell"
    io = stub / "Io"
    io.mkdir(parents=True, exist_ok=False)
    (stub / "qmldir").write_text(
        "module Quickshell\n"
        "singleton Quickshell 1.0 Quickshell.qml\n"
        "Scope 1.0 Scope.qml\n", encoding="utf-8"
    )
    (stub / "Quickshell.qml").write_text(r'''
pragma Singleton
import QtQuick
QtObject {
    property int callCount: 0
    property string lastCommand: ""
    property string nextPayload: ""
    function shellPath(path) { return "/M24-FAKE-NO-EXEC/" + path; }
}
''', encoding="utf-8")
    (stub / "Scope.qml").write_text(r'''
import QtQuick
QtObject {
    default property list<QtObject> data
}
''', encoding="utf-8")
    (io / "qmldir").write_text(
        "module Quickshell.Io\n"
        "Process 1.0 Process.qml\n"
        "StdioCollector 1.0 StdioCollector.qml\n", encoding="utf-8"
    )
    (io / "StdioCollector.qml").write_text(r'''
import QtQuick
QtObject {
    property string text: ""
    signal streamFinished()
}
''', encoding="utf-8")
    (io / "Process.qml").write_text(r'''
import QtQuick
import Quickshell
QtObject {
    id: fakeProcess
    property bool running: false
    property QtObject stdout: null
    signal exited(int exitCode, int exitStatus)
    function exec(argv) {
        if (!Array.isArray(argv) || argv.length !== 4
            || argv[0] !== "/usr/bin/env"
            || argv[1] !== "python3"
            || argv[2] !== Quickshell.shellPath(
                "scripts/finance/market_quota_status.py")
            || argv[3] !== "status")
            throw new Error("M24 refuses any other command");
        Quickshell.callCount += 1;
        Quickshell.lastCommand = JSON.stringify(argv);
        running = true;
        Qt.callLater(function() {
            if (!stdout) throw new Error("M24 missing fake stream");
            stdout.text = Quickshell.nextPayload;
            stdout.streamFinished();
            running = false;
            exited(0, 0);
        });
    }
}
''', encoding="utf-8")


def payload(value):
    return "FINANCE_QUOTA_STATUS " + json.dumps(
        value, separators=(",", ":")
    ) + "\n"


def mount(app, temp, snapshots):
    """Mount real pane and service; inject ONLY the inert M24 Process shim."""
    make_fake_quickshell(temp)
    engine = QQmlEngine()
    engine.addImportPath(str(temp))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(PATH)))
    if component.isError():
        raise RuntimeError("M24 QML load: " +
                           "; ".join(str(x) for x in component.errors()))
    root = component.create()
    if root is None:
        raise RuntimeError("M24 QML create: " +
                           "; ".join(str(x) for x in component.errors()))
    for case, fixture in snapshots.items():
        assert root.setProperty(case.lower() + "Payload", payload(fixture)), case
    pane = root.findChild(QObject, "marketQuotaRealPane")
    service = root.findChild(QObject, "marketQuotaReaderService")
    refresh = root.findChild(QObject, "marketQuotaRefreshButton")
    back = root.findChild(QObject, "marketQuotaBackButton")
    assert all((pane, service, refresh, back)), (
        "Real M21 QML pane/service/buttons were not mounted"
    )
    return engine, root, pane, service, refresh, back


def pump(app):
    for _ in range(15):
        app.processEvents()


def prop(app, obj, name):
    pump(app)
    return obj.property(name)


def setprop(app, obj, name, value):
    assert obj.setProperty(name, value), f"Unable to set {name}"
    pump(app)


def invoke(app, obj, method):
    assert QMetaObject.invokeMethod(obj, method), (
        f"Qt method failed: {method}"
    )
    pump(app)


def click(app, obj):
    assert QMetaObject.invokeMethod(
        obj, "leftClicked", Q_ARG("QVariant", None)
    ), "Real ActionButton signal refused"
    pump(app)


def descendants(item):
    found = []
    for child in item.childItems():
        found.append(child)
        found.extend(descendants(child))
    return found


def label_texts(pane):
    return [
        str(x.property("text")) for x in descendants(pane)
        if x.objectName() == "marketQuotaReservedLabel"
    ]


def ci_verify(app, root, pane, service, refresh, back, expected):
    assert prop(app, service, "state") == "idle"
    assert prop(app, root, "requestCount") == 0
    for case, result in expected.items():
        old = int(prop(app, root, "requestCount"))
        setprop(app, root, "selectedCase", case)
        invoke(app, root, "openCase")
        assert prop(app, root, "paneOpened") is True
        assert prop(app, root, "requestCount") == old + 1
        assert prop(app, service, "state") == result["ledgerState"]
        assert "M24-FAKE-NO-EXEC" in str(prop(app, root, "lastCommand"))
        actual = label_texts(pane)
        if case == "LOW":
            assert sorted(actual) == sorted([
                "LOCAL RESERVED 3 / 20", "LOCAL RESERVED 9 / 25"
            ]), actual
        elif case == "FULL":
            assert sorted(actual) == sorted([
                "LOCAL RESERVED 20 / 20", "LOCAL RESERVED 25 / 25"
            ]), actual
        elif case == "ZERO":
            assert sorted(actual) == sorted([
                "LOCAL RESERVED 0 / 20", "LOCAL RESERVED 0 / 25"
            ]), actual
        else:
            assert actual.count("LOCAL RESERVED UNKNOWN") == 2, actual

        # Real refresh button must re-read only the in-memory fake payload.
        old = int(prop(app, root, "requestCount"))
        click(app, refresh)
        assert prop(app, root, "requestCount") == old + 1
        assert label_texts(pane) == actual, (case, label_texts(pane))

        # Narrow/large native Qt window must not create extra status reads.
        old = int(prop(app, root, "requestCount"))
        setprop(app, root, "width", 365)
        setprop(app, root, "height", 630)
        assert len(label_texts(pane)) == 2
        assert prop(app, root, "requestCount") == old
        setprop(app, root, "width", 750)
        assert prop(app, root, "requestCount") == old

    old_back = int(prop(app, root, "backCount"))
    click(app, back)
    assert prop(app, root, "backCount") == old_back + 1
    assert prop(app, root, "paneOpened") is False
    assert prop(app, service, "state") == "idle"
    old = int(prop(app, root, "requestCount"))
    setprop(app, root, "selectedCase", "LOW")
    invoke(app, root, "openCase")
    assert prop(app, root, "paneOpened") is True
    assert prop(app, root, "requestCount") == old + 1
    assert "LOCAL RESERVED 3 / 20" in label_texts(pane)
    print("Finance M24 disposable SQLite M20->M21 populated-real-QML "
          "LOW/FULL/ZERO/UNKNOWN + Qt resize/refresh/back: PASS", flush=True)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--ci", "--visual"):
        print("USAGE: python3 -B tests/finance/"
              "test_market_m24_populated_visual.py [--ci|--visual]")
        return 2
    with tempfile.TemporaryDirectory(prefix="finance-market-M24-") as temp:
        snapshots, initial = build_fixture(temp)
        if not PATH.is_file():
            raise RuntimeError("M24 QML harness missing")
        app = QGuiApplication([])
        engine, root, pane, service, refresh, back = mount(
            app, temp, snapshots
        )
        try:
            if sys.argv[1] == "--ci":
                ci_verify(app, root, pane, service, refresh, back, snapshots)
            else:
                setprop(app, root, "selectedCase", "LOW")
                invoke(app, root, "openCase")
                print("M24 TEST WINDOW OPEN // DISPOSABLE SQLITE ONLY")
                print("LOW 3/20+9/25, FULL 20/20+25/25, ZERO 0/0, "
                      "ABSENT/UNAVAILABLE UNKNOWN.")
                print("Use actual pane REFRESH LOCAL STATUS / BACK TO STOCKS.")
                print("M24 uses a fake Quickshell Process; "
                      "it NEVER calls real market APIs or the local live DB.")
                print("Closing this test window deletes disposable fixtures.")
                app.exec()
            for file, digest in initial.items():
                if safe_digest(file) != digest:
                    raise RuntimeError(
                        "M24 temporary fixture modified during Qt display"
                    )
            print("M24 disposable database files unchanged during UI; "
                  "real production ledger not inspected", flush=True)
            return 0
        finally:
            root.close()
            root.deleteLater()
            engine.deleteLater()
            pump(app)


if __name__ == "__main__":
    raise SystemExit(main())
