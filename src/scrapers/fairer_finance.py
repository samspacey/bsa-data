"""Fairer Finance editorial-ratings scraper.

Fairer Finance publishes star ratings and methodology reports for UK
financial providers. The public provider page for a building society
includes a Customer Experience Rating (Ribbon: gold/silver/bronze),
satisfaction/trust/happiness percentage scores, and a short editorial
summary. Each of these becomes a ``RawMention`` of type
``editorial_rating`` so it does NOT distort customer-review averages.

If the live page cannot be parsed for a society, we fall back to the
``data/seed/fairer_finance.json`` file for a small curated set of
headline ratings — enough to prove the source works in the demo.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.config.settings import settings
from src.config.societies import BuildingSociety
from src.data.schemas import MentionType, RawMention
from src.scrapers.base import BaseScraper


BASE_URL = "https://www.fairerfinance.com"
SEED_FILE = settings.project_root / "data" / "seed" / "fairer_finance.json"


class FairerFinanceScraper(BaseScraper):
    """Scraper for Fairer Finance editorial ratings."""

    @property
    def source_id(self) -> str:
        return "fairer_finance"

    @property
    def source_name(self) -> str:
        return "Fairer Finance"

    def _load_seed(self) -> dict:
        if not SEED_FILE.exists():
            return {}
        try:
            with open(SEED_FILE) as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return {}

    def _get_slug(self, society: BuildingSociety) -> str:
        """Derive a provider slug for the Fairer Finance URL."""
        slug = getattr(society, "fairer_finance_slug", None)
        if slug:
            return slug
        # Best-effort: lowercase, dashes, canonical name
        return re.sub(r"[^a-z0-9]+", "-", society.canonical_name.lower()).strip("-")

    def _fetch_provider_page(self, slug: str) -> Optional[str]:
        url = urljoin(BASE_URL, f"/providers/{slug}")
        try:
            response = self._fetch_url(url)
            return response.text
        except Exception as e:  # noqa: BLE001
            print(f"  Fairer Finance fetch error for {slug}: {e}")
            return None

    def _parse_ratings(self, html: str, society_id: str, slug: str) -> list[RawMention]:
        """Parse ribbon ratings and percentage scores from the provider page."""
        soup = BeautifulSoup(html, "lxml")
        mentions: list[RawMention] = []
        today = date.today()
        url = urljoin(BASE_URL, f"/providers/{slug}")

        # Ribbon ratings (gold/silver/bronze) — each is a distinct editorial rating
        ribbons = soup.find_all(class_=re.compile(r"ribbon|rating-badge|cer-rating", re.I))
        for idx, ribbon in enumerate(ribbons):
            text = ribbon.get_text(" ", strip=True)
            if not text:
                continue
            label = re.search(r"(Gold|Silver|Bronze|Unrated)", text, re.I)
            category_elem = ribbon.find_previous(["h2", "h3", "h4"]) or ribbon
            category = category_elem.get_text(strip=True)[:100]
            if not label:
                continue

            ribbon_to_value = {"gold": 5.0, "silver": 4.0, "bronze": 3.0, "unrated": None}
            value = ribbon_to_value.get(label.group(1).lower())

            mentions.append(
                RawMention(
                    source_id=self.source_id,
                    source_mention_id=f"ff_{society_id}_ribbon_{idx}",
                    building_society_id=society_id,
                    mention_type=MentionType.EDITORIAL_RATING,
                    mention_date=today,
                    title=f"Fairer Finance — {category}",
                    body=f"Fairer Finance rates {category}: {label.group(1)} Ribbon.",
                    source_url=url,
                    rating_value=value,
                    rating_scale_max=5.0,
                    extra={"category": category, "ribbon": label.group(1).lower()},
                )
            )

        # Percentage scores (trust, happiness, satisfaction)
        score_blocks = soup.find_all(class_=re.compile(r"score|percentage|metric", re.I))
        for idx, block in enumerate(score_blocks):
            text = block.get_text(" ", strip=True)
            match = re.search(r"(trust|happiness|satisfaction)\D*(\d+(?:\.\d+)?)\s*%", text, re.I)
            if not match:
                continue
            dimension, score_str = match.group(1).lower(), match.group(2)
            score = float(score_str)
            mentions.append(
                RawMention(
                    source_id=self.source_id,
                    source_mention_id=f"ff_{society_id}_{dimension}",
                    building_society_id=society_id,
                    mention_type=MentionType.EDITORIAL_RATING,
                    mention_date=today,
                    title=f"Fairer Finance — {dimension.title()} Score",
                    body=f"Fairer Finance {dimension} score: {score}%",
                    source_url=url,
                    rating_value=score,
                    rating_scale_max=100.0,
                    extra={"dimension": dimension},
                )
            )

        return mentions

    def _seed_mentions(self, seed: dict, society: BuildingSociety) -> list[RawMention]:
        """Convert seed JSON entries for this society into RawMentions."""
        entries = seed.get(society.id) or []
        today = date.today()
        mentions = []
        url = urljoin(BASE_URL, f"/providers/{self._get_slug(society)}")
        for idx, entry in enumerate(entries):
            try:
                mentions.append(
                    RawMention(
                        source_id=self.source_id,
                        source_mention_id=f"ff_seed_{society.id}_{idx}",
                        building_society_id=society.id,
                        mention_type=MentionType.EDITORIAL_RATING,
                        mention_date=today,
                        title=f"Fairer Finance — {entry.get('category', '')}",
                        body=entry.get("summary") or entry.get("body", ""),
                        source_url=url,
                        rating_value=entry.get("rating_value"),
                        rating_scale_max=entry.get("rating_scale_max", 5.0),
                        extra={"category": entry.get("category"), "seed": True},
                    )
                )
            except Exception as e:  # noqa: BLE001
                print(f"    Seed parse error: {e}")
                continue
        return mentions

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawMention]:
        slug = self._get_slug(society)
        html = self._fetch_provider_page(slug)

        mentions: list[RawMention] = []
        if html:
            mentions = self._parse_ratings(html, society.id, slug)

        if not mentions:
            seed = self._load_seed()
            mentions = self._seed_mentions(seed, society)
            if mentions:
                print(f"  Using seed data for {society.canonical_name}")

        print(f"  Found {len(mentions)} Fairer Finance ratings for {society.canonical_name}")
        return mentions


if __name__ == "__main__":
    from src.config.societies import get_society_by_id

    society = get_society_by_id("nationwide")
    if society:
        with FairerFinanceScraper() as scraper:
            mentions = scraper.scrape_society(society)
            print(f"Found {len(mentions)} mentions for {society.canonical_name}")
