"""Google Play Store review scraper."""

from datetime import date, datetime
from typing import Optional

from src.config.societies import BuildingSociety
from src.data.schemas import RawReview
from src.scrapers.base import BaseScraper


class PlayStoreScraper(BaseScraper):
    """Scraper for Google Play Store reviews using google_play_scraper library."""

    @property
    def source_id(self) -> str:
        return "play_store"

    @property
    def source_name(self) -> str:
        return "Google Play Store"

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawReview]:
        """Scrape Play Store reviews for a building society's app.

        Args:
            society: Building society to scrape
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of raw reviews
        """
        if not society.play_store_id:
            print(f"  No Play Store ID for {society.canonical_name}")
            return []

        try:
            from google_play_scraper import Sort, reviews as fetch_reviews
        except ImportError:
            print(
                "  google_play_scraper not installed. Install with: pip install google-play-scraper"
            )
            return []

        try:
            print(f"  Fetching Play Store reviews for {society.play_store_id}...")

            all_reviews = []
            continuation_token = None
            batch_count = 0
            max_batches = 50  # Safety limit (50 * 100 = 5000 reviews max)

            while batch_count < max_batches:
                # Fetch a batch of reviews
                result, continuation_token = fetch_reviews(
                    society.play_store_id,
                    lang="en",
                    country="gb",
                    sort=Sort.NEWEST,
                    count=100,
                    continuation_token=continuation_token,
                )

                if not result:
                    break

                batch_count += 1
                print(f"    Batch {batch_count}: {len(result)} reviews")

                for review in result:
                    try:
                        # Parse the date
                        review_date_raw = review.get("at")
                        if isinstance(review_date_raw, datetime):
                            review_date = review_date_raw.date()
                        elif isinstance(review_date_raw, str):
                            review_date = datetime.fromisoformat(review_date_raw).date()
                        else:
                            continue

                        # Apply date filters
                        if start_date and review_date < start_date:
                            # Since we're sorting by newest, we can stop if we hit start_date
                            if all_reviews:  # Only stop if we have some reviews
                                print(f"  Reached start date boundary")
                                continuation_token = None
                                break
                            continue
                        if end_date and review_date > end_date:
                            continue

                        # Extract fields
                        rating = review.get("score", 3)
                        if not isinstance(rating, int):
                            rating = int(rating)
                        rating = max(1, min(5, rating))  # Ensure 1-5 range

                        body = review.get("content", "")
                        if not body:
                            continue

                        # Thumbs up count can indicate review quality
                        thumbs_up = review.get("thumbsUpCount", 0)

                        all_reviews.append(
                            RawReview(
                                source_id=self.source_id,
                                source_review_id=str(
                                    review.get("reviewId", f"playstore_{len(all_reviews)}")
                                ),
                                building_society_id=society.id,
                                review_date=review_date,
                                rating=rating,
                                title=None,  # Play Store reviews don't have titles
                                body=body,
                                reviewer_name=review.get("userName"),
                                app_version=review.get("reviewCreatedVersion"),
                            )
                        )

                    except Exception as e:
                        print(f"    Error parsing review: {e}")
                        continue

                # Check if we should continue
                if not continuation_token:
                    break

                # Small delay between batches
                self._rate_limit()

            return all_reviews

        except Exception as e:
            print(f"  Error fetching Play Store reviews: {e}")
            return []


if __name__ == "__main__":
    # Test the scraper
    from src.config.societies import get_society_by_id

    society = get_society_by_id("nationwide")
    if society:
        with PlayStoreScraper() as scraper:
            reviews = scraper.scrape_society(society)
            print(f"Found {len(reviews)} reviews for {society.canonical_name}")
            if reviews:
                print(f"Sample review: {reviews[0]}")
