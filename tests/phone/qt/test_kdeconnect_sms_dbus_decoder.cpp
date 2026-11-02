// SPDX-License-Identifier: MIT
// Synthetic native Qt D-Bus message decoder tests. Never connect to a bus.
#include "../../../services/phone/qt/KdeConnectSmsDbusDecoder.h"

#include <QCoreApplication>
#include <QDBusArgument>
#include <QJsonArray>
#include <QVariant>

#include <cstdio>
#include <cstdlib>
#include <limits>

using namespace PostApolloPhone;

namespace {
int checks = 0;
void check(bool condition, const char *why)
{
    ++checks;
    if (!condition) {
        std::fprintf(stderr, "FAILED: %s\n", why);
        std::exit(1);
    }
}
SmsFields sample()
{
    SmsFields fields;
    fields.event = 1;
    fields.body = QStringLiteral("synthetic-hello");
    fields.addresses = {{QStringLiteral("fixture-recipient")}};
    fields.date = 1762102000000LL;
    fields.type = 1;
    fields.read = 1;
    fields.threadId = 9007199254740993LL; // above JS integer precision
    fields.messageId = 71;
    fields.subId = -1;
    return fields;
}

void testFieldMapping()
{
    const auto f = sample();
    const auto r = decodeFields(f);
    check(r.ok && r.reason == QStringLiteral("DECODED_ONLY"), "decode valid message");
    check(r.packet.value(QStringLiteral("body")).toString() == QStringLiteral("synthetic-hello"),
          "preserve authorized body in memory");
    check(r.packet.value(QStringLiteral("date")).toString() == QStringLiteral("1762102000000"),
          "exact unix milliseconds");
    check(r.packet.value(QStringLiteral("thread_id")).toString() == QStringLiteral("9007199254740993"),
          "lossless qint64 thread ID");
    check(r.packet.value(QStringLiteral("_id")).toInt() == 71, "native message ID");
    check(r.packet.value(QStringLiteral("read")).toBool(), "native read flag");
    check(r.packet.value(QStringLiteral("addresses")).toArray().size() == 1,
          "address shape for existing Python packet normalizer");
    check(r.packet.value(QStringLiteral("sub_id")).toString() == QStringLiteral("-1"),
          "sub_id represented without deriving any authenticated phone line");
}

void testNativeStates()
{
    for (qint32 native = 1; native <= 6; ++native) {
        auto f = sample();
        f.type = native;
        check(decodeFields(f).ok, "accept known Android SMS states");
    }
    auto f = sample();
    f.type = 7;
    check(!decodeFields(f).ok, "unknown Android SMS state rejected");
}

void testStrictFlags()
{
    auto f = sample();
    f.event = 2;
    check(!decodeFields(f).ok, "attachment-only event not fabricated as text");
    f = sample();
    f.event = 3;
    check(!decodeFields(f).ok, "group event needs multiple addresses");
    f.addresses.append({QStringLiteral("fixture-second")});
    check(decodeFields(f).ok, "group event accepts two addresses");
    f = sample();
    f.read = 2;
    check(!decodeFields(f).ok, "invalid read flag rejected");
}

void testPrivateAttachmentsDropped()
{
    auto f = sample();
    f.attachments = {{
        1, QStringLiteral("image/png"),
        QStringLiteral("secret-base64-thumbnail"),
        QStringLiteral("sensitive-attachment-identifier")
    }};
    auto r = decodeFields(f);
    check(r.ok, "has attachment metadata");
    check(r.packet.value(QStringLiteral("attachments")).toArray().size() == 1,
          "retains attachment presence");
    check(!r.packet.contains(QStringLiteral("encodedFile")), "no encoded data field");
    const QString serialized = QString::fromUtf8(QJsonDocument(r.packet).toJson());
    check(!serialized.contains(QStringLiteral("secret-base64")), "no base64 thumbnail");
    check(!serialized.contains(QStringLiteral("sensitive-attachment")), "no attachment ID");
}

void testRejectInvalidAndOversized()
{
    auto f = sample();
    f.date = 0;
    check(!decodeFields(f).ok, "invalid date");
    f = sample();
    f.threadId = 0;
    check(!decodeFields(f).ok, "invalid thread ID");
    f = sample();
    f.messageId = -1;
    check(!decodeFields(f).ok, "negative message ID");
    f = sample();
    f.body.clear();
    check(!decodeFields(f).ok, "empty body");
    f = sample();
    f.body = QString(16385, QChar::fromLatin1('x'));
    check(!decodeFields(f).ok, "oversized body");
    f = sample();
    f.addresses.clear();
    check(!decodeFields(f).ok, "missing participant");
    f = sample();
    f.addresses[0].value.clear();
    check(!decodeFields(f).ok, "empty participant");
    f = sample();
    f.attachments = QList<SmsAttachment>(13);
    check(!decodeFields(f).ok, "excessive attachment count");
}

void testDbusVariantTypeGate()
{
    QDBusVariant wrong(QVariant(QStringLiteral("not-a-DBus-structure")));
    const auto r = decodeVariant(wrong);
    check(!r.ok, "reject non-DBus variant");
    check(r.reason == QStringLiteral("INVALID_DBUS_VARIANT_TYPE"),
          "stable private-data-free failure reason");
    check(r.packet.isEmpty(), "no data on type error");
}

void testExactDbusStructureRoundTrip()
{
    // Build the identical 10-field structure described by KDE Connect.
    // This is a local Qt marshalling fixture, not a D-Bus connection.
    auto f = sample();
    QDBusArgument arg;
    arg.beginStructure();
    arg << f.event << f.body << f.addresses << f.date << f.type << f.read
        << f.threadId << f.messageId << f.subId << f.attachments;
    arg.endStructure();
    const auto r = decodeVariant(QDBusVariant(QVariant::fromValue(arg)));
    check(r.ok, "QDBusArgument structure successfully decoded");
    check(r.packet.value(QStringLiteral("body")).toString() == f.body,
          "QDBusVariant text survived native structure");
    check(r.packet.value(QStringLiteral("thread_id")).toString()
          == QStringLiteral("9007199254740993"),
          "native Qt D-Bus qint64 exactness");
}
} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    testFieldMapping();
    testNativeStates();
    testStrictFlags();
    testPrivateAttachmentsDropped();
    testRejectInvalidAndOversized();
    testDbusVariantTypeGate();
    testExactDbusStructureRoundTrip();
    std::printf("PASS: %d synthetic Qt decoder assertions\n", checks);
    return 0;
}
