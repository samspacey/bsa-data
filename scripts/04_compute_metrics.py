#!/usr/bin/env python3
"""Script to compute aggregated metrics from enriched reviews."""

import argparse
import sys
from datetime import date
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.data.database import get_engine, get_session
from src.data.models import SummaryMetric
from src.processing.metrics import MetricsComputer


def main():
    parser = argparse.ArgumentParser(description="Compute aggregated metrics")
    parser.add_argument(
        "--granularity",
        choices=["monthly", "quarterly", "yearly"],
        default="monthly",
        help="Time bucket granularity (default: monthly)",
    )
    parser.add_argument(
        "--start-date",
        type=lambda s: date.fromisoformat(s),
        default=None,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=lambda s: date.fromisoformat(s),
        default=None,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="Metric version string",
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Clear existing metrics before computing",
    )

    args = parser.parse_args()

    engine = get_engine()

    with get_session(engine) as session:
        # Optionally clear existing metrics
        if args.clear_existing:
            print("Clearing existing metrics...")
            session.query(SummaryMetric).delete()
            session.commit()

        # Initialize computer
        computer = MetricsComputer(session)

        # Compute metrics
        print(f"Computing metrics with {args.granularity} granularity...")
        metrics = computer.compute_all_metrics(
            granularity=args.granularity,
            start_date=args.start_date,
            end_date=args.end_date,
            metric_version=args.version,
        )

        print(f"Computed {len(metrics)} metric records")

        # Save to database
        print("Saving to database...")
        for metric in metrics:
            session.add(metric)
        session.commit()

    print("\nDone!")
    print(f"Database: {settings.sqlite_db_path}")


if __name__ == "__main__":
    main()
