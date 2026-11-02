// SPDX-License-Identifier: MIT
#include "KdeConnectSmsDbusDecoder.h"

#include <QDBusArgument>
#include <QDBusMetaType>
#include <QJsonArray>
#include <QJsonValue>

namespace PostApolloPhone {
namespace {

// KDE Connect models/conversationmessage.h serializes:
// (i s a(s) x i i x i x a(x s s s))
// This signature is for the message structure itself, excluding the
// enclosing QDBusVariant on the conversationUpdated/Created signals.
constexpr auto kKdeMessageSignature = "(isa(s)xiixixa(xsss))";

SmsDecodeResult failure(const QString &reason)
{
    return {false, reason, QJsonObject()};
}

void registerNestedTypes()
{
    static const bool registered = []() {
        qDBusRegisterMetaType<SmsAddress>();
        qDBusRegisterMetaType<QList<SmsAddress>>();
        qDBusRegisterMetaType<SmsAttachment>();
        qDBusRegisterMetaType<QList<SmsAttachment>>();
        return true;
    }();
    Q_UNUSED(registered);
}

} // namespace

QDBusArgument &operator<<(QDBusArgument &arg, const SmsAddress &v)
{
    arg.beginStructure();
    arg << v.value;
    arg.endStructure();
    return arg;
}

const QDBusArgument &operator>>(const QDBusArgument &arg, SmsAddress &v)
{
    arg.beginStructure();
    arg >> v.value;
    arg.endStructure();
    return arg;
}

QDBusArgument &operator<<(QDBusArgument &arg, const SmsAttachment &v)
{
    arg.beginStructure();
    arg << v.partId << v.mimeType << v.encodedFile << v.identifier;
    arg.endStructure();
    return arg;
}

const QDBusArgument &operator>>(const QDBusArgument &arg, SmsAttachment &v)
{
    arg.beginStructure();
    arg >> v.partId >> v.mimeType >> v.encodedFile >> v.identifier;
    arg.endStructure();
    return arg;
}

SmsDecodeResult decodeFields(const SmsFields &fields)
{
    // Fail closed and mirror the *text-only* subset of
    // KdeConnectSmsNormalize.py. Never fabricate unavailable fields.
    if (fields.event != 1 && fields.event != 3)
        return failure(QStringLiteral("UNSUPPORTED_EVENT"));
    if (fields.type < 1 || fields.type > 6)
        return failure(QStringLiteral("UNSUPPORTED_MESSAGE_TYPE"));
    if (fields.read != 0 && fields.read != 1)
        return failure(QStringLiteral("INVALID_READ_FLAG"));
    if (fields.date <= 0 || fields.threadId <= 0 || fields.messageId <= 0)
        return failure(QStringLiteral("INVALID_NATIVE_ID_OR_TIMESTAMP"));
    if (fields.body.isEmpty() || fields.body.size() > 16384)
        return failure(QStringLiteral("UNSUPPORTED_TEXT_BODY"));
    if (fields.addresses.isEmpty() || fields.addresses.size() > 24)
        return failure(QStringLiteral("INVALID_PARTICIPANT_COUNT"));
    if ((fields.event == 1 && fields.addresses.size() != 1)
        || (fields.event == 3 && fields.addresses.size() < 2))
        return failure(QStringLiteral("INVALID_GROUP_FLAG"));
    if (fields.attachments.size() > 12)
        return failure(QStringLiteral("TOO_MANY_ATTACHMENTS"));

    QJsonArray addresses;
    for (const auto &address : fields.addresses) {
        if (address.value.isEmpty() || address.value.size() > 254)
            return failure(QStringLiteral("INVALID_PARTICIPANT"));
        addresses.append(QJsonObject{{QStringLiteral("address"), address.value}});
    }
    QJsonArray attachments;
    for (const auto &attachment : fields.attachments) {
        // Presence only. Drop base64 thumbnail, identifier and MIME details
        // rather than carrying them into Social's text-only UI record.
        Q_UNUSED(attachment);
        attachments.append(QJsonObject());
    }

    // JSON doubles lose precision for qint64s. Encode native x/int64 fields
    // as decimal strings to preserve exact IDs and Unix millisecond values.
    QJsonObject packet{
        {QStringLiteral("event"), fields.event},
        {QStringLiteral("body"), fields.body},
        {QStringLiteral("addresses"), addresses},
        {QStringLiteral("date"), QString::number(fields.date)},
        {QStringLiteral("type"), fields.type},
        {QStringLiteral("read"), fields.read != 0},
        {QStringLiteral("thread_id"), QString::number(fields.threadId)},
        {QStringLiteral("_id"), fields.messageId},
        {QStringLiteral("sub_id"), QString::number(fields.subId)},
        {QStringLiteral("attachments"), attachments},
    };
    return {true, QStringLiteral("DECODED_ONLY"), packet};
}

SmsDecodeResult decodeVariant(const QDBusVariant &variant)
{
    registerNestedTypes();
    const QVariant value = variant.variant();
    if (value.metaType() != QMetaType::fromType<QDBusArgument>())
        return failure(QStringLiteral("INVALID_DBUS_VARIANT_TYPE"));
    QDBusArgument argument = value.value<QDBusArgument>();
    if (argument.currentSignature() != QLatin1String(kKdeMessageSignature))
        return failure(QStringLiteral("UNEXPECTED_DBUS_SIGNATURE"));

    SmsFields fields;
    argument.beginStructure();
    argument >> fields.event >> fields.body >> fields.addresses >> fields.date
             >> fields.type >> fields.read >> fields.threadId >> fields.messageId
             >> fields.subId >> fields.attachments;
    argument.endStructure();
    return decodeFields(fields);
}

} // namespace PostApolloPhone
