# Hospital // Gated single-owner Vosk streaming handoff

PATIENT // The-Post-Apollo-Project
ROOM // Hospital Surgery / Live Dictation Usability
STAFF ROLE // External Hospital-compatible DOC, no verified live registration
ASSIGNMENT // Stream real provisional/final words through the existing one-recorder Hospital service
SCOPE // Bounded GitHub source, fake tests and source-only disabled integration
PRODUCTION // HOLD

## IMPLEMENTATION

PR #1918 supplies the Surgery pure reducer and separate cyan HEARING preview. This branch is stacked on #1918 to preserve that owner's exact UI work and avoid a conflicting edit.

The new `scripts/hospital_streaming_vosk_owner.py` runs as **one** QML `liveProcess` alternative to the existing Whisper subprocess. It starts one `pw-record` process and **one** isolated Vosk probe child (from merged #1913), forwarding 16kHz mono PCM16 in 100ms frames over stdin. It does not execute Whisper or share a recognizer. No model or microphone is used in synthetic tests.

The model process applies its own Linux limits **before** importing native Vosk: 2 GiB virtual-address cap, 12 CPU seconds, 45s hard wall alarm, two allowed CPU cores, core dumps off, nice +10. The owner separately caps PCM to 25 seconds and aborts slow pipe writes, parser failures and parent loss. Both owned child process groups are sent TERM then KILL on error/cancel/exit. Output is filtered to fixed status/metrics codes or strictly shaped provisional/final text packets. Raw audio, model path and native stderr are not logged.

`HospitalLiveDictationService.qml` reuses its existing **single** `liveProcess` and process watchdog, allowing either:
- Default Standard/Fast Whisper command, unchanged;
- Streaming owner command **only when** `streamingTrialAllowed = true`, `streamingModelDir` is explicitly nonempty, and existing bounded pilot conditions hold.

**Both new properties default to false/empty. HospitalW.qml does NOT enable either property.** A repository merge alone cannot start the trial or load Vosk on the operator's PC.

Surgery offers a STREAMING MODEL TRIAL selection **only when both host gates are set**. The existing inline MIC toggles START/STOP and the red CANCEL control revokes the session and requests backend cancellation. Provisional text remains only in the cyan HEARING line, while finalized segments pass through the existing bounded `HospitalDictationTextPolicy`. The manager refuses stale/reordered packets, cross-field commits, mode changes during capture and simultaneous Whisper/Vosk.

## HOW TO USE

Currently **no live option is enabled** and no packages/models are installed. The operator may continue using Standard Whisper normally. The proposed trial remains a protected source experiment.

For fake/offline verification in a disposable repository environment:
`python3 tests/hospital/test_streaming_owner_contracts.py`

Real activation is a separate operator-controlled change. It requires: model provenance and package review, verifying the exact install path, explicit permission to change host settings, native process lifetime/termination tests, actual audio/latency benchmark, and reversible rollback. Do not enable the properties based solely on synthetic CI.

## VERIFY

- Synthetic recorder and decoder subprocesses demonstrate one host owner, replaceable successive hypotheses, finalized commit, numeric metrics, child teardown, early STOP and CANCEL.
- Negative tests refuse invalid native packets, absent explicit CLI opt-in, malformed decoder output, and unauthorized default runtime configuration.
- This branch's contract tests perform no real audio capture, Vosk import, network call, or model download.
- Real PipeWire/Vosk handling, resource measurements, audio accuracy, and Quickshell visual rendering are **not yet verified**.

## WATCH OUT FOR

- The model's Vosk library remains optional. Absence is a failure, not permission to silently launch Whisper simultaneously.
- Both Python process wrappers have bounded but distinct resource controls; the native model should receive independent OS isolation review before host activation.
- Stage/metric receipts are non-content. Provisional/final speech packets inherently contain spoken words and must not be written to permanent logs.
- The private in-memory run token is not operating-system authentication. One QML-owned process and child-bound output validation are separate ownership boundaries.
- The optional trial does not change the existing Whisper six-chunk ceiling, per-engine CPU/RAM limits, VAD, current recording behavior, or production worker permissions.

## CHECKLIST

- [x] Establish prior #1918 branch/PR ownership and current main
- [x] Add a one-recorder/one-model guarded Vosk owner wrapper
- [x] Connect it through the existing QML liveProcess with default-off gate
- [x] Route hypothesis/commit to in-memory Surgery field preview with STOP/CANCEL
- [x] Add synthetic process/teardown and negative contracts
- [ ] Exact-head CI, independent security review, native trial
- [ ] Operator approval for installation, activation, merge and final acceptance

## NEXT

Validate CI and fix only concrete failures. If the operator later authorizes live testing, verify model provenance, PipeWire and the real host's resource caps before turning on the gate. Benchmark FIRST HYPOTHESIS, FIRST COMMIT, transcription accuracy, memory and cancellation relative to Standard Whisper, then decide whether to keep or discard Vosk.

DECISIONS // External DOC continuity only. This is a stacked draft, not a merge. No local computer writes, package installation, service restart or activated streaming mode. Roll back only this PR to preserve the standalone preview policy.
