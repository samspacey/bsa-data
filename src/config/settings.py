"""Application settings using Pydantic Settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Treat empty env vars as unset so .env values win over inherited blanks
        # from the shell (e.g. an empty ANTHROPIC_API_KEY exported in a parent).
        env_ignore_empty=True,
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

    # Anthropic (primary LLM for chat + intent parsing + follow-ups)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-7"

    # OpenAI (embeddings only — Anthropic doesn't offer an embedding API)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"  # retained for legacy /api/chat/ fallback path
    openai_embedding_model: str = "text-embedding-3-small"

    # Scraping
    scrape_delay_seconds: float = 2.0
    max_retries: int = 3
    request_timeout: int = 30

    # Data collection
    data_start_date: str = "2020-01-01"
    data_end_date: str = "2026-12-31"

    # Processing
    batch_size: int = 50
    max_concurrent_requests: int = 10

    # Reddit (optional — set to enable Reddit scraping)
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "bsa-voc-scraper/0.1 by parklands-internal-research"

    # SerpAPI (optional — set to enable Google scraping)
    serpapi_key: str = ""

    # Email sending for the benchmark report. Either set SMTP_* (preferred) or
    # RESEND_API_KEY. If neither is set, the /report/email endpoint still
    # generates the PDF but returns an error that the frontend can surface.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    resend_api_key: str = ""
    resend_from_email: str = ""

    @property
    def sqlite_url(self) -> str:
        """SQLAlchemy database URL."""
        return f"sqlite:///{self.sqlite_db_path}"


settings = Settings()
