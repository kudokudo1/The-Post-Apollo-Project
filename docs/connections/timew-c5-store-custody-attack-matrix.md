# 🏥💜 DOC 5 // C5 TimeW test-store custody attack matrix

**Patient:** The-Post-Apollo-Project. **Owner:** Connections DOC 5, TimeW-facing C5. **Phase:** source/CI-only negative evidence. **Production:** HOLD. **Hospital:** external-compatible; live registration not verified.

## Mechanism

This is the second isolated test-only DOC 5 increment after [#2196](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2196) (merged, Nurse 2 retrospective scoped PASS). That reference serializes SPENT and REVOKED SQLite writes and returns **no native authority**. Nurse 2 correctly observed that an unprivileged same-UID user can replace or roll back its disposable store. This new matrix executes that failure against the exact existing code rather than hiding it behind documentation.

The Linux tests deliberately demonstrate that the **same owner UID** can:

1. Save the full SQLite file before SPENT, let SPENT commit, restore the old file, then spend the **same fixture grant again**.
2. Delete a spent local fixture, recreate the **test-only** schema, and spend the same fixture grant again.
3. Corrupt the file, which refuses rather than implicitly recreating a grant.
4. On a *disposable CI root invocation only*, fork a **genuine distinct Linux PID** and drop the child to \`nobody\` with \`setgroups/setgid/setuid\`. The child cannot replace, delete or spend a root-private SQLite fixture. The parent checks the actual child effective UID and the unchanged grant.

A test showing that local fixture rollback allows a repeated **synthetic spend** is an *expected PASS of a negative vulnerability demonstration*, not a security property of production. The source still imports only \`TestOnlyC5Fence\` from \`tests/connections/timew/\`; all spend responses hard-deny \`production_authorized\`, \`native_action_allowed\`, \`production_revocation_ack\`, \`retry_allowed\`, \`undo_allowed\`, and return no safe actions. No C5 protected service, Unix socket, agent, signer, Polkit action, SwayPX command, TimeW consumer or shared code path is added.

## How to verify

From repository root on Linux:

\`\`\`sh
python3 -B -I tests/connections/timew/test_timew_c5_store_custody_attacks.py
\`\`\`

The cross-UID test skips without root. On **disposable GitHub runners only**, the dedicated workflow also uses:

\`\`\`sh
sudo -n python3 -B -I tests/connections/timew/test_timew_c5_store_custody_attacks.py
\`\`\`

**Do not run this as root on the user's workstation.** It is a throwaway CI filesystem permissions experiment, not a host installer or privilege enrollment. The CI job runs on temporary Ubuntu runners; it does not touch the operator's Fedora host.

## What this does not prove

- A root-private file is not an independently administered monotonic antirollback anchor. A root writer, disk restore, migration, writer downgrade, crash/forked head or compromised privileged service could still undo local history. Filesystem mode alone does **not** solve C5 custody.
- Correct Linux UID restrictions do not authenticate SwayPX's selected Wayland object, original producer, active unlocked seat or the operator's exact interactive approval.
- This test does not approve canonical fractional binary64 geometry serialization, SwayPX PENDING/CURRENT/settled source, signing format, revocation ACK or native resize/move receipts.
- The reference is intentionally not a general protected C5 issuer. It never issues consent, moves a window, permits a retry or attests a human click.

## Owner decisions and next integration gate

- DOC 5: independently custodied SPENT and revocation history with root/key release pinning, monotonic antirollback/current-head evidence and safe UNKNOWN reconciliation is still required. No custodian or installed UID/rule is selected by this test.
- DOC 1/DOC 2: actual C3e/C4b installed provenance/seat/current source trust is separate.
- TimeW/SwayPX: canonical fractional values, selected surface lifetime and native post-resize/terminal receipts require cross-owner version approval; preserve existing integer-only TimeW storage.
- Nurse 2/operator: exact-head review **before** any merge, and separate approvals for any future installed issuer, protected service, host change and native TimeW Restore.

**Recovery pointers:** [C5 owner REVISE decision #2163](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2163#issuecomment-7088761359), [TimeW #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067), [SwayPX #173](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/173), [cross-owner ledger #2119](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119).

**State:** CI only; no local machine mutation, key/service enrollment, UI integration, desktop activation, live Hospital registration or production permission.
