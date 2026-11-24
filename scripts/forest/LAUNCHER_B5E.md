# Forest Core B5e // Installed disposable launcher and FD exclusion

PATIENT: The-Post-Apollo-Project  
ROOM: Forest Core original host / launcher  
STAFF: Forest backend DOC, external Hospital-compatible  
STATE: CI-only candidate; PRODUCTION HOLD.

B5d #2394 is merged 82e874e7 with 51/51 focused tests and five successful
workflows. Its inherited-descriptor test demonstrates that pathname DAC
does not prevent access via a descriptor already opened by another process.
B5b/B5c/B5d independent reviews remain outstanding when this is prepared.
DOC2's disposition on #2161 accepts only development mechanics.

## IMPLEMENTATION

disposable_launcher_b5e.py creates a fresh unnamed Unix SEQPACKET pair and
launches the exact B5c RPM-installed deny-only B5b candidate at
/usr/libexec/post-apollo/forest-ci/forest-host using /usr/bin/python3 -I -B.
The parent does not take external executable/argv, UID, environment, file
paths or descriptor inputs. It passes only the internally created child
socket via pass_fds and close_fds, redirects all standard streams to
/dev/null, uses fixed minimal environment, cwd / and umask 077. It closes
the parent copy of the child endpoint and closes/reaps the child at context
exit, including exceptional exit or bounded termination after timeout.
A failed spawn closes both endpoints. No retry, no terminal receipt.

The launcher refuses root and requires disposable Linux CI context.
Those checks prevent common accidental invocation, not malicious execution
or independent enrollment. No service, package change, deployment or new
production root. B5b remains the actual egress point; its public HOLD
frame is the only possible packet from the candidate.

## VERIFY

Separate Fedora builder and verifier containers reuse the unmodified B5c
package build. Verify exact installed bytes, roster, permissions and RPM
ownership/integrity, run real launcher as nobody, and erase package.
Tests inspect actual child PID/argv/FD inode and /proc environment, prove
exclusion of deliberately inheritable high-numbered file, pipe, socket
and memfd descriptors while parent copies survive, check private-operation
denial, no external launch arguments, missing CI guard, exit/exception
cleanup, second-send refusal and spawn-failure cleanup. Inherited B5a/B5b
regressions remain separate. Exact-head CI and independent review required.

## WATCH OUT FOR

This is a same-UID disposable installed candidate. It is NOT a protected
launcher, native peer authenticator, filesystem/SELinux sandbox, verified
release, independent seat/recipient evidence, or process/descriptor custody
against malicious same-UID/root code. It does not prevent another process
from passing descriptors after launch, prove all future descriptors are
authorized, or establish a protected revoke fence. B5b rejects ancillary
rights in its one request; actual production broker must independently
authenticate each source and recipient. No private DB or model is wired.
The production launcher, runtime identity, protected opener, storage keys
and C5 issuer remain owner/operator decisions.

## NEXT

Independent Forest Nurse 2 review; DOC1/2 operator-accepted original-source
and runtime/storage custody, DOC3 separate grants and revoke/send ordering.
No local installation or activation. Forest production HOLD.
