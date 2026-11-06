.pragma library

// M6e // Small, READ-ONLY, EDITION-LABELLED historical catalogue.
// Source: Heinrich Cornelius Agrippa, Three Books of Occult Philosophy,
// Book I, chapters XXIII-XXIX, 1651 English edition. Representative terms
// are modernized from that edition; the source contains many more entries,
// and its classes OVERLAP. Never claim a universal/exclusive correspondence.
// Primary text: https://www.esotericarchives.com/agrippa/op1.htm
// Digitized edition: https://wellcomecollection.org/works/ftahuupv
//
// UI inks are Post-Apollo contrast indicators, not historical color claims.
// No medical, spiritual-causation, handling, dosage, ritual or efficacy advice.
var FORMAT="post-apollo.weather.magick-agrippa-m6e.v1";
var SOURCE={
    id:"agrippa-1651-book-i-23-29",
    author:"Heinrich Cornelius Agrippa",
    title:"Three Books of Occult Philosophy",
    edition:"1651 English edition",
    book:"Book I",
    reference:"CHAPTERS XXIII–XXIX",
    textUrl:"https://www.esotericarchives.com/agrippa/op1.htm",
    scanUrl:"https://wellcomecollection.org/works/ftahuupv",
    note:"HISTORICAL ATTRIBUTIONS // NOT PHYSICAL PROPERTIES OR CAUSAL EFFECTS"
};
// Chaldean sequencing is visual presentation only; the chapter numbers
// themselves follow the original Book I order.
var PLANETS=[
 {id:"saturn",label:"SATURN",chapter:25,
  metals:["lead","gold (by weight)"],stones:["onyx","sapphire"],
  plants:["rue","cumin"],ink:"white"},
 {id:"jupiter",label:"JUPITER",chapter:26,
  metals:["tin","silver","gold"],stones:["sapphire","emerald"],
  plants:["basil","mint"],ink:"blue"},
 {id:"mars",label:"MARS",chapter:27,
  metals:["iron","red brass"],stones:["bloodstone","amethyst"],
  plants:["garlic","nettle"],ink:"orange"},
 {id:"sun",label:"SUN",chapter:23,
  metals:["gold"],stones:["chrysolite","carbuncle"],
  plants:["marigold","saffron"],ink:"yellow"},
 {id:"venus",label:"VENUS",chapter:28,
  metals:["silver","yellow brass","red brass"],stones:["emerald","sapphire"],
  plants:["vervain","violet"],ink:"magenta"},
 {id:"mercury",label:"MERCURY",chapter:29,
  metals:["quicksilver","tin"],stones:["agate","topaz"],
  plants:["hazel","parsley"],ink:"cyan"},
 {id:"moon",label:"MOON",chapter:24,
  metals:["silver"],stones:["selenite","pearl"],
  plants:["rosemary","hyssop"],ink:"cyan"}
];
var CATEGORIES=[
    {id:"metals",label:"METALS"},
    {id:"stones",label:"STONES"},
    {id:"plants",label:"PLANTS"}
];
function find(id){
    if(typeof id!=="string")return null;
    for(var i=0;i<PLANETS.length;i++)
        if(PLANETS[i].id===id)return PLANETS[i];
    return null;
}
function category(id){
    return CATEGORIES.some(function(c){return c.id===id;})?id:"";
}
function entry(id,cat){
    var p=find(id),c=category(cat);
    return p && c ? {planet:p.id,category:c,chapter:p.chapter,
                     values:p[c].slice(),sourceId:SOURCE.id} : null;
}
function matches(term){
    if(typeof term!=="string")return [];
    var needle=term.trim().toLowerCase();
    if(!needle || needle.length>80)return [];
    var hits=[];
    for(var i=0;i<PLANETS.length;i++){
        var p=PLANETS[i];
        for(var j=0;j<CATEGORIES.length;j++){
            var cat=CATEGORIES[j].id;
            for(var k=0;k<p[cat].length;k++){
                var value=p[cat][k];
                if(value.toLowerCase().indexOf(needle)>=0)
                    hits.push({planet:p.id,category:cat,value:value,
                               chapter:p.chapter,sourceId:SOURCE.id});
            }
        }
    }
    return hits;
}
function shared(term,cat){
    var id=category(cat),query=typeof term==="string"?term.toLowerCase():"";
    if(!id||!query)return [];
    return PLANETS.filter(function(p){
        return p[id].some(function(v){return v.toLowerCase()===query;});
    }).map(function(p){return p.id;});
}
function rowCount(){return PLANETS.length;}
function colCount(){return CATEGORIES.length;}
function wheel(width,height){
    if(typeof width!=="number"||typeof height!=="number"||
       !isFinite(width)||!isFinite(height) || width<160||height<135)
        return null;
    var radius=Math.min(width*0.40,height*0.42);
    if(radius<45)return null;
    var cx=width/2,cy=height/2;
    return {cx:cx,cy:cy,outer:radius,inner:radius*0.37,
        band:(radius-radius*0.37)/CATEGORIES.length};
}
function pickWheel(width,height,x,y){
    var g=wheel(width,height);
    if(!g || typeof x!=="number"||typeof y!=="number"||
       !isFinite(x)||!isFinite(y))return null;
    var dx=x-g.cx,dy=y-g.cy,r=Math.hypot(dx,dy);
    if(r<g.inner||r>=g.outer)return null;
    var radians=(Math.atan2(dy,dx)+Math.PI/2+Math.PI*2)%(Math.PI*2);
    var planetIndex=Math.floor(radians/(Math.PI*2)*PLANETS.length);
    var categoryIndex=Math.floor((r-g.inner)/g.band);
    if(planetIndex<0||planetIndex>=PLANETS.length||
       categoryIndex<0||categoryIndex>=CATEGORIES.length)return null;
    return {planet:PLANETS[planetIndex].id,
            category:CATEGORIES[categoryIndex].id};
}
function matrixCell(width,height,x,y){
    if(typeof width!=="number"||typeof height!=="number"||
       !isFinite(width)||!isFinite(height)||
       !isFinite(x)||!isFinite(y)||width<210||height<154)
        return null;
    var left=85,top=22,right=width-3,bottom=height-6;
    if(x<left||x>=right||y<top||y>=bottom)return null;
    var col=Math.floor((x-left)/(right-left)*CATEGORIES.length),
        row=Math.floor((y-top)/(bottom-top)*PLANETS.length);
    if(col<0||col>=CATEGORIES.length||row<0||row>=PLANETS.length)
        return null;
    return {planet:PLANETS[row].id,category:CATEGORIES[col].id};
}
