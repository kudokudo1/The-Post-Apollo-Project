// SPDX-License-Identifier: MIT
// Isolated, in-memory KDE Connect SMS D-Bus data decoding. No bus access.
#pragma once

#include <QDBusVariant>
#include <QJsonObject>
#include <QList>
#include <QString>
#include <QtGlobal>

namespace PostApolloPhone {

struct SmsAddress {
    QString value;
};

struct SmsAttachment {
    qint64 partId = 0;
    QString mimeType;
    QString encodedFile;
    QString identifier;
};

// Mirrors KDE Connect models/conversationmessage.h's DBus field ordering.
struct SmsFields {
    qint32 event = 0;
    QString body;
    QList<SmsAddress> addresses;
    qint64 date = 0;
    qint32 type = 0;
    qint32 read = 0;
    qint64 threadId = 0;
    qint32 messageId = 0;
    qint64 subId = -1;
    QList<SmsAttachment> attachments;
};

struct SmsDecodeResult {
    bool ok = false;
    QString reason;     // fixed code only; never expose private data
    QJsonObject packet; // sensitive decoded content, for an authorized caller only
};

// Qt D-Bus stream operators for KDE's two nested structure shapes.
QDBusArgument &operator<<(QDBusArgument &arg, const SmsAddress &v);
const QDBusArgument &operator>>(const QDBusArgument &arg, SmsAddress &v);
QDBusArgument &operator<<(QDBusArgument &arg, const SmsAttachment &v);
const QDBusArgument &operator>>(const QDBusArgument &arg, SmsAttachment &v);

SmsDecodeResult decodeFields(const SmsFields &fields);
SmsDecodeResult decodeVariant(const QDBusVariant &variant);

} // namespace PostApolloPhone

Q_DECLARE_METATYPE(PostApolloPhone::SmsAddress)
Q_DECLARE_METATYPE(PostApolloPhone::SmsAttachment)
Q_DECLARE_METATYPE(QList<PostApolloPhone::SmsAddress>)
Q_DECLARE_METATYPE(QList<PostApolloPhone::SmsAttachment>)
