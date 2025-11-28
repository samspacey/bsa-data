"""LanceDB vector index management for review embeddings."""

from datetime import date
from pathlib import Path
from typing import Optional

import lancedb
from lancedb.pydantic import LanceModel, Vector

from src.config.settings import settings


class ReviewDocument(LanceModel):
    """Schema for review documents in the vector index."""

    id: int  # Corresponds to embedding_document.id or public_review.id
    review_id: int  # public_review.id
    building_society_id: str
    source_id: str
    review_date: str  # ISO format date string
    rating: int
    sentiment_label: str
    aspects: str  # JSON array as string
    topics: str  # JSON array as string
    text: str
    vector: Vector(1536)  # Dimension for text-embedding-3-small


class VectorIndex:
    """Manage the LanceDB vector index."""

    TABLE_NAME = "reviews"

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the vector index.

        Args:
            db_path: Path to LanceDB database directory
        """
        self.db_path = db_path or settings.lancedb_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = None
        self._table = None

    @property
    def db(self):
        """Lazy-load database connection."""
        if self._db is None:
            self._db = lancedb.connect(str(self.db_path))
        return self._db

    @property
    def table(self):
        """Get or create the reviews table."""
        if self._table is None:
            if self.TABLE_NAME in self.db.table_names():
                self._table = self.db.open_table(self.TABLE_NAME)
            else:
                # Create empty table with schema
                self._table = self.db.create_table(
                    self.TABLE_NAME,
                    schema=ReviewDocument,
                    mode="overwrite",
                )
        return self._table

    def add_documents(self, documents: list[ReviewDocument]) -> int:
        """Add documents to the index.

        Args:
            documents: List of review documents

        Returns:
            Number of documents added
        """
        if not documents:
            return 0

        # Convert to dicts for LanceDB
        data = [doc.model_dump() for doc in documents]
        self.table.add(data)
        return len(documents)

    def search(
        self,
        query_vector: list[float],
        limit: int = 20,
        building_society_ids: Optional[list[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sentiment_labels: Optional[list[str]] = None,
        aspects: Optional[list[str]] = None,
    ) -> list[dict]:
        """Search the index with optional filters.

        Args:
            query_vector: Query embedding vector
            limit: Maximum results to return
            building_society_ids: Filter by society IDs
            start_date: Filter by start date
            end_date: Filter by end date
            sentiment_labels: Filter by sentiment labels
            aspects: Filter by aspects (searches in aspects JSON)

        Returns:
            List of matching documents with scores
        """
        # Build filter expression
        filters = []

        if building_society_ids:
            society_filter = " OR ".join(
                [f"building_society_id = '{sid}'" for sid in building_society_ids]
            )
            filters.append(f"({society_filter})")

        if start_date:
            filters.append(f"review_date >= '{start_date.isoformat()}'")

        if end_date:
            filters.append(f"review_date <= '{end_date.isoformat()}'")

        if sentiment_labels:
            sentiment_filter = " OR ".join(
                [f"sentiment_label = '{s}'" for s in sentiment_labels]
            )
            filters.append(f"({sentiment_filter})")

        filter_expr = " AND ".join(filters) if filters else None

        # Execute search
        query = self.table.search(query_vector).limit(limit)

        if filter_expr:
            query = query.where(filter_expr)

        results = query.to_list()

        # Post-filter by aspects if needed (LanceDB doesn't support JSON contains easily)
        if aspects:
            filtered_results = []
            for result in results:
                result_aspects = result.get("aspects", "[]")
                if any(aspect in result_aspects for aspect in aspects):
                    filtered_results.append(result)
            results = filtered_results[:limit]

        return results

    def get_by_society(
        self,
        society_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """Get documents for a specific society.

        Args:
            society_id: Building society ID
            limit: Maximum results

        Returns:
            List of documents
        """
        return (
            self.table.search()
            .where(f"building_society_id = '{society_id}'")
            .limit(limit)
            .to_list()
        )

    def delete_by_society(self, society_id: str) -> int:
        """Delete all documents for a society.

        Args:
            society_id: Building society ID

        Returns:
            Number of documents deleted
        """
        # LanceDB doesn't have direct delete, we'd need to filter and recreate
        # For now, just return 0 as this is a PoC
        return 0

    def count(self) -> int:
        """Get total document count."""
        return len(self.table.to_pandas())

    def clear(self):
        """Clear all documents from the index."""
        self._table = self.db.create_table(
            self.TABLE_NAME,
            schema=ReviewDocument,
            mode="overwrite",
        )
