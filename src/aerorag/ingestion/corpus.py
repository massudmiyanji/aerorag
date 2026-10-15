"""Build the raw corpus: download every source and record it in a manifest."""

import csv
import logging
from collections.abc import Iterable
from pathlib import Path

import httpx
from pydantic import BaseModel

from aerorag.ingestion.download import DownloadResult, download_file
from aerorag.ingestion.sources import SourceDocument

logger = logging.getLogger(__name__)

MANIFEST_FIELDS = (
    "doc_id",
    "title",
    "doc_type",
    "published",
    "url",
    "path",
    "sha256",
    "size_bytes",
    "downloaded_at",
)


class CorpusReport(BaseModel):
    downloaded: int = 0
    skipped: int = 0
    failed: list[str] = []


def _manifest_row(source: SourceDocument, result: DownloadResult) -> dict[str, str]:
    return {
        "doc_id": source.doc_id,
        "title": source.title,
        "doc_type": source.doc_type.value,
        "published": source.published.isoformat() if source.published else "",
        "url": source.url,
        "path": result.path.as_posix(),
        "sha256": result.sha256,
        "size_bytes": str(result.size_bytes),
        "downloaded_at": result.downloaded_at.isoformat(),
    }


def build_corpus(
    client: httpx.Client, sources: Iterable[SourceDocument], raw_dir: Path, manifest_path: Path
) -> CorpusReport:
    """Download each source into raw_dir and write one manifest row per file on disk.

    A failed download is logged and skipped so one bad URL never stops the run.
    """
    report = CorpusReport()
    rows: list[dict[str, str]] = []
    for source in sources:
        try:
            result = download_file(client, source.url, raw_dir, filename=source.filename)
        except httpx.HTTPError as exc:
            logger.warning("failed %s (%s): %s", source.doc_id, source.url, exc)
            report.failed.append(source.doc_id)
            continue
        if result.skipped:
            report.skipped += 1
        else:
            report.downloaded += 1
            logger.info("downloaded %s (%.1f MB)", source.doc_id, result.size_bytes / 1e6)
        rows.append(_manifest_row(source, result))

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: r["doc_id"]))
    return report
