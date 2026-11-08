.pragma library
.import "FavoritesResourcePolicy.js" as Resource
.import "FavoritesDefaultPolicy.js" as Default

// U3a: local grouping metadata only. A group never becomes the writer,
// resolver, subscription owner, or action authority of any contained item.
var SCHEMA = "post-apollo.favorites.collections.v1";
var VERSION = 1;
var MAX_COLLECTIONS = 24;
var MAX_MEMBERS = 80;
var MAX_TOTAL_MEMBERS = 600;
var MAX_NAME = 48;
var MAX_DOCUMENT_CHARS = 262144;

function empty() {
    return {schema:SCHEMA,version:VERSION,revision:0,nextId:1,collections:[]};
}

function normalizedName(name) {
    if (typeof name !== "string" || name !== name.trim()
            || name.length < 1 || name.length > MAX_NAME
            || /[\u0000-\u001f\u007f]/.test(name))
        return "";
    try {
        encodeURIComponent(name);
    } catch (error) {
        return "";
    }
    return name;
}

function checkMemberKey(key) {
    if (typeof key !== "string" || key.length > 500)
        return {ok:false,reason:"INVALID_MEMBER_KEY"};
    const match = /^fav1:local:([a-z][a-z0-9-]{0,47}):([a-z][a-z0-9-]{0,47}):(.+)$/.exec(key);
    if (!match)
        return {ok:false,reason:"INVALID_MEMBER_KEY"};
    let id;
    try {
        id=decodeURIComponent(match[3]);
    } catch (error) {
        return {ok:false,reason:"INVALID_MEMBER_KEY"};
    }
    if (Resource.identityKey(match[1],match[2],id) !== key)
        return {ok:false,reason:"INVALID_MEMBER_KEY"};

    // Legacy resources keep their original data owners. U3a explicitly
    // reviews only two safe identifiers; additional providers need adapters.
    if (match[1] === "time") {
        if (match[2] !== "timezone" || id.length > 100
                || !(id === "UTC"
                     || /^[A-Za-z][A-Za-z0-9._+-]*(?:\/[A-Za-z0-9._+-]+)+$/.test(id)))
            return {ok:false,reason:"UNSUPPORTED_OWNER"};
    } else if (match[1] === "places") {
        if (match[2] !== "saved-place" || !/^[1-9][0-9]{0,14}$/.test(id)
                || !Number.isSafeInteger(Number(id)))
            return {ok:false,reason:"UNSUPPORTED_OWNER"};
    } else if (Default.RESERVED_PROVIDERS.indexOf(match[1]) >= 0) {
        return {ok:false,reason:"UNSUPPORTED_OWNER"};
    } else {
        if (!Default.checkKey(key).ok
                || !/^[A-Za-z0-9][A-Za-z0-9_.:@+-]{0,127}$/.test(id))
            return {ok:false,reason:"UNSAFE_NEW_PROVIDER_ID"};
    }
    return {ok:true,provider:match[1],kind:match[2]};
}

function validCollectionId(id) {
    return typeof id === "string" && /^c[1-9][0-9]{0,14}$/.test(id)
        && Number.isSafeInteger(Number(id.slice(1)));
}

function validate(document) {
    if (!document || typeof document !== "object"
            || Array.isArray(document))
        return {ok:false,reason:"INVALID_DOCUMENT"};
    if (document.schema !== SCHEMA || document.version !== VERSION)
        return {ok:false,reason:"UNSUPPORTED_VERSION"};
    if (Object.keys(document).sort().join("|")
            !== "collections|nextId|revision|schema|version")
        return {ok:false,reason:"UNSUPPORTED_FIELDS"};
    if (!Number.isSafeInteger(document.revision)
            || document.revision < 0
            || !Number.isSafeInteger(document.nextId)
            || document.nextId < 1
            || !Array.isArray(document.collections)
            || document.collections.length > MAX_COLLECTIONS)
        return {ok:false,reason:"INVALID_DOCUMENT"};
    const ids=Object.create(null), names=Object.create(null);
    let total=0, maxId=0;
    for (const c of document.collections) {
        if (!c || typeof c !== "object" || Array.isArray(c)
                || Object.keys(c).sort().join("|") !== "id|members|name"
                || !validCollectionId(c.id) || ids[c.id]
                || !normalizedName(c.name)
                || names[c.name.toLocaleLowerCase()]
                || !Array.isArray(c.members) || c.members.length>MAX_MEMBERS)
            return {ok:false,reason:"INVALID_COLLECTION"};
        ids[c.id]=true;
        names[c.name.toLocaleLowerCase()]=true;
        maxId=Math.max(maxId,Number(c.id.slice(1)));
        const members=Object.create(null);
        for(const key of c.members) {
            if (!checkMemberKey(key).ok || members[key])
                return {ok:false,reason:"INVALID_MEMBERS"};
            members[key]=true;
            total++;
        }
    }
    if (document.nextId<=maxId || total>MAX_TOTAL_MEMBERS)
        return {ok:false,reason:"INVALID_DOCUMENT"};
    return {ok:true};
}

