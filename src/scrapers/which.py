"""Which? Money editorial ratings — seed-driven source.

Which? Money reviews are behind a paywall, so we cannot scrape them
programmatically. Instead this "scraper" reads from a human-curated
JSON seed file and emits ``RawMention`` rows of type
``editorial_rating``. Populate ``data/seed/which_editorial.json`` with
top-line public summary ratings for the demo.
"""

import json
from datetime import date
from pathlib import Path
from typing import Optional

from src.config.settings import settings
from src.config.societies import BuildingSociety
from src.data.schemas import MentionType, RawMention
from src.scrapers.base import BaseScraper


SEED_FILE = settings.project_root / "data" / "seed" / "which_editorial.json"


class WhichScraper(BaseScraper):
    """Which? editorial ratings, read from curated seed JSON."""

    @property
    def source_id(self) -> str:
        return "which"

    @property
    def source_name(self) -> str:
        return "Which? Money"

    def _load_seed(self) -> dict:
        if not SEED_FILE.exists():
            return {}
        try:
            with open(SEED_FILE) as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return {}

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawMention]:
        seed = self._load_seed()
        entries = seed.get(society.id) or []
        today = date.today()

        mentions: list[RawMention] = []
        for idx, entry in enumerate(entries):
            try:
                rating = entry.get("rating_value")
                scale = entry.get("rating_scale_max", 5.0)
                url = entry.get("source_url")
                category = entry.get("category", "")
                summary = entry.get("summary", "") or entry.get("body", "")
                if not summary:
                    continue
                mentions.append(
                    RawMention(
                        source_id=self.source_id,
                        source_mention_id=f"which_{society.id}_{idx}",
                        building_society_id=society.id,
                        mention_type=MentionType.EDITORIAL_RATING,
                        mention_date=today,
                        title=f"Which? — {category}" if category else "Which? Editorial Rating",
                        body=summary,
                        source_url=url,
                        rating_value=rating,
                        rating_scale_max=scale,
                        extra={"category": category, "seed": True},
                    )
                )
            except Exception as e:  # noqa: BLE001
                print(f"    Which? seed parse error: {e}")
                continue

        print(f"  Found {len(mentions)} Which? ratings for {society.canonical_name}")
        return mentions


if __name__ == "__main__":
    from src.config.societies import get_society_by_id

    society = get_society_by_id("nationwide")
    if society:
        with WhichScraper() as scraper:
            mentions = scraper.scrape_society(society)
            print(f"Found {len(mentions)} mentions for {society.canonical_name}")
