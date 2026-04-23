"""Apple App Store review scraper using iTunes RSS endpoint.

The legacy `app_store_scraper` (PyPI 0.3.5, last released 2019) returns empty
results against Apple's current endpoints. This implementation hits the iTunes
RSS customer-reviews feed directly, which still works and is stable.
"""

from datetime import date, datetime
from typing import Optional

from src.config.societies import BuildingSociety
from src.data.schemas import RawReview
from src.scrapers.base import BaseScraper


RSS_URL = (
    "https://itunes.apple.com/{country}/rss/customerreviews"
    "/id={app_id}/sortBy=mostRecent/page={page}/json"
)


class AppStoreScraper(BaseScraper):
    """Scraper for Apple App Store reviews via iTunes RSS feed."""

    COUNTRY = "gb"
    MAX_PAGES = 10  # Apple caps the RSS feed at 10 pages of 50 reviews each

    @property
    def source_id(self) -> str:
        return "app_store"

    @property
    def source_name(self) -> str:
        return "Apple App Store"

    def _parse_entry(self, entry: dict, society_id: str) -> Optional[RawReview]:
        try:
            rating_str = entry.get("im:rating", {}).get("label")
            if not rating_str:
                return None
            rating = max(1, min(5, int(rating_str)))

            body = (entry.get("content", {}) or {}).get("label", "").strip()
            if not body:
                return None

            title = (entry.get("title", {}) or {}).get("label", "").strip() or None

            updated = (entry.get("updated", {}) or {}).get("label", "")
            if not updated:
                return None
            try:
                review_date = datetime.fromisoformat(updated.replace("Z", "+00:00")).date()
            except ValueError:
                return None

            review_id = (entry.get("id", {}) or {}).get("label") or f"appstore_{society_id}_{hash(body) % 10_000_000}"

            author_name = (entry.get("author", {}) or {}).get("name", {}).get("label")
            app_version = (entry.get("im:version", {}) or {}).get("label")
            author_uri = (entry.get("author", {}) or {}).get("uri", {}).get("label")

            return RawReview(
                source_id=self.source_id,
                source_review_id=str(review_id),
                building_society_id=society_id,
                review_date=review_date,
                rating=rating,
                title=title,
                body=body,
                reviewer_name=author_name,
                app_version=app_version,
                source_url=author_uri,  # iTunes review permalink (author's review page)
            )
        except Exception as e:  # noqa: BLE001 - scraper parser, tolerate any entry shape
            print(f"    Error parsing entry: {e}")
            return None

    def _fetch_page(self, app_id: str, page: int) -> list[dict]:
        url = RSS_URL.format(country=self.COUNTRY, app_id=app_id, page=page)
        response = self._fetch_url(url)
        data = response.json()
        entries = data.get("feed", {}).get("entry", [])
        if isinstance(entries, dict):
            entries = [entries]
        return entries or []

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawReview]:
        if not society.app_store_id:
            print(f"  No App Store ID for {society.canonical_name}")
            return []

        all_reviews: list[RawReview] = []
        seen_ids: set[str] = set()

        for page in range(1, self.MAX_PAGES + 1):
            try:
                entries = self._fetch_page(society.app_store_id, page)
            except Exception as e:  # noqa: BLE001
                print(f"  Page {page} fetch error: {e}")
                break

            if not entries:
                if page == 1:
                    print(f"  No App Store reviews in {self.COUNTRY.upper()} for {society.canonical_name}")
                break

            new_count = 0
            for entry in entries:
                review = self._parse_entry(entry, society.id)
                if review is None:
                    continue
                if review.source_review_id in seen_ids:
                    continue
                if start_date and review.review_date < start_date:
                    continue
                if end_date and review.review_date > end_date:
                    continue
                seen_ids.add(review.source_review_id)
                all_reviews.append(review)
                new_count += 1

            print(f"  Page {page}: {new_count} new reviews (running total {len(all_reviews)})")

            # iTunes RSS only ships most-recent pages; if a page is short, assume no more
            if len(entries) < 25:
                break

            if page < self.MAX_PAGES:
                self._rate_limit()

        return all_reviews


if __name__ == "__main__":
    from src.config.societies import get_society_by_id

    society = get_society_by_id("skipton")
    if society:
        with AppStoreScraper() as scraper:
            reviews = scraper.scrape_society(society)
            print(f"Found {len(reviews)} reviews for {society.canonical_name}")
            if reviews:
                print(f"Sample: {reviews[0]}")
