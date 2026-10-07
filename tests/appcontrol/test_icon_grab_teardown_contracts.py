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

assert """onSourceChanged: {
                                // Keep an in-flight grab alive until the Canvas
                                // releases its temporary URL.
                                selectorAppIconBox.verifiedSource = "";""" in text

assert """onSourceChanged: {
                                            // Preserve an in-flight grab until its Canvas
                                            // consumer has released the temporary URL.
                                            selectedAppIconBox.authoritativeSource = "";""" in text

assert """source:
                                selectorAppIcon.Window.window !== null
                                ? selectorAppIcon : null""" in text

assert """source:
                                            selectedAppIcon.Window.window !== null
                                            ? selectedAppIcon : null""" in text

assert "selectorIconColorSampler.Window.window !== null" in text
assert "selectedIconColorSampler.Window.window !== null" in text

print("AppControl icon grab teardown contracts: PASS")
