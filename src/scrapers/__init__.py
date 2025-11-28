"""Scrapers for collecting review data from various sources."""

from src.scrapers.appstore import AppStoreScraper
from src.scrapers.base import BaseScraper
from src.scrapers.feefo import FeefoScraper
from src.scrapers.playstore import PlayStoreScraper
from src.scrapers.smartmoneypeople import SmartMoneyPeopleScraper
from src.scrapers.trustpilot import TrustpilotScraper

__all__ = [
    "BaseScraper",
    "TrustpilotScraper",
    "AppStoreScraper",
    "PlayStoreScraper",
    "SmartMoneyPeopleScraper",
    "FeefoScraper",
]
