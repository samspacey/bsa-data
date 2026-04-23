#!/bin/sh
# Container entrypoint: generate embeddings into the mounted LanceDB volume
# on first boot only, then launch the API.
#
# The volume (Railway) is mounted at /app/data/db/lancedb. On the first deploy
# it's empty — we detect that, run the embedding pipeline against the baked-in
# SQLite DB, then persist the vectors. Subsequent deploys skip this step.

set -e

LANCEDB_DIR="/app/data/db/lancedb"
MARKER_FILE="$LANCEDB_DIR/.bootstrapped"

mkdir -p "$LANCEDB_DIR"

if [ ! -f "$MARKER_FILE" ]; then
    echo "[entrypoint] LanceDB not bootstrapped yet — generating embeddings from SQLite..."
    echo "[entrypoint] This runs once per volume; expect ~5 minutes + a small OpenAI bill."
    if python scripts/05_build_embeddings.py --batch-size 100; then
        touch "$MARKER_FILE"
        echo "[entrypoint] Embeddings complete."
    else
        echo "[entrypoint] WARNING: embedding generation failed. Evidence snippets will be empty but chat will still run." >&2
    fi
else
    echo "[entrypoint] LanceDB already bootstrapped, skipping."
fi

exec uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
