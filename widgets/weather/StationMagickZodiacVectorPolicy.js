.pragma library

// M5i // Font-independent, hand-drawn zodiac glyph vectors.
// Coordinates are 24 x 24 optical artwork units, not sky positions.
// These signs are conventional tropical zodiac sector symbols, not celestial
// bodies or observations. No font lookup, raster asset or file read required.
var STROKES = [
    // ♈ Aries: paired horns and center stem.
    [
        [["M",12,21],["L",12,11],["C",12,5,9,3,6,3],["C",3,3,3,7,4,10]],
        [["M",12,11],["C",12,5,15,3,18,3],["C",21,3,21,7,20,10]]
    ],
    // ♉ Taurus: curved horns over the bull's circular head.
    [
        [["M",4,4],["C",4,9,8,10,12,10],["C",16,10,20,9,20,4]],
        [["M",12,10],["C",20,10,20,21,12,21],["C",4,21,4,10,12,10],["Z"]]
    ],
    // ♊ Gemini: twin columns, connected upper and lower caps.
    [
        [["M",5,4],["Q",12,1,19,4]],
        [["M",8,4],["L",8,20]],
        [["M",16,4],["L",16,20]],
        [["M",5,20],["Q",12,23,19,20]]
    ],
    // ♋ Cancer: opposing loops in the 69-shaped motif.
    [
        [["M",3,9],["C",7,3,16,3,21,8]],
        [["M",20,9],["C",20,13,14,13,14,9],["C",14,5,20,5,20,9],["Z"]],
        [["M",21,15],["C",17,21,8,21,3,16]],
        [["M",10,15],["C",10,11,4,11,4,15],["C",4,19,10,19,10,15],["Z"]]
    ],
    // ♌ Leo: head loop and curling tail.
    [
        [["M",8,8],["C",10,2,18,4,17,10],["C",16,15,12,17,14,20],
         ["C",16,22,21,20,21,16]],
        [["M",8,8],["C",3,8,2,12,5,15],["C",8,18,12,15,12,12],
         ["C",12,9,10,8,8,8],["Z"]]
    ],
    // ♍ Virgo: three arches with curled descending tail.
    [
        [["M",3,6],["L",3,18],["M",3,8],["C",3,4,9,4,9,9],["L",9,18],
         ["M",9,8],["C",9,4,15,4,15,9],["L",15,18]],
        [["M",15,8],["C",17,5,20,7,20,11],["C",20,15,17,17,16,20],
         ["C",19,22,22,20,22,17]]
    ],
    // ♎ Libra: rising balance arch above the baseline.
    [
        [["M",3,19],["L",21,19]],
        [["M",3,15],["L",8,15],["C",7,13,7,10,9,8],
         ["C",11,5,15,5,17,8],["C",19,10,18,13,16,15],["L",21,15]]
    ],
    // ♏ Scorpio: three ascending arches with pointed tail.
    [
        [["M",3,6],["L",3,18],["M",3,8],["C",3,4,9,4,9,9],["L",9,18],
         ["M",9,8],["C",9,4,15,4,15,9],["L",15,18]],
        [["M",15,8],["C",17,5,19,7,19,11],["L",19,20],
         ["M",16,17],["L",19,20],["L",22,17]]
    ],
    // ♐ Sagittarius: diagonally rising arrow with cross stroke.
    [
        [["M",4,20],["L",20,4],["L",11,4]],
        [["M",20,4],["L",20,13]],
        [["M",6,9],["L",15,18]]
    ],
    // ♑ Capricorn: goat-like head and curled fish tail.
    [
        [["M",3,6],["C",4,3,8,3,9,7],["L",11,15],
         ["C",13,8,17,5,20,7],["C",23,9,21,13,18,13],
         ["C",15,13,14,11,14,10]],
        [["M",11,15],["C",9,22,15,23,20,20],
         ["C",22,19,21,17,20,17],["C",19,17,18,18,18,19]]
    ],
    // ♒ Aquarius: two horizontal parallel water-bearer zigzags.
    [
        [["M",2,9],["L",6,5],["L",10,9],["L",14,5],
         ["L",18,9],["L",22,5]],
        [["M",2,18],["L",6,14],["L",10,18],["L",14,14],
         ["L",18,18],["L",22,14]]
    ],
    // ♓ Pisces: facing fish-arc curves with central connecting line.
    [
        [["M",8,3],["C",2,6,2,18,8,21]],
        [["M",16,3],["C",22,6,22,18,16,21]],
        [["M",3,12],["L",21,12]]
    ]
];

// Use one geometry function for every rendering context and compact size.
// Place sector symbols at the CENTER of each 30-degree tropical sector.
// The existing wheel puts 0-degree longitude at the top.
function sectorCenter(index, width, height, wheelRadius) {
    if(typeof index!=="number" || Math.floor(index)!==index ||
       index<0 || index>=12 ||
       !isFinite(width) || !isFinite(height) || !isFinite(wheelRadius) ||
       width<=0 || height<=0 || wheelRadius<=0)return null;
    var edgeDistance=Math.max(8,Math.min(width,height)/2 - 10);
    var symbolRadius=Math.min(wheelRadius+14,edgeDistance);
    var radians=(index+0.5)*Math.PI/6;
    return {x:width/2+symbolRadius*Math.sin(radians),
            y:height/2-symbolRadius*Math.cos(radians),
            radius:symbolRadius};
}
function strokesFor(index) {
    return typeof index==="number" && Math.floor(index)===index &&
           index>=0 && index<STROKES.length ? STROKES[index] : [];
}


// M5j // Keep ordinary signs legible but visually subordinate. Selection is
// explicit and source-derived from the focused body's longitude. The chosen
// sign is rendered LAST so its slight enlargement always sits above peers.
// Defaults remain comfortably separated in 100px-high compact canvases.
function appearance(selected) {
    if(selected) return {
        chipRadius:10.9,chipOpacity:0.99,
        edgeOpacity:1.0,edgeWidth:1.7,edgeGlow:14,
        symbolScale:0.74,outlineWidth:4.7,
        inkWidth:2.9,inkOpacity:1.0,inkGlow:14
    };
    return {
        chipRadius:8.9,chipOpacity:0.86,
        edgeOpacity:0.60,edgeWidth:1.0,edgeGlow:5,
        symbolScale:0.58,outlineWidth:4.1,
        inkWidth:2.1,inkOpacity:0.84,inkGlow:4.5
    };
}
