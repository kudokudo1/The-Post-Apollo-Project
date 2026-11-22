# FOREST CORE // B0 Local Model Inventory

> STATE // Draft, offline-tested contract; not a live Forest agent or UI service.

## Scope and ownership

This is an **independent, read-only Forest adapter**. It does not use Hospital's
PX worker registry, staff roles, credentials, consent, sessions, or room charts.

The visible Forest widget is owned separately. The UI worker may use this
command's JSON format after its own process-integration and focus review, but
this change does **not** edit any Quickshell file or activate an agent.

## How to use (manually)

From the Post-Apollo project root, with Ollama already running:

    python3 scripts/forest/ollama_inventory.py list-models

Custom localhost port:

    python3 scripts/forest/ollama_inventory.py list-models --endpoint http://localhost:11434

The command performs exactly one GET request to
http://127.0.0.1:11434/api/tags by default, then exits. Localhost is converted
to literal 127.0.0.1 before connecting. No process is spawned or stopped.

Example success (the numbers and model names are illustrative):

    {"schema_version":1,"provider":"ollama","status":"REACHABLE","models":[{"name":"qwen3:1.7b","size_bytes":1400000000}],"model_count":1,"capabilities":["list_models"],"generation_enabled":false,"tools_enabled":false,"sessions_enabled":false}

Example unavailable:

    {"schema_version":1,"provider":"ollama","status":"UNAVAILABLE","models":[],"model_count":0,"capabilities":[],"generation_enabled":false,"tools_enabled":false,"sessions_enabled":false,"reason":"OLLAMA_UNAVAILABLE"}

Exit 0 means the inventory response was valid. Exit 2 means the endpoint was
unusable or invalid. Names are untrusted identifiers from a local Ollama server,
not instructions, capabilities, guaranteed context windows, or authorization.

**REACHABLE means the service's model list was retrieved**, not that any model
is loaded on GPU, can handle Hermes's context requirement, or supports thinking.

## Safety boundaries

- Only http://localhost, http://127.0.0.1, or http://[::1] endpoints.
  Hostnames are never expanded into arbitrary network destinations.
- No credentials, paths, query strings, fragments, redirects, or TLS bypasses.
- Timeout 2.5 seconds; 1 MiB JSON response and 256-model cap.
- Invalid/malicious model records fail the entire response; no partial truth.
- No prompts, generation, session creation, model pull, filesystem writes,
  personal memories, or external network traffic.
- No network call on Python import. Executed only by explicit CLI invocation.
- QML/Hermes integration is **not** in this milestone.

## Run tests

    python3 -m unittest discover -s tests/forest -p 'test_ollama_inventory.py' -v

Uses a disposable local fake HTTP server. Does not require installed Ollama,
API tokens, or access to any personal data.

## Next contract (not implemented)

A separate operator-reviewed Forest session and message store will be needed
for cross-model continuity. A provider adapter handling generation also needs
rate/resource control, explicit authorized tool permissions, cancellation, and
privacy review. The UI worker should display model inventory and engine status
only from actual successful calls, not from this document.
