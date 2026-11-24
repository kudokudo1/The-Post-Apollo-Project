# Forest Core B5b // Disposable native process and outgoing FD

PATIENT: The-Post-Apollo-Project  
ROOM: Forest original-host staging, B5a -> B5b  
ROLE: Forest backend DOC; external Hospital-compatible, live registration unverified  
STATE: CI-only native mechanics; production HOLD.

## IMPLEMENTATION

B5a #2373 / corrective #2377 scoped reviews are complete. DOC1 RFC
#2388 and DOC3 #2385 are merged, but no installed Forest-purpose
authority or private-title policy is accepted. B5b creates an actual
Linux child process in disposable tests, with a candidate source path:

    scripts/forest/native_host_candidate_b5b.py

The test harness creates an unnamed AF_UNIX SOCK_SEQPACKET pair and
starts Python with one inherited FD. It closes its copy of that child
endpoint and checks the actual child PID and /proc/PID/fd/FD socket
inode before requesting a response. This is observed local test
ownership, NOT installed release/peer/seat/original-source attestation.
The peer can be inherited, duplicated, or replaced by another same-UID
actor; this is not an enrolled source. No new daemon, listener, bind,
connect, service unit, file path, credential or package is installed.

The candidate reads one bounded packet (128 bytes maximum), rejects
malformed/truncated/ancillary input, and closes received SCM_RIGHTS
descriptors before any early refusal, including empty packets. It
accepts only exact fixed test tokens. The single actual outbound
submission point is _submit_public_hold_once(channel), which sends
a constant public status packet, always UNKNOWN_HOLD, zero private
bytes and false authority/revocation ACK fields. There is no generic
text-send function, private SQLite access, B3 stream, model request,
or trusted UI envelope. One synchronous exchange, no response retry,
no second submission; STOP, malformed input and disconnect close the
channel. Timeout is bounded. No protected revocation ACK is produced.

## HOW TO USE

Run only disposable CI/unit tests from repository root:

    python3 -B -m unittest discover -s tests/forest -p 'test_native_host_candidate_b5b.py' -v

Do not use this candidate as an installed Forest host, give it a
production socket or wire it to ForestW. Its control tokens are not
an accepted native protocol.

## VERIFY

Native CI observes a real subprocess and socket inode, actual kernel
packet delivery, exactly one fixed public output, deny-only operation
tokens, stop, no second send, malformed/oversize/empty requests,
disconnect/timeout, wrong socket type, ancillary rights cleanup
including truncation and empty payloads. B5a/B1/B3/B4a/ForestW regressions
run separately. No inference or private data.

## WATCH OUT FOR

This names a candidate source and actual CI egress point, not an
operator-approved installed host, PID, release or service. An inherited
FD and /proc observation do not provide C3e/C4b enrollment. A successful
send reports local kernel submission, not recipient display or receipt.
STOP is just a single-exchange test input, not protected C5 revocation.
There is no independent revocation/lease coordinator or in-flight
protected send; previously delivered bytes cannot be recalled.
The private DB opener/owner is still unimplemented. B5a's disposable
memory registry is not protected custody and must not be reused as such.

## NEXT / DECISIONS

- Forest Core: propose this candidate's on-demand process architecture,
  actual installed release/lifecycle, privately protected DB ownership
  and recipient FD custody for explicit operator review.
- DOC1/DOC2: Forest-purpose independent enrollment, currentness, original
  process and channel evidence; no Identity-root reuse.
- DOC3: distinct LIST/title and provisional-disclosure permissions,
  independently serialized revocation and terminal settlement; no
  fixture tokens or fixed HOLD responses as authorization.
- ForestW: keep private title read, SEND/voice locked. No wire acceptance.
- Nurse 2: exact-head scoped native-mechanics review, operator merge
  and eventual deployment acceptance separately.

Production Forest, protected data, inference and private text HOLD.
