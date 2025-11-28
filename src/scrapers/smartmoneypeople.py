"""Smart Money People scraper for building society reviews."""

import json
import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.config.societies import BuildingSociety
from src.data.schemas import RawReview
from src.scrapers.base import BaseScraper


# Mapping of society IDs to Smart Money People URL slugs
SOCIETY_SLUGS = {
    "nationwide": "nationwide-building-society",
    "coventry": "coventry-building-society",
    "yorkshire": "yorkshire-building-society",
    "skipton": "skipton-building-society",
    "leeds": "leeds-building-society",
    "principality": "principality-building-society",
    "west-brom": "west-bromwich-building-society",
    "newcastle": "newcastle-building-society",
    "nottingham": "the-nottingham-building-society",
    "cumberland": "cumberland-building-society",
    "bath": "bath-building-society",
    "beverley": "beverley-building-society",
    "buckinghamshire": "buckinghamshire-building-society",
    "cambridge": "cambridge-building-society",
    "chorley": "chorley-building-society",
    "darlington": "darlington-building-society",
    "dudley": "dudley-building-society",
    "earl-shilton": "earl-shilton-building-society",
    "ecology": "ecology-building-society",
    "furness": "furness-building-society",
    "hanley": "hanley-economic-building-society",
    "harpenden": "harpenden-building-society",
    "hinckley-rugby": "hinckley-rugby-building-society",
    "leek-united": "leek-building-society",
    "loughborough": "loughborough-building-society",
    "mansfield": "mansfield-building-society",
    "market-harborough": "market-harborough-building-society",
    "marsden": "marsden-building-society",
    "melton-mowbray": "melton-mowbray-building-society",
    "monmouthshire": "monmouthshire-building-society",
    "national-counties": "national-counties-building-society",
    "newbury": "newbury-building-society",
    "penrith": "penrith-building-society",
    "progressive": "progressive-building-society",
    "saffron": "saffron-building-society",
    "scottish": "scottish-building-society",
    "stafford-railway": "stafford-railway-building-society",
    "suffolk": "suffolk-building-society",
    "swansea": "swansea-building-society",
    "teachers": "teachers-building-society",
    "tipton": "tipton-coseley-building-society",
    "vernon": "vernon-building-society",
}


