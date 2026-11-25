// Pure viewport and request policy for an immutable, local history snapshot.
// Deliberately not mounted in BranchMap yet. No timers, IO or QML object churn.
const SCHEMA = "post-apollo-git-map-index-v1";
const PAGE = 128;
const MAX_ROWS = 1000000;
const MAX_LANES = 512;
const MAX_CACHE = 5;
function integer(value, min, max) {
    return Number.isSafeInteger(value) && value >= min && value <= max;
}
function sha(value) {
    return typeof value === "string" && /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(value);
}
function identity(m) {
    return m && m.schema === SCHEMA && typeof m.snapshot === "string"
        && /^[0-9a-f]{32}$/.test(m.snapshot) && typeof m.repoId === "string"
        && /^[0-9a-f]{64}$/.test(m.repoId);
}
function manifest(m) {
    return identity(m) && m.pageSize === PAGE && integer(m.total,0,MAX_ROWS)
        && integer(m.maxLane,0,MAX_LANES-1) && typeof m.shallow === "boolean"
        && m.scope === "captured-local-ref-tips-and-head";
}
function validGeometry(rowHeight, viewportHeight) {
    return Number.isFinite(rowHeight) && rowHeight >= 1 && rowHeight <= 128
        && Number.isFinite(viewportHeight) && viewportHeight >= 1
        && Math.ceil(viewportHeight/rowHeight) <= 256;
}
function extent(s) {
    return Math.max(s.viewportHeight,s.total*s.rowHeight);
}
function clamp(s,y) {
    return Math.max(0,Math.min(extent(s)-s.viewportHeight,y));
}
function visibleRange(s) {
    if (!s.total) return {first:0,stop:0};
    return {first:Math.min(s.total-1,Math.floor(s.y/s.rowHeight)),
        stop:Math.min(s.total,Math.ceil((s.y+s.viewportHeight)/s.rowHeight))};
}
// Exact span of nodes, connectors and passing lanes in the visible rows.
// Replay from the loaded page boundaries, never scan the whole history.
// A missing visible page is unknown, not evidence that the graph shrank.
function visibleLaneSpan(s) {
    if (!s || !s.total) return {first:0,last:0};
    const range=visibleRange(s);
    let first=MAX_LANES, last=-1;
    const include=lane=>{first=Math.min(first,lane);last=Math.max(last,lane);};
    for (let start=Math.floor(range.first/PAGE)*PAGE; start<range.stop; start+=PAGE) {
        const page=s.cache[start];
        if (!page) return null;
        const frontier=new Map(page.frontier.map(f=>[f.sha,f.lane]));
        for (const row of page.rows) {
            if (row.ordinal>=range.stop) break;
            const visible=row.ordinal>=range.first;
            if (visible) {
                include(row.lane);
                for (const lane of frontier.values()) include(lane);
            }
            frontier.delete(row.sha);
            for (const edge of row.parents) {
                if (visible) include(edge.lane);
                frontier.set(edge.sha,edge.lane);
            }
        }
    }
    return last<0 ? {first:0,last:0} : {first,last};
}
function wantedPages(s) {
    const range = visibleRange(s);
    if (!range.stop) return [];
    const first = Math.floor(range.first/PAGE)*PAGE;
    const last = Math.floor((range.stop-1)/PAGE)*PAGE;
    const visible = [];
    for(let i=first;i<=last;i+=PAGE) visible.push(i);
    // Current viewport first; one page on each side, directional priority.
    const forward = last+PAGE < s.total ? [last+PAGE] : [];
    const back = first>=PAGE ? [first-PAGE] : [];
    return visible.concat(s.direction < 0 ? back.concat(forward) : forward.concat(back));
}
function retain(s) {
    const wanted=wantedPages(s), cache={}, pending={}, errors={};
    for(const key of wanted) {
        if(s.cache[key]) cache[key]=s.cache[key];
        if(s.pending[key]) pending[key]=s.pending[key];
        if(s.errors[key]) errors[key]=s.errors[key];
    }
    return Object.assign({},s,{cache:cache,pending:pending,errors:errors});
}
function activate(previous,m,rowHeight,viewportHeight,anchor) {
    if(!manifest(m) || !validGeometry(rowHeight,viewportHeight)) return null;
    // Replacing a generation requires explicit top selection or a validated
    // exact-SHA locate response. Never silently jump when an anchor is absent.
    const prior = previous ? anchorOf(previous) : null;
    if(previous && (!anchor || (anchor.top !== true &&
            (!identity(anchor) || anchor.snapshot!==m.snapshot || anchor.repoId!==m.repoId
             || !sha(anchor.sha) || !integer(anchor.ordinal,0,m.total-1)
             || !prior || !prior.sha || anchor.sha!==prior.sha
             || anchor.offset!==prior.offset || previous.repoId!==m.repoId
             || !Number.isFinite(anchor.offset) || anchor.offset<0
             || anchor.offset>=rowHeight)))) return null;
    const s={schema:SCHEMA,snapshot:m.snapshot,repoId:m.repoId,total:m.total,
        shallow:m.shallow,maxLane:m.maxLane,rowHeight,viewportHeight,y:0,direction:1,
        epoch:previous?previous.epoch+1:1,sequence:0,cache:{},pending:{},errors:{}};
    if(previous && anchor.top !== true) s.y=clamp(s,anchor.ordinal*rowHeight+anchor.offset);
    return s;
}
function scroll(s,y) {
    if(!Number.isFinite(y)) return s;
    const next=clamp(s,y);
    if(next===s.y) return s;
    return retain(Object.assign({},s,{y:next,direction:next===s.y?s.direction:next>s.y?1:-1}));
}
function resize(s,viewportHeight) {
    if(!validGeometry(s.rowHeight,viewportHeight)) return s;
    const next=Object.assign({},s,{viewportHeight:viewportHeight});
    return retain(Object.assign({},next,{y:clamp(next,s.y)}));
}
function requests(s) {
    let next=Object.assign({},s,{pending:Object.assign({},s.pending)});
    const list=[];
    for(const start of wantedPages(next)) {
        if(next.cache[start] || next.pending[start] || next.errors[start]) continue;
        next.sequence+=1;
        const request={schema:SCHEMA,repoId:next.repoId,snapshot:next.snapshot,
            epoch:next.epoch,sequence:next.sequence,start};
        next.pending[start]=request;
        list.push(request);
    }
    return {state:list.length ? next : s,requests:list};
}
function sameRequest(s,r) {
    if(!identity(r) || r.snapshot!==s.snapshot || r.repoId!==s.repoId
            || r.epoch!==s.epoch || !integer(r.start,0,s.total-1) || r.start%PAGE) return false;
    const p=s.pending[r.start];
    return Boolean(p && p.sequence===r.sequence && p.epoch===r.epoch);
}
function validPage(s,r,p) {
    if(!identity(p) || p.snapshot!==s.snapshot || p.repoId!==s.repoId
            || p.start!==r.start || p.total!==s.total || !Array.isArray(p.rows)
            || p.rows.length!==Math.min(PAGE,s.total-r.start)
            || p.end!==(p.start+p.rows.length===s.total)
            || !Array.isArray(p.frontier) || p.frontier.length>MAX_LANES) return false;
    const lanes=new Set(), frontierShas=new Set(), shas=new Set();
    const laneOk = n=>integer(n,0,s.maxLane);
    for(const f of p.frontier) {
        if(!f || !sha(f.sha) || !laneOk(f.lane)
                || lanes.has(f.lane) || frontierShas.has(f.sha)) return false;
        lanes.add(f.lane);frontierShas.add(f.sha);
    }
    for(let i=0;i<p.rows.length;i++) {
        const row=p.rows[i];
        if(!row || row.ordinal!==p.start+i || !sha(row.sha) || shas.has(row.sha)
                || !laneOk(row.lane) || !integer(row.timestamp,0,Number.MAX_SAFE_INTEGER)
                || typeof row.author!=="string" || row.author.length>512
                || typeof row.subject!=="string" || row.subject.length>2048
                || !Array.isArray(row.parents) || row.parents.length>64) return false;
        shas.add(row.sha);
        const parents=new Set();
        for(let j=0;j<row.parents.length;j++) {
            const edge=row.parents[j];
            if(!edge || edge.position!==j || !sha(edge.sha) || parents.has(edge.sha)
                    || !integer(edge.ordinal,row.ordinal+1,s.total-1) || !laneOk(edge.lane)) return false;
            parents.add(edge.sha);
            const known=edge.ordinal>=p.start && edge.ordinal<p.start+p.rows.length
                ? p.rows[edge.ordinal-p.start] : rowAt(s,edge.ordinal);
            if(known && (known.sha!==edge.sha || known.lane!==edge.lane)) return false;
        }
    }
    // Previously cached child edges that land in the incoming page must agree.
    for(const page of Object.values(s.cache)) for(const row of page.rows) {
        if(shas.has(row.sha) && (row.ordinal<p.start || row.ordinal>=p.start+p.rows.length)) return false;
        for(const edge of row.parents) if(edge.ordinal>=p.start && edge.ordinal<p.start+p.rows.length) {
            const parent=p.rows[edge.ordinal-p.start];
            if(parent.sha!==edge.sha || parent.lane!==edge.lane) return false;
        }
    }
    return true;
}
function reject(s,r,reason) {
    if(!sameRequest(s,r)) return s;
    const pending=Object.assign({},s.pending);delete pending[r.start];
    const errors=Object.assign({},s.errors);
    errors[r.start]=reason;
    return Object.assign({},s,{pending:pending,errors:errors});
}
function accept(s,r,p) {
    if(!sameRequest(s,r)) return s;
    if(!validPage(s,r,p)) return reject(s,r,"INVALID PAGE");
    const pending=Object.assign({},s.pending);delete pending[r.start];
    const cache=Object.assign({},s.cache);
    cache[r.start]=p;
    if(Object.keys(cache).length>MAX_CACHE) return reject(s,r,"CACHE LIMIT");
    // Data arrival changes only the cache and request state, not scroll geometry.
    return Object.assign({},s,{pending:pending,cache:cache});
}
function fail(s,r) {return reject(s,r,"PAGE UNAVAILABLE");}
function retry(s,start) {
    if(!s.errors[start] || !wantedPages(s).includes(start)) return s;
    const errors=Object.assign({},s.errors);delete errors[start];
    return Object.assign({},s,{errors:errors});
}
function rowAt(s,ordinal) {
    if(!integer(ordinal,0,s.total-1)) return null;
    const page=s.cache[Math.floor(ordinal/PAGE)*PAGE];
    return page?page.rows[ordinal-page.start]||null:null;
}
function rowState(s,ordinal) {
    if(!integer(ordinal,0,s.total-1)) return "OUTSIDE HISTORY";
    const start=Math.floor(ordinal/PAGE)*PAGE;
    return rowAt(s,ordinal)?"READY":s.errors[start]?"UNAVAILABLE":"LOADING";
}
function anchorOf(s) {
    if(!s.total) return null;
    const ordinal=visibleRange(s).first,row=rowAt(s,ordinal);
    return {ordinal,offset:s.y-ordinal*s.rowHeight,sha:row?row.sha:null};
}
function bottomState(s) {
    if(!s.total) return "EMPTY LOCAL HISTORY";
    if(s.y<extent(s)-s.viewportHeight) return "HISTORY CONTINUES";
    const range=visibleRange(s);
    for(let i=range.first;i<range.stop;i++) if(rowState(s,i)==="UNAVAILABLE") return "END RANGE UNAVAILABLE";
    for(let i=range.first;i<range.stop;i++) if(!rowAt(s,i)) return "LOADING END RANGE";
    return s.shallow?"SHALLOW LOCAL BOUNDARY":"END OF INDEXED LOCAL HISTORY";
}
