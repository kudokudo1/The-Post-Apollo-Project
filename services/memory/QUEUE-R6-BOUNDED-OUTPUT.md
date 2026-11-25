# R6l // Bounded upstream output

The existing Linux custody supervisor now captures the exact child stdout
and stderr through private pipes. It reads fixed 4096-byte chunks, holds
at most one bounded incomplete frame, and forwards only complete printable
ASCII LF-terminated frames (maximum 16384 bytes including LF, the existing
wire limit). No raw child stderr reaches the shell. Nonempty stderr,
invalid byte, empty/oversized/truncated frame, output flood or deadline
failure terminates custody; the exact child is killed and reaped. The
checkpoint helper must produce exactly one frame and exit normally.
The adapter and canonical host retain all semantic/receipt gates.

Development transport policy: 3s incomplete frame/write deadline, 2s
post-exit pipe drain, 256KiB/one-second output budget and 16MiB per child
session. Budget exhaustion fails closed, never reconnects automatically.
The lifetime limit bounds total forwarded data but does not prove total
Quickshell allocation or eliminate downstream queueing; policy needs
operator review before installation. No protected operations, UI edits
or production launcher/mount. The previous native wrapper trials now
traverse the bounded supervisor. Direct Linux tests cover boundary,
oversize, truncated, partial, control byte, stderr, flood and helper
reply cardinality. Fresh CI and independent review required.
