#!/usr/bin/env python3
"""Run the complete data pipeline from scraping to embeddings."""

import argparse
import subprocess
import sys
from pathlib import Path


def run_script(script_name: str, args: list[str] = None) -> bool:
    """Run a pipeline script.

    Args:
        script_name: Name of the script file
        args: Additional arguments

    Returns:
        True if successful
    """
    script_path = Path(__file__).parent / script_name
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    print(f"\n{'='*60}")
    print(f"Running: {script_name}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run the complete data pipeline")
    parser.add_argument(
        "--skip-scraping",
        action="store_true",
        help="Skip the scraping step (use existing raw data)",
    )
    parser.add_argument(
        "--skip-enrichment",
        action="store_true",
        help="Skip the LLM enrichment step",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of reviews to process (for testing)",
    )
    parser.add_argument(
        "--society",
        type=str,
        default=None,
        help="Process only a specific society ID",
    )

    args = parser.parse_args()

    extra_args = []
    if args.limit:
        extra_args.extend(["--limit", str(args.limit)])
    if args.society:
        extra_args.extend(["--society", args.society])

    # Step 1: Scraping
    if not args.skip_scraping:
        if not run_script("01_scrape_all.py"):
            print("Scraping failed!")
            return 1

    # Step 2: Cleaning
    if not run_script("02_clean_data.py"):
        print("Cleaning failed!")
        return 1

    # Step 3: Enrichment
    if not args.skip_enrichment:
        enrich_args = extra_args.copy()
        if not run_script("03_enrich_data.py", enrich_args):
            print("Enrichment failed!")
            return 1

    # Step 4: Metrics
    if not run_script("04_compute_metrics.py"):
        print("Metrics computation failed!")
        return 1

    # Step 5: Embeddings
    embed_args = extra_args.copy()
    if not run_script("05_build_embeddings.py", embed_args):
        print("Embedding generation failed!")
        return 1

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE!")
    print("=" * 60)
    print("\nTo start the API server, run:")
    print("  python -m src.api.main")
    print("\nOr with uvicorn:")
    print("  uvicorn src.api.main:app --reload")

    return 0


if __name__ == "__main__":
    sys.exit(main())
