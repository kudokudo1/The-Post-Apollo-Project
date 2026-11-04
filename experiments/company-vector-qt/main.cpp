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
#include <cmath>
#include <QFile>
#include <QProcess>
#include <QRegularExpression>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonParseError>
#include <QVariantList>
#include <QVariantMap>
#include <QSet>
#include <QElapsedTimer>
#include <QVector>
#include <QtMath>

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
    const bool fixtureHubs = args.contains("--fixture-hubs");
    const bool benchMotion = args.contains("--bench-pan-zoom");
    // Explicit local owner-only view switch, NOT enterprise authentication.
    const bool ownerLocalHubs = args.contains("--owner-local-hubs");
    if (ownerLocalHubs && (mockHub || fixtureHubs)) {
        qCritical() << "OWNER_VIEW_MUST_NOT_COMBINE_WITH_TEST_HUBS";
        return 14;
    }
    if (fixtureHubs && !anyOnline) {
        qCritical() << "FIXTURE_HUBS_REQUIRE_EXPLICIT_ONLINE_MODE";
        return 8;
    }
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

    // This is a fixed repo-owned, *synthetic* fixture, not a user-supplied
    // path and never a read of private Company data.
    // Reject additional/private fields and any malformed coordinates.
    QVariantList fixtureRecords;
    if (fixtureHubs) {
        QFile fixture(QStringLiteral(COMPANY_PROBE_HUB_FIXTURE_PATH));
        if (!fixture.open(QIODevice::ReadOnly) || fixture.size() > 4096) {
            qCritical() << "FIXTURE_READ_FAILED";
            return 10;
        }
        QJsonParseError parseError;
        auto doc = QJsonDocument::fromJson(fixture.readAll(), &parseError);
        if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
            qCritical() << "FIXTURE_PARSE_FAILED";
            return 10;
        }
        const auto json = doc.object();
        const auto records = json.value("records").toArray();
        if (json.size() != 2 || json.value("schema").toString() !=
                QStringLiteral("post-apollo.company-hubs.fixture.v1")
                || records.size() != 3) {
            qCritical() << "FIXTURE_SCHEMA_REFUSED";
            return 10;
        }
        QSet<QString> ids;
        for (const auto &entry : records) {
            if (!entry.isObject()) return 10;
            const auto hub = entry.toObject();
            const QString id = hub.value("id").toString();
            const QString label = hub.value("label").toString();
            if (hub.size() != 4 || !id.startsWith("fixture-")
                    || ids.contains(id)
                    || !label.startsWith("DEMO NODE ")
                    || label.size() > 24
                    || !hub.value("latitude").isDouble()
                    || !hub.value("longitude").isDouble()) {
                qCritical() << "FIXTURE_FIELD_REFUSED";
                return 10;
            }
            const double lat = hub.value("latitude").toDouble();
            const double lon = hub.value("longitude").toDouble();
            if (!qIsFinite(lat) || !qIsFinite(lon) ||
                    lat < -85 || lat > 85 || lon < -180 || lon > 180) {
                qCritical() << "FIXTURE_COORDINATES_REFUSED";
                return 10;
            }
            ids.insert(id);
            fixtureRecords.append(QVariantMap{{"id", id}, {"label", label},
                {"latitude", lat}, {"longitude", lon}});
        }
        qInfo() << "SYNTHETIC_FIXTURE_VALIDATED" << fixtureRecords.size();
    }

    // Explicit one-shot read. No socket, daemon, arbitrary file path,
    // background refresh, persistence, provider upload or auto-centering.
    // The projection subprocess itself enforces same-UID/nonroot access.
    QVariantList ownerRecords;
    if (ownerLocalHubs) {
        QProcess ownerReader;
        ownerReader.setProgram(QStringLiteral("/usr/bin/python3"));
        ownerReader.setArguments({
            QStringLiteral(COMPANY_OWNER_MAP_READONLY_SCRIPT),
            QStringLiteral("--owner-local-view")
        });
        ownerReader.start();
        if (!ownerReader.waitForStarted(1500)
                || !ownerReader.waitForFinished(4000)) {
            if (ownerReader.state() != QProcess::NotRunning) {
                ownerReader.kill();
                ownerReader.waitForFinished(1000);
            }
            qCritical() << "OWNER_LOCAL_PROJECTION_UNAVAILABLE";
            return 13;
        }
        const QByteArray stdoutData = ownerReader.readAllStandardOutput();
        if (ownerReader.exitStatus()!=QProcess::NormalExit
                || ownerReader.exitCode()!=0
                || stdoutData.size()>32768 || stdoutData.isEmpty()) {
            qCritical() << "OWNER_LOCAL_PROJECTION_REFUSED";
            return 13;
        }
        QJsonParseError parseError;
        const QJsonDocument output = QJsonDocument::fromJson(stdoutData, &parseError);
        if (parseError.error != QJsonParseError::NoError || !output.isObject()) {
            qCritical() << "OWNER_LOCAL_RESPONSE_INVALID";
            return 13;
        }
        const QJsonObject rootDoc=output.object();
        if (rootDoc.size()!=2 || rootDoc.value("ok")!=QJsonValue(true)
                || !rootDoc.value("document").isObject()) {
            qCritical() << "OWNER_LOCAL_RESPONSE_INVALID";
            return 13;
        }
        const QJsonObject result=rootDoc.value("document").toObject();
        const QJsonArray hubs=result.value("hubs").toArray();
        if (result.size()!=4
                || result.value("schema").toString() !=
                     QStringLiteral("post-apollo.company-map.owner-local-v1")
                || result.value("authority").toString() !=
                     QStringLiteral("OWNER_LOCAL_ONLY_NOT_ORGANIZATION_GRANT")
                || !result.value("revision").isDouble()
                || !result.value("hubs").isArray()
                || hubs.size()>150) {
            qCritical() << "OWNER_LOCAL_SCHEMA_REFUSED";
            return 13;
        }
        QSet<QString> seen;
        const QRegularExpression hubIdPattern(QStringLiteral("^hub-[1-9][0-9]{0,7}$"));
        for (const auto &row: hubs) {
            if (!row.isObject()) return 13;
            const auto hub=row.toObject();
            const QString id=hub.value("id").toString();
            if (hub.size()!=4 || !hubIdPattern.match(id).hasMatch()
                    || seen.contains(id) || hub.value("reported")!=QJsonValue(true)
                    || !hub.value("latitude").isDouble()
                    || !hub.value("longitude").isDouble()) {
                qCritical() << "OWNER_LOCAL_RECORD_REFUSED";
                return 13;
            }
            const double lat=hub.value("latitude").toDouble();
            const double lon=hub.value("longitude").toDouble();
            if (!qIsFinite(lat) || !qIsFinite(lon)
                    || lat < -85.05112878 || lat > 85.05112878
                    || lon < -180 || lon > 180) {
                qCritical() << "OWNER_LOCAL_COORDINATES_REFUSED";
                return 13;
            }
            seen.insert(id);
            ownerRecords.append(QVariantMap{
                {"id", id}, {"latitude", lat}, {"longitude", lon}});
        }
        // Only count is logged. Never coordinates, Company labels or IDs.
        qInfo() << "OWNER_LOCAL_PROJECTION_VALIDATED" << ownerRecords.size();
    }

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("probeStyleUrl", styleUrl.toString());
    engine.rootContext()->setContextProperty("probeOnline", anyOnline);
    engine.rootContext()->setContextProperty("probeStyledOnline", styledOnline);
    engine.rootContext()->setContextProperty("probeSample", sample);
    engine.rootContext()->setContextProperty("probeMockHub", mockHub);
    engine.rootContext()->setContextProperty("probeFixtureHubs", fixtureRecords);
    engine.rootContext()->setContextProperty("probeOwnerLocalHubs", ownerRecords);
    engine.rootContext()->setContextProperty("probeOwnerLocalMode", ownerLocalHubs);
    engine.rootContext()->setContextProperty("probeBenchMotion", benchMotion);
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
    if (benchMotion) {
        // QQuickWindow::frameSwapped timestamps include CPU, GPU, compositor
        // and CI scheduling effects. Not a desktop latency/FPS guarantee.
        QElapsedTimer watch;
        watch.start();
        QVector<qint64> intervals;
        qint64 lastSwapNs = -1;
        QObject::connect(window, &QQuickWindow::frameSwapped, window,
            [&watch, &intervals, &lastSwapNs]() {
                const qint64 now = watch.nsecsElapsed();
                // QML starts fixed camera motion at 8 sec, stops by 13 sec.
                if (now < 8000000000LL || now > 13500000000LL) return;
                if (lastSwapNs >= 0) intervals.append(now-lastSwapNs);
                lastSwapNs = now;
            });
        QTimer::singleShot(14600, &app, [&app, &intervals, sample, anyOnline]() {
            std::sort(intervals.begin(), intervals.end());
            const int n = intervals.size();
            auto percentileMs = [&intervals, n](double fraction) -> double {
                if (!n) return 0;
                const int idx = std::min(n-1, std::max(0, int(std::ceil(n*fraction)-1)));
                return double(intervals[idx])/1000000.0;
            };
            const double p50 = percentileMs(0.50);
            const double p95 = percentileMs(0.95);
            const double maxMs = n ? double(intervals.last())/1000000.0 : 0.0;
            QJsonObject report{
                {"sample", sample}, {"online", anyOnline},
                {"frame_intervals", n},
                {"p50_ms", p50}, {"p95_ms", p95}, {"max_ms", maxMs},
                {"window_ms", 5500},
                {"note", "software-renderer scheduling; not host GPU performance"}
            };
            qInfo().noquote() << "BENCH_FRAME_PACING"
                << QString::fromUtf8(QJsonDocument(report).toJson(QJsonDocument::Compact));
            app.exit(n >= 10 ? 0 : 11);
        });
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
