"""Base scraper class with common functionality."""

import json
import time
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.config.societies import BuildingSociety
from src.data.schemas import RawReview


class BaseScraper(ABC):
    """Base class for all scrapers."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        delay_seconds: float = settings.scrape_delay_seconds,
        max_retries: int = settings.max_retries,
    ):
        self.output_dir = output_dir or settings.raw_data_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self._client: Optional[httpx.Client] = None

    @property
    def source_id(self) -> str:
        """Return the source ID for this scraper."""
        raise NotImplementedError

    @property
    def source_name(self) -> str:
        """Return the human-readable source name."""
        raise NotImplementedError

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialized HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=settings.request_timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-GB,en;q=0.9",
                },
                follow_redirects=True,
            )
        return self._client

    def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    def _fetch_url(self, url: str) -> httpx.Response:
        """Fetch a URL with retry logic."""
        response = self.client.get(url)
        response.raise_for_status()
        return response

    def _rate_limit(self):
        """Apply rate limiting delay."""
        time.sleep(self.delay_seconds)

    @abstractmethod
    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawReview]:
        """Scrape reviews for a specific building society.

        Args:
            society: The building society to scrape
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of raw review data
        """
        pass

    def scrape_all(
        self,
        societies: list[BuildingSociety],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[str, list[RawReview]]:
        """Scrape reviews for all societies.

        Args:
            societies: List of building societies to scrape
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict mapping society ID to list of reviews
        """
        results = {}
        for society in societies:
            print(f"Scraping {self.source_name} for {society.canonical_name}...")
            try:
                reviews = self.scrape_society(society, start_date, end_date)
                results[society.id] = reviews
                print(f"  Found {len(reviews)} reviews")
                self.save_reviews(society.id, reviews)
            except Exception as e:
                print(f"  Error scraping {society.canonical_name}: {e}")
                results[society.id] = []
            self._rate_limit()
        return results

    def save_reviews(self, society_id: str, reviews: list[RawReview]) -> Path:
        """Save reviews to JSON file.

        Args:
            society_id: Building society ID
            reviews: List of reviews to save

        Returns:
            Path to saved file
        """
        output_file = self.output_dir / self.source_id / f"{society_id}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        data = {
            "society_id": society_id,
            "source_id": self.source_id,
            "scraped_at": datetime.now().isoformat(),
            "review_count": len(reviews),
            "reviews": [review.model_dump(mode="json") for review in reviews],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        return output_file

    def load_reviews(self, society_id: str) -> list[RawReview]:
        """Load reviews from JSON file.

        Args:
            society_id: Building society ID

        Returns:
            List of reviews
        """
        input_file = self.output_dir / self.source_id / f"{society_id}.json"
        if not input_file.exists():
            return []

        with open(input_file, encoding="utf-8") as f:
            data = json.load(f)

        return [RawReview(**review) for review in data.get("reviews", [])]
