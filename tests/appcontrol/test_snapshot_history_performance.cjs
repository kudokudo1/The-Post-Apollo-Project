'use strict';

// Source contract and deterministic compatibility test for AppControl's
// read-only HUNTER history compaction. No live process or QML instance needed.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..');
const graph = fs.readFileSync(path.join(root, 'widgets/appcontrol/TaskGraphController.qml'), 'utf8');
const app = fs.readFileSync(path.join(root, 'widgets/AppControlW.qml'), 'utf8');

const begin = graph.indexOf('    function updateMiniHunterMetricHistories(rows) {');
const finish = graph.indexOf('\n    function miniCpuHistoryByIdentity(', begin);
assert.ok(begin >= 0 && finish > begin, 'find exact HUNTER updater');
const functionText = graph.slice(begin, finish);

function makeUpdater(state) {
    const presenter = { elapsedSeconds: value => Number(value || 0) };
    return new Function('presentationState', 'hunterPresentation',
        functionText + '\nreturn updateMiniHunterMetricHistories;')(state, presenter);
}

function legacyUpdate(rows, state) {
    const sourceRows = Array.isArray(rows) ? rows : [];
    const previous = state.taskMiniHunterMetricHistories;
    const next = Object.assign({}, previous);
    const livePids = ({});
    function append(metric, pid, value) {
        const key = metric + ':pid:' + String(pid);
        const history = Array.isArray(previous[key]) ? previous[key].slice() : [];
        history.push(Math.max(0, Number(value || 0)));
        while (history.length > state.taskMiniHistoryLimit) history.shift();
        next[key] = history;
    }
    for (const entry of sourceRows) {
        const pid = Number(entry && entry.pid || 0);
        if (pid <= 0) continue;
        livePids[String(pid)] = true;
        const cpu = Math.max(0, Number(entry.cpuInstant !== undefined ? entry.cpuInstant : entry.cpu || 0));
        const memMiB = Math.max(0, Number(entry.rss || 0)) / 1024.0;
        const ioMiB = Math.max(0, Number(entry.ioRate || 0)) / (1024.0 * 1024.0);
        const ageMinutes = Math.max(0, entry.ageSeconds !== undefined
            ? Number(entry.ageSeconds || 0) : Number(entry.elapsed || 0)) / 60.0;
        const combined = cpu + Math.max(0, Number(entry.mem || 0)) * 0.35 + Math.log(1 + ioMiB) * 3.0;
        append('cpu', pid, cpu);
        append('mem', pid, memMiB);
        append('io', pid, ioMiB);
        append('age', pid, ageMinutes);
        append('combined', pid, combined);
    }
    const keys = Object.keys(next);
    for (const key of keys) {
        const pieces = String(key).split(':pid:');
        if (pieces.length !== 2) continue;
        const pidText = pieces[1];
        if (!livePids[pidText] && Number(pidText || 0) !== state.taskHistoryPid)
            delete next[key];
    }
    state.taskMiniHunterMetricHistories = next;
}

function state() {
    return {
        taskMiniHistoryLimit: 48,
        taskHistoryPid: 202,
        taskMiniHunterMetricHistories: {
            'cpu:pid:101': [1, 2], 'cpu:pid:202': [3, 4],
            'cpu:pid:404': [5, 6], 'io:pid:202': [12],
            'legacy-extra': [11], 'odd:pid:5:pid:6': [13],
        },
    };
}

function entries(round) {
    const out = [];
    for (let i = 0; i < 600; ++i) {
        if (i === 202 || (round % 7 === 0 && i % 9 === 0)) continue;
        const pid = i + 1 + (round % 5 === 0 ? 600 : 0);
        out.push({pid, cpu: (i * 3 + round) % 103, mem: i / 13,
            rss: 800 + i * 31, ioRate: i * 250,
            ageSeconds: round * 180 + i * 2});
    }
    return out;
}

test('compacted history update matches legacy outputs through churn and cap', () => {
    const actual = state();
    const expected = state();
    const run = makeUpdater(actual);
    for (let round = 0; round < 62; ++round) {
        const sample = entries(round);
        run(sample);
        legacyUpdate(sample, expected);
        assert.deepStrictEqual(actual.taskMiniHunterMetricHistories,
            expected.taskMiniHunterMetricHistories, 'snapshot round ' + round);
        for (const [key, history] of Object.entries(actual.taskMiniHunterMetricHistories)) {
            if (key.includes(':pid:') && key.split(':pid:').length === 2)
                assert.ok(history.length <= 48, 'bounded ' + key);
        }
    }
});

