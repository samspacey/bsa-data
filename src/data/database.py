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
    """Populate the database with initial building societies and data sources."""
    with get_session(engine) as session:
        # Check if data already exists
        existing_societies = session.query(BuildingSociety).count()
        if existing_societies > 0:
            print(f"Database already contains {existing_societies} societies. Skipping population.")
            return

        # Add data sources
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
        ]

        for source in data_sources:
            session.add(source)

        # Add building societies from config
        for society_config in BUILDING_SOCIETIES:
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

        session.commit()
        print(f"Populated database with {len(BUILDING_SOCIETIES)} building societies and 3 data sources.")


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
