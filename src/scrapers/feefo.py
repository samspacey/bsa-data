"""Feefo scraper for verified purchase reviews."""

import json
from datetime import date, datetime
from typing import Optional

from src.config.societies import BuildingSociety
from src.data.schemas import RawReview
from src.scrapers.base import BaseScraper


# Mapping of society IDs to Feefo merchant identifiers
# These need to be discovered for each society that uses Feefo
SOCIETY_MERCHANT_IDS = {
    "market-harborough": "market-harborough-building-society",
    "penrith": "penrith-building-society",
    "cumberland": "cumberland-building-society",
    "west-brom": "west-bromwich-building-society",
    # Add more as discovered
}


class FeefoScraper(BaseScraper):
    """Scraper for Feefo verified reviews via their public API."""

    API_BASE = "https://api.feefo.com/api/20"  # API version 20

    @property
    def source_id(self) -> str:
        return "feefo"

    @property
    def source_name(self) -> str:
        return "Feefo"

    def _get_merchant_id(self, society: BuildingSociety) -> Optional[str]:
        """Get Feefo merchant identifier for a society."""
        # Check direct mapping
        if society.id in SOCIETY_MERCHANT_IDS:
            return SOCIETY_MERCHANT_IDS[society.id]

        # Try generating from canonical name
        return society.canonical_name.lower().replace(" ", "-")

    def _fetch_reviews_page(
        self,
        merchant_id: str,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """Fetch a page of reviews from Feefo API.

        Args:
            merchant_id: Feefo merchant identifier
            page: Page number
            page_size: Reviews per page

        Returns:
            API response as dict
        """
        url = (
            f"{self.API_BASE}/reviews/all?"
            f"merchant_identifier={merchant_id}"
            f"&page={page}"
            f"&page_size={page_size}"
        )

        response = self._fetch_url(url)
        return response.json()

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse Feefo date string."""
        if not date_str:
            return None

        # Feefo uses ISO format: "2024-01-15T10:30:00+00:00"
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Try fromisoformat
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        except ValueError:
            pass

        return None

    def _parse_review(self, review_data: dict, society_id: str) -> Optional[RawReview]:
        """Parse a single review from API response.

        Args:
            review_data: Review object from API
            society_id: Building society ID

        Returns:
            RawReview or None if parsing fails
        """
        try:
            # Get service review (main review about the business)
            service = review_data.get("service", {})
            if not service:
                # Try product review instead
                products = review_data.get("products", [])
                if products:
                    service = products[0]
                else:
                    return None

            # Get rating
            rating_data = service.get("rating", {})
            rating = rating_data.get("rating")
            if rating is None:
                return None
            rating = int(float(rating))

            # Get date - inside service object
            date_str = service.get("created_at") or review_data.get("last_updated_date")
            review_date = self._parse_date(date_str)
            if not review_date:
                return None

            # Get review text
            title = service.get("title", "")
            body = service.get("review", "")
            if not body and not title:
                return None

            # Combine title and body
            full_text = f"{title}\n{body}".strip() if title else body

            # Get review ID from service
            review_id = service.get("id") or f"feefo_{society_id}_{hash(full_text) % 100000}"

            return RawReview(
                source_id=self.source_id,
                source_review_id=str(review_id),
                building_society_id=society_id,
                review_date=review_date,
                rating=rating,
                title=title if title else None,
                body=full_text,
            )

        except Exception:
            return None

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawReview]:
        """Scrape Feefo reviews for a building society.

        Args:
            society: Building society to scrape
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of raw reviews
        """
        merchant_id = self._get_merchant_id(society)
        if not merchant_id:
            print(f"  No Feefo merchant ID for {society.canonical_name}")
            return []

        all_reviews = []
        page = 1
        max_pages = 50  # Safety limit
        page_size = 100

        while page <= max_pages:
            try:
                data = self._fetch_reviews_page(merchant_id, page, page_size)

                # Check for error
                if "error" in data or "reviews" not in data:
                    if page == 1:
                        print(f"  Merchant not found or no reviews: {merchant_id}")
                    break

                reviews_data = data.get("reviews", [])
                if not reviews_data:
                    break

                # Get pagination info - nested under summary.meta
                summary = data.get("summary", {})
                meta = summary.get("meta", {})
                total_count = meta.get("count", 0)
                total_pages = meta.get("pages", 1)

                if page == 1:
                    print(f"  Found {total_count} reviews across {total_pages} pages")

                # Parse reviews
                page_reviews = []
                for r in reviews_data:
                    review = self._parse_review(r, society.id)
                    if review:
                        page_reviews.append(review)

                all_reviews.extend(page_reviews)
                print(f"  Page {page}: {len(page_reviews)} reviews parsed")

                # Check date bounds
                if start_date and page_reviews:
                    oldest = min(r.review_date for r in page_reviews)
                    if oldest < start_date:
                        print(f"  Reached start date boundary")
                        break

                # Check if more pages
                if page >= total_pages:
                    break

                page += 1
                self._rate_limit()

            except Exception as e:
                print(f"  Error on page {page}: {e}")
                break

        # Filter by date
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

    # Test with Market Harborough (known to use Feefo)
    society = get_society_by_id("market-harborough")
    if society:
        with FeefoScraper() as scraper:
            reviews = scraper.scrape_society(society)
            print(f"\nFound {len(reviews)} reviews for {society.canonical_name}")
            if reviews:
                r = reviews[0]
                print(f"Sample: rating={r.rating}, date={r.review_date}")
                print(f"Body: {r.body[:150]}...")
