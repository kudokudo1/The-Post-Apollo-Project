from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "widgets" / "AppControlW.qml"

text = APP.read_text()

assert text.count(".grabToImage(") >= 2

for icon in ("selectorAppIcon", "selectedAppIcon"):
    assert f"{icon}.Window.window === null" in text
    assert f"{icon}.Window.window !== null" in text

assert "function scheduleResample()" in text
assert text.count("scheduleResample();") >= 6

selector_source = text[text.index("id: selectorAppIcon"):text.index("id: selectorIconColorSampler")]
assert "selectorAppIconBox.iconGrabResult = null;" not in selector_source
assert 'selectorAppIconBox.samplingSource = "";' not in selector_source

selected_source = text[text.index("id: selectedAppIcon"):text.index("id: selectedIconColorSampler")]
assert "selectedAppIconBox.iconGrabResult = null;" not in selected_source
assert 'selectedAppIconBox.samplingSource = "";' not in selected_source

assert """source:
                                selectorAppIcon.Window.window !== null
                                ? selectorAppIcon : null""" in text

assert """source:
                                            selectedAppIcon.Window.window !== null
                                            ? selectedAppIcon : null""" in text

assert "selectorIconColorSampler.Window.window !== null" in text
assert "selectedIconColorSampler.Window.window !== null" in text

print("AppControl icon grab teardown contracts: PASS")
