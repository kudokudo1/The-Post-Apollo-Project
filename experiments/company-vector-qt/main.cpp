// Standalone Qt6 / MapLibre Native Qt v3 graphics compatibility gate.
// No Quickshell changes, personal data, or production provider operations.
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QSGRendererInterface>
#include <QTimer>
#include <QUrl>
#include <QFileInfo>
#include <QImage>
#include <QStringList>
#include <QDebug>
#include <QColor>
#include <algorithm>

int main(int argc, char **argv) {
    // MapLibre Native Qt v3 QML needs OpenGL RHI. This is PROCESS-LOCAL.
    QQuickWindow::setGraphicsApi(QSGRendererInterface::OpenGLRhi);
    QGuiApplication app(argc, argv);
    app.setApplicationName("PostApolloCompanyVectorProbe");
    const QStringList args = app.arguments();

    const bool online = args.contains("--online");
    const bool styledOnline = args.contains("--styled-online");
    const bool anyOnline = online || styledOnline;
    const bool capture = args.contains("--capture");
    const bool mockHub = args.contains("--mock-hub");
    if (mockHub && !anyOnline) {
        qCritical() << "MOCK_HUB_REQUIRES_EXPLICIT_ONLINE_MODE";
        return 7;
    }

    // Limited public regression viewports only, never private user locations.
    QString sample;
    for (const QString &arg : args) {
        if (arg.startsWith(QStringLiteral("--sample=")))
            sample = arg.mid(QStringLiteral("--sample=").size());
    }
    const QStringList allowedSamples = {
        QStringLiteral("USA"), QStringLiteral("PACIFIC"),
        QStringLiteral("MIDWEST"), QStringLiteral("NORTHEAST"),
        QStringLiteral("RURAL"), QStringLiteral("CANADA"),
        QStringLiteral("MEXICO"), QStringLiteral("ALASKA"),
        QStringLiteral("HAWAII"), QStringLiteral("FLINT"),
        QStringLiteral("SUBURB"), QStringLiteral("VILLAGE"),
        QStringLiteral("NEIGHBORHOOD"), QStringLiteral("BORDER")
    };
    if ((!sample.isEmpty() && !allowedSamples.contains(sample))
            || (!sample.isEmpty() && !anyOnline)) {
        qCritical() << "INVALID_OR_OFFLINE_SAMPLE" << sample;
        return 6;
    }
    const QString localPath = QStringLiteral(COMPANY_PROBE_STYLE_PATH);
    const QString styledPath = QStringLiteral(COMPANY_PROBE_ONLINE_STYLE_PATH);
    // No online vector source can be selected implicitly or by theme alone.
    if (!anyOnline && !QFileInfo::exists(localPath)) {
        qCritical() << "OFFLINE_FIXTURE_MISSING" << localPath;
        return 2;
    }
    if (styledOnline && !QFileInfo::exists(styledPath)) {
        qCritical() << "ONLINE_STYLE_FIXTURE_MISSING" << styledPath;
        return 2;
    }
    const QUrl styleUrl = styledOnline
        ? QUrl::fromLocalFile(styledPath)
        : online
        ? QUrl(QStringLiteral("https://tiles.openfreemap.org/styles/liberty"))
        : QUrl::fromLocalFile(localPath);
    qInfo() << "MAPLIBRE_COMPAT_PROBE"
            << "Qt" << QT_VERSION_STR
            << "mode" << (styledOnline ? "post-apollo-vector-online-opt-in"
                            : anyOnline ? "online-opt-in" : "offline")
            << "renderer" << "OpenGLRhi";
    if (anyOnline)
        qInfo() << "ONLINE_MAP_PRIVACY: IP and viewed map tiles may reach OpenFreeMap.";

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("probeStyleUrl", styleUrl.toString());
    engine.rootContext()->setContextProperty("probeOnline", anyOnline);
    engine.rootContext()->setContextProperty("probeStyledOnline", styledOnline);
    engine.rootContext()->setContextProperty("probeSample", sample);
    engine.rootContext()->setContextProperty("probeMockHub", mockHub);
    engine.load(QUrl(QStringLiteral("qrc:/CompanyVectorProbe/main.qml")));
    if (engine.rootObjects().isEmpty()) {
        qCritical() << "QML_PLUGIN_OR_WINDOW_LOAD_FAILED";
        return 3;
    }
    auto *window = qobject_cast<QQuickWindow *>(engine.rootObjects().first());
    if (!window) {
        qCritical() << "UNEXPECTED_ROOT_OBJECT";
        return 4;
    }
    if (capture) {
        // Screenshot proves only that a Qt scene was captured, not that
        // actual streets or the intended vector layers rendered correctly.
        // Offline synthetic capture is quick; online vector tiles and glyphs
        // need additional time before a screenshot can be inspected.
        const int settleMilliseconds = anyOnline ? 15000 : 5500;
        QTimer::singleShot(settleMilliseconds, &app, [&app, window, sample, anyOnline, mockHub]() {
            const QImage screenshot = window->grabWindow();
            const QString out = QStringLiteral("company-vector-probe.png");
            if (screenshot.isNull() || !screenshot.save(out)) {
                qCritical() << "CAPTURE_FAILED";
                app.exit(5);
                return;
            }
            qInfo() << "CAPTURE_CREATED" << out << screenshot.size()
                    << "sample" << sample
                    << "network_style" << anyOnline;
            // Diagnostic count only: a screenshot can exist even when map
            // resources have failed, so humans must inspect the captures.
            int colorfulPixels = 0;
            const int top = std::min(screenshot.height() - 1, 70);
            const int bottom = std::max(top + 1, screenshot.height() - 50);
            for (int y = top; y < bottom; y += 8) {
                for (int x = 30; x < screenshot.width() - 100; x += 8) {
                    const QColor color = screenshot.pixelColor(x, y);
                    if (color.red() > color.blue() * 1.2
                            || color.green() > color.blue() * 1.2)
                        ++colorfulPixels;
                }
            }
            qInfo() << "CAPTURE_DIAGNOSTIC" << "non-purple-samples" << colorfulPixels;
            // Sample the actual map area, excluding the title, footer and
            // camera rail. This is quantitative evidence of palette content,
            // not proof of specific streets or the accuracy of labels.
            int cyanPixels = 0;
            int violetPixels = 0;
            int orangePixels = 0;
            const int mapRight = std::max(0, screenshot.width() - 110);
            const int mapBottom = std::max(64, screenshot.height() - 48);
            for (int y = 60; y < mapBottom; y += 4) {
                for (int x = 10; x < mapRight; x += 4) {
                    const QColor v = screenshot.pixelColor(x, y);
                    if (v.green() > 100 && v.blue() > 95
                            && v.green() > v.red() * 1.28)
                        ++cyanPixels;
                    if (v.red() > 100 && v.blue() > 75
                            && v.red() > v.green() * 1.27)
                        ++violetPixels;
                    if (v.red() > 160 && v.green() > 70
                            && v.green() < 210 && v.blue() < 120)
                        ++orangePixels;
                }
            }
            qInfo() << "MAP_PALETTE_SAMPLES"
                    << "cyan" << cyanPixels
                    << "magenta" << violetPixels
                    << "orange" << orangePixels
                    << "mock_hub" << mockHub;
            app.exit(0);
        });
    }
    return app.exec();
}
