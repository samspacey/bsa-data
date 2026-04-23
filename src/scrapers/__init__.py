"""Scrapers for collecting review and mention data from various sources."""

from src.scrapers.appstore import AppStoreScraper
from src.scrapers.base import BaseScraper
from src.scrapers.fairer_finance import FairerFinanceScraper
from src.scrapers.feefo import FeefoScraper
from src.scrapers.google import GoogleScraper
from src.scrapers.mse import MSEScraper
from src.scrapers.playstore import PlayStoreScraper
from src.scrapers.reddit import RedditScraper
from src.scrapers.smartmoneypeople import SmartMoneyPeopleScraper
from src.scrapers.trustpilot import TrustpilotScraper
from src.scrapers.which import WhichScraper

__all__ = [
    "BaseScraper",
    "TrustpilotScraper",
    "AppStoreScraper",
    "PlayStoreScraper",
    "SmartMoneyPeopleScraper",
    "FeefoScraper",
    "RedditScraper",
    "MSEScraper",
    "GoogleScraper",
    "FairerFinanceScraper",
    "WhichScraper",
]