test('history update is single-pass and preserves selected and non-process state', () => {
    assert.ok(functionText.includes('const next = immutable ? ({}) : previous;'));
    assert.ok(functionText.includes('const selectedPid = Number(presentationState.taskHistoryPid || 0);'));
    assert.ok(!functionText.includes('Object.assign({}, previous)'));
    assert.ok(!functionText.includes('const pieces = key.split(":pid:")'));
    assert.ok(functionText.includes('const livePids = immutable ? null : ({});'),
        'PID membership allocated only for hidden in-place cleanup');
    const stateObj = state();
    makeUpdater(stateObj)([{pid: 101, cpu: 12, mem: 1, rss: 1024, ioRate: 0, ageSeconds: 70}]);
    assert.deepStrictEqual(stateObj.taskMiniHunterMetricHistories['cpu:pid:202'], [3, 4]);
    assert.equal(stateObj.taskMiniHunterMetricHistories['cpu:pid:404'], undefined);
    assert.deepStrictEqual(stateObj.taskMiniHunterMetricHistories['legacy-extra'], [11]);
});

test('hidden HUNTER sampling reuses bounded arrays while matching legacy snapshots', () => {
    const actual = state();
    actual.taskMiniHistoryKeepImmutable = false;
    const expected = state();
    const run = makeUpdater(actual);
    const first = entries(1);
    run(first);
    legacyUpdate(first, expected);
    const key = 'cpu:pid:11';
    const existing = actual.taskMiniHunterMetricHistories[key];
    const map = actual.taskMiniHunterMetricHistories;
    for (let round = 2; round < 62; ++round) {
        const sample = entries(round);
        run(sample);
        legacyUpdate(sample, expected);
        assert.deepStrictEqual(actual.taskMiniHunterMetricHistories,
            expected.taskMiniHunterMetricHistories, 'hidden round ' + round);
        assert.equal(actual.taskMiniHunterMetricHistories, map,
            'hidden map remains stable');
        if (round === 2)
            assert.equal(actual.taskMiniHunterMetricHistories[key], existing,
                'live PID array reused in hidden mode');
    }
    assert.ok(existing.length <= 48);
    assert.deepStrictEqual(actual.taskMiniHunterMetricHistories['cpu:pid:202'],
        expected.taskMiniHunterMetricHistories['cpu:pid:202'],
        'selected PID remains retained after process churn');
});

test('hidden CPU sampling preserves PID and FAVORITES identity histories', () => {
    const cpuStart = graph.indexOf('    function updateMiniCpuHistories(rows) {');
    const cpuEnd = graph.indexOf('    function updateMiniHunterMetricHistories(', cpuStart);
    const cpuText = graph.slice(cpuStart, cpuEnd);
    const run = new Function('presentationState', 'persistentIdentity',
        cpuText + '\nreturn updateMiniCpuHistories;');
    const stateObj = {
        taskMiniHistoryLimit: 3,
        taskMiniHistoryKeepImmutable: false,
        taskMiniCpuHistories: ({}),
        taskMiniCpuIdentityHistories: ({})
    };
    const update = run(stateObj, entry => String(entry.comm || '').toLowerCase());
    const map = stateObj.taskMiniCpuHistories;
    const ids = stateObj.taskMiniCpuIdentityHistories;
    for (const cpu of [1, 2, 3, 4]) {
        update([{pid: 10, comm: 'Brave', cpuInstant: cpu},
                {pid: 20, comm: 'Brave', cpuInstant: cpu + 1}]);
    }
    assert.deepStrictEqual(map['pid:10'], [2, 3, 4]);
    assert.deepStrictEqual(ids['identity:brave'], [3, 4, 5]);
    const history = map['pid:10'];
    update([{pid: 10, comm: 'Brave', cpuInstant: 5}]);
    assert.equal(map['pid:10'], history, 'in-place hidden CPU history');
    assert.equal(stateObj.taskMiniCpuHistories, map, 'stable hidden PID map');
    assert.equal(stateObj.taskMiniCpuIdentityHistories, ids, 'stable identity map');
    assert.equal(map['pid:20'], undefined, 'dead PIDs pruned');
    assert.deepStrictEqual(ids['identity:brave'], [4, 5, 5]);

    stateObj.taskMiniHistoryKeepImmutable = true;
    const before = stateObj.taskMiniCpuHistories['pid:10'];
    update([{pid: 10, comm: 'Brave', cpuInstant: 6}]);
    assert.notEqual(stateObj.taskMiniCpuHistories, map, 'visible map replaced');
    assert.notEqual(stateObj.taskMiniCpuHistories['pid:10'], before,
        'visible array copy-on-write');
    assert.deepStrictEqual(before, [3, 4, 5],
        'previous visible snapshot remains immutable');
});

