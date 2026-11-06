.pragma library

// M6f // Read-only reverse index and nonexclusive overlap graph for the
// existing, separately owned M6e primary-source Agrippa catalogue.
// Caller passes AGRIPPA.PLANETS/CATEGORIES/SOURCE; this module never copies,
// edits or invents historical terms, celestial data, interpretation or records.
var FORMAT="post-apollo.weather.magick-grimoire-atlas.m6f.v1";
var MAX_QUERY=80;
var MAX_PLANETS=7;
var MAX_CATEGORIES=3;
var PAGE_SIZE=5;

function unavailable(reason) {
    return {ready:false,reason:reason||"NO VALID SOURCE CORPUS",
        source:null,entries:[],rows:[],links:[],nodes:[],
        total:0,visible:0,overlaps:0,category:"all",query:"",
        focus:"",format:FORMAT};
}
function normalize(value) {
    return typeof value==="string" ? value.trim().toLowerCase() : "";
}
function build(planets,categories,source,searchText,categoryId,focusPlanet) {
    if(!Array.isArray(planets)||planets.length!==MAX_PLANETS||
       !Array.isArray(categories)||categories.length!==MAX_CATEGORIES||
       !source||source.id!=="agrippa-1651-book-i-23-29" ||
       source.edition!=="1651 English edition" ||
       !source.textUrl || !source.scanUrl)
        return unavailable("AGRIPPA EDITION / SOURCE NOT VERIFIED");
    var query=normalize(searchText),category=categoryId||"all",
        focus=focusPlanet||"",seen={},categoriesSeen={};
    if(query.length>MAX_QUERY || (category!=="all" &&
       !categories.some(function(c){return c&&c.id===category;})) ||
       (focus!=="" && !planets.some(function(p){return p&&p.id===focus;})))
        return unavailable("UNKNOWN CATEGORY, BODY OR SEARCH LIMIT");
    for(var i=0;i<categories.length;i++) {
        if(!categories[i] || typeof categories[i].id!=="string" ||
           !["metals","stones","plants"].includes(categories[i].id) ||
           categoriesSeen[categories[i].id])
            return unavailable("CORRUPT SOURCE CATEGORY");
        categoriesSeen[categories[i].id]=true;
    }
    var all=[],filtered=[],nodeIds=[],linksByPair={};
    for(var p=0;p<planets.length;p++){
        var planet=planets[p];
        if(!planet || typeof planet.id!=="string" ||
           !planet.id || seen[planet.id] ||
           !Number.isInteger(planet.chapter) ||
           planet.chapter<23 || planet.chapter>29)
            return unavailable("INVALID SOURCE CHAPTER OR PLANET");
        seen[planet.id]=true;
        nodeIds.push(planet.id);
        for(var c=0;c<categories.length;c++){
            var id=categories[c].id,items=planet[id];
            if(!Array.isArray(items)||items.length<1||items.length>40)
                return unavailable("SOURCE TERMS MISSING");
            for(var k=0;k<items.length;k++){
                var term=items[k];
                if(typeof term!=="string" || !term.trim() ||
                   term.length>120)
                    return unavailable("INVALID HISTORICAL TERM");
                var record={planet:planet.id,chapter:planet.chapter,
                    category:id,term:term,sourceId:source.id};
                all.push(record);
                // Search only original term strings; never perform a
                // culturally misleading semantic inference/synonym map.
                if((category==="all" || category===id) &&
                   (query==="" || normalize(term).indexOf(query)>=0)) {
                    filtered.push(record);
                }
            }
        }
    }
    var graphTerms={};
    for(var q=0;q<filtered.length;q++){
        var row=filtered[q],key=row.category+"\u0000"+normalize(row.term);
        if(!graphTerms[key])graphTerms[key]=[];
        if(graphTerms[key].indexOf(row.planet)<0)
            graphTerms[key].push(row.planet);
    }
    var keys=Object.keys(graphTerms);
    for(var t=0;t<keys.length;t++){
        var names=graphTerms[keys[t]],parts=keys[t].split("\u0000");
        for(var a=0;a<names.length;a++)for(var b=a+1;b<names.length;b++){
            var ia=nodeIds.indexOf(names[a]),ib=nodeIds.indexOf(names[b]);
            if(ia<0||ib<0 || ia===ib)
                return unavailable("SOURCE GRAPH ID INVALID");
            var low=Math.min(ia,ib),high=Math.max(ia,ib),
                pair=low+":"+high;
            if(!linksByPair[pair])
                linksByPair[pair]={from:nodeIds[low],to:nodeIds[high],
                    fromIndex:low,toIndex:high,count:0,terms:[]};
            linksByPair[pair].count++;
            linksByPair[pair].terms.push({
                category:parts[0],term:parts[1]});
        }
    }
    var links=Object.keys(linksByPair).map(function(key){
        return linksByPair[key];
    }).sort(function(a,b){
        return b.count-a.count || a.fromIndex-b.fromIndex ||
               a.toIndex-b.toIndex;
    });
    var rows=focus===""?filtered:
        filtered.filter(function(row){return row.planet===focus;});
    return {ready:true,reason:"",format:FORMAT,source: {
            id:source.id,author:source.author,title:source.title,
            edition:source.edition,book:source.book,
            reference:source.reference,textUrl:source.textUrl,
            scanUrl:source.scanUrl},
        total:all.length,visible:rows.length,overlaps:links.length,
        entries:filtered,rows:rows,links:links,
        nodes:planets.map(function(p,i){
            return {id:p.id,label:p.label,chapter:p.chapter,index:i};
        }),category:category,query:query,focus:focus};
}
function page(model,index,size) {
    if(!model || model.ready!==true || !Number.isInteger(index) ||
       index<0)return [];
    var limit=Number.isInteger(size) && size>0 && size<=10
              ? size:PAGE_SIZE;
    return model.rows.slice(index*limit,(index+1)*limit);
}
function pages(model,size){
    if(!model || model.ready!==true)return 0;
    var limit=Number.isInteger(size)&&size>0&&size<=10?size:PAGE_SIZE;
    return Math.ceil(model.rows.length/limit);
}
function geometry(width,height){
    if(typeof width!=="number" || typeof height!=="number" ||
       !isFinite(width)||!isFinite(height)||width<175||height<120)
        return null;
    return {cx:width/2,cy:height/2,
        radius:Math.min(width*0.33,height*0.32)};
}
function nodePoint(index,width,height){
    var g=geometry(width,height);
    if(!g || !Number.isInteger(index)||index<0||index>=MAX_PLANETS)
        return null;
    var angle=-Math.PI/2+Math.PI*2*index/MAX_PLANETS;
    return {x:g.cx+g.radius*Math.cos(angle),
            y:g.cy+g.radius*Math.sin(angle)};
}
function pickNode(model,width,height,x,y){
    if(!model||model.ready!==true||typeof x!=="number"||
       typeof y!=="number"||!isFinite(x)||!isFinite(y))return "";
    var best="",radius=15*15;
    for(var i=0;i<model.nodes.length;i++){
        var p=nodePoint(i,width,height);
        if(!p)continue;
        var d=(p.x-x)*(p.x-x)+(p.y-y)*(p.y-y);
        if(d<=radius){best=model.nodes[i].id;radius=d;}
    }
    return best;
}
