# Forest Core B6-R2 // Minimum Useful Canopy selection reference

PATIENT: The-Post-Apollo-Project · ROOM: Forest Core shared infrastructure
ROLE: Forest backend DOC, external Hospital-compatible · PRODUCTION HOLD.

## IMPLEMENTATION

Operator approved B6-R0 then R1 and this registry step. R1 #2421 merged
7ba15c11; independent review still pending at reconciliation. This milestone
adds a pure immutable capability-selection reference, not live activation.

Original archived sources in The-Post-Apollo-Forest-Project,
raw-import/2026-09-22-transfer/:
- Downloads/Forest Logs/bristlecone_capability_registry_and_individual_tool_activation.md
  blob bd39de7768fa07c4066a12d115df182704ebc650
- Downloads/Forest Logs/forest_minimum_useful_canopy_and_tree_workshops.md
  blob ec552c8c4945855432dbc29a02f8155233894b94
- The-Forest/bristlecone/capabilities/registry.yaml
  blob 41648b98905ebc52327d134feb32c032fb6e2230
- workshops/research.yaml 5734bbb8b226ddce5ba834eb47a43b973d9ce10e;
  design.yaml 2981f6b992e2d681677b6d57dc66303509b30cc3;
  code-debug.yaml db6fb604231f3a46f85d380345863313dfeadab7;
  model.yaml 09a72bf819d17d626833f39d3dc60536ad2033e9
- adapters/hermes.yaml 08705321f697f722fa47f893071dab45ec2d86fc
- capabilities/resolver.py 4de8afeab976e4b1b92c249cda5af19d8ca5694e

Recover 18 historical capability definitions, general ready set and four
Workshop profiles as Python reference values (no YAML dependency or
manifest loader yet). Historical adapter target names are descriptive only.
Unknown historical mapping is explicit, never assumed to be supported.
Registry is generic; one definition can be referenced by multiple Tree
profiles. Each profile is scoped to an exact synthetic R1 TaskContext;
membership is not permission. Explicit Workshop Core + individually
selected General/Ready + explicitly retained sticky selections produce
a bounded ordered tuple of metadata references, with no duplicate
capabilities. Dormant capabilities remain metadata only. A previous plan
must match exact context and Workshop for sticky carry; current membership
and sticky policy are checked again. No implicit reuse across generation,
Tree, Clone, owner or task. A synthetic Maple single-file micro Workshop
demonstrates reuse, not a shipped Maple capability or permission profile.

## HOW TO USE / VERIFY

python3 -B -m unittest discover -s tests/forest -p 'test_capability_registry_b6r2.py' -v

23 focused tests plus R1 and P1 regressions. No tools are loaded, no prompt
or schema injected, no execution callbacks, process, disk, network,
model or authority. Every plan is UNKNOWN_HOLD and no safe actions.
Do not import as a production authorization policy.

## WATCH OUT FOR

Selection means planned metadata, not actual runtime activation, live
adapter capability evidence, scheduling, permission or measured speed.
No actual sticky cache, profile signing, manifest persistence, live
currentness or provenance protection. Python values are forgeable.
Workshop selection is explicit; no automatic task classifier yet.
No actual model form or reasoning resolution, which is a separate lane.
No cross-Tree access or actual Mycelium call. Real permissions must be
checked independently before exposing or executing tools. Resource
governor fit is not a reservation. R1 and Connections native gates
unchanged. No production storage/title access.

## NEXT / DECISIONS

Independent review before integration. Recover authoritative pure AUTO
model-form rule separately (archived provenance #7128514407), then agree
the task-local decision and runtime binding. Reuse shared capability
definitions; do not duplicate tools per Bark or Clone. Future protected
LIST_SESSIONS remains first native operation, dependent on DOC1/2/3.
No workstation changes, model execution, installation or production.
