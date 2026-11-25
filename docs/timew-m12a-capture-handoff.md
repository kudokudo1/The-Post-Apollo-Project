# TimeW M12a // Proposed full local capture handoff

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE / Scope A  
**ROLE //** TimeW owner DOC, external Hospital-compatible; live registration unverified  
**PRODUCTION RESTORE // HOLD**

## IMPLEMENTATION
SwayPX #187 proves genuine in-process CURRENT/PENDING binary64 container observations on actual disposable mapped floating XDG candidates. The dormant observer refuses tiled, Xwayland, unmapped, locked, fullscreen, scratchpad and drifted contexts. It exposes process-local references, not a complete desktop source endpoint. Current SwayPX #214 is renderer CI work, not a capture interface. Do not parse test logs or use pointers/rounded IPC geometry as fractional source.

This is a proposed in-process consumer adapter, not an agreed wire protocol. Inputs: two independently acquired ordinary full layout frames and exact per-window observations, a caller-owned original Save UUID, label and timezone-aware capture time. Each input batch has kind swaypx-local-capture-proposal-v1, epoch (canonical v4 UUID), revision (bounded unsigned integer), pending_transaction=false, queued_transaction=false, outputs, workspaces, tree (existing V2 projection input), windows (one row per tracked window). Row: con_id (positive transient integer), lifetime (canonical v4 UUID), app_id, output_id, workspace_id, phase=CURRENT, current_bits (four canonical lowercase 16-hex binary64 words x/y/w/h). Epoch/lifetime token format and revision semantics are a proposal for source-owner review, not existing SwayPX facts. The real producer must derive and bind both ordinary frame and exact observations from one consistent compositor-owned snapshot; repeat acquisition and revision/lifetime continuity must reflect native state, not caller inference or caller-chosen tokens.

TimeW maps each transient ID/lifetime to a checkpoint-local UUIDv5 scoped by original Save UUID and epoch, retains the same mapping across both batches and uses the existing V2 projection to ensure full coverage. Refuse duplicate, missing, extra, changed or invalid windows, changed output/workspace/layout/epoch/revision, PENDING values, transaction-in-progress, invalid bits and unexpected fields. Two same-app windows remain distinct. Never infer fractional values from integer rects, match by app name, or silently drop unsupported windows. Ordinary integer rect versus native CURRENT coordinate correspondence is a source-owned contract requirement; this adapter does not prove it. Equality does not prove two acquisition events, freshness, hidden ABA, atomic capture or origin. Return V1/V2 and exact CURRENT observations suitable for the existing M10 API, local/untrusted flags only; no writes, CLI, process, transport or Save hook.

## HOW TO USE
Development API only. Explicit caller passes two supplied batches to prepare_local_capture; when valid, the returned documents/observations can be passed to M10 in a separately authorized caller. No current operator button calls it. Existing Save remains unchanged. No actual source endpoint assumed.

## VERIFY
Synthetic multi-output/duplicate-app frames and binary64 one-ULP differences, invalid metadata/lifetime/phase/bits, full coverage, changed snapshots, bounded input, unchanged caller-owned input references and no writes on preparation. Explicit disposable test caller exercises real M10 SQLite Save and recovery with the prepared bundle. Regressions M6–M10 and existing Save UI contract. Passing this tests consumer mapping and local store integration, not genuine native acquisition.

## WATCH OUT FOR
The existing #187 reader cannot supply a complete desktop batch. SwayPX owner must establish actual full-layout source coverage or explicit refusal/fallback; no authority-bearing interface is created. Agree source epoch/revision/lifetime, coordinate semantics, atomic acquisition, output/workspace generation and stable con_id mapping, unsupported window handling, and resource limits before actual capture. Scope A protected selection/ACK/frame/C5 remains separate. No silent fractional fallback, no change to old Save. Source owner owns compositor hooks. Retention and durable caller input policy still open.

## NEXT / DECISIONS
Request cross-owner feasibility/accept/revise on proposed source contract, independent review of TimeW consumer and actual producer handoff next. No merge, host change or production activation.
