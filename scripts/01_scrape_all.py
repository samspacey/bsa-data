#!/usr/bin/env python3
"""Script to scrape reviews from all sources for all building societies."""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.config.societies import get_all_societies, get_society_by_id
from src.scrapers import (
    AppStoreScraper,
    FeefoScraper,
    PlayStoreScraper,
    SmartMoneyPeopleScraper,
    TrustpilotScraper,
)


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(description="Scrape reviews from all sources")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["trustpilot", "appstore", "playstore", "smartmoneypeople", "feefo", "all"],
        default=["all"],
        help="Sources to scrape (default: all)",
    )
    parser.add_argument(
        "--societies",
        nargs="+",
        help="Society IDs to scrape (default: all)",
    )
    parser.add_argument(
        "--start-date",
        type=parse_date,
        default=parse_date(settings.data_start_date),
        help=f"Start date for reviews (default: {settings.data_start_date})",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=parse_date(settings.data_end_date),
        help=f"End date for reviews (default: {settings.data_end_date})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.raw_data_dir,
        help=f"Output directory for scraped data (default: {settings.raw_data_dir})",
    )

    args = parser.parse_args()

    # Determine which societies to scrape
    if args.societies:
        societies = []
        for sid in args.societies:
            s = get_society_by_id(sid)
            if s:
                societies.append(s)
            else:
                print(f"Warning: Unknown society ID '{sid}'")
    else:
        societies = get_all_societies()

    print(f"Scraping reviews for {len(societies)} building societies")
    print(f"Date range: {args.start_date} to {args.end_date}")
    print(f"Output directory: {args.output_dir}")
    print()

    # Determine which sources to scrape
    all_sources = ["trustpilot", "appstore", "playstore", "smartmoneypeople", "feefo"]
    sources = args.sources if "all" not in args.sources else all_sources

    total_reviews = 0

    # Scrape Trustpilot
    if "trustpilot" in sources:
        print("=" * 60)
        print("TRUSTPILOT")
        print("=" * 60)
        with TrustpilotScraper(output_dir=args.output_dir) as scraper:
            results = scraper.scrape_all(societies, args.start_date, args.end_date)
            count = sum(len(r) for r in results.values())
            total_reviews += count
            print(f"Total Trustpilot reviews: {count}")
        print()

    # Scrape App Store
    if "appstore" in sources:
        print("=" * 60)
        print("APPLE APP STORE")
        print("=" * 60)
        with AppStoreScraper(output_dir=args.output_dir) as scraper:
            results = scraper.scrape_all(societies, args.start_date, args.end_date)
            count = sum(len(r) for r in results.values())
            total_reviews += count
            print(f"Total App Store reviews: {count}")
        print()

    # Scrape Play Store
    if "playstore" in sources:
        print("=" * 60)
        print("GOOGLE PLAY STORE")
        print("=" * 60)
        with PlayStoreScraper(output_dir=args.output_dir) as scraper:
            results = scraper.scrape_all(societies, args.start_date, args.end_date)
            count = sum(len(r) for r in results.values())
            total_reviews += count
            print(f"Total Play Store reviews: {count}")
        print()

    # Scrape Smart Money People
    if "smartmoneypeople" in sources:
        print("=" * 60)
        print("SMART MONEY PEOPLE")
        print("=" * 60)
        with SmartMoneyPeopleScraper(output_dir=args.output_dir) as scraper:
            results = scraper.scrape_all(societies, args.start_date, args.end_date)
            count = sum(len(r) for r in results.values())
            total_reviews += count
            print(f"Total Smart Money People reviews: {count}")
        print()

    # Scrape Feefo
    if "feefo" in sources:
        print("=" * 60)
        print("FEEFO")
        print("=" * 60)
        with FeefoScraper(output_dir=args.output_dir) as scraper:
            results = scraper.scrape_all(societies, args.start_date, args.end_date)
            count = sum(len(r) for r in results.values())
            total_reviews += count
            print(f"Total Feefo reviews: {count}")
        print()

    print("=" * 60)
    print(f"TOTAL REVIEWS SCRAPED: {total_reviews}")
    print("=" * 60)


if __name__ == "__main__":
    main()
