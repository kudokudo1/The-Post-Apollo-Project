# FOREST CORE // B2 Explicit Local Ollama Chat Transport

> STATUS // draft transport contract, not deployed or bound to ForestW.
> OWNER // Forest backend DOC lane. UI worker owns ForestW, dock, icons and menus.

## Mechanism

The caller provides the exact model name and a short message history. B2
sends a single JSON POST to the loopback Ollama /api/chat endpoint, reads
newline-delimited JSON chunks, and emits machine-readable events:

- STARTED: an HTTP 200 stream was opened (not proof of any model accuracy)
- DELTA: provisional output text; do not save or call this a completed answer
- COMPLETE: Ollama explicitly emitted done=true with nonempty output text
- REFUSED: CLI emits a static reason if validation/network/streaming fails

The Python API raises ChatRefusal on error instead of yielding REFUSED.
A partially streamed answer must be marked incomplete and must NEVER be
silently committed as a successful assistant response. Retry and cancellation ownership remain with the session host. B2 accepts
an optional host-owned, one-operation threading.Event; setting it interrupts
this request's connected socket and yields no further successful completion
once cancellation is observed. The host must never clear or reuse the event.

## How to run an explicit local trial

Only after operator permission to invoke the local model:

    printf 'Hello from Forest\n' | python3 scripts/forest/ollama_chat_transport.py chat --model qwen3:1.7b --prompt-stdin

No local machine changes or real model calls were performed while creating
this draft. This command itself deliberately calls the local Ollama server;
it may load the requested model and use CPU/GPU resources. If the model is not
installed Ollama returns a static refusal. DO NOT paste sensitive prompts
into shell command arguments; standard input is used instead.

No web or hosted AI provider, no model pull, no Hermes thought settings.

Default safety/resource limits:

- Only HTTP on literal IPv4/IPv6 loopback, never redirect or nonlocal host.
- Max 16 user/assistant messages, 4096 bytes each, 16384 bytes combined.
- Response line 65536 bytes, response stream 1 MiB, answer text 32768 bytes.
- 6-second socket inactivity/connect timeout and 120-second aggregate I/O
  deadline, enforced by a per-exchange socket shutdown watchdog. Literal
  loopback connect is bounded separately and checked before dispatch.
- 256 predicted tokens and 4096-token context by default; accepted bounds
  max_predict 1..512, num_ctx 512..8192. Smaller context is NOT Hermes agent
  readiness; direct Ollama does not need Hermes's 64K minimum.
- No system prompt, tools, thinking, keep_alive or format options sent.
- No automatic retries, process control, uploads, side effects or persistence.
- Model names are validated but still untrusted provider identifiers.
- The response may have a server-side thinking field; B2 never displays it.

## Operator test and CI

    python3 -m unittest discover -s tests/forest -p 'test_ollama_chat_transport.py' -v

Tests use disposable fake HTTP endpoints on 127.0.0.1. They verify:
successful chunk flow, bounded model/history request, reject external
endpoints, invalid HTTP and content types, malformed/duplicated JSON, tool
call rejection, incomplete streams, early cancellation, overlong output,
and CLI output. No installed Ollama server, real model or personal data is
needed in CI.

## Backend integration still needed

B0 only lists models. B1 persists synthetic conversation records. B2 is a
transport primitive, NOT a trusted connector joining B1 to real user data.
The subsequent consumer must hold a verified user identity, enforce a single
session owner and revision, and append assistant content ONLY after a COMPLETE
event. A protected storage host, privacy review, and user authorization are
required for durable real conversation history. No ForestW source was edited
and no Hospital/PX worker authority is inherited.

## DOC 2F interruptible transport checkpoint

The watchdog only shuts down a duplicate of this request's TCP socket. It
never kills, unloads or retries a model. The generator owner closes the
response and joins the watchdog on exit. STOP is an observed local transport
interruption, not proof of remote inference termination or resource release.
A STOP racing with COMPLETE requires host-owned terminal reconciliation;
B2 cannot revoke a durable turn, grant disclosure or settle an unknown B3
attempt. B3 integration is deliberately unchanged pending shared ownership
agreement. The focused tests exercise pre-dispatch refusal, stalled headers,
partial-line cancellation, deadline and cancellation between events using
public disposable loopback fixtures only.

## Real ForestW request binding (source-only)

For the real local P0 path, `prepare_chat_request` uses B2's existing
validator and exact JSON encoder without I/O. The returned immutable
request retains resolved loopback host/port, model, exact POST bytes and
SHA256. Never log the object body or digest; it is not authority. The
owner may supply `expected_request` to `stream_chat`: any mismatch in
validated destination or payload refuses before connect. A matching
request does not authorize a POST, authenticate an installed artifact,
prove resource capacity or grant output release. Existing B2 callers
and its CLI retain their previous behavior. No new executable entry,
QML binding, provider admission, or model invocation is added here.

P0 owner plan: UI1 captures the actual original draft and selected model
from ForestW SEND, held until an independently admitted host exists.
Runtime must retain the approved public input and selected settings,
use the same B2 preparation for original commitment and exact B3/R3
stream dispatch, and independently fence authority and resource admission
before the POST. Mind's existing exact-input M2/B3 path uses a disposable
in-memory journal. The original worker consumes R3 and projects bounded
same-row replacement snapshots; UI2 renders only the independently
current original view. STOP uses original R2/R3 control independent of
blocked B2 I/O; close withdraws output and must not imply provider idle.
No fixed mock substitution, new journal, tools, protected history,
model pull, fallback, retry, or shared-service change. H9 A–F, H13 and
First Light trial checklist still require actual host, installed digest,
exclusive runner, preventive RAM/CPU/device/time/egress limits, original
custody and one explicit operator trial authorization; Stage1 hosted
staging is separate. Actual SEND binding and execution remain HOLD.
