#!/usr/bin/env python3
"""Render real QML lunar shapes offscreen. No live forecast or user machine.

Requires PySide6 and a Qt Quick scene (CI runs under Xvfb). Fail on invalid
QML type, indistinguishable phases, wrong light-side orientation or cloud
foreground loss. Saves the exact rendered fixture for human visual review.
"""
import math
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QUICK_BACKEND", "software")
from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/weather/fixtures/WeatherMoonMatrix.qml"
ARTIFACT = ROOT / "weather-moon-matrix.png"

app = QGuiApplication(sys.argv)
view = QQuickView()
view.setResizeMode(QQuickView.SizeRootObjectToView)
view.setSource(QUrl.fromLocalFile(str(FIXTURE)))
if view.status() == QQuickView.Error:
    raise RuntimeError(f"QML fixture failed: {view.errors()}")
view.show()
loop = QEventLoop()
QTimer.singleShot(1100, loop.quit)
loop.exec()
image = view.grabWindow()
if image.isNull() or image.width() != 800 or image.height() != 330:
    raise RuntimeError(f"QML rendered no usable image: {image.size()}")
image.save(str(ARTIFACT))
print("Rendered actual QML:", ARTIFACT)

PHASES = [
    "new", "waxing-crescent", "first-quarter", "waxing-gibbous",
    "full", "waning-gibbous", "last-quarter", "waning-crescent"
]

def is_lit(px, py):
    col = image.pixelColor(int(px), int(py))
    return (col.red() > 165 and col.green() > 62
            and col.blue() < 115 and col.red() - col.green() > 36)

def pixels_for(phase_index, row, scale):
    # Matrix cell 100x110; big celestial is 80x80 centered at (10,8).
    # Its phase-only moon is centered at (20,20), whereas the composed
    # moon is anchored at (16,15) in normalized 40x40 art coordinates.
    ox = phase_index * 100 + (100 - scale * 40) / 2
    oy = row * 110 + 8
    cx, cy = (20, 20) if row == 0 else (16, 15)
    values = []
    # Iterate actual framebuffer pixels rather than sampling only odd
    # pixels. The previous odd-pixel-only sampling introduced an artificial
    # 1.5px right bias that made perfectly mirrored lunar areas look unequal.
    for py in range(scale * 40):
        for px in range(scale * 40):
            nx = (px + 0.5) / scale
            ny = (py + 0.5) / scale
            if math.hypot(nx - cx, ny - cy) < 11.8:
                values.append((nx - cx, is_lit(ox + px, oy + py)))
    return values

fractions = []
centroids = []
for i, name in enumerate(PHASES):
    samples = pixels_for(i, 0, 2)
    lit = [x for x, hit in samples if hit]
    fraction = len(lit) / len(samples)
    centroid = sum(lit) / len(lit) if lit else 0.0
    fractions.append(fraction)
    centroids.append(centroid)
    print(f"{name:18} illuminated={fraction:0.3f} weighted-x={centroid:+0.2f}")

def between(value, low, high, label):
    if not low <= value <= high:
        raise AssertionError(f"{label}: {value:.3f} not in [{low},{high}]")

for index in (0,):
    between(fractions[index], 0, 0.05, PHASES[index])
for index in (1, 7):
    between(fractions[index], 0.05, 0.38, PHASES[index])
for index in (2, 6):
    between(fractions[index], 0.34, 0.66, PHASES[index])
for index in (3, 5):
    between(fractions[index], 0.62, 0.95, PHASES[index])
between(fractions[4], 0.95, 1.0, "full")
# Crescent, quarter and gibbous must use the *same* lit silhouette
# under horizontal mirroring. This catches the QML PathArc direction bug.
for waxing, waning in ((1, 7), (2, 6), (3, 5)):
    assert abs(fractions[waxing] - fractions[waning]) < 0.035, (
        f"asymmetric pair {PHASES[waxing]}/{PHASES[waning]}: "
        f"{fractions[waxing]:.3f}/{fractions[waning]:.3f}")
    assert centroids[waxing] > 0.8, f"waxing light wrong: {PHASES[waxing]}"
    assert centroids[waning] < -0.8, f"waning light wrong: {PHASES[waning]}"
    assert abs(centroids[waxing] + centroids[waning]) < 1.2, (
        f"shape centroids not mirrored: {PHASES[waxing]} / {PHASES[waning]}")
assert len({round(x, 2) for x in fractions}) >= 4, "moon phases indistinguishable"

# New moon's dark lower disk must be covered by an opaque orange foreground
# cloud. With the new-phase clear composition the same area stays unlit.
i = 0
base_x = i * 100 + 10
assert not is_lit(base_x + 2 * 20, 8 + 2 * 26), "new moon itself is lit"
assert is_lit(base_x + 2 * 20, 110 + 8 + 2 * 26), "foreground cloud not opaque"
# In the dock-sized row ensure the new moon still has dark center.
small_x = i * 100 + 30
assert not is_lit(small_x + 16, 220 + 8 + 15), "dock new moon not dark"

print("Eight-phase Qt Quick visual matrix: PASS")
view.close()
