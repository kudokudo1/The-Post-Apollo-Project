#!/usr/bin/bash
# Source-only compilation of a test SELinux domain. No VM or host policy
# changes. Output remains entirely inside the disposable Fedora container.
set -Eeuo pipefail
[[ "$GITHUB_ACTIONS" == true &&
   "$RUNNER_ENVIRONMENT" == github-hosted &&
   "$POST_APOLLO_ID_SILVERBLUE_CI_ONLY" == 1 &&
   "$(id -u)" == 0 ]] ||
  { echo "C4B_ID_BLOCKED // SELINUX_POLICY_BUILD_NOT_DISPOSABLE"; exit 2; }
source_file=/src/tests/connections/identity_silverblue/selinux/postapollo_identity_ci.te
[[ -f "$source_file" && ! -L "$source_file" ]] ||
  { echo "C4B_ID_BLOCKED // SELINUX_OWNED_POLICY_SOURCE_MISSING"; exit 2; }
grep -Fxq 'init_daemon_domain(postapollo_identity_ci_t, postapollo_identity_ci_exec_t)' "$source_file" ||
  { echo "C4B_ID_BLOCKED // UNIQUE_DAEMON_DOMAIN_MISSING"; exit 2; }
for banned in 'permissive postapollo_identity_ci_t' \
  'unconfined_domain(postapollo_identity_ci_t)' \
  'allow postapollo_identity_ci_t self:tcp_socket' \
  'allow postapollo_identity_ci_t self:udp_socket' \
  'allow postapollo_identity_ci_t domain:process'; do
  if grep -Fq "$banned" "$source_file"; then
    echo "C4B_ID_BLOCKED // BROAD_OR_NONLOCAL_SELINUX_PERMISSION"
    exit 2
  fi
done
dnf -y --setopt=install_weak_deps=False install \
  make selinux-policy-devel checkpolicy policycoreutils
work="$(mktemp -d /tmp/c4b-id-selinux-XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
install -m 0644 "$source_file" "$work/postapollo_identity_ci.te"
cd "$work"
make -f /usr/share/selinux/devel/Makefile postapollo_identity_ci.pp
[[ -s postapollo_identity_ci.pp ]] ||
  { echo "C4B_ID_BLOCKED // SELINUX_MODULE_NOT_BUILT"; exit 2; }
sha256sum postapollo_identity_ci.pp
echo "C4B_ID_SELINUX_PASS // FEDORA44_CUSTOM_DOMAIN_MODULE_COMPILED_UNLOADED"
echo "C4B_ID_SELINUX_LIMITATION // NO_KERNEL_POLICY_LOAD_OR_CONFINE_CLAIM"
