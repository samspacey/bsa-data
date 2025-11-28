"""Apple App Store review scraper."""

from datetime import date, datetime
from typing import Optional

from src.config.societies import BuildingSociety
from src.data.schemas import RawReview
from src.scrapers.base import BaseScraper


class AppStoreScraper(BaseScraper):
    """Scraper for Apple App Store reviews using app_store_scraper library."""

    @property
    def source_id(self) -> str:
        return "app_store"

    @property
    def source_name(self) -> str:
        return "Apple App Store"

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawReview]:
        """Scrape App Store reviews for a building society's app.

        Args:
            society: Building society to scrape
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of raw reviews
        """
        if not society.app_store_id:
            print(f"  No App Store ID for {society.canonical_name}")
            return []

        try:
            from app_store_scraper import AppStore
        except ImportError:
            print("  app_store_scraper not installed. Install with: pip install app-store-scraper")
            return []

        try:
            # Initialize the scraper
            app = AppStore(
                country="gb",
                app_name=society.canonical_name.lower().replace(" ", "-"),
                app_id=society.app_store_id,
            )

            # Fetch reviews
            print(f"  Fetching App Store reviews for app ID {society.app_store_id}...")
            app.review(how_many=5000)  # Fetch up to 5000 reviews

            reviews = []
            for review in app.reviews:
                try:
                    # Parse the date
                    review_date_raw = review.get("date")
                    if isinstance(review_date_raw, datetime):
                        review_date = review_date_raw.date()
                    elif isinstance(review_date_raw, str):
                        review_date = datetime.fromisoformat(review_date_raw).date()
                    else:
                        continue

                    # Apply date filters
                    if start_date and review_date < start_date:
                        continue
                    if end_date and review_date > end_date:
                        continue

                    # Extract fields
                    rating = review.get("rating", 3)
                    if not isinstance(rating, int):
                        rating = int(rating)
                    rating = max(1, min(5, rating))  # Ensure 1-5 range

                    title = review.get("title", "")
                    body = review.get("review", "")

                    if not body:
                        continue

                    reviews.append(
                        RawReview(
                            source_id=self.source_id,
                            source_review_id=str(review.get("id", f"appstore_{len(reviews)}")),
                            building_society_id=society.id,
                            review_date=review_date,
                            rating=rating,
                            title=title if title else None,
                            body=body,
                            reviewer_name=review.get("userName"),
                            app_version=review.get("version"),
                        )
                    )

                except Exception as e:
                    print(f"    Error parsing review: {e}")
                    continue

            return reviews

        except Exception as e:
            print(f"  Error fetching App Store reviews: {e}")
            return []


if __name__ == "__main__":
    # Test the scraper
    from src.config.societies import get_society_by_id

    society = get_society_by_id("nationwide")
    if society:
        with AppStoreScraper() as scraper:
            reviews = scraper.scrape_society(society)
            print(f"Found {len(reviews)} reviews for {society.canonical_name}")
            if reviews:
                print(f"Sample review: {reviews[0]}")
