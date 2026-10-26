from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "services/messaging/bridges/kakaotalk/FEASIBILITY.md"
ADAPTER = ROOT / "services/messaging/adapters/KakaoTalkAdapter.qml"

assert DOC.is_file(), DOC
text = " ".join(DOC.read_text().split())

for required in (
    "BLOCKED / RESEARCH",
    "Kakao Talk Social",
    "Kakao Talk Message",
    "additional feature permission",
    "ordinary user's existing KakaoTalk chatroom history",
    "No official Linux KakaoTalk desktop client",
    "Do not create a fake",
    "permissioned outbound message/share",
):
    assert required in text, required

# Research did not verify a contract-compliant full inbox transport.
assert not ADAPTER.exists(), ADAPTER

print("KakaoTalk personal inbox feasibility contract: PASS")
