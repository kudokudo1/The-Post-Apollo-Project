.pragma library

// M7a // No persistence, no journal store, no telemetry or system writes.
// This policy only formats an ephemeral local scratch preview.
var FORMAT="post-apollo.weather.magick-journal-draft.m7a.v1";
var MAX_TITLE=96;
var MAX_BODY=2048;
function summary(title,body){
    if(typeof title!=="string"||typeof body!=="string"||
       title.length>MAX_TITLE||body.length>MAX_BODY)
        return {valid:false,reason:"DRAFT INPUT LIMIT",hasContent:false,
            preview:"",wordCount:0,sessionOnly:true};
    var a=title.trim(),b=body.trim();
    var words=b?b.split(/\s+/).length:0;
    return {format:FORMAT,valid:true,reason:"",hasContent:!!(a||b),
        title:a,preview:b.length>140?b.slice(0,140)+"…":b,
        wordCount:words,characters:b.length,
        sessionOnly:true,persisted:false,
        provenance:"USER-ENTERED DRAFT // NOT SAVED"};
}
