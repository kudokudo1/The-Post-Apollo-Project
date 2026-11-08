// Company M30v // real QImage metadata tests, no QPA, MapLibre, sockets or
// owner state. The experiment is ONLY a CPU readback format/pitch witness.
#include "../../../experiments/company-vector-qt/CompanyVectorReadbackEvidence.h"
#include <QImage>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSize>
#include <QString>
#include <iostream>
#include <cstdlib>

using CompanyVectorReadbackEvidence::inspect;

static void require(bool condition, const char *reason) {
    if (!condition) {
        std::cerr << "M30V_TEST_FAILED " << reason << '\n';
        std::exit(1);
    }
}

static void neverNative(const QJsonObject &report) {
    require(report.value("productionAuthority").toBool(true) == false,
            "native-production-authority-must-remain-OFF");
    require(report.value("selectedNativeActorVerified").toBool(true) == false,
            "selected-actor-must-remain-unverified");
    require(report.value("waylandBufferAttested").toBool(true) == false,
            "wayland-buffer-must-remain-unverified");
    require(report.value("scope").toString() ==
            QStringLiteral("QT_CPU_READBACK_ONLY"), "cpu-readback-only");
    require(report.value("nativeBufferFormat").isNull(),
            "native-drm-format-unknown");
    require(report.value("nativeBufferStrideBytes").isNull(),
            "actual-wl-buffer-stride-unknown");
    require(report.value("nativeBufferModifier").isNull(),
            "native-modifier-unknown");
    require(report.value("nativeBufferAllocationKind").isNull(),
            "native-buffer-allocation-unknown");
    require(report.value("nativeSurfaceScale").isNull(),
            "native-surface-scale-unknown");
}

int main() {
    QImage odd(1493,788,QImage::Format_RGBA8888);
    require(!odd.isNull(), "odd-image-allocated");
    auto oddReport=inspect(odd,QSize(1493,788),1.0);
    require(oddReport.value("status").toString() ==
            QStringLiteral("OBSERVED_QT_READBACK"),"odd-qimage-observed");
    require(oddReport.value("readbackWidth").toInt()==1493,
            "odd-qimage-width");
    require(oddReport.value("readbackBytesPerLine").toInt() ==
            int(odd.bytesPerLine()), "odd-qimage-actual-row-stride");
    require(oddReport.value("readbackBytesPerLine").toInt()==5972,
            "odd-qimage-readback-width-times-four");
    require(oddReport.value("readbackDepthBits").toInt()==32,
            "odd-qimage-depth");
    require(oddReport.value("readbackRowPaddingBytes").toInt()==0,
            "odd-qimage-has-no-added-cpu-padding");
    require(oddReport.value("readyForNativeBufferImport").toBool(true)==false,
            "cpu-qimage-never-approves-import");
    require(oddReport.value("requiresIndependentHostBufferEvidence").toBool(),
            "host-must-independently-attest");
    neverNative(oddReport);

    QImage even(1494,788,QImage::Format_RGBA8888);
    auto evenReport=inspect(even,QSize(1493,788),1.0);
    require(evenReport.value("status").toString() ==
            QStringLiteral("OBSERVED_QT_READBACK"),"even-qimage-observed");
    require(evenReport.value("readbackBytesPerLine").toInt() ==
            int(even.bytesPerLine()),"even-actual-cpu-stride");
    require(evenReport.value("readbackBytesPerLine").toInt()==5976,
            "even-qimage-expected-cpu-row-size");
    // The real logical host size and physical readback width remain
    // distinct; an extra column is not proof of renderer import rights.
    require(evenReport.value("logicalWindowWidth").toInt()==1493,
            "logical-window-width-preserved");
    require(evenReport.value("readbackWidth").toInt()==1494,
            "physical-cpu-readback-width");
    neverNative(evenReport);

    // Three-byte RGB888 shows why a universal four-byte/pixel inference
    // would be wrong. We report QImage's ACTUAL CPU bytesPerLine.
    QImage rgb(3,2,QImage::Format_RGB888);
    auto rgbReport=inspect(rgb,QSize(3,2),1.0);
    require(rgbReport.value("status").toString() ==
            QStringLiteral("OBSERVED_QT_READBACK"),"rgb888-observed");
    require(rgbReport.value("readbackDepthBits").toInt()==24,
            "rgb888-real-bit-depth");
    require(rgbReport.value("readbackBytesPerLine").toInt() ==
            int(rgb.bytesPerLine()),"rgb888-real-pitch");
    require(rgbReport.value("readbackMinimumStrideBytes").toInt()==9,
            "rgb888-minimum-physical-row");
    require(rgbReport.value("readbackRowPaddingBytes").toInt() ==
            int(rgb.bytesPerLine()) - 9,
            "rgb888-actual-padding");
    neverNative(rgbReport);

    // Window/Qt CPU DPR are observed separately; neither can become
    // the unverified compositor surface scale.
    even.setDevicePixelRatio(2.0);
    auto highDpiReport=inspect(even,QSize(747,394),2.0);
    require(highDpiReport.value("readbackDevicePixelRatio").toDouble()==2.0,
            "qt-image-dpr-observed");
    require(highDpiReport.value("windowDevicePixelRatio").toDouble()==2.0,
            "qt-window-dpr-observed");
    require(highDpiReport.value("nativeSurfaceScale").isNull(),
            "native-wl-surface-scale-still-unknown");
    neverNative(highDpiReport);

    auto missing=inspect(QImage(),QSize(1493,788),1.0);
    require(missing.value("status").toString()==QStringLiteral("REFUSED"),
            "missing-readback-refused");
    require(missing.value("reason").toString() ==
            QStringLiteral("NO_QT_READBACK_IMAGE"),"missing-reason");
    neverNative(missing);

    for (const auto &bad : {
        inspect(odd,QSize(),1.0),
        inspect(odd,QSize(1493,788),0.0),
        inspect(odd,QSize(1493,788),17.0),
        inspect(QImage(8193,1,QImage::Format_RGBA8888),QSize(8193,1),1.0)
    }) {
        require(bad.value("status").toString() ==
                QStringLiteral("REFUSED"),"invalid-geometry-refused");
        neverNative(bad);
    }
    std::cout << "COMPANY_M30V_QIMAGE_METADATA "
              << "odd_width=1493 cpu_bytes_per_line=5972 "
              << "even_width=1494 cpu_bytes_per_line=5976 "
              << "actual_native_wl_buffer_metadata=UNAVAILABLE "
              << "unknown_formats_and_surfaces=NOT_APPROVED PASS\n";
    return 0;
}
