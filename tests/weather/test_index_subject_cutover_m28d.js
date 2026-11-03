"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = file => fs.readFileSync(path.join(root, file), "utf8");
const navigation = read("widgets/weather/StationSubjectNavigationPolicy.js");
const preview = read("widgets/weather/StationSubjectNavigationPreviewPolicy.js");
const navigator = read("widgets/weather/StationSubjectNavigator.qml");
const terminalTests = read("tests/weather/test_tools_terminal_cutover_m28c.js");
const newsTests = read("tests/weather/test_media_news_feed_map_companion_m28b.js");
const mapTests = read("tests/weather/test_media_earth_mentions_cutover_m28a.js");
const ctx = vm.createContext({});
vm.runInContext(navigation.replace(/^\.pragma library\s*$/m, ""), ctx);
vm.runInContext(preview.replace(/^\.pragma library\s*$/m, ""), ctx);
const plain = x => JSON.parse(JSON.stringify(x));
const ids = [
  "map-news-mentions", "map-news-inspector",
  "news-topic-filter", "news-publisher-country-filter",
  "news-language-time-region-filter", "news-reporting-trend",
  "news-story-families", "news-article-viewer",
  "terminal-star-map", "terminal-context-console"
];

test("only individually reviewed M28-A/B/C controls are classified as wired", () => {
  const original = Object.keys(ctx.WIRED_IN_SUBJECTS)
    .filter(id => ["M28-A","M28-B","M28-C"].includes(ctx.WIRED_IN_SUBJECTS[id]))
    .sort();
  assert.deepEqual(original, ids.sort());
  for (const milestone of ["M28-A","M28-B","M28-C"])
    assert.ok(Object.values(ctx.WIRED_IN_SUBJECTS).includes(milestone));
  for (const id of ids) assert.ok(ctx.PANELS[id], id);
  assert.match(mapTests, /MEDIA location handoff/);
  assert.match(newsTests, /MEDIA headline list is primary/);
  assert.match(terminalTests, /TOOLS routes preserve the original STAR MAP/);
});

test("the historical M1 source map stays intact, without mislabeling all controls as migrated", () => {
  const before = JSON.stringify(ctx.PANELS);
  assert.deepEqual(plain(ctx.sourcePagesForPath("media/news", ctx.PANELS).map(x => x.id)),
    ["map","news"]);
  assert.deepEqual(plain(ctx.sourcePagesForPath("tools/terminal", ctx.PANELS).map(x => x.id)),
    ["terminal"]);
  assert.deepEqual(plain(ctx.remainingSourcePagesForPath("weather", ctx.PANELS)),
    plain(ctx.sourcePagesForPath("weather", ctx.PANELS)));
  assert.deepEqual(plain(ctx.remainingSourcePagesForPath("earth", ctx.PANELS)),
    plain(ctx.sourcePagesForPath("earth", ctx.PANELS)));
  assert.deepEqual(plain(ctx.remainingSourcePagesForPath("media/watch", ctx.PANELS)),
    plain(ctx.sourcePagesForPath("media/watch", ctx.PANELS)));
  assert.equal(JSON.stringify(ctx.PANELS), before, "source map mutated");
});

test("M28-A/B/C replaced only their own INDEX CLASSIC jumps", () => {
  assert.deepEqual(plain(ctx.remainingSourcePagesForPath("media/news", ctx.PANELS)), []);
  assert.deepEqual(plain(ctx.remainingSourcePagesForPath("tools/terminal", ctx.PANELS)), []);
  assert.deepEqual(plain(ctx.remainingSourcePagesForPath("media/news/locations", ctx.PANELS)), []);
  assert.deepEqual(plain(ctx.remainingSourcePagesForPath("tools/terminal/star-map", ctx.PANELS)), []);
  assert.deepEqual(plain(ctx.nativeDestinationsForPath("tools/terminal", ctx.PANELS).map(x => x.path)),
    ["tools/terminal/consoles", "tools/terminal/star-map"]);
  assert.deepEqual(plain(ctx.nativeDestinationsForPath("media/news/locations", ctx.PANELS)),
    [{path:"media/news/locations",panels:2,milestones:["M28-A"]}]);
  assert.ok(ctx.remainingSourcePagesForPath("media", ctx.PANELS).length > 0,
    "unreviewed MEDIA watch/radio/creator handoffs must remain reachable");
});

test("native INDEX shortcuts point to known concrete subject panels and deduplicate by destination", () => {
  const media = read("widgets/weather/StationMediaSubjectPanelPolicy.js");
  const tools = read("widgets/weather/StationToolsSubjectPanelPolicy.js");
  for (const pathId of ["media/news", "tools/terminal"]) {
    const links = plain(ctx.nativeDestinationsForPath(pathId, ctx.PANELS));
    assert.ok(links.length > 0, pathId);
    assert.equal(new Set(links.map(x => x.path)).size, links.length);
    for (const link of links) {
      const item = ctx.findRoute(link.path);
      assert.ok(item && !item.group, link.path);
      assert.ok(link.panels > 0, link.path);
      assert.ok((link.path.startsWith("media/") ? media : tools).includes('"' + link.path + '"'),
        "native pane does not register route " + link.path);
    }
  }
});

test("INDEX shows direct SUBJECTS buttons while retaining non-migrated CLASSIC links", () => {
  assert.match(navigator, /PreviewRoutes\.remainingSourcePagesForPath\(currentPath, SubjectRoutes\.PANELS\)/);
  assert.match(navigator, /PreviewRoutes\.nativeDestinationsForPath\(currentPath, SubjectRoutes\.PANELS\)/);
  assert.match(navigator, /model: browser\.nativeDestinations/);
  assert.match(navigator, /label: "OPEN SUBJECTS \/\/ "/);
  assert.match(navigator, /onClicked: browser\.chooseRoute\(modelData\.path\)/);
  assert.match(navigator, /model: browser\.classicSources/);
  assert.match(navigator, /onClicked: browser\.legacyPageRequested\(modelData\.id\)/);
  assert.match(navigator, /STILL PENDING \/\/ CLASSIC/);
  assert.ok(!preview.includes("Process {") && !preview.includes("FileView {"));
});

test("invalid paths do not leak INDEX destinations or fake completed migration", () => {
  for (const value of [null, {}, [], "weather//maps", "../media", "MEDIA", "media?news=1"]) {
    assert.deepEqual(plain(ctx.nativeDestinationsForPath(value, ctx.PANELS)), []);
    assert.deepEqual(plain(ctx.remainingSourcePagesForPath(value, ctx.PANELS)), []);
  }
  assert.deepEqual(plain(ctx.nativeDestinationsForPath("magick/astrology", ctx.PANELS)), []);
  assert.deepEqual(plain(ctx.nativeDestinationsForPath("media/news", null)), []);
});
