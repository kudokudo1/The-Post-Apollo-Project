.pragma library

// MAGICK G1 // cross-domain astronomical references, not a divination engine.
// Astronomical measurements and symbolic interpretations are different kinds
// of claims. These entries only reuse existing COSMOS SKY instruments.
// No astrology ephemeris, ritual clock, saved journal or tarot generator.
var FORMAT = "post-apollo.weather.magick-reference.g1.v1";
var ROUTES = {
  "magick/overview": {
    title:"MAGICK // OBSERVATION AND INTERPRETATION",
    source:"cosmos/moon/ephemeris",
    secondary:"cosmos/sun/twilight",
    note:"THE MOON AND SUN PANELS ARE OBSERVATIONAL REFERENCES. ASTROLOGY, RITUAL TIMING AND DIVINATION ARE SEPARATE INTERPRETIVE SYSTEMS, NOT PRODUCED BY THESE READINGS."
  },
  "magick/astrology/charts": {
    title:"ASTROLOGY // CHARTS",
    source:"cosmos/planets-stars/celestial-fix",
    note:"USNO CURRENT SKY OBJECTS ARE AN ASTRONOMICAL REFERENCE ONLY. A NATAL OR EVENT CHART REQUIRES PRECISE LONGITUDES, ZODIAC FRAME, HOUSE SYSTEM, TIME, LOCATION AND EXPLICIT CHART CALCULATION, NONE OF WHICH IS CONNECTED."
  },
  "magick/astrology/zodiac": {
    title:"ASTROLOGY // ZODIAC",
    note:"NO TROPICAL OR SIDEREAL ZODIAC LONGITUDES OR SIGN CALCULATOR IS CONNECTED. CONSTELLATIONS ON THE SKY ARE NOT THE SAME THING AS ZODIAC SIGNS."
  },
  "magick/astrology/aspects": {
    title:"ASTROLOGY // ASPECTS",
    note:"NO PLANETARY ECLIPTIC-LONGITUDE PAIRS, ORBS, OR ASPECT CALCULATOR HAVE BEEN IMPLEMENTED. NO ASPECT IS INFERRED FROM RISE/SET OR ALTITUDE DATA."
  },
  "magick/astrology/retrogrades": {
    title:"ASTROLOGY // RETROGRADES",
    note:"RETROGRADE MOTION REQUIRES A TIME SERIES OF GEOCENTRIC POSITIONS. THE CURRENT PLANET RISE/SET FEED DOES NOT ESTABLISH RETROGRADE STATUS."
  },
  "magick/astrology/transits": {
    title:"ASTROLOGY // TRANSITS",
    note:"ASTROLOGICAL TRANSIT ANALYSIS REQUIRES A CHART, AN EPHEMERIS AND A CHOSEN CONVENTION. NOTHING IS CALCULATED HERE."
  },
  "magick/planetary/hours": {
    title:"PLANETARY MAGICK // HOURS",
    source:"cosmos/sun/twilight",
    note:"SUNRISE AND SUNSET PROVIDE CIVIL/TWILIGHT REFERENCE TIMES. NO TRADITIONAL PLANETARY-HOUR DIVISION, WEEKDAY SEQUENCE OR NIGHT-HOUR TIMING IS CALCULATED."
  },
  "magick/planetary/correspondences": {
    title:"PLANETARY MAGICK // CORRESPONDENCES",
    source:"cosmos/planets-stars/planet-clock",
    note:"VISIBLE PLANET RISE/SET TIMES ARE SCIENTIFIC OBSERVATIONS. PLANETARY COLORS, METALS, SYMBOLS OR DEITIES ARE CULTURAL ASSOCIATIONS THAT REQUIRE A CHOSEN TRADITION AND SOURCED REFERENCE LIBRARY."
  },
  "magick/planetary/timing": {
    title:"PLANETARY MAGICK // TRADITIONAL TIMING",
    source:"cosmos/sun/twilight",
    note:"SOLAR LIGHT WINDOWS ARE GIVEN FOR REFERENCE. NO AUSPICIOUS TIMING, RITUAL SCHEDULER, ASTROLOGICAL ELECTION OR PLANETARY-HOUR RULE IS CONNECTED."
  },
  "magick/lunar-solar/moon": {
    title:"LUNAR AND SOLAR // LUNAR CYCLES",
    source:"cosmos/moon/ephemeris",
    note:"THE USNO MOON PHASE, ILLUMINATION AND RISE/SET/TIME DATA ARE ASTRONOMICAL. TRADITIONAL PHASE MEANINGS AND PERSONAL INTERPRETATION ARE NOT PHYSICAL PROPERTIES OR AUTOMATED HERE."
  },
  "magick/lunar-solar/seasons": {
    title:"LUNAR AND SOLAR // SEASONS",
    source:"cosmos/sun/position",
    note:"LOCAL SOLAR POSITION AND DAYLIGHT ARE REFERENCES ONLY. EXACT EQUINOX/SOLSTICE INSTANTS AND TRADITIONAL SEASONAL CALENDAR DATES ARE NOT CONNECTED."
  },
  "magick/lunar-solar/calendar": {
    title:"LUNAR AND SOLAR // PRACTICE CALENDAR",
    source:"cosmos/moon/ephemeris",
    note:"CURRENT MOON EPHEMERIS IS REUSED. NO PLANNER, RITUAL EVENT RECORD, REMINDER OR RECURRING OBSERVANCE IS CREATED OR SAVED."
  },
  "magick/divination/tarot": {
    title:"DIVINATION // TAROT",
    note:"NO DECK, SHUFFLE, SPREAD PLACEMENT, CARD RECORD OR INTERPRETIVE MODEL HAS BEEN CONNECTED. TAROT IS A SYMBOLIC PRACTICE, NOT AN ASTRONOMICAL MEASUREMENT."
  },
  "magick/divination/symbolism": {
    title:"DIVINATION // SYMBOLISM",
    note:"SYMBOLIC REFERENCES REQUIRE A CHOSEN SOURCE/TRADITION. NO CULTURAL CORRESPONDENCE OR UNIVERSAL MEANING IS PRESENTED AS VERIFIED FACT."
  },
  "magick/grimoire/references": {
    title:"GRIMOIRE // REFERENCES",
    note:"NO SOURCED, EDITION-AWARE TEXT OR CORRESPONDENCE CATALOGUE IS CONNECTED. THE REFERENCE LIBRARY IS NOT IMPLEMENTED."
  },
  "magick/grimoire/journal": {
    title:"GRIMOIRE // JOURNAL",
    note:"NO JOURNAL STORAGE, ENCRYPTION, EXPORT, ATTACHMENT OR EDIT CONTROLS ARE CONNECTED. THIS ROUTE NEVER WRITES A PERSONAL RECORD."
  }
};

function routeInfo(path) {
  return typeof path === "string"
    && Object.prototype.hasOwnProperty.call(ROUTES,path)
    ? ROUTES[path] : null;
}
function kindForRoute(path) {
  return routeInfo(path) ? "reference" : "";
}
function sourceFor(path) {
  var row=routeInfo(path);
  return row && row.source ? row.source : "";
}
function secondarySourceFor(path) {
  var row=routeInfo(path);
  return row && row.secondary ? row.secondary : "";
}
function titleFor(path) {
  var row=routeInfo(path);
  return row ? row.title : "";
}
function noteFor(path) {
  var row=routeInfo(path);
  return row ? row.note : "";
}
function hasObservation(path) {
  return sourceFor(path) !== "";
}
function isInterpretationImplemented(path) {
  return false; // No future route silently becomes a real reading.
}
