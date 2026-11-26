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

test('Hunter display short circuits preserve thresholds and protection classes', () => {
    const start=app.indexOf('    function hunterTaskActive(entry) {');
    const end=app.indexOf('    function hunterMetricAccent()',start);
    assert.ok(start>=0&&end>start);
    const create=new Function('counts',app.slice(start,end)+`
        const hunterMetricCombined=0,hunterMetricCpu=1,hunterMetricMemory=2,
              hunterMetricIo=3,hunterMetricAge=4;
        const hunterVisibilityProtected=1,hunterVisibilityAll=2;
        let hunterMetricMode=0,hunterVisibilityMode=0;
        function hunterTaskPeak(e){counts.peak++;return e.peak;}
        function hunterTaskAverage(e){counts.avg++;return e.avg;}
        function hunterTaskMemoryMiB(e){counts.mem++;return e.mem;}
        function hunterTaskIoRate(e){return e.io;}
        function taskElapsedSeconds(v){return Number(v);}
        function taskRequiresDangerUnlock(e){counts.protected++;return e.protected;}
        return {active:hunterTaskActive,visible:hunterTaskClassVisible,
            metric(v){hunterMetricMode=v;},visibility(v){hunterVisibilityMode=v;}};
    `);
    const counts={peak:0,avg:0,mem:0,protected:0};
    const model=create(counts);
    const rows=[null,{},...Array.from({length:600},(_,i)=>({
        _taskRecord:i%13!==0,peak:[0,.34,.35,NaN][i%4],
        avg:[0,.14,.15,NaN][Math.floor(i/4)%4],mem:[0,15,16,127,128,NaN][Math.floor(i/16)%6],
        io:i%2?1023:1024,elapsed:i%3?'0':'1',protected:i%4===0
    }))];
    function oldActive(e,mode) {
        if(!e||!e._taskRecord)return false;
        if(mode===2)return e.mem>=16;
        if(mode===3)return e.io>=1024;
        if(mode===4)return Number(e.elapsed)>0;
        return e.peak>=.35||e.avg>=.15||(mode===0&&e.mem>=128);
    }
    function oldVisible(e,mode) {
        if(!e||!e._taskRecord)return false;
        if(mode===1)return e.protected;
        if(mode===2)return true;
        return !e.protected;
    }
    for(let mode=0;mode<5;mode++){
        model.metric(mode);
        for(const row of rows)assert.equal(model.active(row),oldActive(row,mode));
    }
    for(let mode=0;mode<3;mode++){
        model.visibility(mode);
        for(const row of rows)assert.equal(model.visible(row),oldVisible(row,mode));
    }
    model.metric(0);
    model.visibility(2);
    Object.keys(counts).forEach(k=>counts[k]=0);
    const sufficient={_taskRecord:true,mem:128,peak:0,avg:0,protected:true};
    assert.equal(model.active(sufficient),true);
    assert.equal(model.visible(sufficient),true);
    assert.equal(counts.peak,0);
    assert.equal(counts.avg,0);
    assert.equal(counts.protected,0);
    model.metric(1);
    model.visibility(1);
    assert.equal(model.active(sufficient),false);
    assert.equal(model.visible(sufficient),true);
    assert.equal(counts.peak,1);
    assert.equal(counts.avg,1);
    assert.equal(counts.protected,1);
    const gate=app.slice(app.indexOf('function taskEligibleForKillAll(entry)'),app.indexOf('function killAllEligibleTasks()'));
    assert.match(gate,/return !taskProtectedFromKillAll\(entry\)/);
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

test('mini COMBI histories align once on demand and preserve snapshot isolation', () => {
    const start = app.indexOf('                            function snapshotCombiHistory(live) {');
    const end = app.indexOf('                            function refreshHistory(animateScroll) {', start);
    assert.ok(start >= 0 && end > start, 'locate exact mini canvas helper');
    const create = new Function('combiView', 'emptyCombiHistories', 'taskGraphController',
        app.slice(start, end) + '\nreturn snapshotCombiHistory;');
    const empty = {cpu: [], mem: [], io: [], age: []};
    const source = {cpu: [1, 2, 3], mem: [4, 5], io: [0], age: [9, 10]};
    const entry = {pid: 99};
    let calls = [];
    let copies = 0;
    const controller = {
        miniHunterHistoryForMetric: (live, metric) => {
            assert.equal(live, entry);
            calls.push(metric);
            return new Proxy(source[metric], {
                get(target, key, receiver) {
                    if (key === 'slice') copies++;
                    return Reflect.get(target, key, receiver);
                }
            });
        }
    };
    function legacyVisible() {
        const length = Math.min(...Object.values(source).map(v => v.length));
        return Object.fromEntries(Object.entries(source).map(([key,value]) =>
            [key,value.slice(value.length-length)]));
    }
    const off = create(false, empty, controller);
    for (let n = 0; n < 100; n++)
        assert.equal(off(entry), empty, 'stable inactive history object');
    assert.deepStrictEqual(calls, [], 'no metric retrieval or copying outside COMBI');
    const on = create(true, empty, controller);
    const expected = legacyVisible();
    const active = on(entry);
    assert.deepStrictEqual(calls, ['cpu', 'mem', 'io', 'age']);
    assert.equal(copies,4,'one isolated copy per series');
    assert.deepStrictEqual(active, expected, 'same common tail as previous renderer');
    for (const metric of Object.keys(source))
        assert.notEqual(active[metric], source[metric], 'local copy ' + metric);
    source.cpu.push(4);
    assert.deepStrictEqual(active,expected,'active readers keep snapshot');
    assert.equal(off(entry), empty, 'exit drops local copies');
    assert.deepStrictEqual(on(entry), legacyVisible(), 're-entry sees latest samples');
    for (const length of [0,1,2,47,48]) {
        for (const [i,key] of Object.keys(source).entries())
            source[key]=Array.from({length:length===0&&i===0?0:length+i},(_,n)=>n+i);
        copies=0;
        assert.deepStrictEqual(on(entry),legacyVisible(),'aligned length '+length);
        assert.equal(copies,length===0?0:4);
    }
    const refresh = app.slice(end, app.indexOf('// Keep the same three-quarter grid', end));
    assert.match(refresh, /const nextCombi = snapshotCombiHistory\(live\);/);
    assert.match(refresh, /historyFrame = \{\s*values: Array.isArray\(next\) \? next.slice\(\) : \[\],\s*combi: nextCombi\s*\};/);
    assert.match(refresh, /onCombiViewChanged:\s*\{\s*if \(graphReady\)\s*refreshHistory\(false\);/);
    assert.match(refresh, /Component\.onCompleted:\s*\{\s*graphReady = true;\s*refreshHistory\(false\);/);
    assert.match(refresh, /onHistoryRevisionChanged: refreshHistory\(true\)/);
    assert.match(refresh, /onTaskIdentityChanged\(\)/);
    assert.match(refresh, /onRowItemChanged\(\)/);
    const traceStart=app.indexOf('readonly property var metricHistory:',app.indexOf('id: miniCombiTrace'));
    const trace=app.slice(traceStart,app.indexOf('readonly property var metricPoints:',traceStart));
    assert.match(trace,/combiHistories\[modelData.metric\]/);
    assert.doesNotMatch(trace,/\.slice\(|commonLength|for\s*\(/);
});

test('mini graph scroll moves one trace layer, not every rectangle', () => {
    const start = app.indexOf('id: killMiniCpuCanvas');
    const stop = app.indexOf('id: selectorAppIconBox', start);
    assert.ok(start >= 0 && stop > start);
    const mini = app.slice(start, stop);
    const layerStart = mini.indexOf('id: miniTraceLayer');
    assert.ok(layerStart > 0);
    const controls = mini.slice(0, layerStart);
    const trace = mini.slice(layerStart);
    assert.match(controls, /clip: true/);
    assert.match(controls, /duration: appControlWindow.taskMiniGraphScrollDuration/);
    assert.match(controls, /model: 3\s+delegate: Rectangle/);
    assert.match(controls, /readonly property bool fillReady:\s*graphPoints.length >= 2/);
    assert.match(trace, /anchors.fill: parent\s+transform: Translate \{\s*x: killMiniCpuCanvas.graphScrollOffset\s*\}/);
    assert.equal((mini.match(/killMiniCpuCanvas\.graphScrollOffset/g) || []).length, 1,
        'only one animated geometry dependency per mini graph');
    assert.match(trace, /model:\s*killMiniCpuCanvas.combiView\s*\? killMiniCpuCanvas.combiSeries : \[\]/);
    assert.match(trace, /x:\s*graphPoint.x\s*- width \/ 2\s+y: graphPoint.y/);
    assert.match(trace, /x:\s*leftX\s+y: topY/);
    assert.equal((trace.match(/x:\s*parent\.p1\.x\s+y: parent\.p1\.y/g) || []).length, 4);
    assert.match(trace, /rotation: parent.segmentAngle/);
    assert.match(trace, /transformOrigin: Item.Left/);
    assert.match(trace, /killMiniCpuCanvas\.graphPoints.length - 1/);
    // The polling, history and destructive-action owners remain outside this
    // presentation change. Never reduce safety refreshes to improve rendering.
    assert.match(app, /\? 600\s*:\s*appControlWindow.menuOpen/);
    assert.match(app, /id: taskMiniDisplayTimer[\s\S]*?interval: 1200/);
});

test('explicit Kill ranking snapshots score once per eligible task and retains legacy order', () => {
    const start=app.indexOf('    function killTaskRankKey(');
    const end=app.indexOf('    // HUNTER answers two separate questions',start);
    assert.ok(start>=0 && end>start);
    const create=new Function('initial','active','counter',app.slice(start,end)+`
        const killViewNormal=0,killViewHunter=1;
        let killViewMode=killViewHunter, taskRows=initial,killTaskOrderIds=[];
        function killTaskVisibleForView(entry,mode) {
            counter.visible++;
            return !!entry && (mode===killViewNormal || active(entry));
        }
        function hunterTaskMetricScore(entry) {counter.score++; return entry.score;}
        return {
            rebuild(mode) {rebuildKillTaskOrderSnapshot(mode);return killTaskOrderIds.slice();},
            append(rows) {appendNewKillTaskOrderIds(rows);return killTaskOrderIds.slice();},
            mode(value) {killViewMode=value;}
        };
    `);
    const id=e=>String(e.id || ('task:'+String(e.pid||0)));
    const rows=Array.from({length:600},(_,i)=>({pid:i+2,
        cpu:i%13,mem:i%7,score:(i*17)%41,active:i%3!==0,
        ...(i%5===0?{id:'task:'+String(i+2)}:{})}));
    const eligible=e=>e.active;
    function legacyRank(mode){
        return rows.filter(e=>mode===0||eligible(e)).sort((a,b)=>{
            if(mode===1){const delta=b.score-a.score;if(Math.abs(delta)>0.001)return delta;}
            const cpu=Number(b.cpu||0)-Number(a.cpu||0);
            if(Math.abs(cpu)>0.001)return cpu;
            const mem=Number(b.mem||0)-Number(a.mem||0);
            if(Math.abs(mem)>0.001)return mem;
            return Number(a.pid||0)-Number(b.pid||0);
        }).map(id);
    }
    const count={score:0,visible:0};
    const actual=create(rows,eligible,count);
    assert.deepStrictEqual(actual.rebuild(0),legacyRank(0));
    assert.equal(count.score,0);
    count.visible=0;
    const ranked=actual.rebuild(1);
    assert.deepStrictEqual(ranked,legacyRank(1));
    assert.equal(count.score,ranked.length,'one score per admitted task');
    assert.equal(count.visible,rows.length);
    count.visible=0;
    assert.deepStrictEqual(actual.append(rows),ranked,'unchanged snapshot keeps slots');
    assert.equal(count.visible,rows.length-ranked.length,'known rows skip eligibility');
    const changed=[...rows.map(e=>({...e,active:!e.active})),
        {pid:1002,active:true},{pid:1001,active:true},{pid:1001,active:true},null];
    const known=new Set(ranked);
    const expected=ranked.slice();
    for(const entry of changed.filter(e=>e&&eligible(e)&&!known.has(id(e)))
        .sort((a,b)=>a.pid-b.pid)){
        if(!known.has(id(entry))){known.add(id(entry));expected.push(id(entry));}
    }
    assert.deepStrictEqual(actual.append(changed),expected,'late eligibility, duplicates and churn retain old order');
    actual.mode(0);
    assert.deepStrictEqual(actual.append([null,{pid:9000,active:false}]),[...expected,'task:9000']);
    const model=app.slice(app.indexOf('id: killTaskResults'),app.indexOf('id: thermalResults'));
    assert.match(model,/if \(appControlWindow.killTaskModelBlank\)/);
    assert.match(model,/hunterTaskActive\(entry\)\s*&& appControlWindow.hunterTaskClassVisible\(entry\)/);
    assert.match(model,/objectProp: "id"/);
});

test('visible Kill model resolves each stable slot once without changing display order', () => {
    const start = app.indexOf('    function buildKillTaskOrderPositions(');
    const end = app.indexOf('    function killTaskVisibleForView(', start);
    assert.ok(start >= 0 && end > start);
    const make = new Function(app.slice(start,end) +
        '\nreturn {build:buildKillTaskOrderPositions,order:orderVisibleKillRows};');
    const actual = make();
    const order = Array.from({length:600}, (_,i) => 'task:'+(601-i));
    order.push('task:20'); // last duplicate slot wins as before
    const rows = Array.from({length:600}, (_,i) => ({pid:i+2,
        ...(i%3===0?{id:'task:'+(i+2)}:{})}));
    rows.push({pid:20,label:'duplicate known'}, {pid:9999}, {pid:9998},
        {pid:9999,label:'duplicate unknown'});
    const id = e => String(e.id || ('task:'+String(e.pid||0)));
    const positions = {};
    order.forEach((v,i)=>positions[String(v)]=i);
    function legacy(source) {
        return source.slice().sort((a,b)=>{
            const x=positions[id(a)],y=positions[id(b)];
            if(x!==undefined&&y!==undefined)return x-y;
            if(x!==undefined)return -1;
            if(y!==undefined)return 1;
            return Number(a.pid||0)-Number(b.pid||0);
        });
    }
    const cached = actual.build(order);
    let reads = 0;
    const observed = new Proxy(cached,{get(target,key){reads++;return target[key];}});
    for (const source of [rows,rows.filter(e=>e.pid%3===0),rows.slice().reverse(),[]]) {
        reads=0;
        const result=actual.order(source,observed);
        const expected=legacy(source);
        assert.deepStrictEqual(result,expected);
        result.forEach((entry,i)=>assert.equal(entry,expected[i],'same row object'));
        assert.equal(reads,source.length,'one slot lookup per filtered row');
    }
    assert.equal(cached['task:20'],order.length-1);
    const changed=actual.build(['task:9999','task:20']);
    assert.equal(actual.order(rows,changed)[0].pid,9999);
    assert.equal(cached['task:20'],order.length-1,'old index not mutated');
    const model=app.slice(app.indexOf('id: killTaskResults'),app.indexOf('id: thermalResults'));
    assert.match(app,/readonly property var killTaskOrderPositions:\s*buildKillTaskOrderPositions\(killTaskOrderIds\)/);
    assert.match(model,/orderVisibleKillRows\(\s*rows, appControlWindow.killTaskOrderPositions/);
    assert.match(model,/hunterTaskActive\(entry\)\s*&& appControlWindow.hunterTaskClassVisible\(entry\)/);
    assert.match(model,/if \(appControlWindow.killTaskModelBlank\)/);
});


test('opt-in AppControl opening markers preserve synchronous operation order', () => {
    const begin = app.indexOf('    function traceAppControlOpen(');
    const end = app.indexOf('    function applyTaskSnapshot(', begin);
    assert.ok(begin >= 0 && end > begin);
    let clockReads = 0;
    const messages = [];
    const trace = new Function('Date', 'console', 'diagnosticCaptureActive', 'appControlSnapshotTraceEnabled', 'diagnosticOpeningStage', app.slice(begin, end)
        + '\nreturn traceAppControlOpen;')(
        {now: () => { clockReads++; return 150; }},
        {warn: message => messages.push(message)}, false, true, () => {});
    assert.equal(trace('selection', 0, 100), 0);
    assert.equal(clockReads, 0);
    assert.equal(messages.length, 0);
    assert.equal(trace('selection', 7, 100), 150);
    assert.equal(clockReads, 1);
    assert.deepEqual(messages, [
        'SYNTAGMA_COMPLETION_PROBE // service=appcontrol stage=open:selection:end seq=7 elapsedMs=50 tsMs=150'
    ]);
    const opening = app.slice(app.indexOf('    onMenuOpenChanged: {'),
        app.indexOf('        } else {\n            recentModeIndex', app.indexOf('    onMenuOpenChanged: {')));
    assert.match(opening, /const openTrace = \(appControlSnapshotTraceEnabled \|\| diagnosticCaptureActive\)\s*\? \+\+appControlOpenTraceSequence : 0/);
    assert.match(opening, /const openStart = openTrace \? Date\.now\(\) : 0/);
    let prev = -1;
    for (const marker of [
        'taskMiniHistoryRevision += 1',
        'traceAppControlOpen("graph-invalidation"',
        'restoreInputForMode(selectedModeIndex)',
        'traceAppControlOpen("mode-restore"',
        'resetDetailActionSelection()',
        'traceAppControlOpen("selection"',
        'scheduleTabAudioProbe()',
        'traceAppControlOpen("probe-schedule"',
        'refreshWindowState()',
        'refreshTaskManager()',
        'refreshBottleList()',
        'traceAppControlOpen("refresh-dispatch"',
        'searchInput.forceActiveFocus()',
        'traceAppControlOpen("focus"',
        'traceAppControlOpen("handler-total"'
    ]) {
        const ix = opening.indexOf(marker);
        assert.ok(ix > prev, 'ordered marker: ' + marker);
        prev = ix;
    }
});


test('preferred detail selection reuses action snapshots without changing favorite identity or first match', () => {
    const section=(source,a,b)=>source.slice(source.indexOf('    function '+a+'('),
        source.indexOf('    function '+b+'(',source.indexOf('    function '+a+'(')));
    const code=section(app,'detailFavoriteContextKey','detailActionAvailable')
        +section(app,'favoriteDetailActionIndex','toggleDetailActionFavorite');
    const stubs= [
        "function selectedResult(){return state.entry;}",
        "function favoriteSourceItem(e){return e&&e._favoriteRecord?e._sourceItem:e;}",
        "function selectedResultIsApplication(){return state.mode==='app';}",
        "function selectedResultIsRun(){return state.mode==='run';}",
        "function appEntryKey(e){return String(e.id||e.name||'');}",
        "const runModeIndex=3;",
        "function favoriteKeyFor(e){return e.id;}",
        "function appDesktopActions(e){counts.actions++;return e._hiddenCommand?[]:e.actions.slice();}",
        "function detailActionCount(){counts.count++;if(!state.entry)return 0;const e=favoriteSourceItem(state.entry);return state.mode==='app'?(e._hiddenCommand?7:6+appDesktopActions(e).length):state.mode==='run'?6:3;}"
    ].join('\n');
    const make=new Function('state','counts','favoriteStore',stubs+'\n'+code+
        '\nreturn {pick:favoriteDetailActionIndex,key:detailFavoriteKeyFor,legacy:function(){const n=detailActionCount();for(let i=0;i<n;i++)if(isDetailActionFavorite(i))return i;return -1;}};');
    const cases=[
        {mode:'app',entry:{id:'browser|a',actions:[{name:'New window'},{name:'New window'},{_appControlBuiltin:'history'},{}]}},
        {mode:'app',entry:{_favoriteRecord:true,_sourceItem:{id:'wrapped',actions:[{name:'é'}]}}},
        {mode:'app',entry:{id:'hidden',_hiddenCommand:true,actions:[]}},
        {mode:'run',entry:{id:'run|sample'}},
        {mode:'other',entry:{id:'task'}},
        {mode:'app',entry:null}
    ];
    for(const state of cases){
        const counts={actions:0,count:0}, store={favoriteDetailActionKeys:[]};
        const model=make(state,counts,store);
        const ids=Array.from({length:16},(_,i)=>model.key(i)).filter(Boolean);
        for(const keys of [[],['app|unrelated|launch'],ids.slice().reverse(),ids.slice(-1),ids.slice(1,3),['bad|key',...ids]]){
            store.favoriteDetailActionKeys=keys;
            const expected=model.legacy();
            counts.actions=0;counts.count=0;
            assert.equal(model.pick(),expected);
            assert.ok(counts.actions<=2,'one count snapshot and one action snapshot');
            if(!keys.length||keys[0]==='app|unrelated|launch')assert.equal(counts.actions,0);
        }
        if(state.mode==='app'&&state.entry&&!state.entry._favoriteRecord&&state.entry.id==='browser|a'){
            assert.equal(model.key(1),'app|browser%7Ca|desktop|New%20window');
            assert.equal(model.key(2),model.key(1));
            assert.equal(model.key(3),'app|browser%7Ca|builtin|history');
            assert.equal(model.key(4),'app|browser%7Ca|desktop|3');
            assert.equal(model.key(8),'app|browser%7Ca|freeze-app');
            store.favoriteDetailActionKeys=[model.key(2)];
            counts.actions=0;counts.count=0;
            assert.equal(model.pick(10),1);
            assert.equal(counts.actions,1);
            assert.equal(counts.count,0);
        }
    }
    assert.match(app,/function resetDetailActionSelection\(\) \{[\s\S]*?favoriteDetailActionIndex\(count\)[\s\S]*?detailActionAvailable\(favoriteIndex\)/);
    assert.match(app,/function activateFavoriteDetailActionFromSelector\(\) \{[\s\S]*?favoriteIndex < 0[\s\S]*?!detailActionAvailable\(favoriteIndex\)/);
});

test('opening substages and runtime KILL work remain opt-in and keep existing operations',()=>{
    const opening=app.slice(app.indexOf('    onMenuOpenChanged: {'),app.indexOf('        } else {\n            recentModeIndex',app.indexOf('    onMenuOpenChanged: {')));
    let last=-1;
    for(const marker of ['const selectionStart = openStage','traceAppControlOpen("selection-state"','restoreRememberedAppSelection()','traceAppControlOpen("selection-row"','resetDetailActionSelection()','traceAppControlOpen("selection-detail"','traceAppControlOpen("selection", openTrace, selectionStart)']){
        const next=opening.indexOf(marker);assert.ok(next>last,marker);last=next;
    }
    assert.match(app,/return diagnosticCaptureActive && menuOpen && selectedModeIndex === killModeIndex/);
    assert.match(app,/if \(!startMs \|\| !killDiagnosticActive\(\)\)\s*return/);
    assert.match(app,/traceKillWork\("snapshot-selection", selectionStart\)/);
    const mini=app.slice(app.indexOf('    function applyTaskMiniProbeRows('),app.indexOf('    Timer {',app.indexOf('    function applyTaskMiniProbeRows(')));
    assert.match(mini,/updateTaskMiniCpuHistories\(samples\);[\s\S]*?traceKillWork\("mini-cpu-history"[\s\S]*?updateTaskMiniHunterMetricHistories\(samples\);[\s\S]*?traceKillWork\("mini-hunter-history"[\s\S]*?taskMiniDisplayRevision \+= 1;[\s\S]*?traceKillWork\("mini-history-revisions"/);
});


test('mini graph publishes isolated equal-length frames and skips non-task refreshes', () => {
    const start=app.indexOf('                            function refreshHistory(animateScroll) {');
    const end=app.indexOf('                            onHistoryRevisionChanged:',start);
    assert.ok(start>=0&&end>start);
    // Execute the actual refresh function with QML-like owned properties.
    const body=app.slice(start,end);
    const create=new Function('state',
        'let graphReady=true; const killMiniGraphBox=state.box; const emptyCombiHistories=state.empty;'+
        'let historyFrame={values:[],combi:emptyCombiHistories}; let historyValues=historyFrame.values,combiHistories=historyFrame.combi;'+
        'const appControlWindow={selectedModeIndex:1,killModeIndex:7,killViewMode:0,killViewHunter:1};'+
        'const taskGraphController={liveTaskForMiniGraph(){state.lookups++;return state.box.rowItem;},miniCpuHistoryByIdentity(){return state.values;},miniHunterHistoryForEntry(){return state.values;}};'+
        'function snapshotCombiHistory(){return emptyCombiHistories;} function startGraphScroll(){state.starts++;} function stopGraphScroll(){state.stops++;}'+body+
        '\nreturn {run(animate){refreshHistory(animate);historyValues=historyFrame.values;combiHistories=historyFrame.combi;return historyFrame;},ready(v){graphReady=v;}};');
    const state={box:{showingTask:false,rowItem:{pid:10},taskIdentity:'task'},empty:{cpu:[],mem:[],io:[],age:[]},values:[1,2],lookups:0,starts:0,stops:0};
    const graph=create(state);
    const empty=graph.run(true);
    assert.equal(graph.run(true),empty);
    assert.equal(state.lookups,0);
    graph.ready(false);state.box.showingTask=true;assert.equal(graph.run(true),empty);
    graph.ready(true);
    const first=graph.run(false);
    assert.deepStrictEqual(first.values,[1,2]);
    assert.notEqual(first.values,state.values);
    state.values=[2,3];
    const second=graph.run(true);
    assert.deepStrictEqual(second.values,[2,3]);
    assert.notEqual(second,first);
    assert.deepStrictEqual(first.values,[1,2]);
    assert.equal(state.starts,1);
    state.box.showingTask=false;
    const cleared=graph.run(true);
    assert.deepStrictEqual(cleared.values,[]);
    assert.equal(graph.run(true),cleared);
    assert.equal(state.lookups,2);
    state.box.showingTask=true;
    assert.deepStrictEqual(graph.run(false).values,[2,3]);
    const mini=app.slice(app.indexOf('id: killMiniCpuCanvas'),app.indexOf('id: selectorAppIconBox',app.indexOf('id: killMiniCpuCanvas')));
    assert.doesNotMatch(mini,/graphEpoch/);
    assert.match(mini,/property int historyRevision:\s*killMiniGraphBox.showingTask\s*\? appControlWindow.taskMiniDisplayRevision : -1/);
    assert.match(mini,/onShowingTaskChanged\(\)/);
    assert.match(mini,/readonly property point p1:\s*killMiniCpuCanvas.graphPoints\[index\]/);
    assert.match(mini,/readonly property point p2:\s*killMiniCpuCanvas.graphPoints\[index \+ 1\]/);
});


test('application sort snapshots preserve favorites, source ties and row identity', () => {
    const start=app.indexOf('    function sortApplicationRows(');
    const end=app.indexOf('    ScriptModel {',start);
    assert.ok(start>=0&&end>start);
    const counters={favorite:0,source:0,key:0};
    const fav=e=>e.favorite;
    const matches=e=>e.matches;
    const key=e=>String(e.id||e.name||"");
    const sorted=new Function('isFavorite','appEntryMatchesSelectedSource','appEntryKey',
        app.slice(start,end)+'\nreturn sortApplicationRows;')(
            e=>{counters.favorite++;return fav(e);},
            e=>{counters.source++;return matches(e);},
            e=>{counters.key++;return key(e);});
    function legacy(rows) {
        return rows.slice().sort((a,b)=>{
            if(fav(a)!==fav(b))return fav(a)?-1:1;
            const n=String(a.name||"").localeCompare(String(b.name||""));
            if(n!==0)return n;
            if(matches(a)!==matches(b))return matches(a)?-1:1;
            return key(a).localeCompare(key(b));
        });
    }
    const rows=Array.from({length:600},(_,i)=>({name:['A','a','É','same','',undefined][i%6],id:'id'+(i%31),favorite:i%7===0,matches:i%3===0}));
    for(const source of [[],[rows[0]],rows,rows.slice().reverse(),rows.filter(x=>x.favorite)]){
        counters.favorite=0;counters.source=0;counters.key=0;
        const result=sorted(source), expected=legacy(source);
        assert.equal(result.length,expected.length);
        result.forEach((row,i)=>assert.equal(row,expected[i]));
        assert.equal(counters.favorite,source.length);
        assert.ok(counters.source<=source.length);
        assert.ok(counters.key<=source.length);
    }
    assert.match(app,/return appControlWindow.sortApplicationRows\(filtered\);/);
});
test('task favorite first matches use one pass and avoid unneeded snapshot subscriptions',()=>{
    const start=app.indexOf('    function firstFavoriteTaskRows(');
    const end=app.indexOf('    ScriptModel {',start);
    assert.ok(start>=0&&end>start);
    let reads=0;
    const first=new Function('taskPersistentIdentity',app.slice(start,end)+'\nreturn firstFavoriteTaskRows;')(
        e=>{reads++;return e.identity;});
    const rows=Array.from({length:600},(_,i)=>({identity:'task'+i%90,pid:i+2}));
    rows.push({identity:'__proto__',pid:900});
    for(const wanted of [[],['task20'],['task40','task20','absent'],['task0','__proto__']]){
        reads=0;
        const result=first(wanted,rows);
        for(const id of wanted)assert.equal(result[id],rows.find(e=>e.identity===id));
        assert.ok(reads<=rows.length);
        if(!wanted.length)assert.equal(reads,0);
    }
    const model=app.slice(app.indexOf('id: favoriteResults'),app.indexOf('function resultCount()'));
    assert.equal((model.match(/appControlWindow\.taskRows/g)||[]).length,1);
    assert.match(model,/if \(watchedIdentities.length > 0\) \{\s*const first = appControlWindow.firstFavoriteTaskRows\(\s*watchedIdentities, appControlWindow.taskRows\)/);
    assert.match(model,/favoriteRecordForTaskIdentity\(\s*identity,\s*first\[identity\] \|\| null/);
});

test('APP row restore observes read, scan, assignment and deferred view without changing order',()=>{
    const start=app.indexOf('    function restoreRememberedAppSelection()');
    const end=app.indexOf('    function switchMode(',start);
    const body=app.slice(start,end);
    let prev=-1;
    for(const marker of ['currentApplicationValues()','traceDiagnosticWork("app-model-read"','appEntryKey(apps[i])','traceDiagnosticWork("app-key-scan"','selectedResultIndex = restoredIndex','traceDiagnosticWork("app-index-write"','Qt.callLater','resultList.positionViewAtIndex','traceDiagnosticWork("app-position-view"']){
        const ix=body.indexOf(marker,prev+1);assert.ok(ix>prev,marker);prev=ix;
    }
    assert.match(app,/if \(!startMs \|\| !diagnosticCaptureActive\)\s*return 0/);
    assert.match(app,/traceSequence = \(appControlSnapshotTraceEnabled \|\| diagnosticCaptureActive\)/);
    assert.match(app,/else if \(diagnosticCaptureActive\)\s*diagnosticWorkStage\(stage, elapsedMs, now\)/);
});
