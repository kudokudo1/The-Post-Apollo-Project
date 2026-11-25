#!/usr/bin/bash
set -Eeuo pipefail
trap 'echo "CPU_MEM_TRACECAP_FAIL // wrapper line=$LINENO"' ERR
fixture=/usr/local/libexec/postapollo-memory-ci-tracecap.py
/usr/bin/python3 -I -B "$fixture" guard
/usr/bin/python3 -I -B "$fixture" run
echo "CPU_MEM_TRACECAP_STAGE // REQUEST_GUEST_POWEROFF"
/usr/bin/systemctl --no-block poweroff
