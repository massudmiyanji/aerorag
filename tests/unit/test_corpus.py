import csv
from pathlib import Path

import httpx

from aerorag.ingestion.corpus import build_corpus
from aerorag.ingestion.sources import (
    DocType,
    SourceDocument,
    fetch_airworthiness_directives,
)


def _ad(number: str, title: str, pdf_url: str | None = "https://govinfo.gov/x.pdf") -> dict:
    return {
        "document_number": number,
        "title": title,
        "pdf_url": pdf_url,
        "publication_date": "2026-04-24",
    }


def test_fetch_directives_filters_and_follows_pages() -> None:
    pages = {
        "1": {
            "results": [
                _ad("2026-1", "Airworthiness Directives; Pratt & Whitney Engines"),
                _ad("2026-2", "Airworthiness Directives; The Boeing Company Airplanes"),
                _ad("2026-3", "Airworthiness Directives; Pratt & Whitney Engines", None),
            ],
            "next_page_url": "https://www.federalregister.gov/api/v1/documents.json?page=2",
        },
        "2": {
            "results": [_ad("2026-4", "Airworthiness Directives; Pratt & Whitney Canada Corp.")],
            "next_page_url": None,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pages[request.url.params.get("page", "1")])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        docs = list(fetch_airworthiness_directives(client))

    assert [d.doc_id for d in docs] == ["FR-2026-1", "FR-2026-4"]
    assert all(d.doc_type is DocType.AIRWORTHINESS_DIRECTIVE for d in docs)


def test_fetch_directives_respects_max_docs() -> None:
    page = {
        "results": [
            _ad(f"2026-{i}", "Airworthiness Directives; Pratt & Whitney") for i in range(5)
        ],
        "next_page_url": None,
    }
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=page))) as c:
        assert len(list(fetch_airworthiness_directives(c, max_docs=2))) == 2


def test_build_corpus_writes_manifest_and_survives_failures(tmp_path: Path) -> None:
    sources = [
        SourceDocument(doc_id="OK-1", title="Good", doc_type=DocType.HANDBOOK, url="https://x/ok"),
        SourceDocument(
            doc_id="BAD-1", title="Gone", doc_type=DocType.HANDBOOK, url="https://x/404"
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/404":
            return httpx.Response(404)
        return httpx.Response(200, content=b"%PDF data")

    manifest = tmp_path / "manifest.csv"
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = build_corpus(client, sources, tmp_path / "raw", manifest)

    assert report.downloaded == 1
    assert report.failed == ["BAD-1"]
    rows = list(csv.DictReader(manifest.open()))
    assert [r["doc_id"] for r in rows] == ["OK-1"]
    assert rows[0]["path"].endswith("raw/OK-1.pdf")
