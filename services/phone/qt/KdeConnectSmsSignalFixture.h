// SPDX-License-Identifier: MIT
// Synthetic-only KDE Connect conversation signal receiver.
// Hardwired to org.postapollo.phone.fixture, NEVER to live org.kde.kdeconnect.
#pragma once

#include "KdeConnectSmsDbusDecoder.h"

#include <QDBusConnection>
#include <QJsonObject>
#include <QObject>
#include <QString>

#include <optional>

namespace PostApolloPhone {

class KdeConnectSmsSignalFixture final : public QObject
{
    Q_OBJECT
public:
    explicit KdeConnectSmsSignalFixture(QObject *parent = nullptr);
    ~KdeConnectSmsSignalFixture() override;

    // Requires a supplied test bus on which THIS process owns the isolated
    // synthetic service. Does not discover phones or connect to KDE Connect.
    bool start(QDBusConnection bus, const QString &fixtureDeviceId);
    void stop();
    bool active() const { return m_active; }

Q_SIGNALS:
    // Sensitive test content. Production UI must require a trusted broker.
    void syntheticMessage(const QJsonObject &packet);
    void rejected(const QString &fixedCode);

private Q_SLOTS:
    void receive(const QDBusVariant &message);

private:
    std::optional<QDBusConnection> m_bus;
    QString m_path;
    bool m_active = false;
};

} // namespace PostApolloPhone
