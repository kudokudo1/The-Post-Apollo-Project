# Forest Heart I6c // Offline manifest-to-weight reference

PATIENT: The-Post-Apollo-Project · ROOM: Spirit measurement infrastructure
ROLE: external Hospital-compatible Forest Heart DOC · PRODUCTION HOLD.

## IMPLEMENTATION
Independent additive slice from main 8b077705. I6b #2490 remains open;
its provider digest comparison is not a dependency of this source.
A provider's model digest and the digest of a model weight blob are
different reference levels. Hash exact bounded caller-supplied manifest
bytes and require the expected full SHA-256; parse the legacy single
model-layer manifest layout, validate config and layer descriptors,
and return the one weight reference internally. Public status contains
only reference-match flags, layer count and declared weight size.
No raw digest or content is returned by the public projection.

Layout reference: upstream Ollama manifest/manifest.go and
manifest/layer.go:
https://github.com/ollama/ollama/blob/main/manifest/manifest.go
https://github.com/ollama/ollama/blob/main/manifest/layer.go
These are upstream format references, not installed version evidence.
Manifest lists, explicit runner/format fields, auxiliary model layers
(adapters/projectors/drafts/tensors), duplicate digests and unknown
layouts refuse. No inference about the actual weight file format.

## HOW TO USE
Developer-only pure function inspect_manifest(raw_bytes, expected_digest).
public_status(raw_bytes, expected_digest) provides a redacted diagnostic.
No CLI or file reader; no workstation commands or native trial required.

## VERIFY
python3 -B -m unittest discover -s tests/forest -p 'test_manifest_reference_i6c.py' -v

Synthetic fixtures verify exact byte hash, strict JSON, bounds, supported
layout, private-field omission, invalid/ambiguous references and
non-authority flags. No native Ollama file or real model read.

## WATCH OUT FOR
Matching supplied bytes proves only a mathematical relationship to the
supplied digest. It does not establish who supplied the bytes, whether
they are installed, whether the referenced weight bytes match the
descriptor, or whether an active runner maps those bytes. Declared
weight size is not a memory requirement. Do not combine with I6
group charges as an attribution. No change to I6 same-UID restriction.
No model store paths, process cmdline, environment, maps, executable
contents, private files, service account access, networking or writes.

## NEXT / DECISIONS
Proposed (not approved): use an independently authenticated service-side
source for exact installed manifest and runtime runner references;
verify bounded manifest-to-weight relation, and establish a stable
file object reference with a trusted producer. Correlate only explicitly
authorized runner and group references; preserve freshness, race and
multiple-model handling. A file mapping is not proof of exclusive
resident allocation. Connections owns protected installed-process
identity/authority; no new issuer or service introduced here.
Nurse 2 review and owner agreement remain necessary for native mapping.
#2490 dedicated 114/114 passed; overall 3/4 due to shared ForestW slider
assertion also reproduced in #2491. Cross-owner comments posted.
No auto merge, production activation or native inference.
