#!/usr/bin/bash
set -Eeuo pipefail
trap 'echo "CPU_MEM_SIGNALCUSTODY_FAIL // wrapper line=$LINENO"' ERR
fixture=/usr/local/libexec/postapollo-memory-ci-signalcustody.py
/usr/bin/python3 -I -B "$fixture" guard
/usr/bin/python3 -I -B "$fixture" run
echo "CPU_MEM_SIGNALCUSTODY_STAGE // REQUEST_GUEST_POWEROFF"
/usr/bin/systemctl --no-block poweroff
