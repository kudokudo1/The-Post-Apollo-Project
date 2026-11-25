#!/usr/bin/bash
set -Eeuo pipefail
trap 'echo "CPU_MEM_INTERFERENCE_FAIL // wrapper line=$LINENO"' ERR
fixture=/usr/local/libexec/postapollo-memory-ci-interference.py
/usr/bin/python3 -I -B "$fixture" guard
/usr/bin/bash /usr/local/libexec/postapollo-memory-ci-cycle.sh
/usr/bin/python3 -I -B "$fixture" run
echo "CPU_MEM_INTERFERENCE_STAGE // REQUEST_GUEST_POWEROFF"
/usr/bin/systemctl --no-block poweroff
