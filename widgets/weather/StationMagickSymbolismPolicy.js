.pragma library

// M7a // Historical SYMBOLISM is not an empirical claim or universal oracle.
// Derive every selectable term from M6e's identified Agrippa Book I corpus.
// Another tradition/edition must be added with separate provenance later.
var FORMAT="post-apollo.weather.magick-symbolism.m7a.v1";
function build(planets,categories,source,category,needle){
    if(!Array.isArray(planets)||planets.length!==7||
       !Array.isArray(categories)||categories.length!==3||
       !source||source.id!=="agrippa-1651-book-i-23-29"||
       !["all","metals","stones","plants"].includes(category))
        return {ready:false,reason:"SOURCE OR CATEGORY NOT VERIFIED",
            rows:[],terms:[],count:0};
    var text=typeof needle==="string"?needle.trim().toLowerCase():"";
    if(text.length>80)return {ready:false,reason:"SEARCH TOO LONG",rows:[],terms:[],count:0};
    var rows=[],terms=[],termKeys={};
    for(var i=0;i<planets.length;i++){
        var p=planets[i];
        if(!p||typeof p.chapter!=="number" ||
           p.chapter<23||p.chapter>29)
            return {ready:false,reason:"SOURCE CHAPTER INVALID",rows:[],terms:[],count:0};
        for(var j=0;j<categories.length;j++){
            var cat=categories[j].id,values=p[cat];
            if(!Array.isArray(values))
                return {ready:false,reason:"SOURCE VALUE MISSING",rows:[],terms:[],count:0};
            if(category!=="all"&&category!==cat)continue;
            for(var k=0;k<values.length;k++){
                var term=values[k];
                if(typeof term!=="string" || !term)
                    return {ready:false,reason:"SOURCE TERM INVALID",rows:[],terms:[],count:0};
                if(text && term.toLowerCase().indexOf(text)<0)continue;
                rows.push({planet:p.id,chapter:p.chapter,
                    category:cat,term:term,sourceId:source.id});
                var key=cat+"\u0000"+term.toLowerCase();
                if(!termKeys[key]){
                    termKeys[key]=true;
                    terms.push({term:term,category:cat});
                }
            }
        }
    }
    return {ready:true,reason:"",format:FORMAT,rows:rows,
        terms:terms,count:rows.length,sourceId:source.id,
        sourceLabel:"AGRIPPA // BOOK I, 1651 ENGLISH",
        category:category,query:text};
}
function associated(model,term,category){
    if(!model||!model.ready||
       typeof term!=="string"||typeof category!=="string")return [];
    return model.rows.filter(function(row){
        return row.category===category&&
            row.term.toLowerCase()===term.toLowerCase();
    });
}
function place(index,width,height){
    if(!Number.isInteger(index)||index<0||index>=7||
       typeof width!=="number"||typeof height!=="number"||
       width<200||height<130)return null;
    var a=-Math.PI/2+2*Math.PI*index/7,r=Math.min(width*0.35,height*0.36);
    return {x:width/2+r*Math.cos(a),y:height/2+r*Math.sin(a)};
}
function hit(index,width,height,x,y){
    var point=place(index,width,height);
    if(!point)return false;
    return (point.x-x)*(point.x-x)+(point.y-y)*(point.y-y)<=17*17;
}
