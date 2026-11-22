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
silently committed as a successful assistant response. Retry and cancellation
are owned by a future session host, not by this transport.

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
- 6-second socket timeout and 120-second aggregate checked deadline.
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
