"""Reddit scraper for building society mentions in UK personal finance subs.

Uses PRAW (the official Reddit API wrapper). Requires a script-type OAuth app.
Set ``REDDIT_CLIENT_ID`` and ``REDDIT_CLIENT_SECRET`` in ``.env`` to enable.

Create the app at https://www.reddit.com/prefs/apps (type: "script"). PRAW's
search API caps historical results at ~1000 items per query, so this scraper
deliberately scopes to the most recent 12 months and surfaces that in the
``extra`` metadata for transparency.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional

from src.config.settings import settings
from src.config.societies import BuildingSociety
from src.data.schemas import MentionType, RawMention
from src.scrapers.base import BaseScraper


DEFAULT_SUBREDDITS = [
    "UKPersonalFinance",
    "HousingUK",
    "UKSavings",
    "MortgageUK",
    "unitedkingdom",
]


class RedditScraper(BaseScraper):
    """Scraper for Reddit mentions of building societies."""

    @property
    def source_id(self) -> str:
        return "reddit"

    @property
    def source_name(self) -> str:
        return "Reddit"

    def __init__(
        self,
        *args,
        subreddits: Optional[Iterable[str]] = None,
        lookback_days: int = 365,
        per_query_limit: int = 250,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.subreddits = list(subreddits or DEFAULT_SUBREDDITS)
        self.lookback_days = lookback_days
        self.per_query_limit = per_query_limit
        self._reddit = None

    def _get_reddit(self):
        """Lazy-initialize the PRAW client."""
        if self._reddit is not None:
            return self._reddit

        if not settings.reddit_client_id or not settings.reddit_client_secret:
            raise RuntimeError(
                "Reddit credentials missing. Set REDDIT_CLIENT_ID and "
                "REDDIT_CLIENT_SECRET in .env to enable Reddit scraping."
            )

        try:
            import praw  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "praw not installed. Add 'praw>=7.7.0' to dependencies."
            ) from exc

        self._reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )
        self._reddit.read_only = True
        return self._reddit

    def _search_terms(self, society: BuildingSociety) -> list[str]:
        """Build list of search queries for this society."""
        terms = {society.canonical_name}
        for alias in society.aliases:
            # Skip very short acronyms that would produce noise
            if len(alias) >= 4 and alias.lower() not in {"bs", "the"}:
                terms.add(alias)
        # Always include the website domain as a likely mention marker
        if society.website_domain:
            terms.add(society.website_domain)
        return sorted(terms)

    def scrape_society(
        self,
        society: BuildingSociety,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[RawMention]:
        try:
            reddit = self._get_reddit()
        except RuntimeError as e:
            print(f"  Reddit disabled: {e}")
            return []

        cutoff = start_date or (date.today() - timedelta(days=self.lookback_days))
        cutoff_ts = datetime.combine(cutoff, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp()

        mentions: list[RawMention] = []
        seen_ids: set[str] = set()

        for term in self._search_terms(society):
            query = f'"{term}"'
            for subreddit in self.subreddits:
                try:
                    listing = reddit.subreddit(subreddit).search(
                        query,
                        sort="new",
                        time_filter="year",
                        limit=self.per_query_limit,
                    )
                    for submission in listing:
                        if submission.id in seen_ids:
                            continue
                        if submission.created_utc < cutoff_ts:
                            continue

                        body = (submission.selftext or "").strip()
                        title = (submission.title or "").strip()
                        # Skip link-only posts with no text — low signal
                        if not body and not title:
                            continue

                        mention_date = datetime.fromtimestamp(
                            submission.created_utc, tz=timezone.utc
                        ).date()

                        mentions.append(
                            RawMention(
                                source_id=self.source_id,
                                source_mention_id=f"reddit_{submission.id}",
                                building_society_id=society.id,
                                mention_type=MentionType.FORUM_POST,
                                mention_date=mention_date,
                                title=title or None,
                                body=body or title,
                                author=str(submission.author) if submission.author else None,
                                source_url=f"https://reddit.com{submission.permalink}",
                                extra={
                                    "subreddit": subreddit,
                                    "search_term": term,
                                    "score": submission.score,
                                    "num_comments": submission.num_comments,
                                    "upvote_ratio": submission.upvote_ratio,
                                },
                            )
                        )
                        seen_ids.add(submission.id)
                except Exception as e:  # noqa: BLE001
                    print(f"    Reddit error {subreddit}/'{term}': {e}")
                    continue
            self._rate_limit()

        if end_date:
            mentions = [m for m in mentions if m.mention_date <= end_date]

        print(f"  Found {len(mentions)} Reddit mentions across {len(self.subreddits)} subs")
        return mentions


if __name__ == "__main__":
    from src.config.societies import get_society_by_id

    society = get_society_by_id("nationwide")
    if society:
        with RedditScraper() as scraper:
            mentions = scraper.scrape_society(society)
            print(f"Found {len(mentions)} mentions for {society.canonical_name}")
            if mentions:
                print(f"Sample: {mentions[0]}")
