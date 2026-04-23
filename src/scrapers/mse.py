"""MoneySavingExpert forum scraper for building society mentions.

MSE's forum search endpoint returns a server-rendered discussion listing, so
we use httpx + BeautifulSoup rather than a headless browser. Stays within
robots.txt by limiting depth to the first few search pages per society and
rate-limiting requests.
"""

import re
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from src.config.societies import BuildingSociety
from src.data.schemas import MentionType, RawMention
from src.scrapers.base import BaseScraper


BASE_URL = "https://forums.moneysavingexpert.com"
SEARCH_URL = BASE_URL + "/search?Search={query}&Page=p{page}"


class MSEScraper(BaseScraper):
    """Scraper for MoneySavingExpert forum mentions."""

    MAX_PAGES = 3  # Per search term — deep pages quickly lose relevance

    @property
    def source_id(self) -> str:
        return "mse"

    @property
    def source_name(self) -> str:
        return "MoneySavingExpert Forum"

    def __init__(self, *args, lookback_days: int = 365, **kwargs):
        super().__init__(*args, **kwargs)
        self.lookback_days = lookback_days

    def _search_terms(self, society: BuildingSociety) -> list[str]:
        terms = {society.canonical_name}
        for alias in society.aliases:
            if len(alias) >= 4 and alias.lower() not in {"the", "bs"}:
                terms.add(alias)
        return sorted(terms)

    def _parse_relative_date(self, text: str) -> Optional[date]:
        """MSE uses strings like '12 December 2024' or '3h'/'2d' relatives."""
        text = text.strip()
        today = date.today()

        # Relative: "3h", "15m", "2d", "1w"
        match = re.match(r"(\d+)\s*([smhdw])", text.lower())
        if match:
            n = int(match.group(1))
            unit = match.group(2)
            if unit in ("s", "m", "h"):
                return today
            if unit == "d":
                return today - timedelta(days=n)
            if unit == "w":
                return today - timedelta(weeks=n)

        # Absolute date formats
        for fmt in ("%d %B %Y", "%B %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_search_page(self, html: str, society: BuildingSociety, search_term: str) -> list[RawMention]:
        soup = BeautifulSoup(html, "lxml")
        mentions: list[RawMention] = []

        # MSE renders search hits as .MItem, .Item, or .DiscussionRow
        items = soup.select(".MItem, .Item.ItemDiscussion, li.DiscussionRow, article.SearchResult")
        if not items:
            items = soup.select("li[id^=Discussion], article[data-item-id]")

        for item in items:
            try:
                title_link = item.find("a", class_=re.compile("Title|title-link"))
                if not title_link:
                    title_link = item.find("h3", recursive=True)
                    if title_link:
                        title_link = title_link.find("a")
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                href = title_link.get("href") or ""
                url = href if href.startswith("http") else urljoin(BASE_URL, href)

                # Extract discussion ID from URL
                id_match = re.search(r"/discussion/(\d+)", url)
                mention_id = f"mse_{id_match.group(1)}" if id_match else f"mse_{abs(hash(url)) % 10_000_000}"

                # Excerpt (body)
                excerpt_elem = item.find(class_=re.compile("Excerpt|Summary|excerpt"))
                body = excerpt_elem.get_text(strip=True) if excerpt_elem else title
                if len(body) < 10:
                    body = title

                # Author
                author_elem = item.find(class_=re.compile("Username|Author"))
                author = author_elem.get_text(strip=True) if author_elem else None

                # Date
                date_elem = item.find("time")
                if date_elem:
                    raw_date = date_elem.get("datetime") or date_elem.get_text(strip=True)
                    mention_date = self._parse_relative_date(raw_date) or date.today()
                else:
                    mention_date = date.today()

                # Only keep recent posts
                cutoff = date.today() - timedelta(days=self.lookback_days)
                if mention_date < cutoff:
                    continue

                mentions.append(
                    RawMention(
                        source_id=self.source_id,
                        source_mention_id=mention_id,
                        building_society_id=society.id,
                        mention_type=MentionType.FORUM_POST,
                        mention_date=mention_date,
                        title=title,
                        body=body,
                        author=author,
                        source_url=url,
                        extra={"search_term": search_term},
                    )
                )
            except Exception as e:  # noqa: BLE001
                print(f"    MSE parse error: {e}")
                continue

        return mentions

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawMention]:
        all_mentions: list[RawMention] = []
        seen: set[str] = set()

        for term in self._search_terms(society):
            for page in range(1, self.MAX_PAGES + 1):
                url = SEARCH_URL.format(query=quote_plus(term), page=page)
                try:
                    response = self._fetch_url(url)
                except Exception as e:  # noqa: BLE001
                    print(f"  MSE fetch error '{term}' p{page}: {e}")
                    break

                page_mentions = self._parse_search_page(response.text, society, term)
                if not page_mentions:
                    break

                new = 0
                for m in page_mentions:
                    if m.source_mention_id not in seen:
                        seen.add(m.source_mention_id)
                        if start_date and m.mention_date < start_date:
                            continue
                        if end_date and m.mention_date > end_date:
                            continue
                        all_mentions.append(m)
                        new += 1
                if new == 0:
                    break
                self._rate_limit()

        print(f"  Found {len(all_mentions)} MSE mentions for {society.canonical_name}")
        return all_mentions


if __name__ == "__main__":
    from src.config.societies import get_society_by_id

    society = get_society_by_id("nationwide")
    if society:
        with MSEScraper() as scraper:
            mentions = scraper.scrape_society(society)
            print(f"Found {len(mentions)} mentions for {society.canonical_name}")
