"""Download the AeroRAG corpus into data/raw and write data/manifest.csv.

Usage: uv run python scripts/download_corpus.py [--max-ads 60]
"""

import argparse
import itertools
import logging

from aerorag.config import get_settings
from aerorag.ingestion.corpus import build_corpus
from aerorag.ingestion.download import make_client
from aerorag.ingestion.sources import HANDBOOKS, fetch_airworthiness_directives


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-ads", type=int, default=60, help="Max airworthiness directives")
    parser.add_argument("--skip-handbooks", action="store_true", help="Only fetch directives")
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(message)s")

    with make_client() as client:
        directives = fetch_airworthiness_directives(client, max_docs=args.max_ads)
        handbooks = () if args.skip_handbooks else HANDBOOKS
        report = build_corpus(
            client,
            itertools.chain(handbooks, directives),
            raw_dir=settings.data_dir / "raw",
            manifest_path=settings.data_dir / "manifest.csv",
        )

    logging.info(
        "done: %d downloaded, %d already present, %d failed %s",
        report.downloaded,
        report.skipped,
        len(report.failed),
        report.failed or "",
    )


if __name__ == "__main__":
    main()
