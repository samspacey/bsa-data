"""Building society definitions and aliases for the MVP."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BuildingSociety:
    """Canonical building society definition."""

    id: str
    canonical_name: str
    bsa_name: str
    size_bucket: str  # mega, large, regional
    website_domain: str
    trustpilot_url: Optional[str] = None
    app_store_id: Optional[str] = None  # Apple App Store app ID
    play_store_id: Optional[str] = None  # Google Play package name
    aliases: List[str] = field(default_factory=list)
    notes: str = ""


# All 42 BSA member building societies
# Ordered by size: mega -> large -> regional -> small
BUILDING_SOCIETIES: list[BuildingSociety] = [
    BuildingSociety(
        id="nationwide",
        canonical_name="Nationwide Building Society",
        bsa_name="Nationwide Building Society",
        size_bucket="mega",
        website_domain="nationwide.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.nationwide.co.uk",
        app_store_id="583784694",
        play_store_id="co.uk.Nationwide.Mobile",
        aliases=[
            "Nationwide",
            "Nationwide BS",
            "NBS",
            "The Nationwide",
        ],
    ),
    BuildingSociety(
        id="coventry",
        canonical_name="Coventry Building Society",
        bsa_name="Coventry Building Society",
        size_bucket="large",
        website_domain="coventrybuildingsociety.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.coventrybuildingsociety.co.uk",
        app_store_id="1491465498",
        play_store_id="uk.co.coventrybuildingsociety.mobile",
        aliases=[
            "Coventry",
            "Coventry BS",
            "CBS",
        ],
    ),
    BuildingSociety(
        id="yorkshire",
        canonical_name="Yorkshire Building Society",
        bsa_name="Yorkshire Building Society",
        size_bucket="large",
        website_domain="ybs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.ybs.co.uk",
        app_store_id="1114783498",
        play_store_id="uk.co.ybs.app",
        aliases=[
            "Yorkshire",
            "Yorkshire BS",
            "YBS",
        ],
    ),
    BuildingSociety(
        id="skipton",
        canonical_name="Skipton Building Society",
        bsa_name="Skipton Building Society",
        size_bucket="large",
        website_domain="skipton.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.skipton.co.uk",
        app_store_id="1244142924",
        play_store_id="uk.co.skipton.android",
        aliases=[
            "Skipton",
            "Skipton BS",
            "SBS",
        ],
    ),
    BuildingSociety(
        id="leeds",
        canonical_name="Leeds Building Society",
        bsa_name="Leeds Building Society",
        size_bucket="large",
        website_domain="leedsbuildingsociety.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.leedsbuildingsociety.co.uk",
        app_store_id=None,  # Leeds BS does not have a mobile app
        play_store_id=None,  # Leeds BS does not have a mobile app
        aliases=[
            "Leeds",
            "Leeds BS",
            "LBS",
        ],
    ),
    BuildingSociety(
        id="principality",
        canonical_name="Principality Building Society",
        bsa_name="Principality Building Society",
        size_bucket="large",
        website_domain="principality.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.principality.co.uk",
        app_store_id="1552883252",
        play_store_id="uk.co.principality.mobileapp",
        aliases=[
            "Principality",
            "Principality BS",
            "PBS",
        ],
    ),
    BuildingSociety(
        id="west-brom",
        canonical_name="West Bromwich Building Society",
        bsa_name="West Bromwich Building Society",
        size_bucket="regional",
        website_domain="westbrom.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.westbrom.co.uk",
        app_store_id="1508440285",
        play_store_id="uk.co.westbrom.mobilebanking",
        aliases=[
            "West Brom",
            "West Bromwich",
            "West Bromwich BS",
            "WBBS",
            "The West Brom",
        ],
    ),
    BuildingSociety(
        id="newcastle",
        canonical_name="Newcastle Building Society",
        bsa_name="Newcastle Building Society",
        size_bucket="regional",
        website_domain="newcastle.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.newcastle.co.uk",
        app_store_id="1479823972",
        play_store_id="uk.co.newcastle.mobilebanking",
        aliases=[
            "Newcastle",
            "Newcastle BS",
            "NBS",
        ],
    ),
    BuildingSociety(
        id="nottingham",
        canonical_name="Nottingham Building Society",
        bsa_name="The Nottingham Building Society",
        size_bucket="regional",
        website_domain="thenottingham.com",
        trustpilot_url="https://uk.trustpilot.com/review/www.thenottingham.com",
        app_store_id="1478367116",
        play_store_id="uk.co.thenottingham.mobilebanking",
        aliases=[
            "Nottingham",
            "Nottingham BS",
            "The Nottingham",
            "NBS",
        ],
    ),
    BuildingSociety(
        id="cumberland",
        canonical_name="Cumberland Building Society",
        bsa_name="Cumberland Building Society",
        size_bucket="regional",
        website_domain="cumberland.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.cumberland.co.uk",
        app_store_id="1437991284",
        play_store_id="uk.co.cumberland.mobilebanking",
        aliases=[
            "Cumberland",
            "Cumberland BS",
            "The Cumberland",
        ],
    ),
    # ===== Additional BSA Members (32 societies) =====
    BuildingSociety(
        id="bath",
        canonical_name="Bath Building Society",
        bsa_name="Bath Building Society",
        size_bucket="small",
        website_domain="bathbuildingsociety.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/bathbuildingsociety.co.uk",
        aliases=[
            "Bath",
            "Bath BS",
        ],
    ),
    BuildingSociety(
        id="beverley",
        canonical_name="Beverley Building Society",
        bsa_name="Beverley Building Society",
        size_bucket="small",
        website_domain="beverleybs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/beverleybs.co.uk",
        aliases=[
            "Beverley",
            "Beverley BS",
        ],
    ),
    BuildingSociety(
        id="buckinghamshire",
        canonical_name="Buckinghamshire Building Society",
        bsa_name="Buckinghamshire Building Society",
        size_bucket="small",
        website_domain="bucksbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.bucksbs.co.uk",
        aliases=[
            "Buckinghamshire",
            "Buckinghamshire BS",
            "Bucks BS",
            "Bucks",
        ],
    ),
    BuildingSociety(
        id="cambridge",
        canonical_name="Cambridge Building Society",
        bsa_name="The Cambridge Building Society",
        size_bucket="regional",
        website_domain="cambridgebs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.cambridgebs.co.uk",
        aliases=[
            "Cambridge",
            "Cambridge BS",
            "The Cambridge",
        ],
    ),
    BuildingSociety(
        id="chorley",
        canonical_name="Chorley Building Society",
        bsa_name="Chorley & District Building Society",
        size_bucket="small",
        website_domain="chorleybs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/chorleybs.co.uk",
        aliases=[
            "Chorley",
            "Chorley BS",
            "Chorley & District",
        ],
    ),
    BuildingSociety(
        id="darlington",
        canonical_name="Darlington Building Society",
        bsa_name="Darlington Building Society",
        size_bucket="regional",
        website_domain="darlington.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/darlington.co.uk",
        aliases=[
            "Darlington",
            "Darlington BS",
        ],
        notes="Has mobile app - Darlingtonline",
    ),
    BuildingSociety(
        id="dudley",
        canonical_name="Dudley Building Society",
        bsa_name="Dudley Building Society",
        size_bucket="small",
        website_domain="dudleybuildingsociety.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/dudleybuildingsociety.co.uk",
        aliases=[
            "Dudley",
            "Dudley BS",
        ],
    ),
    BuildingSociety(
        id="earl-shilton",
        canonical_name="Earl Shilton Building Society",
        bsa_name="Earl Shilton Building Society",
        size_bucket="small",
        website_domain="esbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/esbs.co.uk",
        aliases=[
            "Earl Shilton",
            "Earl Shilton BS",
            "ESBS",
        ],
    ),
    BuildingSociety(
        id="ecology",
        canonical_name="Ecology Building Society",
        bsa_name="Ecology Building Society",
        size_bucket="small",
        website_domain="ecology.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/ecology.co.uk",
        aliases=[
            "Ecology",
            "Ecology BS",
            "EBS",
        ],
        notes="Ethical/green building society founded 1981",
    ),
    BuildingSociety(
        id="furness",
        canonical_name="Furness Building Society",
        bsa_name="Furness Building Society",
        size_bucket="regional",
        website_domain="furnessbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/furnessbs.co.uk",
        app_store_id="6502988567",
        play_store_id="uk.co.furnessbs",
        aliases=[
            "Furness",
            "Furness BS",
        ],
    ),
    BuildingSociety(
        id="hanley",
        canonical_name="Hanley Economic Building Society",
        bsa_name="Hanley Economic Building Society",
        size_bucket="small",
        website_domain="thehanley.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/thehanley.co.uk",
        aliases=[
            "Hanley Economic",
            "Hanley",
            "The Hanley",
        ],
    ),
    BuildingSociety(
        id="harpenden",
        canonical_name="Harpenden Building Society",
        bsa_name="Harpenden Building Society",
        size_bucket="small",
        website_domain="harpendenbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/harpendenbs.co.uk",
        aliases=[
            "Harpenden",
            "Harpenden BS",
        ],
    ),
    BuildingSociety(
        id="hinckley-rugby",
        canonical_name="Hinckley & Rugby Building Society",
        bsa_name="Hinckley and Rugby Building Society",
        size_bucket="regional",
        website_domain="hrbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.hrbs.co.uk",
        aliases=[
            "Hinckley & Rugby",
            "Hinckley and Rugby",
            "H&R",
            "HRBS",
        ],
        notes="Launched mobile app May 2025",
    ),
    BuildingSociety(
        id="leek-united",
        canonical_name="Leek United Building Society",
        bsa_name="Leek United Building Society",
        size_bucket="regional",
        website_domain="leekunited.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.leekunited.co.uk",
        aliases=[
            "Leek United",
            "Leek",
            "Leek BS",
        ],
    ),
    BuildingSociety(
        id="loughborough",
        canonical_name="Loughborough Building Society",
        bsa_name="Loughborough Building Society",
        size_bucket="small",
        website_domain="theloughborough.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/theloughborough.co.uk",
        aliases=[
            "Loughborough",
            "Loughborough BS",
            "The Loughborough",
        ],
    ),
    BuildingSociety(
        id="mansfield",
        canonical_name="Mansfield Building Society",
        bsa_name="The Mansfield Building Society",
        size_bucket="regional",
        website_domain="mansfieldbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/mansfieldbs.co.uk",
        aliases=[
            "Mansfield",
            "Mansfield BS",
            "The Mansfield",
        ],
    ),
    BuildingSociety(
        id="market-harborough",
        canonical_name="Market Harborough Building Society",
        bsa_name="Market Harborough Building Society",
        size_bucket="regional",
        website_domain="mhbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.mhbs.co.uk",
        aliases=[
            "Market Harborough",
            "Market Harborough BS",
            "MHBS",
        ],
        notes="Also on Feefo - Platinum Trusted Service Award",
    ),
    BuildingSociety(
        id="marsden",
        canonical_name="Marsden Building Society",
        bsa_name="Marsden Building Society",
        size_bucket="small",
        website_domain="themarsden.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/themarsden.co.uk",
        aliases=[
            "Marsden",
            "Marsden BS",
            "The Marsden",
        ],
    ),
    BuildingSociety(
        id="melton-mowbray",
        canonical_name="Melton Mowbray Building Society",
        bsa_name="Melton Mowbray Building Society",
        size_bucket="small",
        website_domain="mmbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/mmbs.co.uk",
        aliases=[
            "Melton Mowbray",
            "Melton",
            "MMBS",
        ],
    ),
    BuildingSociety(
        id="monmouthshire",
        canonical_name="Monmouthshire Building Society",
        bsa_name="Monmouthshire Building Society",
        size_bucket="regional",
        website_domain="monbs.com",
        trustpilot_url="https://uk.trustpilot.com/review/monbs.com",
        aliases=[
            "Monmouthshire",
            "Monmouthshire BS",
            "Mon BS",
        ],
        notes="Has mobile app",
    ),
    BuildingSociety(
        id="national-counties",
        canonical_name="National Counties Building Society",
        bsa_name="National Counties Building Society",
        size_bucket="small",
        website_domain="ncbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/ncbs.co.uk",
        aliases=[
            "National Counties",
            "National Counties BS",
            "NCBS",
            "Family Building Society",
        ],
        notes="Also trades as Family Building Society",
    ),
    BuildingSociety(
        id="newbury",
        canonical_name="Newbury Building Society",
        bsa_name="Newbury Building Society",
        size_bucket="small",
        website_domain="newbury.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/www.newbury.co.uk",
        aliases=[
            "Newbury",
            "Newbury BS",
        ],
    ),
    BuildingSociety(
        id="penrith",
        canonical_name="Penrith Building Society",
        bsa_name="Penrith Building Society",
        size_bucket="small",
        website_domain="penrithbuildingsociety.co.uk",
        trustpilot_url=None,  # Not found on Trustpilot, uses Feefo
        aliases=[
            "Penrith",
            "Penrith BS",
        ],
        notes="Uses Feefo for reviews instead of Trustpilot",
    ),
    BuildingSociety(
        id="progressive",
        canonical_name="Progressive Building Society",
        bsa_name="Progressive Building Society",
        size_bucket="regional",
        website_domain="theprogressive.com",
        trustpilot_url="https://uk.trustpilot.com/review/www.theprogressive.com",
        aliases=[
            "Progressive",
            "Progressive BS",
            "The Progressive",
        ],
        notes="Northern Ireland's largest locally-owned financial institution",
    ),
    BuildingSociety(
        id="saffron",
        canonical_name="Saffron Building Society",
        bsa_name="Saffron Building Society",
        size_bucket="regional",
        website_domain="saffronbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/saffronbs.co.uk",
        app_store_id="1482290341",
        play_store_id="uk.co.saffronbs.ebanking",
        aliases=[
            "Saffron",
            "Saffron BS",
        ],
    ),
    BuildingSociety(
        id="scottish",
        canonical_name="Scottish Building Society",
        bsa_name="Scottish Building Society",
        size_bucket="regional",
        website_domain="scottishbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/scottishbs.co.uk",
        app_store_id="1632028844",
        play_store_id="com.scottishbuildingsociety.nivo",
        aliases=[
            "Scottish",
            "Scottish BS",
            "SBS",
        ],
        notes="Oldest building society in the world (1848). App is for broker use only.",
    ),
    BuildingSociety(
        id="stafford-railway",
        canonical_name="Stafford Railway Building Society",
        bsa_name="Stafford Railway Building Society",
        size_bucket="small",
        website_domain="srbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/srbs.co.uk",
        aliases=[
            "Stafford Railway",
            "Stafford Railway BS",
            "SRBS",
        ],
    ),
    BuildingSociety(
        id="suffolk",
        canonical_name="Suffolk Building Society",
        bsa_name="Suffolk Building Society",
        size_bucket="small",
        website_domain="suffolkbuildingsociety.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/ibs.co.uk",
        aliases=[
            "Suffolk",
            "Suffolk BS",
            "Ipswich Building Society",
            "Ipswich BS",
        ],
        notes="Formerly Ipswich Building Society until 2021",
    ),
    BuildingSociety(
        id="swansea",
        canonical_name="Swansea Building Society",
        bsa_name="Swansea Building Society",
        size_bucket="small",
        website_domain="swansea-bs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/swansea-bs.co.uk",
        aliases=[
            "Swansea",
            "Swansea BS",
        ],
    ),
    BuildingSociety(
        id="teachers",
        canonical_name="Teachers Building Society",
        bsa_name="Teachers Building Society",
        size_bucket="small",
        website_domain="teachersbs.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/teachersbs.co.uk",
        aliases=[
            "Teachers",
            "Teachers BS",
            "TBS",
        ],
        notes="Founded 1966, originally for teachers",
    ),
    BuildingSociety(
        id="tipton",
        canonical_name="Tipton & Coseley Building Society",
        bsa_name="Tipton & Coseley Building Society",
        size_bucket="small",
        website_domain="thetipton.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/thetipton.co.uk",
        aliases=[
            "Tipton & Coseley",
            "Tipton",
            "The Tipton",
        ],
    ),
    BuildingSociety(
        id="vernon",
        canonical_name="Vernon Building Society",
        bsa_name="Vernon Building Society",
        size_bucket="small",
        website_domain="thevernon.co.uk",
        trustpilot_url="https://uk.trustpilot.com/review/thevernon.co.uk",
        aliases=[
            "Vernon",
            "Vernon BS",
            "The Vernon",
        ],
        notes="Stockport-based, founded 1924",
    ),
]

# Build lookup dictionaries
SOCIETY_BY_ID: Dict[str, BuildingSociety] = {s.id: s for s in BUILDING_SOCIETIES}

# Build alias lookup (lowercase normalized)
ALIAS_TO_SOCIETY_ID: Dict[str, str] = {}
for society in BUILDING_SOCIETIES:
    # Add canonical name
    ALIAS_TO_SOCIETY_ID[society.canonical_name.lower()] = society.id
    # Add all aliases
    for alias in society.aliases:
        ALIAS_TO_SOCIETY_ID[alias.lower()] = society.id


def get_society_by_id(society_id: str) -> Optional[BuildingSociety]:
    """Get a building society by its ID."""
    return SOCIETY_BY_ID.get(society_id)


def get_society_by_alias(alias: str) -> Optional[BuildingSociety]:
    """Get a building society by any of its aliases (case-insensitive)."""
    society_id = ALIAS_TO_SOCIETY_ID.get(alias.lower().strip())
    if society_id:
        return SOCIETY_BY_ID.get(society_id)
    return None


def get_all_societies() -> List[BuildingSociety]:
    """Get all building societies."""
    return BUILDING_SOCIETIES.copy()
