"""Google Maps reviews scraper via SerpAPI.

Emits standard ``RawReview`` objects (star-rated customer reviews), NOT
``RawMention``. Google Places API licence terms forbid storage for analysis,
so SerpAPI is used as the legitimate path for internal research use only.

Configuration:
- Set ``SERPAPI_KEY`` in ``.env``
- Populate ``google_place_ids`` per society in ``src/config/societies.py``.
  If a society has no place_id, the scraper first searches Google Maps to
  discover one (one extra API call per society).

Cost expectations (Dec 2025): SerpAPI pricing is ~$75 for 5000 searches.
Scraping 42 societies × 1 place × 4 review pages ≈ 170 searches.
"""

from datetime import date, datetime
from typing import Optional

from src.config.settings import settings
from src.config.societies import BuildingSociety
from src.data.schemas import RawReview
from src.scrapers.base import BaseScraper


class GoogleScraper(BaseScraper):
    """Scraper for Google Maps reviews via SerpAPI."""

    MAX_REVIEW_PAGES = 4  # Each page returns ~10 reviews; 40 reviews per society is plenty

    @property
    def source_id(self) -> str:
        return "google"

    @property
    def source_name(self) -> str:
        return "Google Reviews"

    def _check_credentials(self) -> bool:
        if not settings.serpapi_key:
            print("  SerpAPI key missing. Set SERPAPI_KEY in .env to enable Google scraping.")
            return False
        return True

    def _serpapi_get(self, params: dict) -> dict:
        params = {**params, "api_key": settings.serpapi_key, "hl": "en", "gl": "uk"}
        response = self._fetch_url(
            "https://serpapi.com/search.json?" + "&".join(f"{k}={v}" for k, v in params.items())
        )
        return response.json()

    def _discover_place_id(self, society: BuildingSociety) -> Optional[str]:
        """Search Google Maps for a society's HQ and extract the place_id."""
        query = f"{society.canonical_name} headquarters".replace(" ", "+")
        try:
            data = self._serpapi_get({"engine": "google_maps", "q": query, "type": "search"})
        except Exception as e:  # noqa: BLE001
            print(f"  SerpAPI place lookup error: {e}")
            return None

        # Single-result or listing
        place = data.get("place_results") or {}
        if place.get("place_id"):
            return place["place_id"]

        results = data.get("local_results") or []
        if results and isinstance(results, list):
            return results[0].get("place_id")
        return None

    def _parse_review(self, raw: dict, society_id: str) -> Optional[RawReview]:
        try:
            review_id = raw.get("review_id") or raw.get("link") or raw.get("source")
            if not review_id:
                return None

            rating = raw.get("rating")
            if rating is None:
                return None
            rating = max(1, min(5, int(rating)))

            snippet = (raw.get("snippet") or raw.get("description") or "").strip()
            if not snippet:
                return None

            # Dates from SerpAPI are relative ("3 weeks ago") — iso_date_of_last_edit is more reliable
            iso_date = (
                raw.get("iso_date_of_last_edit")
                or raw.get("iso_date")
                or raw.get("date")
            )
            review_date: Optional[date] = None
            if iso_date:
                try:
                    review_date = datetime.fromisoformat(iso_date.replace("Z", "+00:00")).date()
                except ValueError:
                    review_date = None
            if review_date is None:
                review_date = date.today()  # Fallback; relative dates lose precision

            user = raw.get("user", {}) or {}

            return RawReview(
                source_id=self.source_id,
                source_review_id=str(review_id),
                building_society_id=society_id,
                review_date=review_date,
                rating=rating,
                title=None,
                body=snippet,
                reviewer_name=user.get("name") if isinstance(user, dict) else None,
                source_url=raw.get("link"),
            )
        except Exception as e:  # noqa: BLE001
            print(f"    Google review parse error: {e}")
            return None

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawReview]:
        if not self._check_credentials():
            return []

        place_id = getattr(society, "google_place_id", None)
        if not place_id:
            place_id = self._discover_place_id(society)
            if not place_id:
                print(f"  Could not discover Google place_id for {society.canonical_name}")
                return []

        all_reviews: list[RawReview] = []
        seen_ids: set[str] = set()
        next_page_token: Optional[str] = None

        for page in range(self.MAX_REVIEW_PAGES):
            params = {"engine": "google_maps_reviews", "place_id": place_id, "sort_by": "newestFirst"}
            if next_page_token:
                params["next_page_token"] = next_page_token

            try:
                data = self._serpapi_get(params)
            except Exception as e:  # noqa: BLE001
                print(f"  SerpAPI reviews error page {page}: {e}")
                break

            reviews = data.get("reviews") or []
            if not reviews:
                break

            new_count = 0
            for r in reviews:
                parsed = self._parse_review(r, society.id)
                if parsed is None or parsed.source_review_id in seen_ids:
                    continue
                if start_date and parsed.review_date < start_date:
                    continue
                if end_date and parsed.review_date > end_date:
                    continue
                seen_ids.add(parsed.source_review_id)
                all_reviews.append(parsed)
                new_count += 1

            print(f"  Google page {page + 1}: {new_count} reviews (running {len(all_reviews)})")

            next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
            if not next_page_token:
                break
            self._rate_limit()

        return all_reviews


if __name__ == "__main__":
    from src.config.societies import get_society_by_id

    society = get_society_by_id("nationwide")
    if society:
        with GoogleScraper() as scraper:
            reviews = scraper.scrape_society(society)
            print(f"Found {len(reviews)} reviews for {society.canonical_name}")