class SmartMoneyPeopleScraper(BaseScraper):
    """Scraper for Smart Money People reviews."""

    BASE_URL = "https://smartmoneypeople.com"

    @property
    def source_id(self) -> str:
        return "smartmoneypeople"

    @property
    def source_name(self) -> str:
        return "Smart Money People"

    def _get_society_url(self, slug: str, page: int = 1) -> str:
        """Build URL for a society's review page."""
        base = f"{self.BASE_URL}/{slug}-reviews/products"
        if page > 1:
            return f"{base}?page={page}"
        return base

    def _get_slug_for_society(self, society: BuildingSociety) -> Optional[str]:
        """Get Smart Money People URL slug for a society."""
        # First try direct lookup
        if society.id in SOCIETY_SLUGS:
            return SOCIETY_SLUGS[society.id]

        # Try generating from canonical name
        slug = society.canonical_name.lower().replace(" ", "-")
        return slug

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None

        # ISO format from JSON-LD
        try:
            # Handle "2025-11-27T15:46:29+00:00"
            if "T" in date_str:
                clean = date_str.replace("+00:00", "").replace("Z", "")
                if "." in clean:
                    clean = clean.split(".")[0]
                return datetime.fromisoformat(clean).date()
        except ValueError:
            pass

        # Text formats like "27th November 2025"
        formats = [
            "%d %B %Y",
            "%dth %B %Y",
            "%dst %B %Y",
            "%dnd %B %Y",
            "%drd %B %Y",
            "%B %d, %Y",
            "%Y-%m-%d",
        ]

        # Remove ordinal suffixes
        clean_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str)

        for fmt in formats:
            try:
                return datetime.strptime(clean_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def _extract_json_ld_reviews(self, html: str, society_id: str) -> list[RawReview]:
        """Extract reviews from JSON-LD structured data."""
        soup = BeautifulSoup(html, "lxml")
        reviews = []

        # Find all JSON-LD script tags
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            try:
                data = json.loads(script.string)

                # Handle single review object
                if isinstance(data, dict) and data.get("@type") == "Review":
                    review = self._parse_json_ld_review(data, society_id)
                    if review:
                        reviews.append(review)

                # Handle array of reviews
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Review":
                            review = self._parse_json_ld_review(item, society_id)
                            if review:
                                reviews.append(review)

                # Handle @graph array
                elif isinstance(data, dict) and "@graph" in data:
                    for item in data["@graph"]:
                        if isinstance(item, dict) and item.get("@type") == "Review":
                            review = self._parse_json_ld_review(item, society_id)
                            if review:
                                reviews.append(review)

            except (json.JSONDecodeError, TypeError):
                continue

        return reviews

    def _parse_json_ld_review(self, data: dict, society_id: str) -> Optional[RawReview]:
        """Parse a single JSON-LD review object."""
        try:
            # Get rating
            rating_data = data.get("reviewRating", {})
            rating = rating_data.get("ratingValue")
            if rating is None:
                return None
            rating = int(float(rating))

            # Get date
            date_str = data.get("datePublished")
            review_date = self._parse_date(date_str)
            if not review_date:
                return None

            # Get body
            body = data.get("reviewBody", "").strip()
            if not body or len(body) < 10:
                return None

            # Get product type if available
            product_type = None
            item_reviewed = data.get("itemReviewed", {})
            if isinstance(item_reviewed, dict):
                product_type = item_reviewed.get("name")

            # Generate a unique ID
            review_id = f"smp_{society_id}_{date_str}_{hash(body) % 10000}"

            return RawReview(
                source_id=self.source_id,
                source_review_id=review_id,
                building_society_id=society_id,
                review_date=review_date,
                rating=rating,
                title=None,  # Smart Money People doesn't have titles
                body=body,
            )

        except Exception:
            return None

    def _extract_html_reviews(self, html: str, society_id: str) -> list[RawReview]:
        """Extract reviews from HTML when JSON-LD is not available."""
        soup = BeautifulSoup(html, "lxml")
        reviews = []

        # Find review containers - try common patterns
        review_containers = soup.find_all(
            "div", class_=re.compile(r"review|rating-card|customer-review", re.I)
        )

        for container in review_containers:
            try:
                # Look for rating
                rating_elem = container.find(
                    string=re.compile(r"Rated\s*\*?\*?(\d+)/5")
                )
                if rating_elem:
                    match = re.search(r"(\d+)/5", rating_elem)
                    if match:
                        rating = int(match.group(1))
                    else:
                        continue
                else:
                    # Try finding star elements
                    stars = container.find_all(
                        class_=re.compile(r"star|rating", re.I)
                    )
                    rating = len(stars) if stars else None
                    if not rating:
                        continue

                # Look for date
                date_elem = container.find(string=re.compile(r"\d{1,2}.*\d{4}"))
                review_date = self._parse_date(str(date_elem)) if date_elem else None
                if not review_date:
                    continue

                # Look for body text
                body_elem = container.find("p") or container.find(
                    class_=re.compile(r"body|text|content", re.I)
                )
                body = body_elem.get_text(strip=True) if body_elem else ""
                if not body or len(body) < 10:
                    continue

                # Generate ID
                review_id = f"smp_{society_id}_{review_date}_{hash(body) % 10000}"

                reviews.append(
                    RawReview(
                        source_id=self.source_id,
                        source_review_id=review_id,
                        building_society_id=society_id,
                        review_date=review_date,
                        rating=rating,
                        body=body,
                    )
                )

            except Exception:
                continue

        return reviews

    def _get_total_reviews(self, html: str) -> int:
        """Extract total review count from page."""
        # Look for "Showing X of Y reviews" pattern
        match = re.search(r"of\s*\*?\*?(\d[\d,]*)\s*(?:company\s*)?reviews", html, re.I)
        if match:
            return int(match.group(1).replace(",", ""))

        # Try JSON-LD aggregate rating
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    agg = data.get("aggregateRating", {})
                    count = agg.get("reviewCount") or agg.get("ratingCount")
                    if count:
                        return int(count)
            except (json.JSONDecodeError, TypeError):
                continue

        return 0

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawReview]:
        """Scrape Smart Money People reviews for a building society.

        Args:
            society: Building society to scrape
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of raw reviews
        """
        slug = self._get_slug_for_society(society)
        if not slug:
            print(f"  No Smart Money People slug for {society.canonical_name}")
            return []

        all_reviews = []
        seen_ids = set()  # Dedupe by ID
        page = 1
        max_pages = 50  # Safety limit
        reviews_per_page = 10  # Estimate

        # Fetch first page
        url = self._get_society_url(slug)
        try:
            response = self._fetch_url(url)
            if response.status_code == 404:
                print(f"  Society not found on Smart Money People")
                return []

            total_reviews = self._get_total_reviews(response.text)
            total_pages = min((total_reviews // reviews_per_page) + 1, max_pages)
            print(f"  Found ~{total_reviews} reviews across ~{total_pages} pages")

            # Parse first page
            reviews = self._extract_json_ld_reviews(response.text, society.id)
            if not reviews:
                reviews = self._extract_html_reviews(response.text, society.id)

            for r in reviews:
                if r.source_review_id not in seen_ids:
                    all_reviews.append(r)
                    seen_ids.add(r.source_review_id)

        except Exception as e:
            print(f"  Error fetching first page: {e}")
            return []

        # Try different pagination methods
        for page in range(2, total_pages + 1):
            self._rate_limit()

            # Try page parameter
            url = self._get_society_url(slug, page)
            try:
                response = self._fetch_url(url)

                reviews = self._extract_json_ld_reviews(response.text, society.id)
                if not reviews:
                    reviews = self._extract_html_reviews(response.text, society.id)

                new_count = 0
                for r in reviews:
                    if r.source_review_id not in seen_ids:
                        all_reviews.append(r)
                        seen_ids.add(r.source_review_id)
                        new_count += 1

                if new_count == 0:
                    print(f"  No new reviews on page {page}, stopping")
                    break

                print(f"  Page {page}: {new_count} new reviews")

                # Check date bounds
                if start_date and reviews:
                    oldest = min(r.review_date for r in reviews)
                    if oldest < start_date:
                        print(f"  Reached start date boundary")
                        break

            except Exception as e:
                print(f"  Error on page {page}: {e}")
                continue

        # Filter by date if specified
        if start_date or end_date:
            original = len(all_reviews)
            all_reviews = [
                r
                for r in all_reviews
                if (not start_date or r.review_date >= start_date)
                and (not end_date or r.review_date <= end_date)
            ]
            print(f"  Filtered {original} to {len(all_reviews)} by date")

        return all_reviews


if __name__ == "__main__":
    # Test the scraper
    from src.config.societies import get_society_by_id

    society = get_society_by_id("bath")
    if society:
        with SmartMoneyPeopleScraper() as scraper:
            reviews = scraper.scrape_society(society)
            print(f"\nFound {len(reviews)} reviews for {society.canonical_name}")
            if reviews:
                print(f"Sample: {reviews[0]}")
