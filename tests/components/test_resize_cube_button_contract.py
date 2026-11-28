#!/usr/bin/env python3
"""Static contract for the approved V14-A resize cube and its aligned halos."""
from pathlib import Path
import math
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "assets/resize"
NS = "{http://www.w3.org/2000/svg}"
core, glow, contrast = [ET.parse(BASE / name).getroot() for name in
    ("cube-v14a.svg", "cube-v14a-glow.svg", "cube-v14a-contrast.svg")]
qml = (ROOT / "components/ResizeCubeButton.qml").read_text()
colors = (ROOT / "components/Colors.qml").read_text()
assert "ResizeCubeButton 1.0 ResizeCubeButton.qml" in (ROOT / "components/qmldir").read_text()
assert re.search(r"(?m)^ActionButton\s*\{", qml)
for token in ("implicitWidth: 30", "implicitHeight: 30", "height: width",
              'keyboardActivationSignal: "leftClicked"', "contentGlowEnabled: false",
              "contentGlowSource: null", "sourceSize.width: root.rasterSize"):
    assert token in qml, token
assert "MouseArea" not in qml and "Timer" not in qml
for prefix in ("idle", "hover", "pressed", "selected", "keyboardSelected"):
    assert prefix + "BorderColor: Colors.yellow" in qml
    assert prefix + "SoftGlowColor: Colors.magenta" in qml
assert all(x.attrib["viewBox"] == "-12 -12 88 88" for x in (core, glow, contrast))
for color, rgb in (("magenta", "#C74EC7"), ("cyan", "#55CFCA"), ("yellow", "#F2BE4E"), ("black", "#1B0623")):
    assert re.search(r'property color '+color+r': "'+rgb+'"', colors)

def strokes(group):
    return [(x.attrib["d"], x.attrib.get("stroke")) for x in group.iter(NS+"path")]

def transforms(group):
    return [x.attrib["transform"] for x in group.iter(NS+"g") if "transform" in x.attrib]

g = core.find(NS+"g")
assert g.attrib["stroke-width"] == "1.65"
expected = [
    ("M8.617314 18.5 L20.774221 23.414387 M32 5 L34.734698 17.815964 M55.382686 18.5 L43.252183 29.481440 M55.382686 45.5 L41.176227 39.695468 M32 59 L27.215751 45.293891 M8.617314 45.5 L18.698265 33.628415 M32 32 L29.291707 35.079863", "#55CFCA"),
    ("M32 5 V18.912631", "#C74EC7"),
    ("M43.252183 29.481440 L41.176227 39.695468", "#C74EC7"),
    ("M41.176227 39.695468 L27.215751 45.293891", "#55CFCA"),
    ("M20.774221 23.414387 L18.698265 33.628415 L27.215751 45.293891 L29.291707 35.079863", "#C74EC7"),
    ("M20.774221 23.414387 L34.734698 17.815964 L43.252183 29.481440", "#55CFCA"),
    ("M20.774221 23.414387 L29.291707 35.079863", "#55CFCA"),
    ("M29.291707 35.079863 L43.252183 29.481440", "#55CFCA"),
    ("M8.617314 45.5 L8.617314 18.5 L32 5 L55.382686 18.5 M32 59 L8.617314 45.5 M8.617314 18.5 L32 32 L55.382686 18.5", "#C74EC7"),
    ("M55.382686 18.5 V45.5 L32 59", "#C74EC7"),
    ("M32 32 V59", "#C74EC7"),
] + [("M5 -4.284444020226 L8 0 L5 4.284444020226", None)] * 3
assert strokes(g) == expected, "V14-A geometry/order changed"
assert transforms(g) == ["translate(8.617314 18.5) rotate(-150)", "translate(55.382686 18.5) rotate(-30)", "translate(32 59) rotate(90)"]
assert math.isclose(2*math.degrees(math.atan(4.284444020226/3)),110,abs_tol=1e-8)
assert len(glow.findall(NS+"g")) == 3
for layer in glow.findall(NS+"g"):
    assert strokes(layer) == expected and transforms(layer) == transforms(g)
    assert [x.attrib.get("stroke") for x in layer.iter(NS+"g") if "transform" in x.attrib] == ["#F2BE4E"]*3
assert [x[0] for x in strokes(contrast.find(NS+"g"))] == [x[0] for x in expected]
assert transforms(contrast.find(NS+"g")) == transforms(g)
print("ResizeCubeButton V14-A static contract PASS")
