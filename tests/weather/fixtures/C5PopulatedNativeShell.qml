import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// Synthetic DATA ONLY for an offscreen source→renderer smoke. No external
// provider response is fabricated in production; existing QML is unmodified.
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property string route: "cosmos/planets-stars/planet-clock"
    property real meteorHeaderY: -1
    property real catalogScrollY: -1

    QtObject {
        id: fakeWeather
        property real latitude: 38.9
        property real longitude: -76.75
        property var dailyForecast: []
        property int airQualityUtcOffsetMinutes: -300
        property bool ready: false
        property bool loading: false
        property string localObservationDateTime: ""
        property real localObservationAnchorMs: 0
    }

    Window {
        visible: true
        width: 520
        height: 340
        color: "black"
        Weather.StationCosmosModesPane {
            id: focused
            anchors.fill: parent
            subjectRoute: root.route
            weatherService: fakeWeather
            spaceService: null
            runtimeNowMs: Date.UTC(2026, 10, 5, 13, 0)
        }
    }

    function findNamed(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        const children = item.children || [];
        for (let i=0;i<children.length;i++) {
            const hit = findNamed(children[i], name);
            if (hit) return hit;
        }
        return null;
    }

    function countNamed(item, name) {
        if (!item) return 0;
        let count = item.objectName === name ? 1 : 0;
        const children = item.children || [];
        for (let i=0;i<children.length;i++)
            count += countNamed(children[i], name);
        return count;
    }

    function dumpTree(item, depth, out) {
        if (!item || depth > 8 || out.length >= 90) return;
        out.push(depth+":"+(item.objectName || "(unnamed)")
            +"["+String(item)+"]"
            +" children="+((item.children || []).length));
        const children = item.children || [];
        for(let i=0;i<children.length;i++)
            dumpTree(children[i],depth+1,out);
    }

    function fail(reason) {
        if (done) return;
        done = true;
        console.error("C5_POPULATED_FAIL // " + reason
            + " // route=" + focused.subjectRoute
            + " kind=" + focused.kind
            + " clock=" + focused.visibleClockLaneCount
            + " cards=" + (focused.cards ? focused.cards.length : "null"));
        Qt.quit();
    }

    function succeed() {
        if (done) return;
        done = true;
        console.log("C5_POPULATED_PASS // SUN_ARC PLANET_EVENTS ISS_TIMES ACTIVE_METEORS C6_DETAILS C7_12_TILE_GRID");
        Qt.quit();
    }

    Timer {
        interval: 110
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if (root.ticks > 45) return root.fail("TIMEOUT");
            if (root.phase === 0) {
                if (!focused.planetSource || !focused.planetSource.configured)
                    return root.fail("MISSING_USNO_PROVIDER_CONFIGURATION");
                // Stop the network collector; supply a dated sample through
                // its real read-only presentation interface.
                focused.planetSource.active = false;
                focused.planetSource.loadedKey = focused.planetSource.currentKey;
                focused.planetSource.rows = [{
                    name:"MERCURY", date:focused.civilDate, status:"NORMAL",
                    rise:"06:15", transit:"12:00", set:"18:20"
                }];
                focused.planetSource.ready = true;
                root.phase = 1;
            } else if (root.phase === 1) {
                if (focused.planetRows[0].events.length !== 3)
                    return root.fail("USNO_RECORDS_NOT_MAPPED_TO_EVENT_CLOCK");
                const clock = focused.instrumentItem;
                const dial = findNamed(clock,"cosmos-c28-clock-dial-canvas");
                const frame = findNamed(clock,"cosmos-c28-clock-dial-frame");
                const inspector = findNamed(clock,"cosmos-c28-event-inspector");
                const filter = findNamed(clock,"cosmos-c28-event-type-filters");
                const firstMarker = findNamed(clock,"cosmos-c5-planet-event-marker");
                if (!dial || !frame || !inspector || !filter
                    || clock.renderedRowCount !== 5
                    || clock.events.length !== 3
                    || dial.width < 130 || dial.height < 130
                    || inspector.width < 150 || inspector.height < 130
                    || countNamed(clock,"cosmos-c5-planet-event-marker") !== 3
                    || !firstMarker || firstMarker.pos === null) {
                    let names = [];
                    dumpTree(clock,0,names);
                    console.log("C28_RENDER_TREE // "+names.join("|"));
                    return root.fail("C28_USNO_CIRCULAR_CLOCK_NOT_RENDERED");
                }
                // Real circular markers expose their original event kind and
                // local civil time, and not a fabricated orbit/sky position.
                if (clock.events[0].source !== "USNO MRST"
                    || firstMarker.eventData.minute !== clock.events[0].minute
                    || clock.events.some(e => e.date !== focused.civilDate))
                    return root.fail("C28_USNO_EVENT_PROVENANCE_LOST");
                clock.pickKind("rise");
                if (clock.events.length !== 1
                    || clock.events[0].kind !== "rise")
                    return root.fail("C28_RING_RISE_FILTER_BROKEN");
                clock.pickKind("ALL");
                clock.pickPlanet("MERCURY");
                if (clock.events.length !== 3)
                    return root.fail("C28_PLANET_FILTER_BROKEN");
                clock.step(1);
                if (!clock.lockedEvent || !clock.lockedEvent.id
                    || clock.events.every(e=>e.id !== clock.lockedEvent.id))
                    return root.fail("C28_EVENT_INSPECTOR_STEPPER_BROKEN");
                clock.pickPlanet("ALL");
                root.phase = 2;
                root.route = "cosmos/events/iss";
            } else if (root.phase === 2) {
                if (!focused.issSource || !focused.issSource.configured)
                    return root.fail("ISS_LOCATION_NOT_CONFIGURED");
                focused.issSource.active = false;
                focused.issSource.passes = [{
                    rise:{timeUtc:"2026-11-05 12:00Z",direction:"W",azimuth:268},
                    culminate:{degrees:42.3,timeUtc:"2026-11-05 12:04Z",
                        direction:"N",azimuth:15},
                    set:{timeUtc:"2026-11-05 12:07Z",direction:"E",azimuth:74},
                    durationLabel:"7:00",minutesUntilRise:22
                }];
                focused.issSource.ready = true;
                root.phase = 3;
            } else if (root.phase === 3) {
                const details = focused.instrumentItem;
                if (!details || details.recordCount !== 1
                        || details.facts.length !== 12
                        || details.facts[1].value.indexOf("12:04Z") < 0
                        || details.facts[2].value.indexOf("12:07Z") < 0)
                    return root.fail("ISS_FULL_RECORD_FIELDS_NOT_RENDERED");
                if (countNamed(details,"cosmos-c6-observation-cell") !== 12)
                    return root.fail("ISS_DETAIL_CELLS_NOT_IN_VISUAL_TREE");
                if (details.renderedFactCount !== 12
                        || details.facts[9].value !== "7:00")
                    return root.fail("ISS_ALL_TWELVE_FACTS_NOT_VISIBLE");
                root.phase = 4;
                root.route = "cosmos/events/meteors";
            } else if (root.phase === 4) {
                if (!focused.meteorSource || !focused.meteorSource.configured)
                    return root.fail("IAU_LOCATION_NOT_CONFIGURED");
                focused.meteorSource.active = false;
                focused.meteorSource.activeShowers = [{
                    name:"SAMPLE ACTIVE",peakUtc:"2026-11-05 23:00Z",
                    code:"TEST-A"
                }];
                focused.meteorSource.upcomingShowers = [{
                    name:"SAMPLE FUTURE",peakUtc:"2026-11-12 23:00Z",
                    code:"TEST-B",daysToPeak:7.0,ra:46.8,dec:31.2
                }];
                focused.meteorSource.ready = true;
                root.phase = 5;
            } else if (root.phase === 5) {
                if (!focused.cards || focused.cards.length !== 2
                        || focused.cards[0].info !== "ACTIVE NOW"
                        || focused.cards[1].info !== "UPCOMING")
                    return root.fail("ACTIVE_IAU_RECORDS_MISSING");
                if (countNamed(focused.instrumentItem,
                        "cosmos-c5-meteor-card") !== 2)
                    return root.fail("IAU_CARDS_NOT_RENDERED");
                const instrument = focused.instrumentItem;
                const header = findNamed(instrument,
                    "cosmos-c25-meteor-sticky-header");
                const peaks = findNamed(instrument,
                    "cosmos-c25-meteor-next-peaks-row");
                const frame = findNamed(instrument,
                    "cosmos-c25-meteor-catalog-frame");
                const scroll = findNamed(instrument,
                    "cosmos-c25-meteor-catalog-scroll");
                if (!header || !peaks || !frame || !scroll
                    || countNamed(instrument,"cosmos-c25-meteor-peak-card") !== 3
                    || peaks.height < 65
                    || scroll.height < 35
                    || frame.y < header.height
                    || scroll.contentHeight !== 99)
                    return root.fail("C25_STICKY_METEOR_HEADER_OR_CATALOG_BOUNDS");
                // C29 joins the fixed archival image + countdown to the
                // existing C25 scroll without depending on remote image load.
                const visual = findNamed(instrument,
                    "cosmos-c29-meteor-image-panel");
                const photograph = findNamed(instrument,
                    "cosmos-c29-nasa-archival-photo");
                const meter = findNamed(instrument,
                    "cosmos-c29-source-countdown-fill");
                if (!visual || !photograph || !meter
                    || !visual.sourceReady
                    || visual.width < 150
                    || visual.height < 55
                    || scroll.width < 140
                    || Math.abs(visual.daysToPeak - 7) > 0.001
                    || Math.abs(visual.remaining30DayFraction-7/30)>0.001)
                    return root.fail("C29_METEOR_PHOTO_AND_DATA_METER_MISSING");
                visual.setZoom(3.8);
                if (visual.zoom !== 3)
                    return root.fail("C29_PHOTO_ZOOM_BOUNDS_BROKEN");
                visual.panX = 31;
                visual.panY = 12;
                visual.resetView();
                if (visual.zoom !== 1 || visual.panX !== 0 || visual.panY !== 0)
                    return root.fail("C29_PHOTO_RESET_BROKEN");
                const simulatedSky = findNamed(instrument,
                    "cosmos-c30-simulated-motion-view");
                const movingCanvas = findNamed(instrument,
                    "cosmos-c30-meteor-moving-sky");
                if (!simulatedSky || !movingCanvas
                    || !simulatedSky.visible || !visual.playing
                    || visual.showArchive
                    || visual.archiveFrames.length !== 2
                    || !simulatedSky.radiantValid
                    || Math.abs(simulatedSky.radiantX-46.8/360) > 0.001
                    || Math.abs(simulatedSky.radiantY-(90-31.2)/180) > 0.001)
                    return root.fail("C30_MOVING_SOURCE_RADIANT_NOT_RENDERED");
                visual.playing = false;
                if (simulatedSky.motionRunning || visual.archiveCycling)
                    return root.fail("C30_PAUSE_DID_NOT_STOP_ANIMATION");
                visual.showArchive = true;
                if (!visual.showArchive || simulatedSky.visible
                    || visual.archiveFrame.name !== "PERSEIDS 2016")
                    return root.fail("C30_GALLERY_SWITCH_BROKEN");
                visual.nextArchive();
                if (visual.archiveIndex !== 1
                    || visual.archiveFrame.name !== "SPRUCE KNOB 2016")
                    return root.fail("C30_GALLERY_NEXT_BROKEN");
                const meteorFocus = findNamed(instrument,
                    "cosmos-c33-meteor-photo-focus");
                const meteorExpand = findNamed(instrument,
                    "cosmos-c33-meteor-expand");
                if (!meteorFocus || !meteorExpand)
                    return root.fail("C33_METEOR_EXPAND_ACTION_MISSING");
                visual.expandRequested();
                if (!meteorFocus.visible
                    || meteorFocus.width !== instrument.width
                    || meteorFocus.height !== instrument.height
                    || meteorFocus.sourceUrl !== visual.archiveFrame.url)
                    return root.fail("C33_METEOR_PHOTO_NOT_IN_STAGE");
                meteorFocus.setZoom(6);
                if (meteorFocus.zoom !== 4)
                    return root.fail("C33_PHOTO_STAGE_ZOOM_NOT_CLAMPED");
                meteorFocus.resetView();
                if (meteorFocus.zoom !== 1
                    || meteorFocus.panX !== 0 || meteorFocus.panY !== 0)
                    return root.fail("C33_PHOTO_STAGE_RESET_FAILED");
                meteorFocus.nextRequested();
                if (visual.archiveIndex !== 0)
                    return root.fail("C33_METEOR_EXPANDED_NEXT_FAILED");
                meteorFocus.closeRequested();
                if (meteorFocus.visible
                    || !visual.showArchive
                    || meteorScroll.contentY !== 0)
                    return root.fail("C33_METEOR_BACK_DID_NOT_RESTORE_CATALOG");
                visual.showArchive = false;
                visual.playing = true;
                // Populate a long bounded catalog after the old two-card
                // acceptance check. A real scroll must leave the header still.
                const extra = [];
                for (let i=1;i<=7;i++)
                    extra.push({name:"FUTURE "+i,
                        peakUtc:"2026-11-20T11:30:00Z",
                        code:"T-"+i,daysToPeak:12+i,ra:45+i,dec:18+i});
                focused.meteorSource.upcomingShowers = [{
                    name:"SAMPLE FUTURE",peakUtc:"2026-11-12T23:00:00Z",
                    code:"TEST-B",daysToPeak:7,ra:46.8,dec:31.2
                }].concat(extra);
                root.phase = 55;
            } else if (root.phase === 55) {
                const instrument = focused.instrumentItem;
                const header = findNamed(instrument,
                    "cosmos-c25-meteor-sticky-header");
                const frame = findNamed(instrument,
                    "cosmos-c25-meteor-catalog-frame");
                const scroll = findNamed(instrument,
                    "cosmos-c25-meteor-catalog-scroll");
                if (!header || !frame || !scroll
                    || countNamed(instrument,"cosmos-c5-meteor-card") !== 9
                    || scroll.contentHeight <= scroll.height
                    || scroll.height < 35)
                    return root.fail("C25_LONG_CATALOG_NOT_SCROLLABLE");
                root.meteorHeaderY = header.mapToItem(instrument,0,0).y;
                scroll.contentY = Math.min(90,scroll.contentHeight-scroll.height);
                root.catalogScrollY = scroll.contentY;
                root.phase = 56;
            } else if (root.phase === 56) {
                const instrument = focused.instrumentItem;
                const header = findNamed(instrument,
                    "cosmos-c25-meteor-sticky-header");
                const scroll = findNamed(instrument,
                    "cosmos-c25-meteor-catalog-scroll");
                if (!header || !scroll
                    || scroll.contentY < 30
                    || header.mapToItem(instrument,0,0).y !== root.meteorHeaderY)
                    return root.fail("C25_PINNED_HEADER_MOVED_WITH_SCROLL");
                instrument.jumpToShower("FUTURE 7");
                if (instrument.selectedShowerName !== "FUTURE 7"
                    || scroll.contentY <= root.catalogScrollY)
                    return root.fail("C25_PEAK_CARD_CANNOT_REVEAL_CATALOG_RECORD");
                root.phase = 6;
                root.route = "cosmos/sun/position";
            } else if (root.phase === 6) {
                const sun = findNamed(focused.instrumentItem,
                    "cosmos-c12-sun-path-hero");
                if (!sun || !sun.solarData || !sun.solarData.ready
                        || sun.solarData.rows.length < 60)
                    return root.fail("SOURCE_BACKED_SOLAR_ARC_NOT_RENDERED");
                if (!focused.skyFeed || focused.skyFeed.focusedLocalMinute < 0)
                    return root.fail("VERIFIED_LOCAL_MINUTE_MISSING");
                root.phase = 7;
                root.route = "cosmos/events/eclipses";
            } else if (root.phase === 7) {
                if (!focused.eclipseSource)
                    return root.fail("NASA_SOURCE_NOT_MOUNTED");
                focused.eclipseSource.active = false;
                focused.eclipseSource.sourceName = "NASA GSFC";
                focused.eclipseSource.dateScope = "2026-2028";
                focused.eclipseSource.events = [{
                    event:"TOTAL SOLAR ECLIPSE",date:"2027-08-02",
                    body:"SOLAR",phase:"TOTAL",daysUntil:270
                },{
                    event:"PENUMBRAL LUNAR ECLIPSE",date:"2027-02-20",
                    body:"LUNAR",phase:"PENUMBRAL",daysUntil:106
                }];
                focused.eclipseSource.eventCount = 2;
                focused.eclipseSource.nextSolar = focused.eclipseSource.events[0];
                focused.eclipseSource.nextLunar = focused.eclipseSource.events[1];
                focused.eclipseSource.ready = true;
                root.phase = 8;
            } else if (root.phase === 8) {
                const details = focused.instrumentItem;
                if (!details || details.recordCount !== 2
                        || details.facts[1].value !== "2027-08-02")
                    return root.fail("ECLIPSE_FULL_CALENDAR_MISSING");
                details.selectedIndex = 1;
                if (details.facts[1].value !== "2027-02-20")
                    return root.fail("ECLIPSE_NEXT_ITEM_MISSING");
                if (details.renderedFactCount !== 12
                        || details.facts[8].value !== "NOT CALCULATED")
                    return root.fail("ECLIPSE_LOCAL_VISIBILITY_CAVEAT_MISSING");
                const featured = findNamed(details,"cosmos-c26-eclipse-sticky-header");
                const highlights = findNamed(details,"cosmos-c26-eclipse-highlight-row");
                const frame = findNamed(details,"cosmos-c26-eclipse-catalog-frame");
                const scroll = findNamed(details,"cosmos-c26-eclipse-catalog-scroll");
                if (!featured || !highlights || !frame || !scroll
                    || countNamed(details,"cosmos-c26-eclipse-highlight") !== 2
                    || countNamed(details,"cosmos-c26-eclipse-event-card") !== 2
                    || highlights.height < 70 || scroll.height < 30
                    || frame.y <= featured.height)
                    return root.fail("C26_ECLIPSE_PINNED_HIGHLIGHTS_MISSING");
                const solarMotion = findNamed(details,
                    "cosmos-c31-featured-eclipse-motion");
                const archiveToggle = findNamed(details,
                    "cosmos-c31-archive-toggle");
                const playToggle = findNamed(details,
                    "cosmos-c31-motion-play-pause");
                if (!solarMotion || !archiveToggle || !playToggle
                    || countNamed(details,"cosmos-c31-featured-eclipse-motion") !== 2
                    || countNamed(details,"cosmos-c31-eclipse-live-canvas") !== 2
                    || countNamed(details,"cosmos-c31-nasa-eclipse-archive") !== 2
                    || solarMotion.body !== "SOLAR"
                    || !solarMotion.eventRecord
                    || solarMotion.eventRecord.phase !== "TOTAL"
                    || solarMotion.width < 60
                    || !solarMotion.motionRunning)
                    return root.fail("C31_ECLIPSE_DUAL_MOVING_VISUALS_MISSING");
                solarMotion.seek(0.7);
                if (Math.abs(solarMotion.demoPhase-0.7)>0.001)
                    return root.fail("C31_ECLIPSE_SEEK_BROKEN");
                details.motionPlaying = false;
                if (solarMotion.motionRunning)
                    return root.fail("C31_ECLIPSE_PAUSE_FAILED");
                details.showArchive = true;
                if (!solarMotion.showArchive || solarMotion.motionRunning
                    || solarMotion.archiveCredit.indexOf("NASA")<0)
                    return root.fail("C31_ECLIPSE_PHOTO_MODE_FAILED");
                const eclipseFocus = findNamed(details,
                    "cosmos-c33-eclipse-photo-focus");
                if (!eclipseFocus
                    || countNamed(details,"cosmos-c33-eclipse-expand") !== 2)
                    return root.fail("C33_ECLIPSE_EXPAND_ACTIONS_MISSING");
                details.expandedImageIndex = 0;
                if (!eclipseFocus.visible
                    || eclipseFocus.width !== details.width
                    || eclipseFocus.height !== details.height
                    || eclipseFocus.sourceUrl !== solarMotion.archiveUrl)
                    return root.fail("C33_ECLIPSE_SOLAR_FOCUS_NOT_IN_STAGE");
                eclipseFocus.nextRequested();
                if (details.expandedImageIndex !== 1
                    || eclipseFocus.sourceUrl === solarMotion.archiveUrl)
                    return root.fail("C33_ECLIPSE_LUNAR_GALLERY_SWITCH_FAILED");
                eclipseFocus.closeRequested();
                if (eclipseFocus.visible
                    || details.expandedImageIndex !== -1)
                    return root.fail("C33_ECLIPSE_BACK_DID_NOT_RESTORE_CALENDAR");
                details.showArchive = false;
                details.motionPlaying = true;
                // C6 inspector still exposes all source facts when explicitly opened.
                details.inspectRecord(1);
                if (!details.inspecting || details.selectedIndex !== 1
                    || countNamed(details,"cosmos-c6-observation-cell") !== 12)
                    return root.fail("C26_C6_TWELVE_FACT_INSPECTOR_BROKEN");
                details.inspecting = false;
                const more = [];
                for(let n=0;n<8;n++)
                    more.push({event:"ECLIPSE TEST "+n,
                        date:"2028-04-03",body:n%2===0?"SOLAR":"LUNAR",
                        phase:"PARTIAL",daysUntil:510+n});
                focused.eclipseSource.events =
                    focused.eclipseSource.events.concat(more);
                root.phase = 85;
            } else if (root.phase === 85) {
                const details = focused.instrumentItem;
                const featured = findNamed(details,"cosmos-c26-eclipse-sticky-header");
                const scroll = findNamed(details,"cosmos-c26-eclipse-catalog-scroll");
                if (!featured || !scroll || details.recordCount !== 10
                    || countNamed(details,"cosmos-c26-eclipse-event-card") !== 10
                    || scroll.contentHeight <= scroll.height)
                    return root.fail("C26_ECLIPSE_CATALOG_NOT_SCROLLABLE");
                const y = featured.mapToItem(details,0,0).y;
                scroll.contentY = Math.min(90,scroll.contentHeight-scroll.height);
                if (scroll.contentY < 20
                    || featured.mapToItem(details,0,0).y !== y)
                    return root.fail("C26_ECLIPSE_FIXED_HIGHLIGHTS_SCROLL_WITH_LIST");
                root.phase = 9;
                root.route = "cosmos/planets-stars/celestial-fix";
            } else if (root.phase === 9) {
                if (!focused.celnav)
                    return root.fail("CELESTIAL_SOURCE_NOT_MOUNTED");
                focused.celnav.active = false;
                focused.celnav.snapshot = {
                    date:"2026-11-05",time:"13:00",planets:[
                       {name:"MARS",altitude:37.5,azimuth:203.4,direction:"SSW"},
                       {name:"JUPITER",altitude:18.2,azimuth:125.2,direction:"SE"}
                    ],
                    stars:[{name:"SIRIUS",altitude:42.1,azimuth:177.9,
                        direction:"S",constellation:"CANIS MAJOR",navStarNumber:19}],
                    constellations:[{name:"CANIS MAJOR",count:1,
                        anchorStar:"SIRIUS",anchorAltitude:42.1,
                        anchorAzimuth:177.9,anchorDirection:"S",
                        starNames:["SIRIUS"],directions:["S"]}]
                };
                focused.celnav.ready = true;
                root.phase = 10;
            } else if (root.phase === 10) {
                const details = focused.instrumentItem;
                if (!details || details.recordCount !== 2
                        || details.facts[0].value !== "37.5°"
                        || countNamed(details,"cosmos-c6-observation-cell") !== 12)
                    return root.fail("PLANET_TWELVE_FACTS_MISSING");
                details.selectedIndex = 1;
                if (details.facts[1].value !== "125.2°")
                    return root.fail("PLANET_NEXT_ITEM_MISSING");
                root.phase = 11;
                root.route = "cosmos/planets-stars/constellations";
            } else if (root.phase === 11) {
                const details = focused.instrumentItem;
                if (!details || details.recordCount !== 1
                        || details.facts[0].value !== "SIRIUS"
                        || countNamed(details,"cosmos-c6-observation-cell") !== 12)
                    return root.fail("CONSTELLATION_TWELVE_FACTS_MISSING");
                details.starsAsNav = true;
                if (details.recordCount !== 1
                        || details.facts[3].value !== "CANIS MAJOR")
                    return root.fail("STAR_NAVIGATION_DETAILS_MISSING");
                // Now exercise the new fixed plot and one contained catalog,
                // not just the backwards-compatible twelve-fact inspector.
                details.starsAsNav = false;
                const header = findNamed(details,"cosmos-c27-sky-now-sticky-header");
                const plot = findNamed(details,"cosmos-c27-sky-position-plot");
                const starPoint = findNamed(details,"cosmos-c27-plotted-usno-star");
                const anchor = findNamed(details,"cosmos-c27-featured-star-reading");
                const frame = findNamed(details,"cosmos-c27-star-catalog-frame");
                const scroll = findNamed(details,"cosmos-c27-star-catalog-scroll");
                if (!header || !plot || !starPoint || !anchor
                    || !frame || !scroll || plot.width < 70
                    || scroll.height < 20
                    || countNamed(details,"cosmos-c27-star-catalog-record") !== 1
                    || frame.y <= header.height)
                    return root.fail("C27_SKY_NOW_FIXED_INSTRUMENT_MISSING");
                const skyVisual = findNamed(details,"cosmos-c32-sky-image-panel");
                const movingStars = findNamed(details,"cosmos-c32-moving-star-field");
                const archivePhoto = findNamed(details,"cosmos-c32-hubble-archive-photo");
                const photoToggle = findNamed(details,"cosmos-c32-sky-photo-toggle");
                const pauseToggle = findNamed(details,"cosmos-c32-sky-play-pause");
                const nextToggle = findNamed(details,"cosmos-c32-hubble-next");
                if (!skyVisual || !movingStars || !archivePhoto
                    || !photoToggle || !pauseToggle || !nextToggle
                    || !skyVisual.motionRunning || !movingStars.visible
                    || !plot.visible || !starPoint.visible
                    || skyVisual.archiveFrames.length !== 2)
                    return root.fail("C32_LIVING_USNO_SKY_MISSING");
                details.visualPlaying = false;
                if (skyVisual.motionRunning || skyVisual.galleryRunning)
                    return root.fail("C32_PAUSE_SKY_FAILED");
                details.showArchive = true;
                if (!skyVisual.showArchive || skyVisual.motionRunning
                    || plot.visible || starPoint.visible
                    || skyVisual.archiveFrame.name !== "MESSIER 3")
                    return root.fail("C32_SKY_ARCHIVE_SWITCH_FAILED");
                skyVisual.nextArchive();
                if (skyVisual.archiveIndex !== 1
                    || skyVisual.archiveFrame.name !== "MESSIER 28")
                    return root.fail("C32_SKY_ARCHIVE_NEXT_FAILED");
                const starFocus = findNamed(details,
                    "cosmos-c33-stars-photo-focus");
                const starExpand = findNamed(details,
                    "cosmos-c33-stars-expand");
                if (!starFocus || !starExpand)
                    return root.fail("C33_STARS_EXPAND_ACTION_MISSING");
                details.expandedArchive = true;
                if (!starFocus.visible
                    || starFocus.width !== details.width
                    || starFocus.height !== details.height
                    || starFocus.sourceUrl !== skyVisual.archiveFrame.url)
                    return root.fail("C33_STARS_PHOTO_NOT_IN_STAGE");
                starFocus.setZoom(7);
                if (starFocus.zoom !== 4)
                    return root.fail("C33_STARS_PHOTO_ZOOM_LIMIT_BROKEN");
                starFocus.resetView();
                if (starFocus.zoom !== 1
                    || starFocus.panX !== 0 || starFocus.panY !== 0)
                    return root.fail("C33_STARS_PHOTO_FIT_BROKEN");
                starFocus.nextRequested();
                if (skyVisual.archiveIndex !== 0
                    || starFocus.photoTitle !== "MESSIER 3")
                    return root.fail("C33_STARS_EXPANDED_NEXT_BROKEN");
                starFocus.playRequested();
                if (!details.visualPlaying)
                    return root.fail("C33_STARS_EXPANDED_PLAY_BROKEN");
                starFocus.playRequested();
                starFocus.closeRequested();
                if (starFocus.visible
                    || details.expandedArchive
                    || !details.showArchive)
                    return root.fail("C33_STARS_BACK_DID_NOT_RESTORE_SKY");
                skyVisual.zoomTo(4);
                if (skyVisual.zoom !== 3)
                    return root.fail("C32_SKY_PHOTO_ZOOM_BOUND_BROKEN");
                skyVisual.resetPhoto();
                if (skyVisual.zoom !== 1 || skyVisual.panX !== 0
                    || skyVisual.panY !== 0)
                    return root.fail("C32_SKY_PHOTO_RESET_BROKEN");
                details.showArchive = false;
                details.visualPlaying = true;
                if (!plot.visible || !starPoint.visible)
                    return root.fail("C32_USNO_DOTS_NOT_RESTORED");
                details.inspectStar(0);
                if (!details.inspecting || details.recordCount !== 1
                    || details.facts[0].value !== "42.1°")
                    return root.fail("C27_USNO_STAR_PLOT_INSPECTOR_MISSING");
                details.inspecting = false;
                const s = focused.celnav.snapshot;
                const extra = [];
                for (let k=0;k<11;k++)
                    extra.push({name:"NAV SAMPLE "+k,
                        altitude:12+k,azimuth:(k*31)%360,direction:"NE",
                        constellation:"SAMPLE GROUP",navStarNumber:110+k});
                focused.celnav.snapshot = {
                    date:s.date,time:s.time,planets:s.planets,
                    constellations:s.constellations,
                    stars:s.stars.concat(extra)
                };
                root.phase = 12;
            } else if (root.phase === 12) {
                const details = focused.instrumentItem;
                const header = findNamed(details,"cosmos-c27-sky-now-sticky-header");
                const scroll = findNamed(details,"cosmos-c27-star-catalog-scroll");
                const dots = countNamed(details,"cosmos-c27-plotted-usno-star");
                if (!header || !scroll || dots !== 12
                    || countNamed(details,"cosmos-c27-star-catalog-record") !== 12
                    || scroll.contentHeight <= scroll.height)
                    return root.fail("C27_USNO_PLOT_CATALOG_NOT_POPULATED");
                const fixedY = header.mapToItem(details,0,0).y;
                scroll.contentY = Math.min(90,scroll.contentHeight-scroll.height);
                if (scroll.contentY < 20
                    || header.mapToItem(details,0,0).y !== fixedY)
                    return root.fail("C27_USNO_PLOT_HEADER_SCROLLED");
                details.inspectStar(8);
                if (!details.inspecting || details.selectedIndex !== 8
                    || details.facts[0].value !== "19.0°"
                    || countNamed(details,"cosmos-c6-observation-cell") !== 12)
                    return root.fail("C27_USNO_SAMPLE_CLICK_DETAILS_BROKEN");
                root.succeed();
            }
        }
    }
}
