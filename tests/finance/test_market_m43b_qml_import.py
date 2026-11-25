"""Compile the actual Market policy in Qt's QML JS engine, not Node."""
from pathlib import Path
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

root = Path(__file__).resolve().parents[2]
app = QGuiApplication([])
engine = QQmlEngine()
component = QQmlComponent(engine)
component.setData(b'''
import QtQuick
import "FinanceStockRangeAnalysisPolicy.js" as Policy
Item {
    property bool verified: {
        var identity = {figi:"BBG000000001",ticker:"ASML",name:"ASML",exchCode:"NA"};
        var listing = {symbol:"ASML.AS",code:"ASML",exchange:"AS",name:"ASML",currency:"EUR"};
        var rows = [{date:"2026-11-02",price:100},{date:"2026-11-04",price:110}];
        var data = {schemaVersion:1,readOnly:true,identityVerified:false,
            source:"eodhd-eod",symbol:"ASML.AS",currency:"EUR",
            currencySource:"eodhd-search",priceBasis:"CLOSE",
            from:"2026-11-01",to:"2026-11-06",retrievedAt:"2026-11-06T21:00:00Z",
            bars:rows,first:rows[0],last:rows[1]};
        var copied = Policy.captureGlobalHistory(identity,listing,data);
        if (!copied) return false;
        rows[0].price=1;
        return copied.first.price===100 && copied.bars[0].price===100
            && copied.last.price===110 && copied.currency==="EUR";
    }
}
''', QUrl.fromLocalFile(str(root / "widgets" / "MarketM43bImportProbe.qml")))
assert component.isReady(), "\n".join(e.toString() for e in component.errors())
obj = component.create()
assert obj is not None, "\n".join(e.toString() for e in component.errors())
assert obj.property("verified") is True, "Actual QML policy import/copy failed"
print("Finance M43b actual Qt QML JavaScript import and detached endpoint copy: PASS")
