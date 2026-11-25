# R6k // Checkpoint helper custody

Canonical desktop wrapper now routes GEN_LOAD/SAVE/ADVANCE through the
same exact-child Linux pidfd supervisor used by the queue owner. Only
the three generation operations are accepted, with a private directory
and checked helper script. Isolated interpreter bootstraps only the
checked script's sibling imports. Successful supervisor exit requires
a matching normal child exit; adapter still requires the exact bounded
response, generation, ticket and operation. Failure/timeout remains
unknown, never automatic replay. Existing direct legacy/disposable
adapter callers remain supported; path/mode is pinned on first use.

Existing five actual wrapper trials now traverse custody for both
owner and checkpoint helper. New direct test covers argument, private
directory, environment and nonzero helper exit. No installed protected
bundle provenance, race-free same-UID file protection, raw upstream
allocation bound or production mount is claimed. Fresh CI required.
