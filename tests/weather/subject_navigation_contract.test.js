"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const policyPath = path.resolve(__dirname, "../../widgets/weather/StationSubjectNavigationPolicy.js");
const source = fs.readFileSync(policyPath, "utf8");
const context = vm.createContext({});
vm.runInContext(source.replace(/^\.pragma library\s*$/m, ""), context, {filename:policyPath});

const plain = value => JSON.parse(JSON.stringify(value));

test("six stable subject roots are subject-first", () => {
  assert.deepEqual(plain(context.SUBJECTS.map(s => s.id)),
    ["weather","cosmos","earth","media","magick","tools"]);
  assert.equal(context.FORMAT, "post-apollo.weather.subject-navigation.v1");
});

test("every navigation path exists and identifiers are unique per sibling group", () => {
  const paths = new Set();
  function walk(route) {
    assert.equal(context.findRoute(route).path, route);
    assert.equal(paths.has(route), false, "duplicate route: " + route);
    paths.add(route);
    const rows = context.childrenOf(route);
    const ids = rows.map(row => row.path.split("/").at(-1));
    assert.equal(new Set(ids).size, ids.length, "duplicate child: " + route);
    rows.forEach(row => walk(row.path));
  }
  context.SUBJECTS.forEach(s => walk(s.id));
  assert.ok(paths.size >= 100);
});

test("all existing legacy modes have deterministic landing hints", () => {
  for (const id of ["home","ground","sky","space","map","news","radio","terminal"])
    assert.ok(context.findRoute(context.legacyLanding(id)), id);
  assert.equal(context.legacyLanding("random"), "");
});

test("every migrated panel has a valid owner route", () => {
  const panels = Object.keys(context.PANELS);
  assert.ok(panels.length >= 90);
  for (const panel of panels)
    assert.ok(context.findRoute(context.panelLanding(panel)), panel);
  assert.equal(context.panelLanding("missing-control"), "");
});

test("mixed legacy pages split by subject, rather than moving whole pages", () => {
  assert.equal(context.panelLanding("sky-hourly-forecast"), "weather/forecasts/hourly");
  assert.equal(context.panelLanding("sky-moon-usno"), "cosmos/moon/ephemeris");
  assert.equal(context.panelLanding("ground-usgs-seismic"), "earth/geology/earthquakes");
  assert.equal(context.panelLanding("ground-coast-coops"), "weather/water/coast");
  assert.equal(context.panelLanding("map-mrms-radar"), "weather/maps/radar");
  assert.equal(context.panelLanding("map-eonet-layer"), "earth/events/eonet");
  assert.equal(context.panelLanding("map-news-mentions"), "media/news/locations");
});

test("per-subject navigation remembers context and rejects cross-subject pollution", () => {
  assert.equal(context.resumeSubject("weather", {weather:"weather/water/rivers/hydrograph"}),
    "weather/water/rivers/hydrograph");
  assert.equal(context.resumeSubject("cosmos", {cosmos:"weather/water/rivers/hydrograph"}),
    "cosmos/overview");
  assert.equal(context.resumeSubject("magick", {}),
    "magick/overview");
  assert.equal(context.resumeSubject("unknown", {}),
    "");
});

test("breadcrumbs and nested navigation are stable", () => {
  assert.deepEqual(plain(context.breadcrumbs("weather/water/rivers/hydrograph").map(x => x.path)),
    ["weather","weather/water","weather/water/rivers","weather/water/rivers/hydrograph"]);
  assert.deepEqual(plain(context.childrenOf("cosmos/moon").map(x => x.path)),
    ["cosmos/moon/ephemeris","cosmos/moon/position"]);
  assert.deepEqual(plain(context.breadcrumbs("not-real")), []);
});

test("invalid paths are refused rather than interpreted or executed", () => {
  for (const value of ["",null,"weather//water","weather/../moon","weather/water?x=1","WEATHER",
                        "magick/nonexistent",{},["cosmos","moon"]])
    assert.equal(context.findRoute(value), null);
});

test("cross-subject reuse is explicit and keeps source ownership independent", () => {
  assert.deepEqual(plain(context.relatedRoutes("moon")),
    ["cosmos/moon","magick/lunar-solar/moon","magick/astrology/charts"]);
  assert.deepEqual(plain(context.relatedRoutes("news-location")),
    ["media/news/locations","earth/maps/overview"]);
  assert.deepEqual(plain(context.relatedRoutes("unknown")), []);
});

test("contract is passive: no mutation or Quickshell executable commands", () => {
  for (const forbidden of ["Process {","curl ","swaymsg","launchProcess","FileView {","Qt.callLater","new XMLHttpRequest"])
    assert.equal(source.includes(forbidden), false, "found forbidden: " + forbidden);
  assert.equal(context.findRoute("magick/astrology/retrogrades").status, "SPEC_ONLY");
});
