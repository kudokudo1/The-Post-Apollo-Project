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

int main(int argc, char **argv) {
    // MapLibre Native Qt v3 QML needs OpenGL RHI. This is PROCESS-LOCAL.
    QQuickWindow::setGraphicsApi(QSGRendererInterface::OpenGLRhi);
    QGuiApplication app(argc, argv);
    app.setApplicationName("PostApolloCompanyVectorProbe");
    const QStringList args = app.arguments();

    const bool online = args.contains("--online");
    const bool capture = args.contains("--capture");
    const QString localPath = QStringLiteral(COMPANY_PROBE_STYLE_PATH);
    if (!online && !QFileInfo::exists(localPath)) {
        qCritical() << "OFFLINE_FIXTURE_MISSING" << localPath;
        return 2;
    }
    const QUrl styleUrl = online
        ? QUrl(QStringLiteral("https://tiles.openfreemap.org/styles/liberty"))
        : QUrl::fromLocalFile(localPath);
    qInfo() << "MAPLIBRE_COMPAT_PROBE"
            << "Qt" << QT_VERSION_STR
            << "mode" << (online ? "online-opt-in" : "offline")
            << "renderer" << "OpenGLRhi";
    if (online)
        qInfo() << "ONLINE_MAP_PRIVACY: IP and viewed map tiles may reach OpenFreeMap.";

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("probeStyleUrl", styleUrl.toString());
    engine.rootContext()->setContextProperty("probeOnline", online);
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
        QTimer::singleShot(5500, &app, [&app, window]() {
            const QImage screenshot = window->grabWindow();
            const QString out = QStringLiteral("company-vector-probe.png");
            if (screenshot.isNull() || !screenshot.save(out)) {
                qCritical() << "CAPTURE_FAILED";
                app.exit(5);
                return;
            }
            qInfo() << "CAPTURE_CREATED" << out << screenshot.size();
            app.exit(0);
        });
    }
    return app.exec();
}
