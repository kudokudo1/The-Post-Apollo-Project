#!/usr/bin/bash
# P53 separate PHONE CI SELinux module, build only in Fedora container.
set -Eeuo pipefail
[[ "${GITHUB_ACTIONS:-}" == true &&
   "${RUNNER_ENVIRONMENT:-}" == github-hosted &&
   "${POST_APOLLO_PHONE_RPM_CI_ONLY:-}" == 1 &&
   "$(id -u)" == 0 && -d /out ]] ||
  { echo "P53_BLOCKED // NON_DISPOSABLE_POLICY_COMPILER"; exit 78; }
file=/src/tests/phone/p53_selinux/postapollo_phone_ci.te
[[ -f "$file" && ! -L "$file" ]] ||
  { echo "P53_BLOCKED // PHONE_POLICY_SOURCE_MISSING"; exit 78; }
grep -Fxq 'init_daemon_domain(postapollo_phone_ci_t, postapollo_phone_ci_exec_t)' "$file" ||
  { echo "P53_BLOCKED // PHONE_DOMAIN_DECLARATION_MISSING"; exit 78; }
for forbidden in \
  'permissive postapollo_phone_ci_t' \
  'unconfined_domain(postapollo_phone_ci_t)' \
  'allow postapollo_phone_ci_t self:tcp_socket' \
  'allow postapollo_phone_ci_t self:udp_socket' \
  'allow postapollo_phone_ci_t domain:process'; do
  ! grep -Fq "$forbidden" "$file" ||
    { echo "P53_BLOCKED // PHONE_BROAD_SELINUX_PERMISSION"; exit 78; }
done
[[ -z "$(find /out -mindepth 1 -maxdepth 1 -print -quit)" ]] ||
  { echo "P53_BLOCKED // NONEMPTY_POLICY_OUTPUT"; exit 78; }
dnf -y --setopt=install_weak_deps=False install \
  make selinux-policy-devel checkpolicy policycoreutils
work="$(mktemp -d /tmp/p53-phone-policy-XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
install -m 0644 "$file" "$work/postapollo_phone_ci.te"
cd "$work"
make -f /usr/share/selinux/devel/Makefile postapollo_phone_ci.pp
[[ -s postapollo_phone_ci.pp ]] ||
  { echo "P53_BLOCKED // POLICY_NOT_COMPILED"; exit 78; }
install -m 0644 postapollo_phone_ci.pp /out/postapollo_phone_ci.pp
(cd /out && sha256sum postapollo_phone_ci.pp > postapollo_phone_ci.sha256)
chmod 0644 /out/postapollo_phone_ci.sha256
echo "P53_PASS // DISTINCT_PHONE_SELINUX_POLICY_COMPILED_FOR_OFFLINE_GUEST"
echo "P53_LIMITATION // POLICY_NOT_LOADED_OUTSIDE_DISPOSABLE_VM"
