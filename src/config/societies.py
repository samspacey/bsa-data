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


# Target building societies for MVP (10 societies)
# Based on BSA membership and Trustpilot presence
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
