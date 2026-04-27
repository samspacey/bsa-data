FROM python:3.11-slim

# System libs:
#  - build-essential for lancedb / pyarrow / numpy wheels
#  - WeasyPrint needs pango, harfbuzz, cairo, fontconfig for HTML->PDF rendering
#    of the benchmark report
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libcairo2 \
        libffi-dev \
        shared-mime-info \
        fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so this layer caches independently of code.
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
        "fastapi>=0.109.0" \
        "uvicorn[standard]>=0.27.0" \
        "pydantic[email]>=2.5.0" \
        "pydantic-settings>=2.3.0" \
        "sqlalchemy>=2.0.0" \
        "lancedb>=0.4.0" \
        "pylance>=0.21.0" \
        "httpx>=0.26.0" \
        "beautifulsoup4>=4.12.0" \
        "lxml>=5.0.0" \
        "openai>=1.10.0" \
        "tiktoken>=0.5.0" \
        "pandas>=2.1.0" \
        "regex>=2023.12.0" \
        "langdetect>=1.0.9" \
        "rapidfuzz>=3.6.0" \
        "python-dotenv>=1.0.0" \
        "tqdm>=4.66.0" \
        "tenacity>=8.2.0" \
        "weasyprint>=60.0"

# Code + pre-built SQLite (contains the ~14.9k enriched reviews + 16+
# analytics events including captured leads). The Railway volume is
# mounted at /app/data/db, which shadows the bsa.db that was COPY'd in.
# We keep a seed copy at /app/data-seed/bsa.db so the entrypoint can
# hydrate the empty volume on first boot. The LanceDB vector index is
# generated from SQLite on first boot into the same volume.
COPY src /app/src
COPY data /app/data
COPY scripts /app/scripts
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /app/data-seed \
    && cp /app/data/db/bsa.db /app/data-seed/bsa.db

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", 8000)}/health').read()"

CMD ["/app/entrypoint.sh"]
