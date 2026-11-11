# Hospital // Offline streaming recognizer feasibility proof

PATIENT // The-Post-Apollo-Project
ROOM // Hospital Surgery / Live Dictation Usability
ROLE // External Hospital-compatible DOC (not live registered)
ASSIGNMENT // Operator-authorized next voice responsiveness milestone
STATE // Offline source/CI proof only; not installed, authorized or wired into Hospital

## Problem

The existing private Whisper server returns text after each request completes.
Shorter capture windows and the separate #1904 responsive experiment can lower
some collection delay, but cannot make that server emit continuously revised words.

An actual streaming decoder yields a **provisional hypothesis** during ongoing
audio and a **final segment** when the speech decoder closes that utterance.
The Surgery editor must not append the provisional text. Otherwise corrections
like "why do" -> "why did" leave duplicate or incorrect irreversible words.

## Proof boundaries

- New, standalone `scripts/hospital_streaming_vosk_probe.py` reads **only
  standard input** containing 16 kHz, mono, PCM16LE frames. It does not select
  or open any microphone, start PipeWire, launch Hospital workers, write files,
  download models, or talk to any socket/cloud service.
- Direct execution requires **both** `--offline-probe` and a user-provided
  local `--model-dir`; absent flags refuse. The optional Vosk import is lazy.
  No package/model installation or desktop activation occurs in this change.
- 100ms PCM frames are supplied to **one** `KaldiRecognizer` instance via
  `AcceptWaveform`. Nonfinal `PartialResult` becomes `hypothesis` and
  final `Result` or EOF `FinalResult` becomes `commit`.
- `hypothesis` includes the complete **replaceable** provisional string.
  `commit` includes `clear_provisional: true` and is the only legal source
  of permanent editor text. `revision` increments with emitted updates,
  not per audio packet. Empty final results clear stale hypotheses.
- No audio, transcript text or model details enter diagnostic **status** or
  **metrics** packets. The hypothetical text packets themselves contain speech
  because a future, explicitly controlled UI must render it; stdout is not
  a private journal. Do not redirect output to persistent files.
- Maximum captured bytes are equivalent to 25 seconds. Text is bounded to
  4000 characters, update events to 300, and subprocess model execution is
  guarded on Linux before import by RLIMIT_AS 2 GiB, RLIMIT_CPU 12 seconds,
  RLIMIT_CORE 0, nice +10, and affinity restricted to two already allowed
  CPUs. These are prototype guards, **not a certified production sandbox**.
- Synthetic tests use an in-memory fake decoder and fake PCM. They verify
  successive provisional corrections, final commits, duration limits, strict
  JSON shapes and refusal without explicit opt-in.

## Candidate choice / external evidence

The Vosk Python API exposes `AcceptWaveform`, `PartialResult`,
`Result` and `FinalResult`:
https://github.com/alphacep/vosk-api/blob/master/python/vosk/__init__.py

Vosk's official model catalog describes a small English model (40MB),
typically ~300MB runtime memory for small models, licensed Apache 2.0.
Those numbers are upstream estimates, **not measured on this PC**:
https://alphacephei.com/vosk/models

sherpa-onnx is a separate viable CPU streaming candidate, with
`create_stream`, `accept_waveform`, `is_ready`, `decode_stream` and
`get_result` APIs:
https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/python/sherpa_onnx/online_recognizer.py

This proof chooses Vosk for minimal optional adapter surface, **not**
because its accuracy or latency has been proven superior to Whisper.

## Important separation from existing PRs

#1899 (red stop/finalizing UI) and #1904 (single early Whisper partial) remain
draft and independent. This branch adds **only** the standalone source,
synthetic tests, CI, and this contract. No shared Surgery QML or Whisper
files are changed. It may be reviewed and tested without merging either PR.

## Preconditions before any native trial

1. Operator explicitly approves any local model/package installation,
   desktop mutation, live microphone capture or Quickshell reload.
2. Audit the Vosk Python wheel/library and selected model provenance,
   signature/hash and license. Set a restricted, separate process boundary
   before integrating with the Hospital-owned microphone.
3. Implement a dedicated **preview** slot in Surgery that replaces
   hypotheses, and a separate **commit** path that appends only final text.
   No autosubmit, AI request, assignment activation or permission grant.
4. Compare the exact same spoken phrases, numbers, punctuation and natural
   speech in Vosk versus Standard Whisper; record first hypothesis, first
   committed word, accuracy, CPU/memory and cancellation behavior.
5. Preserve native STOP/CANCEL resource teardown, six-job Whisper safety
   baseline and operator rejection/rollback.

## Acceptance and rollback

Synthetic CI success proves only code-contract behavior, not model speed,
quality, real OS isolation, or working Quickshell controls. The user decides
when any later host trial is acceptable. This branch has no runtime
effect; rollback is to close/revert its independent PR.
