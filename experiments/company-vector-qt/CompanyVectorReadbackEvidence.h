#pragma once

// Company M30v // read-only diagnostic of *Qt CPU readback image* layout.
//
// QQuickWindow::grabWindow() returns a QImage owned by Qt. Its format and
// bytesPerLine are REAL for THAT QImage, but do NOT attest the format,
// modifier, stride, allocation, scale or identity of a compositor wl_buffer.
// Those unknowns MUST be collected independently by SwayPX's selected-host
// owner, using the true compositor/native-surface lineage.
//
// There is no IO, IPC, window control, allocation, renderer activation,
// Company-record access, location lookup or production authority here.
#include <QImage>
#include <QJsonObject>
#include <QJsonValue>
#include <QSize>
#include <QString>
#include <QtGlobal>
#include <cmath>

namespace CompanyVectorReadbackEvidence {

inline QJsonObject base() {
    return QJsonObject{
        {"schema", QStringLiteral("post-apollo.company.qt-readback-evidence.m30v.v1")},
        {"status", QStringLiteral("REFUSED")},
        {"scope", QStringLiteral("QT_CPU_READBACK_ONLY")},
        {"source", QStringLiteral("QQuickWindow::grabWindow")},
        {"productionAuthority", false},
        {"selectedNativeActorVerified", false},
        {"waylandBufferAttested", false},
        {"nativeBufferFormat", QJsonValue(QJsonValue::Null)},
        {"nativeBufferStrideBytes", QJsonValue(QJsonValue::Null)},
        {"nativeBufferModifier", QJsonValue(QJsonValue::Null)},
        {"nativeBufferAllocationKind", QJsonValue(QJsonValue::Null)},
        {"nativeSurfaceScale", QJsonValue(QJsonValue::Null)}
    };
}

inline QJsonObject refused(const QString &reason) {
    auto result = base();
    result.insert(QStringLiteral("reason"), reason);
    return result;
}

// Outputs only the already-created image's dimensions/format/byte pitch;
// it never inspects or exposes image pixels. Bounds prevent overflowing
// the metadata calculation, and source/window scale is OBSERVED not inferred.
inline QJsonObject inspect(const QImage &image,
                           const QSize &windowLogicalSize,
                           double windowDevicePixelRatio) {
    constexpr int maxWidth = 8192;
    constexpr int maxHeight = 8192;
    constexpr int maxDepthBits = 128;
    constexpr int maxStrideBytes = maxWidth * (maxDepthBits / 8);

    if (image.isNull())
        return refused(QStringLiteral("NO_QT_READBACK_IMAGE"));
    if (image.width() <= 0 || image.height() <= 0 ||
            image.width() > maxWidth || image.height() > maxHeight ||
            windowLogicalSize.width() <= 0 ||
            windowLogicalSize.height() <= 0 ||
            windowLogicalSize.width() > maxWidth ||
            windowLogicalSize.height() > maxHeight ||
            !std::isfinite(windowDevicePixelRatio) ||
            windowDevicePixelRatio <= 0.0 ||
            windowDevicePixelRatio > 16.0 ||
            !std::isfinite(image.devicePixelRatio()) ||
            image.devicePixelRatio() <= 0.0 ||
            image.devicePixelRatio() > 16.0)
        return refused(QStringLiteral("INVALID_OR_UNBOUNDED_READBACK_GEOMETRY"));

    const int depth = image.depth();
    const auto actualStride = image.bytesPerLine();
    if (depth <= 0 || depth > maxDepthBits ||
            actualStride <= 0 || actualStride > maxStrideBytes)
        return refused(QStringLiteral("UNSUPPORTED_CPU_READBACK_LAYOUT"));

    // This minimum is a bit-depth arithmetic sanity bound, not a guessed
    // DRM/Wayland pitch. The actual CPU pitch is image.bytesPerLine().
    const qint64 minimumStride =
        (qint64(image.width()) * qint64(depth) + 7) / 8;
    if (actualStride < minimumStride)
        return refused(QStringLiteral("INCONSISTENT_CPU_READBACK_STRIDE"));

    auto result = base();
    result.insert(QStringLiteral("status"), QStringLiteral("OBSERVED_QT_READBACK"));
    result.insert(QStringLiteral("readbackWidth"), image.width());
    result.insert(QStringLiteral("readbackHeight"), image.height());
    result.insert(QStringLiteral("readbackFormatEnum"), int(image.format()));
    result.insert(QStringLiteral("readbackDepthBits"), depth);
    result.insert(QStringLiteral("readbackBytesPerLine"), int(actualStride));
    result.insert(QStringLiteral("readbackMinimumStrideBytes"), int(minimumStride));
    result.insert(QStringLiteral("readbackRowPaddingBytes"),
                  int(actualStride-minimumStride));
    result.insert(QStringLiteral("readbackDevicePixelRatio"),
                  image.devicePixelRatio());
    result.insert(QStringLiteral("logicalWindowWidth"), windowLogicalSize.width());
    result.insert(QStringLiteral("logicalWindowHeight"), windowLogicalSize.height());
    result.insert(QStringLiteral("windowDevicePixelRatio"),
                  windowDevicePixelRatio);
    result.insert(QStringLiteral("readyForNativeBufferImport"), false);
    result.insert(QStringLiteral("requiresIndependentHostBufferEvidence"), true);
    return result;
}
} // namespace CompanyVectorReadbackEvidence
