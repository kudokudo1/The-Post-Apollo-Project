# 🏥💜 Trash++ U9 // Disposable Real GIO Trash → Restore Runner Acceptance

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External Hospital-compatible DOC, live Hospital registration unverified  
ASSIGNMENT // Validate actual GIO file move into Trash and existing Trash++ GIO Restore backend with disposable CI data  
BASE // `main 2587cfb06319cae66f4a5c70d18332b914cc2127`  
SCOPE // `scripts/trash/gio_disposable_roundtrip_u9.py`, `tests/trash/test_gio_disposable_roundtrip_u9.py`, Trash CI workflow and this runbook.

## IMPLEMENTATION

U5–U7 native **UI control** checks were operator-reported 5/5 PASS following merged PR #1986. U8 read-only Media boundary merged at #2000, with NRS-2 post-merge technical PASS. Actual recoverable GIO file operations remained unwitnessed.

U9 adds a **real, one-disposable-file CI-only** experiment that invokes the installed runner's `gio trash` binary and the actual `scripts/trash/trash_cli.py` index/restore entrypoints. It does not replace or edit the GIO backend, touch the Camera source adapter, call Media's MPD, or introduce production permissions.

The fixture:
1. Refuses to run unless `CI=true`, `GITHUB_ACTIONS=true`, `RUNNER_TEMP` is absolute, existing, a real directory and owned by the runner. This is a **safety latch**, not a security assertion against forged environment values.
2. Creates a private new `TemporaryDirectory` beneath CI `RUNNER_TEMP`. HOME, `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` and `XDG_RUNTIME_DIR` all point inside. It sets `GIO_USE_VFS=local` and passes a minimal isolated environment to both GIO and the Trash++ CLI.
3. Requires the isolated `trash_cli index` to be **empty** before any mutation. Never touches an unknown Trash entry.
4. Creates one random test file in that private HOME, calls **real `gio trash file`**, requires the original file to disappear, and matches exactly one indexed GIO `trash:///` item with that original path and valid opaque review ID.
5. Creates an artificial **collision sentinel** at the original destination and requires actual Trash++ Restore to fail `RESTORE_TARGET_EXISTS`, preserving its bytes and the Trash entry.
6. Removes only that disposable collision sentinel inside runner temp. Calls actual Trash++ `restore URI ORIGINAL`. Requires GIO's `RESTORED` receipt, actual restored file bytes matching the original SHA-256, and isolated Trash index returning empty.
7. Replays the already-used restore URI and requires `STALE_OR_UNKNOWN_TRASH_ITEM`, leaving restored file intact.
8. Emits a bounded result without leaking source paths, user files or private data. No `gio remove`, `trash --empty`, Burn, production path, or host Quickshell operation.

`tests/trash/test_gio_disposable_roundtrip_u9.py` verifies six synthetic/preflight/refusal cases without running GIO.

## HOW TO USE

After separately approved merge, the action runs automatically on GitHub's ephemeral Ubuntu Trash workflow for changes under Trash's existing path filters. CI-only invocation, never run manually on an operator workstation:

```sh
python3 -I -B scripts/trash/gio_disposable_roundtrip_u9.py
```

Outside GitHub Actions, the script fails closed with `CI_ONLY`. It makes an actual file in a private CI sandbox and moves it into that sandbox's GIO Trash. This is **not** a completely read-only test, but all mutations are restricted to disposable runner state.

## VERIFY

- Exact PR head must show the entire existing Trash Python suite, U3–U8 regression steps and the **new real-GIO** step PASS. Do not claim completion before CI.
- A successful result contains `gioReal:true`, `restoredBytesVerified:true`, `collisionDenied:true`, `staleReplayDenied:true`, `postRestoreInventoryEmpty:true`, `fileBurnUsed:false`, `hostAcceptance:false`.
- A real isolated runner result does **not** establish the operator's native Camera → GIO Trash → Trash++ Restore round trip, nor that arbitrary mounts' trash behavior is equivalent.

## WATCH OUT FOR

- This is a single file, on a single temporary runner filesystem. It does not exercise multi-mount Trash, desktop camera backend plan generation, Quickshell rendering, or real personal files.
- The actual GIO backend still has a race between listing a `trash:///` URI and restoring it; this experiment detects representative stale replay and destination collision but does not eliminate external concurrent changes.
- The only accepted tested source is a disposable CI file. No automatic cleanup of any operator Trash; no production data touched.
- Media's MPD `deleteid` is a queue mutation, not a GIO file delete. U8 boundaries remain intact.
- If the stock Ubuntu runner lacks `gio` or the isolated GIO backend refuses operations, the test should fail visibly. Do not silently skip the acceptance check or substitute mocked success.

## CHECKLIST

- [x] Inspect Syntagma and live `main`, Trash CLI, U4 review, U5–U8 evidence
- [x] New real-GIO runner fixture, isolation and negative refusal tests
- [x] Add an explicit Trash CI step without changing owner backends
- [ ] Exact-head real GIO and full regression result
- [ ] Independent Nurse 2 review and operator merge decision
- [ ] Authorized native disposable-file Camera ingress → Restore host acceptance if needed

## NEXT

If CI succeeds, submit isolated exact-head verification for independent review. A later **separately authorized** user-host exercise can create one disposable Camera-owned image under an existing permitted Gallery root, move it via the U5 reviewed TRASH click, and restore it through Trash++ while verifying actual file contents. Do not perform this automatically or use the U7 Desktop bulk TRASH action.

## DECISIONS

No workstation writes, PR merge, protected Archive or Media changes, source owner authority expansion or background action. All code changes are Trash-owned. The test is CI-only; manual operator production file deletion is neither required nor authorized.
