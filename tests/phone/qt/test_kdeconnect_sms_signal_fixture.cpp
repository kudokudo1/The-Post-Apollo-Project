// SPDX-License-Identifier: MIT
// Disposable D-Bus test bus only; no real org.kde.kdeconnect service.
#include "../../../services/phone/qt/KdeConnectSmsSignalFixture.h"

#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusMetaType>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QJsonObject>
#include <QThread>
#include <QVariant>

#include <cstdio>
#include <cstdlib>
#include <functional>

using namespace PostApolloPhone;

namespace {
constexpr auto kService = "org.postapollo.phone.fixture";
constexpr auto kInterface = "org.kde.kdeconnect.device.conversations";
constexpr auto kDeviceA = "testphone0000001";
constexpr auto kDeviceB = "testphone0000002";
int checks = 0;

void require(bool condition, const char *label)
{
    ++checks;
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", label);
        std::exit(1);
    }
}

QString pathFor(const QString &device)
{
    return QStringLiteral("/modules/kdeconnect/devices/") + device;
}

SmsFields syntheticFields()
{
    SmsFields f;
    f.event = 1;
    f.body = QStringLiteral("fixture-message-only");
    f.addresses = {{QStringLiteral("test-address")}};
    f.date = 1762102000000LL;
    f.type = 1;
    f.read = 0;
    f.threadId = 9007199254740993LL;
    f.messageId = 11;
    f.subId = -1;
    return f;
}

void sendSignal(const QDBusConnection &bus, const QString &device,
                const QString &iface, const QString &signal,
                const QDBusVariant &payload)
{
    QDBusMessage message = QDBusMessage::createSignal(pathFor(device), iface, signal);
    message.setArguments({QVariant::fromValue(payload)});
    require(bus.send(message), "synthetic bus send succeeded");
}

bool until(const std::function<bool()> &condition, int milliseconds = 700)
{
    QElapsedTimer clock;
    clock.start();
    while (!condition() && clock.elapsed() < milliseconds) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 10);
        QThread::msleep(2);
    }
    return condition();
}

void pump(int milliseconds = 80)
{
    until([]{ return false; }, milliseconds);
}

void registerTypes()
{
    qDBusRegisterMetaType<SmsAddress>();
    qDBusRegisterMetaType<QList<SmsAddress>>();
    qDBusRegisterMetaType<SmsAttachment>();
    qDBusRegisterMetaType<QList<SmsAttachment>>();
    qDBusRegisterMetaType<SmsFields>();
}

void testFixtureSourceAndDeviceIsolation(QDBusConnection bus)
{
    KdeConnectSmsSignalFixture stream;
    require(!stream.start(bus, QString::fromLatin1(kDeviceA)),
            "cannot attach without fixture service owned by test process");
    require(!stream.start(bus, QStringLiteral("../bad")),
            "invalid device ID rejected");
    require(bus.registerService(QString::fromLatin1(kService)),
            "register isolated fixture service");
    require(!stream.start(bus, QStringLiteral("short")),
            "invalid short device ID rejected");
    require(stream.start(bus, QString::fromLatin1(kDeviceA)),
            "valid fixture source and device accepted");
    require(stream.active(), "stream started");
    require(!stream.start(bus, QString::fromLatin1(kDeviceB)),
            "cannot silently change device while already active");

    int decoded = 0;
    int rejected = 0;
    QJsonObject last;
    QString error;
    QObject::connect(&stream, &KdeConnectSmsSignalFixture::syntheticMessage,
                     &stream, [&](const QJsonObject &packet) {
                         ++decoded;
                         last = packet;
                     });
    QObject::connect(&stream, &KdeConnectSmsSignalFixture::rejected,
                     &stream, [&](const QString &code) {
                         ++rejected;
                         error = code;
                     });

    const QDBusVariant good(QVariant::fromValue(syntheticFields()));
    sendSignal(bus, QString::fromLatin1(kDeviceB), QString::fromLatin1(kInterface),
               QStringLiteral("conversationUpdated"), good);
    sendSignal(bus, QString::fromLatin1(kDeviceA), QStringLiteral("org.example.unrelated"),
               QStringLiteral("conversationUpdated"), good);
    sendSignal(bus, QString::fromLatin1(kDeviceA), QString::fromLatin1(kInterface),
               QStringLiteral("unrelatedEvent"), good);
    pump();
    require(decoded == 0 && rejected == 0,
            "device/interface/signal mismatch ignored");

    sendSignal(bus, QString::fromLatin1(kDeviceA), QString::fromLatin1(kInterface),
               QStringLiteral("conversationCreated"), good);
    require(until([&]{ return decoded == 1; }),
            "accepted synthetic conversationCreated signal");
    require(last.value(QStringLiteral("body")).toString() ==
            QStringLiteral("fixture-message-only"), "keeps synthetic decoded body");
    require(last.value(QStringLiteral("thread_id")).toString() ==
            QStringLiteral("9007199254740993"), "64-bit precision retained");

    sendSignal(bus, QString::fromLatin1(kDeviceA), QString::fromLatin1(kInterface),
               QStringLiteral("conversationUpdated"), good);
    require(until([&]{ return decoded == 2; }),
            "accepted synthetic conversationUpdated signal");

    const QDBusVariant invalid(QVariant::fromValue(QStringLiteral("bad-fixture-data")));
    sendSignal(bus, QString::fromLatin1(kDeviceA), QString::fromLatin1(kInterface),
               QStringLiteral("conversationUpdated"), invalid);
    require(until([&]{ return rejected == 1; }),
            "invalid variant rejected and not forwarded");
    require(error == QStringLiteral("INVALID_DBUS_VARIANT_TYPE"),
            "rejection has fixed code, not sensitive content");

    stream.stop();
    require(!stream.active(), "explicit stop deactivates stream");
    sendSignal(bus, QString::fromLatin1(kDeviceA), QString::fromLatin1(kInterface),
               QStringLiteral("conversationUpdated"), good);
    pump();
    require(decoded == 2, "stopped stream cannot emit further records");
    require(stream.start(bus, QString::fromLatin1(kDeviceB)),
            "explicit restart may select a different fixture device");
    sendSignal(bus, QString::fromLatin1(kDeviceA), QString::fromLatin1(kInterface),
               QStringLiteral("conversationUpdated"), good);
    pump();
    require(decoded == 2, "old device ignored following device switch");
    sendSignal(bus, QString::fromLatin1(kDeviceB), QString::fromLatin1(kInterface),
               QStringLiteral("conversationUpdated"), good);
    require(until([&]{ return decoded == 3; }),
            "new device works only after explicit reconnect");

    stream.stop();
    require(bus.unregisterService(QString::fromLatin1(kService)),
            "unregister test-only fixture service");
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    registerTypes();
    auto bus = QDBusConnection::sessionBus();
    require(bus.isConnected(), "disposable test session bus is connected");
    testFixtureSourceAndDeviceIsolation(bus);
    std::printf("PASS: %d synthetic stream fixture assertions\n", checks);
    return 0;
}
