// SPDX-License-Identifier: MIT
#include "KdeConnectSmsSignalFixture.h"

#include <QDBusConnectionInterface>
#include <QRegularExpression>

namespace PostApolloPhone {
namespace {
const QString kFixtureBusName = QStringLiteral("org.postapollo.phone.fixture");
const QString kSignalInterface = QStringLiteral("org.kde.kdeconnect.device.conversations");
const QString kCreated = QStringLiteral("conversationCreated");
const QString kUpdated = QStringLiteral("conversationUpdated");

QString checkedPath(const QString &deviceId)
{
    // Match the existing KDE metadata probe's opaque device-ID constraints.
    static const QRegularExpression id(QStringLiteral("^[A-Za-z0-9_]{8,80}$"));
    if (!id.match(deviceId).hasMatch())
        return {};
    return QStringLiteral("/modules/kdeconnect/devices/") + deviceId;
}
} // namespace

KdeConnectSmsSignalFixture::KdeConnectSmsSignalFixture(QObject *parent)
    : QObject(parent)
{
}

KdeConnectSmsSignalFixture::~KdeConnectSmsSignalFixture()
{
    stop();
}

bool KdeConnectSmsSignalFixture::start(const QDBusConnection &bus,
                                       const QString &fixtureDeviceId)
{
    // Fail closed on reactivation. Never silently change source/device.
    if (m_active || !bus.isConnected())
        return false;
    const QString path = checkedPath(fixtureDeviceId);
    if (path.isEmpty() || !bus.interface())
        return false;

    // A different process cannot use this as a proxy to inspect a real KDE
    // Connect service. Test sender must be owned by this test process.
    const auto owner = bus.interface()->serviceOwner(kFixtureBusName);
    if (!owner.isValid() || owner.value() != bus.baseService())
        return false;

    if (!bus.connect(kFixtureBusName, path, kSignalInterface, kCreated,
                     this, SLOT(receive(QDBusVariant))))
        return false;
    if (!bus.connect(kFixtureBusName, path, kSignalInterface, kUpdated,
                     this, SLOT(receive(QDBusVariant)))) {
        bus.disconnect(kFixtureBusName, path, kSignalInterface, kCreated,
                       this, SLOT(receive(QDBusVariant)));
        return false;
    }

    m_bus = bus;
    m_path = path;
    m_active = true;
    return true;
}

void KdeConnectSmsSignalFixture::stop()
{
    m_active = false;
    if (m_bus.has_value()) {
        m_bus->disconnect(kFixtureBusName, m_path, kSignalInterface, kCreated,
                          this, SLOT(receive(QDBusVariant)));
        m_bus->disconnect(kFixtureBusName, m_path, kSignalInterface, kUpdated,
                          this, SLOT(receive(QDBusVariant)));
    }
    m_path.clear();
    m_bus.reset();
}

void KdeConnectSmsSignalFixture::receive(const QDBusVariant &message)
{
    if (!m_active)
        return;
    const auto decoded = decodeVariant(message);
    if (!decoded.ok) {
        // Fixed error codes, never D-Bus text or private content.
        Q_EMIT rejected(decoded.reason);
        return;
    }
    // This signal carries synthetic payloads ONLY. No storage or logs.
    Q_EMIT syntheticMessage(decoded.packet);
}
} // namespace PostApolloPhone
