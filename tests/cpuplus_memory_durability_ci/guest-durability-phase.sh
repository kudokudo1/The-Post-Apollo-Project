#!/usr/bin/bash
set -Eeuo pipefail
trap 'echo "CPU_MEM_DURABILITY_FAIL // wrapper line=$LINENO"' ERR
fixture=/usr/local/libexec/postapollo-memory-ci-durability.py
/usr/bin/python3 -I -B "$fixture" guard
witness=/var/lib/postapollo-memory-native-fault-witness.json
if [[ -e "$witness" || -L "$witness" ]]; then
    /usr/bin/python3 -I -B "$fixture" after-reboot
    echo "CPU_MEM_DURABILITY_STAGE // REQUEST_GUEST_POWEROFF_REBOOT"
else
    /usr/bin/bash /usr/local/libexec/postapollo-memory-ci-cycle.sh
    /usr/bin/python3 -I -B "$fixture" prepare
    echo "CPU_MEM_DURABILITY_STAGE // REQUEST_GUEST_POWEROFF_INITIAL"
fi
/usr/bin/systemctl --no-block poweroff
