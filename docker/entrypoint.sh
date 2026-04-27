#!/bin/sh
# Container entrypoint.
#
# Persistence model:
#   - The Railway volume is mounted at /app/data/db (the whole DB dir).
#   - First boot: volume is empty -> we hydrate it with the seed bsa.db
#     baked into the image at /app/data-seed/bsa.db.
#   - Subsequent boots: bsa.db already on the volume, contains all the
#     captured leads + chat events from previous runs. We use it as-is.
#   - LanceDB lives at /app/data/db/lancedb on the same volume. Built
#     from SQLite on first boot via the embedding pipeline; persists
#     across redeploys after that.

set -e

DB_DIR="/app/data/db"
SQLITE_DB="$DB_DIR/bsa.db"
SEED_DB="/app/data-seed/bsa.db"
LANCEDB_DIR="$DB_DIR/lancedb"
BOOTSTRAP_MARKER="$LANCEDB_DIR/.bootstrapped"

mkdir -p "$DB_DIR" "$LANCEDB_DIR"

# Hydrate the SQLite DB on first boot when the volume is empty.
if [ ! -f "$SQLITE_DB" ]; then
    if [ -f "$SEED_DB" ]; then
        echo "[entrypoint] No bsa.db on volume yet -> seeding from $SEED_DB"
        cp "$SEED_DB" "$SQLITE_DB"
    else
        echo "[entrypoint] WARNING: no bsa.db and no seed available; the app will start with an empty DB." >&2
    fi
else
    echo "[entrypoint] bsa.db already on volume ($(stat -c%s "$SQLITE_DB" 2>/dev/null || stat -f%z "$SQLITE_DB") bytes) - leaving in place."
fi

# Bootstrap LanceDB embeddings on first boot only.
if [ ! -f "$BOOTSTRAP_MARKER" ]; then
    echo "[entrypoint] LanceDB not bootstrapped yet - generating embeddings from SQLite..."
    echo "[entrypoint] One-off cost: ~5 min + ~\$0.01 OpenAI."
    if python scripts/05_build_embeddings.py --batch-size 100; then
        touch "$BOOTSTRAP_MARKER"
        echo "[entrypoint] Embeddings complete."
    else
        echo "[entrypoint] WARNING: embedding generation failed. Evidence snippets will be empty but chat will still run." >&2
    fi
else
    echo "[entrypoint] LanceDB already bootstrapped, skipping."
fi

exec uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
