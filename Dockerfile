FROM python:3.11-slim

# System libs needed by lancedb / pyarrow for building wheels on slim images
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so the dependency layer caches independently of code.
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
        "fastapi>=0.109.0" \
        "uvicorn[standard]>=0.27.0" \
        "pydantic>=2.5.0" \
        "pydantic-settings>=2.3.0" \
        "sqlalchemy>=2.0.0" \
        "lancedb>=0.4.0" \
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
        "tenacity>=8.2.0"

# App code + the pre-built SQLite + LanceDB assets. Large (~80 MB) but keeps
# the backend stateless from Railway's perspective — no attached volume needed.
COPY src /app/src
COPY data /app/data
COPY scripts /app/scripts

# Railway injects PORT dynamically; default to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

# Health check: the app exposes /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", 8000)}/health').read()"

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
