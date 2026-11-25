# R6d // Retained checkpoint generations (development only)

Stacked only on reviewed R6b #2769; no modifications to reviewed PRs.
Generation zero keeps the original checkpoint directory and original files.
An explicit trusted-wrapper receipt closes a generation with a write-once
seal containing the exact dismissal receipt and hash of its validated
checkpoint snapshot. A later generation uses independent write-once slots.
A missing or corrupt seal, missing predecessor, historical corruption or
reused action UUID refuses. A complete seal without next directory can
be resumed only by an explicit same-receipt retention call, never replay.
No cleanup, expiry, overwrite, automatic rotation, transport or startup
release. Cap of 32 generations is a development bound, not approved
installed capacity. No old writer may operate concurrently; flock applies
to cooperating generation clients only. Same-UID adversaries, directory
rollback, trusted receipt provenance, power loss and installed custody
remain outside this library's scope. Actual trusted owner receipt history,
adapter version negotiation, legacy-reader retirement, committed (rather
than dismissed PREPARED) action retention and desktop qualification remain
separate integration gates. Storage generation creation is not permission
for a new action. All loads return startup_unlock:false and can_execute:false.
