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
    note:"USNO CURRENT OBJECTS REMAIN A SKY REFERENCE. JPL ECLIPTIC LONGITUDES MAY BE CALCULATED ON DEMAND WHEN THE KERNEL IS CONFIGURED. A COMPLETE NATAL/EVENT CHART REQUIRES HOUSE SYSTEM, EXACT LOCATION, TIME AND ZODIAC CHOICES; NONE OF WHICH IS CONNECTED AS A FULL CHART."
  },
  "magick/astrology/zodiac": {
    title:"ASTROLOGY // ZODIAC",
    note:"JPL TRUE-ECLIPTIC LONGITUDE WHEEL IS AVAILABLE ON DEMAND WHEN CONFIGURED. NO SIDEREAL SIGN CALCULATOR OR ASTROLOGICAL INTERPRETATION LIBRARY IS CONNECTED. CONSTELLATIONS ARE NOT TROPICAL ZODIAC SIGNS."
  },
  "magick/astrology/aspects": {
    title:"ASTROLOGY // ASPECTS",
    note:"JPL LONGITUDE SEPARATION AND CONVENTIONAL ASPECT ORBS MAY BE CALCULATED ON DEMAND. NO ASPECT INFLUENCE OR INTERPRETIVE READING IS INFERRED FROM THE ASTRONOMICAL MEASUREMENTS, RISE/SET OR ALTITUDE."
  },
  "magick/astrology/retrogrades": {
    title:"ASTROLOGY // RETROGRADES",
    note:"RETROGRADE MOTION REQUIRES A TIME SERIES OF GEOCENTRIC POSITIONS. ON-DEMAND JPL TIME SERIES MAY SHOW APPARENT MERCURY MOTION IF CONFIGURED; RISE/SET DOES NOT ESTABLISH RETROGRADE STATUS."
  },
  "magick/astrology/transits": {
    title:"ASTROLOGY // TRANSITS",
    note:"M6C COMPARES TWO ACTUAL JPL GEOCENTRIC APPARENT ECLIPTIC LONGITUDE SNAPSHOTS IN THEIR RESPECTIVE DATE-DEPENDENT FRAMES. REF DEFAULTS TO FIRST SOURCE UTC; PIN REF CHOOSES ANOTHER SAMPLE. NOT A NATAL/HOUSE CHART, CROSS-EPOCH ASPECT ENGINE, INTERPRETATION OR CAUSAL TRANSIT READING."
  },
  "magick/planetary/hours": {
    title:"PLANETARY MAGICK // HOURS",
    source:"cosmos/sun/twilight",
    note:"M6D CHALDEAN-ORDER PLANETARY HOURS DIVIDE THE EXISTING PROVIDER-LOCAL SUNRISE-TO-SUNSET AND SUNSET-TO-NEXT-SUNRISE CLOCK WINDOWS INTO TWELVE EACH. THE RULERS ARE A HISTORICAL CONVENTION, NOT ASTRONOMICAL CAUSATION OR AN AUSPICIOUSNESS FORECAST. WEATHER DATA LACKS PER-EVENT TIMEZONE OFFSETS, SO DST-TRANSITION ELAPSED DURATIONS ARE UNVERIFIED."
  },
  "magick/planetary/correspondences": {
    title:"PLANETARY MAGICK // CORRESPONDENCES",
    source:"cosmos/planets-stars/planet-clock",
    note:"M6E ADDS AN AGRIPPA 1651 ENGLISH, BOOK I CHAPTERS XXIII–XXIX PLANETARY REFERENCE INSIDE THE EXISTING LENSES SCREEN. HISTORICAL METALS, STONES AND PLANTS ARE SOURCE-ATTRIBUTED AND MAY OVERLAP. DISPLAY COLORS ARE UI CHOICES, NOT AGRIPPA COLOR CLAIMS. COSMOS RISE/SET DATA REMAINS A SEPARATE SCIENTIFIC REFERENCE; NO SYMBOLIC CAUSATION OR FULL GRIMOIRE IS IMPLEMENTED."
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
    note:"M6F SOURCE ATLAS INDEXES THE EXISTING M6E AGRIPPA 1651 ENGLISH BOOK I XXIII–XXIX CORRESPONDENCE TERMS, WITH TERM SEARCH, CATEGORY FILTER, CHAPTER REFERENCES AND A SHARED-TERM NETWORK. THIS IS ONE HISTORICAL EDITION, NOT A COMPLETE GRIMOIRE, DIVINATION READING OR PERSONAL JOURNAL. NO NEW TEXTS, MEDICAL EFFECTS, CAUSAL CLAIMS OR AUTOMATIC PRACTICE ADVICE ARE PROVIDED."
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
// M5b // Observational calculation routes only. Not spiritual interpretation.
function visualForRoute(path) {
  return path === "magick/astrology/charts"
      || path === "magick/astrology/zodiac"
      || path === "magick/astrology/aspects"
      || path === "magick/astrology/retrogrades"
      || path === "magick/astrology/transits";
}
function isInterpretationImplemented(path) {
  return false; // No future route silently becomes a real reading.
}
