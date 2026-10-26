from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "services/messaging/bridges/bereal/FEASIBILITY.md"
ADAPTER = ROOT / "services/messaging/adapters/BeRealAdapter.qml"

assert DOC.is_file(), DOC
text = DOC.read_text()

for required in (
    "BLOCKED / RESEARCH",
    "No official desktop client",
    "web personal inbox",
    "public developer messaging API",
    "automated accounts/bots",
    "private mobile endpoints",
    "decorative launcher rather than a connection",
):
    assert required in text, required

assert not ADAPTER.exists(), ADAPTER

print("BeReal desktop messaging feasibility contract: PASS")
