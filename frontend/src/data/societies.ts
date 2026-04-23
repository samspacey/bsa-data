export interface Society {
  id: string;
  name: string;
  short: string;
  region: string;
  founded: number;
  hue: number;
  domain: string;
}

// 42 BSA member building societies with website domains for real logos.
export const societies: Society[] = [
  { id: "nationwide",       name: "Nationwide Building Society",        short: "Nationwide",        region: "National",    founded: 1846, hue: 215, domain: "nationwide.co.uk" },
  { id: "coventry",         name: "Coventry Building Society",          short: "Coventry",          region: "Midlands",    founded: 1884, hue: 210, domain: "coventrybuildingsociety.co.uk" },
  { id: "yorkshire",        name: "Yorkshire Building Society",         short: "Yorkshire",         region: "Yorkshire",   founded: 1864, hue: 220, domain: "ybs.co.uk" },
  { id: "skipton",          name: "Skipton Building Society",           short: "Skipton",           region: "Yorkshire",   founded: 1853, hue: 205, domain: "skipton.co.uk" },
  { id: "leeds",            name: "Leeds Building Society",             short: "Leeds",             region: "Yorkshire",   founded: 1875, hue: 208, domain: "leedsbuildingsociety.co.uk" },
  { id: "principality",     name: "Principality Building Society",      short: "Principality",      region: "Wales",       founded: 1860, hue: 340, domain: "principality.co.uk" },
  { id: "west-brom",        name: "West Bromwich Building Society",     short: "West Brom",         region: "Midlands",    founded: 1849, hue: 0,   domain: "westbrom.co.uk" },
  { id: "newcastle",        name: "Newcastle Building Society",         short: "Newcastle",         region: "North East",  founded: 1861, hue: 198, domain: "newcastle.co.uk" },
  { id: "nottingham",       name: "Nottingham Building Society",        short: "Nottingham",        region: "Midlands",    founded: 1849, hue: 155, domain: "thenottingham.com" },
  { id: "cumberland",       name: "Cumberland Building Society",        short: "Cumberland",        region: "Cumbria",     founded: 1850, hue: 165, domain: "cumberland.co.uk" },
  { id: "cambridge",        name: "Cambridge Building Society",         short: "Cambridge",         region: "East Anglia", founded: 1850, hue: 270, domain: "cambridgebs.co.uk" },
  { id: "saffron",          name: "Saffron Building Society",           short: "Saffron",           region: "East Anglia", founded: 1849, hue: 30,  domain: "saffronbs.co.uk" },
  { id: "furness",          name: "Furness Building Society",           short: "Furness",           region: "Cumbria",     founded: 1865, hue: 190, domain: "furnessbs.co.uk" },
  { id: "market-harborough", name: "Market Harborough Building Society", short: "Market Harborough", region: "Midlands",    founded: 1870, hue: 75,  domain: "mhbs.co.uk" },
  { id: "scottish",         name: "Scottish Building Society",          short: "Scottish",          region: "Scotland",    founded: 1848, hue: 230, domain: "scottishbs.co.uk" },
  { id: "monmouthshire",    name: "Monmouthshire Building Society",     short: "Monmouthshire",     region: "Wales",       founded: 1869, hue: 225, domain: "monbs.com" },
  { id: "marsden",          name: "Marsden Building Society",           short: "Marsden",           region: "Yorkshire",   founded: 1860, hue: 250, domain: "themarsden.co.uk" },
  { id: "newbury",          name: "Newbury Building Society",           short: "Newbury",           region: "South East",  founded: 1856, hue: 140, domain: "newbury.co.uk" },
  { id: "national-counties", name: "National Counties Building Society", short: "National Counties", region: "South East",  founded: 1896, hue: 235, domain: "ncbs.co.uk" },
  { id: "suffolk",          name: "Suffolk Building Society",           short: "Suffolk",           region: "East Anglia", founded: 1849, hue: 50,  domain: "suffolkbuildingsociety.co.uk" },
  { id: "progressive",      name: "Progressive Building Society",       short: "Progressive",       region: "Northern Ireland", founded: 1914, hue: 180, domain: "theprogressive.com" },
  { id: "bath",             name: "Bath Building Society",              short: "Bath",              region: "South West",  founded: 1904, hue: 20,  domain: "bathbuildingsociety.co.uk" },
  { id: "hanley",           name: "Hanley Economic Building Society",   short: "Hanley Economic",   region: "Midlands",    founded: 1854, hue: 10,  domain: "thehanley.co.uk" },
  { id: "ecology",          name: "Ecology Building Society",           short: "Ecology",           region: "Yorkshire",   founded: 1981, hue: 100, domain: "ecology.co.uk" },
  { id: "mansfield",        name: "Mansfield Building Society",         short: "Mansfield",         region: "Midlands",    founded: 1870, hue: 125, domain: "mansfieldbs.co.uk" },
  { id: "melton-mowbray",   name: "Melton Mowbray Building Society",    short: "Melton Mowbray",    region: "Midlands",    founded: 1875, hue: 45,  domain: "mmbs.co.uk" },
  { id: "leek-united",      name: "Leek United Building Society",       short: "Leek",              region: "Midlands",    founded: 1863, hue: 280, domain: "leekunited.co.uk" },
  { id: "darlington",       name: "Darlington Building Society",        short: "Darlington",        region: "North East",  founded: 1856, hue: 325, domain: "darlington.co.uk" },
  { id: "tipton",           name: "Tipton & Coseley Building Society",  short: "Tipton",            region: "Midlands",    founded: 1901, hue: 195, domain: "thetipton.co.uk" },
  { id: "buckinghamshire",  name: "Buckinghamshire Building Society",   short: "Buckinghamshire",   region: "South East",  founded: 1907, hue: 240, domain: "bucksbs.co.uk" },
  { id: "hinckley-rugby",   name: "Hinckley & Rugby Building Society",  short: "Hinckley & Rugby",  region: "Midlands",    founded: 1865, hue: 5,   domain: "hrbs.co.uk" },
  { id: "dudley",           name: "Dudley Building Society",            short: "Dudley",            region: "Midlands",    founded: 1858, hue: 260, domain: "dudleybuildingsociety.co.uk" },
  { id: "teachers",         name: "Teachers Building Society",          short: "Teachers",          region: "South West",  founded: 1966, hue: 215, domain: "teachersbs.co.uk" },
  { id: "harpenden",        name: "Harpenden Building Society",         short: "Harpenden",         region: "South East",  founded: 1953, hue: 170, domain: "harpendenbs.co.uk" },
  { id: "swansea",          name: "Swansea Building Society",           short: "Swansea",           region: "Wales",       founded: 1923, hue: 345, domain: "swansea-bs.co.uk" },
  { id: "vernon",           name: "Vernon Building Society",            short: "Vernon",            region: "North West",  founded: 1875, hue: 290, domain: "thevernon.co.uk" },
  { id: "penrith",          name: "Penrith Building Society",           short: "Penrith",           region: "Cumbria",     founded: 1877, hue: 0,   domain: "penrithbuildingsociety.co.uk" },
  { id: "chorley",          name: "Chorley Building Society",           short: "Chorley",           region: "North West",  founded: 1859, hue: 85,  domain: "chorleybs.co.uk" },
  { id: "earl-shilton",     name: "Earl Shilton Building Society",      short: "Earl Shilton",      region: "Midlands",    founded: 1857, hue: 55,  domain: "esbs.co.uk" },
  { id: "loughborough",     name: "Loughborough Building Society",      short: "Loughborough",      region: "Midlands",    founded: 1867, hue: 300, domain: "theloughborough.co.uk" },
  { id: "stafford-railway", name: "Stafford Railway Building Society",  short: "Stafford Railway",  region: "Midlands",    founded: 1877, hue: 200, domain: "srbs.co.uk" },
  { id: "beverley",         name: "Beverley Building Society",          short: "Beverley",          region: "Yorkshire",   founded: 1866, hue: 310, domain: "beverleybs.co.uk" },
];

export function findSociety(id: string): Society | undefined {
  return societies.find(s => s.id === id);
}