function parse(raw) {
    const text=String(raw===null || raw===undefined ? "" : raw);
    if (!text || text.length>MAX_DOCUMENT_CHARS)
        return {ok:false,reason:"INVALID_DOCUMENT"};
    let doc;
    try {doc=JSON.parse(text);}
    catch(error){return {ok:false,reason:"INVALID_JSON"};}
    const checked=validate(doc);
    if (!checked.ok)
        return checked;
    return {ok:true,document:clone(doc)};
}

function clone(doc) {
    return {schema:SCHEMA,version:VERSION,revision:doc.revision,
        nextId:doc.nextId,collections:doc.collections.map(c=>({
            id:c.id,name:c.name,members:c.members.slice()
        }))};
}

function memberOf(doc,collectionId,key) {
    if (!doc || !Array.isArray(doc.collections))
        return false;
    const c=doc.collections.find(x=>x.id===collectionId);
    return !!c && c.members.indexOf(key)>=0;
}

function change(doc,action) {
    const valid=validate(doc);
    if (!valid.ok) return valid;
    if (!action || typeof action !== "object" || Array.isArray(action))
        return {ok:false,reason:"INVALID_ACTION"};
    if (typeof action.type !== "string")
        return {ok:false,reason:"INVALID_ACTION"};
    let next=clone(doc), changed=false, createdId="";
    const id=action.collectionId;
    const index=next.collections.findIndex(c=>c.id===id);
    const collection=index>=0 ? next.collections[index] : null;

    if (action.type==="create") {
        const name=normalizedName(action.name);
        if (!name) return {ok:false,reason:"INVALID_NAME"};
        if (next.collections.some(c=>c.name.toLocaleLowerCase()===name.toLocaleLowerCase()))
            return {ok:false,reason:"DUPLICATE_NAME"};
        if (next.collections.length>=MAX_COLLECTIONS)
            return {ok:false,reason:"COLLECTION_LIMIT"};
        if (next.nextId>=Number.MAX_SAFE_INTEGER)
            return {ok:false,reason:"ID_LIMIT"};
        createdId="c"+next.nextId;
        next.nextId++;
        next.collections.push({id:createdId,name,members:[]});
        changed=true;
    } else if (action.type==="rename") {
        if (!collection) return {ok:false,reason:"UNKNOWN_COLLECTION"};
        const name=normalizedName(action.name);
        if (!name) return {ok:false,reason:"INVALID_NAME"};
        if (next.collections.some(c=>c.id!==id
                && c.name.toLocaleLowerCase()===name.toLocaleLowerCase()))
            return {ok:false,reason:"DUPLICATE_NAME"};
        if (collection.name!==name) {collection.name=name;changed=true;}
    } else if (action.type==="delete") {
        if (!collection) return {ok:false,reason:"UNKNOWN_COLLECTION"};
        next.collections.splice(index,1);
        changed=true;
    } else if (action.type==="set-member") {
        if (!collection) return {ok:false,reason:"UNKNOWN_COLLECTION"};
        const check=checkMemberKey(action.key);
        if (!check.ok) return check;
        if (typeof action.enabled!=="boolean")
            return {ok:false,reason:"INVALID_ACTION"};
        const m=collection.members, at=m.indexOf(action.key);
        if ((at>=0)===action.enabled)
            return {ok:true,changed:false,document:doc};
        if (action.enabled) {
            if (m.length>=MAX_MEMBERS
                    || next.collections.reduce((n,c)=>n+c.members.length,0)>=MAX_TOTAL_MEMBERS)
                return {ok:false,reason:"MEMBERSHIP_LIMIT"};
            m.push(action.key);
        } else m.splice(at,1);
        changed=true;
    } else if (action.type==="move-member") {
        if (!collection || !checkMemberKey(action.key).ok)
            return {ok:false,reason:"INVALID_MEMBER"};
        if (action.direction!==1 && action.direction!==-1)
            return {ok:false,reason:"INVALID_DIRECTION"};
        const old=collection.members.indexOf(action.key), pos=old+action.direction;
        if(old<0) return {ok:false,reason:"MEMBER_NOT_FOUND"};
        if(pos<0 || pos>=collection.members.length)
            return {ok:true,changed:false,document:doc};
        collection.members.splice(old,1);
        collection.members.splice(pos,0,action.key);
        changed=true;
    } else return {ok:false,reason:"INVALID_ACTION"};

    if (!changed) return {ok:true,changed:false,document:doc};
    if (doc.revision>=Number.MAX_SAFE_INTEGER-1)
        return {ok:false,reason:"REVISION_LIMIT"};
    next.revision++;
    if(JSON.stringify(next).length>MAX_DOCUMENT_CHARS)
        return {ok:false,reason:"DOCUMENT_FULL"};
    return {ok:true,changed:true,document:next,collectionId:createdId};
}
