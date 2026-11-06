.pragma library

// M6h // Manual transcription of physical Tarot draws, no random generator.
// The operator physically shuffles and chooses the cards; this policy only
// assigns verified deck IDs and orientation to predeclared spread positions.
// No journal, file writes, uploaded images, interpretations or persistence.
var FORMAT="post-apollo.weather.magick-tarot-physical.m6h.v1";
var MAX_CARDS=78;
function fail(reason,state){
    return {ok:false,reason:reason||"MANUAL CARD ENTRY UNAVAILABLE",state:state||null};
}
function slotsFor(spreads,id){
    if(!Array.isArray(spreads))return null;
    for(var i=0;i<spreads.length;i++){
        var row=spreads[i];
        if(row && row.id===id && Array.isArray(row.slots) &&
           row.slots.length>=1 && row.slots.length<=5 &&
           row.slots.every(function(s){
               return typeof s==="string" && s.length>0;
           }))return row.slots;
    }
    return null;
}
function validDeck(cards){
    if(!Array.isArray(cards) || cards.length!==MAX_CARDS)return false;
    var seen={};
    for(var i=0;i<cards.length;i++){
        var c=cards[i];
        if(!c || typeof c.id!=="string" || !c.id ||
           typeof c.title!=="string" || !c.title ||
           !Number.isInteger(c.index) || c.index!==i ||
           Object.prototype.hasOwnProperty.call(seen,c.id))return false;
        seen[c.id]=true;
    }
    return true;
}
function cardAt(cards,id){
    if(typeof id!=="string")return null;
    for(var i=0;i<cards.length;i++)
        if(cards[i].id===id)return cards[i];
    return null;
}
function start(spreads,deckId,spreadId){
    var slots=slotsFor(spreads,spreadId);
    if(typeof deckId!=="string" || !deckId || !slots)
        return {ready:false,reason:"SPREAD OR DECK UNVERIFIED",
            cards:[],count:0,complete:false};
    return {ready:true,reason:"",format:FORMAT,method:"PHYSICAL CARD ENTRY",
        deckId:deckId,spread:spreadId,total:slots.length,count:0,
        cards:[],complete:false,nextPosition:slots[0]};
}
function validate(spreads,cards,state){
    if(!validDeck(cards) || !state || state.ready!==true ||
       state.format!==FORMAT || state.method!=="PHYSICAL CARD ENTRY" ||
       typeof state.deckId!=="string" || !state.deckId ||
       !Array.isArray(state.cards) || !Number.isInteger(state.count) ||
       state.count!==state.cards.length)return false;
    var slots=slotsFor(spreads,state.spread),seen={};
    if(!slots || state.total!==slots.length ||
       state.count<0 || state.count>slots.length ||
       state.complete!==(state.count===slots.length) ||
       state.nextPosition!==(state.complete?"":slots[state.count]))
        return false;
    for(var i=0;i<state.cards.length;i++){
        var c=state.cards[i],original=c&&cardAt(cards,c.id);
        if(!original || c.title!==original.title ||
           c.family!==original.family || c.index!==original.index ||
           c.position!==slots[i] || typeof c.reversed!=="boolean" ||
           Object.prototype.hasOwnProperty.call(seen,c.id))return false;
        seen[c.id]=true;
    }
    return true;
}
function add(spreads,cards,state,cardId,reversed){
    if(!validate(spreads,cards,state))
        return fail("EXISTING PHYSICAL SPREAD INVALID",state);
    if(state.complete)return fail("SPREAD ALREADY COMPLETE",state);
    if(typeof reversed!=="boolean")
        return fail("ORIENTATION MUST BE EXPLICIT",state);
    var original=cardAt(cards,cardId);
    if(!original)return fail("CARD NOT IN SELECTED DECK",state);
    if(state.cards.some(function(c){return c.id===cardId;}))
        return fail("CARD ALREADY IN THIS SPREAD",state);
    var slots=slotsFor(spreads,state.spread),selected=state.cards.slice();
    selected.push({id:original.id,title:original.title,
        family:original.family,index:original.index,
        reversed:reversed,position:slots[selected.length]});
    return {ok:true,reason:"",state:{
        ready:true,reason:"",format:FORMAT,method:state.method,
        deckId:state.deckId,spread:state.spread,total:slots.length,
        count:selected.length,cards:selected,
        complete:selected.length===slots.length,
        nextPosition:selected.length===slots.length?"":slots[selected.length]
    }};
}
function undo(spreads,cards,state){
    if(!validate(spreads,cards,state))return fail("INVALID PHYSICAL SPREAD",state);
    if(state.count===0)return fail("NOTHING TO UNDO",state);
    var chosen=state.cards.slice(0,-1),slots=slotsFor(spreads,state.spread);
    return {ok:true,reason:"",state:{
        ready:true,reason:"",format:FORMAT,method:state.method,
        deckId:state.deckId,spread:state.spread,total:slots.length,
        count:chosen.length,cards:chosen,complete:false,
        nextPosition:slots[chosen.length]
    }};
}
function contains(state,cardId){
    return !!state && Array.isArray(state.cards) &&
        state.cards.some(function(c){return c.id===cardId;});
}