test('menu visibility binds immutable graph presentation policy', () => {
    assert.match(app, /taskMiniHistoryKeepImmutable:\s*appControlWindow\.menuOpen/);
    assert.match(graph, /if \(immutable\) \{/);
});

test('AppControl six stage markers remain opt-in and preserve model assignment', () => {
    assert.ok(app.includes('Quickshell.env("POST_APOLLO_SUBPROCESS_LAG_PROBE")'));
    assert.ok(app.includes('readonly property bool appControlSnapshotTraceEnabled:'));
    assert.ok(app.includes('if (sequence <= 0)\n            return;'));
    assert.ok(app.includes('SYNTAGMA_COMPLETION_PROBE // service=appcontrol'));
    const body = app.split('function applyTaskSnapshot(rows) {', 2)[1].split(
        '// ============================================================', 1)[0];
    const order = ['cpu-history', 'hunter-history', 'history-revisions',
        'task-order', 'task-rows', 'metric-alerts'];
    let prev = -1;
    for (const step of order) {
        const ix = body.indexOf('traceTaskSnapshotDuration("' + step + '"');
        assert.ok(ix > prev, 'ordered stage: ' + step);
        prev = ix;
    }
    assert.ok(body.indexOf('taskRows = snapshotRows;') > body.indexOf('traceTaskSnapshotDuration("task-order"'));
    assert.ok(body.indexOf('taskRows = snapshotRows;') < body.indexOf('traceTaskSnapshotDuration("task-rows"'));
    assert.ok(body.includes('Qt.callLater(function() {'));
    assert.ok(body.includes('checkTaskMetricAlerts(snapshotRows);'));
    assert.ok(body.includes('taskMiniHistoryRevision += 1;'));
    assert.ok(body.includes('taskMiniDisplayRevision += 1;'));
});

test('mini graph lookup preserves old scan results and rebuilds on snapshot replacement', () => {
    const start = graph.indexOf('    function sourceItem(entry) {');
    const end = graph.indexOf('    // Hidden state', start);
    assert.ok(start >= 0 && end > start);
    const create = new Function('rows', 'count', graph.slice(start, end) + `
        const originalIdentity = persistentIdentity;
        persistentIdentity = function(entry) {
            count.calls++;
            return originalIdentity(entry);
        };
        const miniTaskLookup = buildMiniTaskLookup(rows);
        return { resolve: liveTaskForMiniGraph, identity: originalIdentity,
                 entryIdentity: identityForEntry, source: sourceItem };
    `);
    const row = (pid, comm, cpu) => ({pid, comm, cpu, _taskRecord: true});
    const favorite = (source, key) => ({_favoriteRecord: true,
        _favoriteType: 'task', _favoriteKey: 'task|' + encodeURIComponent(key),
        _sourceItem: source});
    const first = row(9, 'Brave', 4);
    const tied = row(10, 'BRAVE', 8);
    const rows = [null, first, row(9, 'other', 100), tied,
        row(11, 'brave', 8), row(1, 'init', 1), row(0, 'brave', 999),
        row(14, '__proto__', 7), {pid: 15, args: '/usr/bin/tool --x',
            cpu: 3, _taskRecord: true}];
    const entries = [...rows, {}, row(999, 'brave', 9),
        favorite(row(999, 'old', 0), 'BRAVE'),
        favorite(row(9, 'old', 0), 'brave'),
        favorite(row(999, 'old', 0), '__proto__'),
        favorite(row(999, 'old', 0), 'tool'),
        favorite(row(999, 'old', 0), 'missing'),
        favorite(row(0, 'init', 0), 'init')];
    function oldScan(entry, rows, helpers) {
        const source = helpers.source(entry) || entry;
        if (!source || !source._taskRecord) return null;
        const pid = Number(source.pid || 0);
        if (pid > 1) {
            for (const exact of rows) {
                if (Number(exact && exact.pid || 0) === pid) return exact;
            }
            if (!entry._favoriteRecord) return source;
        }
        const identity = helpers.entryIdentity(entry);
        if (identity) {
            let best = null;
            for (const candidate of rows) {
                if (helpers.identity(candidate) !== identity) continue;
                if (Number(candidate.pid || 0) <= 0) continue;
                if (!best || Number(candidate.cpu || 0) > Number(best.cpu || 0))
                    best = candidate;
            }
            if (best) return best;
        }
        return source;
    }
    const count = {calls: 0};
    const indexed = create(rows, count);
    assert.equal(count.calls, rows.length, 'one index pass');
    for (const entry of entries)
        assert.equal(indexed.resolve(entry), oldScan(entry, rows, indexed));
    assert.equal(indexed.resolve(favorite(row(999, 'old', 0), 'brave')), tied);
    assert.equal(indexed.resolve(first), first, 'first duplicate PID wins');
    count.calls = 0;
    for (let repeat = 0; repeat < 100; repeat++)
        assert.equal(indexed.resolve(first), first);
    assert.equal(count.calls, 0, 'exact-PID readers do not rescan identities');
    const replacement = [row(25, 'brave', 100)];
    const updated = create(replacement, {calls: 0});
    const stale = favorite(first, 'brave');
    assert.equal(updated.resolve(stale), replacement[0]);
    assert.equal(indexed.resolve(stale), first);
    assert.match(graph, /readonly property var miniTaskLookup:\s*buildMiniTaskLookup\(taskRows\)/);
    assert.match(app, /taskRows:\s*appControlWindow\.taskRows/);
    assert.match(app, /taskRows = snapshotRows;/);
});

test('mini COMBI histories copy only on demand and preserve snapshot isolation', () => {
    const start = app.indexOf('                            function snapshotCombiHistory(live) {');
    const end = app.indexOf('                            function refreshHistory(animateScroll) {', start);
    assert.ok(start >= 0 && end > start, 'locate exact mini canvas helper');
    const create = new Function('combiView', 'emptyCombiHistories', 'taskGraphController',
        app.slice(start, end) + '\nreturn snapshotCombiHistory;');
    const empty = {cpu: [], mem: [], io: [], age: []};
    const source = {cpu: [1, 2, 3], mem: [4, 5], io: [0], age: [9, 10]};
    const entry = {pid: 99};
    let calls = [];
    const controller = {
        miniHunterHistoryForMetric: (live, metric) => {
            assert.equal(live, entry);
            calls.push(metric);
            return source[metric];
        }
    };
    const off = create(false, empty, controller);
    for (let n = 0; n < 100; n++)
        assert.equal(off(entry), empty, 'stable inactive history object');
    assert.deepStrictEqual(calls, [], 'no metric retrieval or copying outside COMBI');
    const on = create(true, empty, controller);
    const active = on(entry);
    assert.deepStrictEqual(calls, ['cpu', 'mem', 'io', 'age']);
    assert.deepStrictEqual(active, source, 'all four histories preserved');
    for (const metric of Object.keys(source))
        assert.notEqual(active[metric], source[metric], 'local copy ' + metric);
    source.cpu.push(4);
    assert.deepStrictEqual(active.cpu, [1, 2, 3], 'active readers keep snapshot');
    assert.equal(off(entry), empty, 'exit drops local copies');
    assert.deepStrictEqual(on(entry).cpu, [1, 2, 3, 4], 're-entry sees latest samples');
    const refresh = app.slice(end, app.indexOf('// Keep the same three-quarter grid', end));
    assert.match(refresh, /const nextCombi = snapshotCombiHistory\(live\);/);
    assert.match(refresh, /if \(combiHistories !== nextCombi\)\s+combiHistories = nextCombi;/);
    assert.match(refresh, /onCombiViewChanged:\s*\{\s*if \(graphReady\)\s*refreshHistory\(false\);/);
    assert.match(refresh, /Component\.onCompleted:\s*\{\s*graphReady = true;\s*refreshHistory\(false\);/);
    assert.match(refresh, /onHistoryRevisionChanged: refreshHistory\(true\)/);
    assert.match(refresh, /onTaskIdentityChanged\(\)/);
    assert.match(refresh, /onRowItemChanged\(\)/);
});
