.pragma library

// MAGICK M6g // Wild Unknown Tarot-compatible CARD IDENTITIES ONLY.
// Kim Krans retains rights in her original illustrations and guidebook.
// This source contains no card images, copied guidebook interpretations,
// remote art URLs, journal records or licensed artwork claims.
// The four courts use the actual Daughter / Son / Mother / Father titles.
//
// This is a SYMBOLIC DRAW, using injected pseudorandom values. It is not
// cryptographic randomness, a scientific prediction or a saved reading.
var FORMAT="post-apollo.weather.magick-tarot.m6g.v1";
var DECK={
    id:"the-wild-unknown-tarot",
    name:"THE WILD UNKNOWN TAROT",
    creator:"KIM KRANS",
    publisher:"HARPERONE",
    count:78,
    cardIdentityOnly:true,
    artworkIncluded:false,
    guidebookTextIncluded:false,
    artPolicy:"USER-SUPPLIED LOCAL FILES ONLY // NO BUNDLED ILLUSTRATIONS",
    sourceUrl:"https://kimkrans.com/the-wild-unknown"
};
var MAJORS=[
    "The Fool","The Magician","The High Priestess","The Empress",
    "The Emperor","The Hierophant","The Lovers","The Chariot",
    "Strength","The Hermit","Wheel of Fortune","Justice",
    "The Hanged Man","Death","Temperance","The Devil","The Tower",
    "The Star","The Moon","The Sun","Judgement","The World"
];
// Display order only. No numbered-major claim; sources differ on
// Strength/Justice sequence in printed variants.
var SUITS=["Wands","Cups","Swords","Pentacles"];
var COURTS=["Daughter","Son","Mother","Father"];
var SPREADS=[
    {id:"one",label:"SINGLE",slots:["CARD"]},
    {id:"three",label:"THREE",slots:["PAST","PRESENT","FUTURE"]},
    {id:"five",label:"FIVE",slots:[
        "CONTEXT","TENSION","PERSPECTIVE","POSSIBILITY","REFLECTION"]}
];
function key(text){
    return text.toLowerCase().replace(/[^a-z0-9]+/g,"-")
               .replace(/^-|-$/g,"");
}
function createCards(){
    var cards=[],i;
    for(i=0;i<MAJORS.length;i++)
        cards.push({id:"major-"+key(MAJORS[i]),
                    title:MAJORS[i],family:"major",
                    rank:"",suit:"",index:cards.length});
    for(var s=0;s<SUITS.length;s++){
        var suit=SUITS[s],family=suit.toLowerCase();
        var ranks=["Ace","2","3","4","5","6","7","8","9","10"]
                    .concat(COURTS);
        for(i=0;i<ranks.length;i++){
            var rank=ranks[i];
            cards.push({id:family+"-"+key(rank),
                title:rank+" of "+suit,family:family,
                rank:rank,suit:suit,index:cards.length});
        }
    }
    return cards;
}
var CARDS=createCards();

function cardById(id){
    if(typeof id!=="string")return null;
    for(var i=0;i<CARDS.length;i++)
        if(CARDS[i].id===id)return CARDS[i];
    return null;
}
function family(id){
    if(id==="all"||id==="major"||
       SUITS.some(function(s){return s.toLowerCase()===id;}))
        return id;
    return "";
}
function catalog(familyId){
    var group=family(familyId);
    if(group==="")return [];
    return CARDS.filter(function(c){
        return group==="all" || c.family===group;
    });
}
function spread(id){
    for(var i=0;i<SPREADS.length;i++)
        if(SPREADS[i].id===id)return SPREADS[i];
    return null;
}
// Fisher-Yates, randomFn MUST return 0 <= x < 1. A successful draw
// takes no duplicate card and does not mutate the shared catalogue.
// Failure returns no partial reading. Reversals use a *separate* roll.
function draw(spreadId,randomFn,allowReversals) {
    var spec=spread(spreadId);
    if(!spec || typeof randomFn!=="function" ||
       typeof allowReversals!=="boolean" ||
       CARDS.length!==DECK.count)
        return {ready:false,reason:"INVALID DRAW CONTROLS",cards:[]};
    var order=CARDS.slice(),choice=[],roll;
    for(var i=order.length-1;i>0;i--){
        roll=randomFn();
        if(typeof roll!=="number" || !isFinite(roll) ||
           roll<0 || roll>=1)
            return {ready:false,reason:"RANDOM SOURCE OUT OF RANGE",cards:[]};
        var j=Math.floor(roll*(i+1));
        var swap=order[i];order[i]=order[j];order[j]=swap;
    }
    for(var c=0;c<spec.slots.length;c++){
        var original=order[c],reversed=false;
        if(allowReversals){
            roll=randomFn();
            if(typeof roll!=="number" || !isFinite(roll) ||
               roll<0 || roll>=1)
                return {ready:false,reason:"REVERSAL SOURCE OUT OF RANGE",cards:[]};
            reversed=roll>=0.5;
        }
        choice.push({id:original.id,title:original.title,
            family:original.family,index:original.index,
            position:spec.slots[c],reversed:reversed});
    }
    return {ready:true,reason:"",format:FORMAT,
        deckId:DECK.id,spread:spreadId,count:choice.length,
        method:"FISHER-YATES / PSEUDORANDOM MATH.RANDOM",
        cards:choice};
}
// No auto-scan, copying, uploading, web URL or external-file traversal.
// User consciously supplies a local absolute directory containing
// filenames such as "major-the-fool.png", "wands-daughter.png".
function localArtworkUrl(folder,id){
    if(typeof folder!=="string" || typeof id!=="string" ||
       folder.length>1024 || folder.length<2 || folder.charAt(0)!=="/" ||
       folder.indexOf("..")>=0 || folder.indexOf("\\")>=0 ||
       folder.indexOf(":")>=0 || /[\u0000-\u001f]/.test(folder) ||
       !cardById(id))
        return "";
    var path=folder.split("/").filter(function(part){return part!=="";});
    if(!path.length)return "";
    return "file:///"+path.map(encodeURIComponent).join("/")+
        "/"+encodeURIComponent(id)+".png";
}

// The same known card can be provided as PNG, JPEG or WebP. There is no
// folder scan or network lookup: QML only tries these exact local names.
// If none is readable it must explicitly show an artwork-unavailable status.
function localArtworkCandidates(folder,id) {
    var png=localArtworkUrl(folder,id);
    if(!png)return [];
    var prefix=png.slice(0,-4);
    return [png,prefix+".jpg",prefix+".jpeg",prefix+".webp"];
}


// M6k // QtQuick.Dialogs.FolderDialog.selectedFolder is a file:/// URL.
// Convert it to the existing localArtworkUrl() contract's absolute path.
// This does not test file existence, scan folders or grant any write access.
function localFolderPath(url) {
    var value=String(url===null || url===undefined?"":url);
    if(value.slice(0,8)!=="file:///" || /[?#]/.test(value) ||
       /%2f|%5c/i.test(value))
        return "";
    var source=value.slice(8).replace(/\/$/,"");
    if(!source)return "";
    var raw=source.split("/"),parts=[];
    for(var i=0;i<raw.length;i++) {
        if(!raw[i])return "";
        try {
            var part=decodeURIComponent(raw[i]);
            if(part==="" || part==="." || part===".." ||
               part.indexOf("/")>=0 || part.indexOf("\\")>=0)
                return "";
            parts.push(part);
        }catch(err){return "";}
    }
    var folder="/"+parts.join("/");
    return localArtworkUrl(folder,"major-the-fool")!==""?folder:"";
}
