"""Application settings using Pydantic Settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    project_root: Path = Path(__file__).parent.parent.parent
    data_dir: Path = project_root / "data"
    raw_data_dir: Path = data_dir / "raw"
    processed_data_dir: Path = data_dir / "processed"
    db_dir: Path = data_dir / "db"

    # Database
    sqlite_db_path: Path = db_dir / "bsa.db"
    lancedb_path: Path = db_dir / "lancedb"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Scraping
    scrape_delay_seconds: float = 2.0
    max_retries: int = 3
    request_timeout: int = 30

    # Data collection
    data_start_date: str = "2020-01-01"
    data_end_date: str = "2025-12-31"

    # Processing
    batch_size: int = 50
    max_concurrent_requests: int = 10

    @property
    def sqlite_url(self) -> str:
        """SQLAlchemy database URL."""
        return f"sqlite:///{self.sqlite_db_path}"


settings = Settings()
