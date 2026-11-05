# C2o ONLY: built from a narrow, staged GitHub CI context, never deployed.
# Fedora 44 systemd and system-bus smoke. Linux host is an ephemeral runner.
FROM fedora:44
ENV container=docker

RUN dnf -y install \
      systemd dbus-daemon dbus-broker python3 python3-pip \
      shadow-utils util-linux procps-ng policycoreutils selinux-policy-targeted \
    && dnf clean all

RUN python3 -m venv /opt/postapollo-c2o-venv \
    && /opt/postapollo-c2o-venv/bin/python3 -m pip install --disable-pip-version-check "dbus-next==0.2.3"

RUN groupadd --system postapollo-connections \
    && groupadd --system postapollo-status-readers \
    && groupadd --system c2o-test-clients \
    && useradd --system --no-create-home --shell /usr/sbin/nologin \
        --gid postapollo-connections postapollo-connections \
    && useradd --system --no-create-home --shell /usr/sbin/nologin \
        --gid c2o-test-clients --groups postapollo-status-readers c2o-reader \
    && useradd --system --no-create-home --shell /usr/sbin/nologin \
        --gid c2o-test-clients c2o-outsider

COPY postapollo-connections-status.service.template \
    /usr/lib/systemd/system/postapollo-connections-status.service
COPY org.postapollo.ConnectionsStatus1.conf.template \
    /usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf
COPY FakeStatusHost.py /usr/libexec/post-apollo/connections-status-host
COPY BusPolicyClient.py /opt/c2o/BusPolicyClient.py
COPY test_inside.sh /opt/c2o/test_inside.sh

RUN chown root:root /usr/lib/systemd/system/postapollo-connections-status.service \
        /usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf \
        /usr/libexec/post-apollo/connections-status-host \
        /opt/c2o/BusPolicyClient.py /opt/c2o/test_inside.sh \
    && chmod 0644 /usr/lib/systemd/system/postapollo-connections-status.service \
        /usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf \
        /opt/c2o/BusPolicyClient.py /opt/c2o/test_inside.sh \
    && chmod 0555 /usr/libexec/post-apollo/connections-status-host \
    && chmod 0755 /opt/c2o \
    && chmod -R go-w /opt/postapollo-c2o-venv

STOPSIGNAL SIGRTMIN+3
CMD ["/usr/sbin/init"]
