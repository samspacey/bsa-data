"""Database connection and initialization."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings
from src.config.societies import BUILDING_SOCIETIES
from src.data.models import (
    Base,
    BuildingSociety,
    BuildingSocietyAlias,
    DataSource,
)


def get_engine(db_path: Optional[Path] = None):
    """Create SQLAlchemy engine."""
    path = db_path or settings.sqlite_db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", echo=False)


def get_session_factory(engine=None):
    """Create session factory."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)


@contextmanager
def get_session(engine=None) -> Generator[Session, None, None]:
    """Get a database session as a context manager."""
    SessionFactory = get_session_factory(engine)
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(engine=None) -> None:
    """Initialize the database with all tables."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)


def populate_initial_data(engine=None) -> None:
    """Populate the database with initial building societies and data sources.

    This function is idempotent - it will add any missing societies or data sources
    without duplicating existing ones.
    """
    with get_session(engine) as session:
        # Get existing society IDs
        existing_society_ids = {s.id for s in session.query(BuildingSociety.id).all()}
        existing_source_ids = {s.id for s in session.query(DataSource.id).all()}

        # Add data sources if they don't exist
        data_sources = [
            DataSource(
                id="trustpilot",
                name="Trustpilot",
                source_type="review_platform",
                url_pattern="https://uk.trustpilot.com/review/{domain}",
                terms_version_note="Reviews scraped respecting robots.txt and rate limits",
            ),
            DataSource(
                id="app_store",
                name="Apple App Store",
                source_type="app_store",
                url_pattern="https://apps.apple.com/gb/app/id{app_id}",
                terms_version_note="Reviews collected via App Store Scraper library",
            ),
            DataSource(
                id="play_store",
                name="Google Play Store",
                source_type="app_store",
                url_pattern="https://play.google.com/store/apps/details?id={package}",
                terms_version_note="Reviews collected via Google Play Scraper library",
            ),
            DataSource(
                id="smartmoneypeople",
                name="Smart Money People",
                source_type="review_platform",
                url_pattern="https://smartmoneypeople.com/provider/{slug}",
                terms_version_note="Reviews scraped respecting robots.txt and rate limits",
            ),
            DataSource(
                id="feefo",
                name="Feefo",
                source_type="review_platform",
                url_pattern="https://www.feefo.com/en-GB/reviews/{slug}",
                terms_version_note="Reviews scraped respecting robots.txt and rate limits",
            ),
            DataSource(
                id="reddit",
                name="Reddit",
                source_type="forum",
                url_pattern="https://reddit.com/r/{subreddit}/comments/{id}",
                terms_version_note="Fetched via PRAW (Reddit's public API) under API Terms of Use; scoped to last 12 months",
            ),
            DataSource(
                id="mse",
                name="MoneySavingExpert Forum",
                source_type="forum",
                url_pattern="https://forums.moneysavingexpert.com/discussion/{id}",
                terms_version_note="Forum content scraped for internal research use; respecting robots.txt and rate limits",
            ),
            DataSource(
                id="google",
                name="Google Reviews",
                source_type="maps",
                url_pattern="https://www.google.com/maps/place/?q=place_id:{place_id}",
                terms_version_note="Fetched via SerpAPI — internal research use only",
            ),
            DataSource(
                id="fairer_finance",
                name="Fairer Finance",
                source_type="editorial",
                url_pattern="https://www.fairerfinance.com/ratings/customer-experience-ratings/{slug}",
                terms_version_note="Editorial star ratings from Fairer Finance (public pages)",
            ),
            DataSource(
                id="which",
                name="Which? Money",
                source_type="editorial",
                url_pattern="https://www.which.co.uk/reviews/current-accounts/{slug}",
                terms_version_note="Manually curated Which? top-line ratings from public summary pages",
            ),
        ]

        sources_added = 0
        for source in data_sources:
            if source.id not in existing_source_ids:
                session.add(source)
                sources_added += 1

        # Add building societies from config (only new ones)
        societies_added = 0
        for society_config in BUILDING_SOCIETIES:
            if society_config.id not in existing_society_ids:
                society = BuildingSociety(
                    id=society_config.id,
                    canonical_name=society_config.canonical_name,
                    bsa_name=society_config.bsa_name,
                    size_bucket=society_config.size_bucket,
                    website_domain=society_config.website_domain,
                    trustpilot_url=society_config.trustpilot_url,
                    app_store_id=society_config.app_store_id,
                    play_store_id=society_config.play_store_id,
                    notes=society_config.notes or None,
                )
                session.add(society)

                # Add aliases
                # First, add the canonical name as an alias
                session.add(
                    BuildingSocietyAlias(
                        building_society_id=society_config.id,
                        alias_text=society_config.canonical_name,
                        alias_type="canonical",
                        confidence_score=1.0,
                    )
                )

                # Add configured aliases
                for alias in society_config.aliases:
                    alias_type = "acronym" if alias.isupper() else "short_name"
                    session.add(
                        BuildingSocietyAlias(
                            building_society_id=society_config.id,
                            alias_text=alias,
                            alias_type=alias_type,
                            confidence_score=1.0,
                        )
                    )
                societies_added += 1

        session.commit()

        total_societies = len(existing_society_ids) + societies_added
        if societies_added > 0 or sources_added > 0:
            print(f"Added {societies_added} new societies, {sources_added} new data sources.")
            print(f"Database now contains {total_societies} societies.")
        else:
            print(f"Database already up to date with {total_societies} societies.")


def reset_database(engine=None) -> None:
    """Drop all tables and recreate them."""
    if engine is None:
        engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Database reset complete.")


if __name__ == "__main__":
    # When run directly, initialize and populate the database
    print(f"Initializing database at: {settings.sqlite_db_path}")
    engine = get_engine()
    init_database(engine)
    populate_initial_data(engine)
    print("Done!")
