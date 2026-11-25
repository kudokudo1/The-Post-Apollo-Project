#!/usr/bin/bash
set -Eeuo pipefail
trap 'echo "CPU_MEM_POWERCUT_FAIL // wrapper line=$LINENO"' ERR
fixture=/usr/local/libexec/postapollo-memory-ci-powercut.py
/usr/bin/python3 -I -B "$fixture" guard
witness=/var/lib/postapollo-memory-native-powercut-witness.json
if [[ -e "$witness" || -L "$witness" ]]; then
    /usr/bin/python3 -I -B "$fixture" after-cut
    echo "CPU_MEM_POWERCUT_STAGE // REQUEST_GUEST_POWEROFF_REBOOT"
    /usr/bin/systemctl --no-block poweroff
else
    /usr/bin/bash /usr/local/libexec/postapollo-memory-ci-cycle.sh
    /usr/bin/python3 -I -B "$fixture" prepare
    echo "CPU_MEM_POWERCUT_FAIL // prepare unexpectedly returned"
    exit 2
fi
