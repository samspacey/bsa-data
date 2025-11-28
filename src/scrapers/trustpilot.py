"""Trustpilot scraper for building society reviews."""

import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.config.societies import BuildingSociety
from src.data.schemas import RawReview
from src.scrapers.base import BaseScraper


class TrustpilotScraper(BaseScraper):
    """Scraper for Trustpilot reviews."""

    BASE_URL = "https://uk.trustpilot.com"

    @property
    def source_id(self) -> str:
        return "trustpilot"

    @property
    def source_name(self) -> str:
        return "Trustpilot"

    def _get_review_page_url(self, domain: str, page: int = 1) -> str:
        """Build URL for a review page."""
        return f"{self.BASE_URL}/review/{domain}?page={page}"

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse Trustpilot date string to date object."""
        if not date_str:
            return None

        # Try various date formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d",
            "%d %B %Y",
            "%B %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        # Try parsing ISO format with timezone
        try:
            # Handle formats like "2024-01-15T10:30:00.000Z"
            clean_date = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_date).date()
        except ValueError:
            pass

        return None

    def _parse_rating(self, rating_element) -> int:
        """Extract star rating from element."""
        if rating_element is None:
            return 3  # Default to neutral

        # Try to find rating in data attribute
        rating_attr = rating_element.get("data-service-review-rating")
        if rating_attr:
            try:
                return int(rating_attr)
            except ValueError:
                pass

        # Try to find in class name (e.g., "star-rating star-rating-5")
        classes = rating_element.get("class", [])
        for cls in classes:
            if "star-rating-" in cls:
                try:
                    return int(cls.split("-")[-1])
                except ValueError:
                    pass

        # Look for img alt text
        img = rating_element.find("img")
        if img:
            alt = img.get("alt", "")
            match = re.search(r"(\d)", alt)
            if match:
                return int(match.group(1))

        return 3

    def _extract_reviews_from_page(self, html: str, society_id: str) -> list[RawReview]:
        """Parse reviews from a Trustpilot page HTML."""
        soup = BeautifulSoup(html, "lxml")
        reviews = []

        # Find all review cards
        review_cards = soup.find_all("article", {"data-service-review-card-paper": True})

        # Alternative selectors if the above doesn't work
        if not review_cards:
            review_cards = soup.find_all("div", class_=re.compile(r"review-card|styles_reviewCard"))

        if not review_cards:
            review_cards = soup.find_all("article", class_=re.compile(r"review"))

        for card in review_cards:
            try:
                # Extract review ID
                review_id = card.get("data-service-review-id") or card.get("id", "")
                if not review_id:
                    # Try to find in link
                    link = card.find("a", href=re.compile(r"/reviews/"))
                    if link:
                        review_id = link.get("href", "").split("/")[-1]

                if not review_id:
                    continue

                # Extract date
                date_elem = card.find("time")
                if date_elem:
                    date_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
                    review_date = self._parse_date(date_str)
                else:
                    # Look for date in data attributes
                    date_attr = card.get("data-service-review-date-of-experience")
                    review_date = self._parse_date(date_attr) if date_attr else None

                if not review_date:
                    continue

                # Extract rating
                rating_elem = card.find(attrs={"data-service-review-rating": True})
                if not rating_elem:
                    rating_elem = card.find(class_=re.compile(r"star-rating|StarRating"))
                rating = self._parse_rating(rating_elem)

                # Extract title
                title_elem = card.find("h2") or card.find(class_=re.compile(r"title|Title"))
                title = title_elem.get_text(strip=True) if title_elem else None

                # Extract body
                body_elem = card.find("p", class_=re.compile(r"text|content|body|Text|Content"))
                if not body_elem:
                    body_elem = card.find("p", attrs={"data-service-review-text-typography": True})
                if not body_elem:
                    # Try finding any paragraph that looks like review text
                    paragraphs = card.find_all("p")
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if len(text) > 50:  # Likely the review body
                            body_elem = p
                            break

                body = body_elem.get_text(strip=True) if body_elem else ""
                if not body:
                    continue

                # Extract location (if available)
                location_elem = card.find(class_=re.compile(r"location|Location"))
                location = location_elem.get_text(strip=True) if location_elem else None

                reviews.append(
                    RawReview(
                        source_id=self.source_id,
                        source_review_id=str(review_id),
                        building_society_id=society_id,
                        review_date=review_date,
                        rating=rating,
                        title=title,
                        body=body,
                        location=location,
                    )
                )

            except Exception as e:
                print(f"    Error parsing review: {e}")
                continue

        return reviews

    def _get_total_pages(self, html: str) -> int:
        """Extract total number of pages from HTML."""
        soup = BeautifulSoup(html, "lxml")

        # Look for pagination
        pagination = soup.find("nav", {"aria-label": "Pagination"})
        if pagination:
            page_links = pagination.find_all("a", href=re.compile(r"page=\d+"))
            if page_links:
                pages = []
                for link in page_links:
                    match = re.search(r"page=(\d+)", link.get("href", ""))
                    if match:
                        pages.append(int(match.group(1)))
                if pages:
                    return max(pages)

        # Alternative: look for page numbers in text
        page_nums = soup.find_all(string=re.compile(r"Page \d+ of (\d+)"))
        for text in page_nums:
            match = re.search(r"of (\d+)", text)
            if match:
                return int(match.group(1))

        return 1

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawReview]:
        """Scrape Trustpilot reviews for a building society.

        Args:
            society: Building society to scrape
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of raw reviews
        """
        if not society.trustpilot_url:
            print(f"  No Trustpilot URL for {society.canonical_name}")
            return []

        # Extract domain from URL
        domain = society.website_domain
        if not domain:
            # Try to extract from trustpilot_url
            match = re.search(r"/review/(?:www\.)?(.+?)(?:\?|$)", society.trustpilot_url)
            if match:
                domain = match.group(1)
            else:
                print(f"  Could not determine domain for {society.canonical_name}")
                return []

        all_reviews = []
        page = 1
        max_pages = 100  # Safety limit

        # Get first page to determine total pages
        first_url = self._get_review_page_url(domain, 1)
        try:
            response = self._fetch_url(first_url)
            total_pages = min(self._get_total_pages(response.text), max_pages)
            print(f"  Found {total_pages} pages of reviews")

            # Parse first page
            reviews = self._extract_reviews_from_page(response.text, society.id)
            all_reviews.extend(reviews)

        except Exception as e:
            print(f"  Error fetching first page: {e}")
            return []

        # Fetch remaining pages
        for page in range(2, total_pages + 1):
            self._rate_limit()
            url = self._get_review_page_url(domain, page)
            try:
                response = self._fetch_url(url)
                reviews = self._extract_reviews_from_page(response.text, society.id)

                if not reviews:
                    print(f"  No reviews found on page {page}, stopping")
                    break

                all_reviews.extend(reviews)
                print(f"  Page {page}/{total_pages}: {len(reviews)} reviews")

                # Check date bounds
                if start_date:
                    oldest_on_page = min(r.review_date for r in reviews)
                    if oldest_on_page < start_date:
                        print(f"  Reached start date boundary")
                        break

            except Exception as e:
                print(f"  Error fetching page {page}: {e}")
                continue

        # Filter by date if specified
        if start_date or end_date:
            original_count = len(all_reviews)
            all_reviews = [
                r
                for r in all_reviews
                if (not start_date or r.review_date >= start_date)
                and (not end_date or r.review_date <= end_date)
            ]
            print(f"  Filtered {original_count} reviews to {len(all_reviews)} by date")

        return all_reviews


if __name__ == "__main__":
    # Test the scraper
    from src.config.societies import get_society_by_id

    society = get_society_by_id("nationwide")
    if society:
        with TrustpilotScraper() as scraper:
            reviews = scraper.scrape_society(society)
            print(f"Found {len(reviews)} reviews for {society.canonical_name}")
            if reviews:
                print(f"Sample review: {reviews[0]}")
