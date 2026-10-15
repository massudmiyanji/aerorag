"""Where the corpus comes from: fixed FAA handbooks plus Pratt & Whitney airworthiness directives.

Real Pratt & Whitney manuals are proprietary, so the corpus uses public US-government
documents. Each source becomes a SourceDocument; downloading is handled elsewhere.
"""

from collections.abc import Iterator
from datetime import date
from enum import StrEnum

import httpx
from pydantic import BaseModel

FEDERAL_REGISTER_API = "https://www.federalregister.gov/api/v1/documents.json"
_FAA_HANDBOOKS = "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation"


class DocType(StrEnum):
    HANDBOOK = "handbook"
    AIRWORTHINESS_DIRECTIVE = "airworthiness_directive"


class SourceDocument(BaseModel):
    doc_id: str  # stable id, also used as the file stem
    title: str
    doc_type: DocType
    url: str
    published: date | None = None

    @property
    def filename(self) -> str:
        return f"{self.doc_id}.pdf"


HANDBOOKS: tuple[SourceDocument, ...] = (
    SourceDocument(
        doc_id="FAA-H-8083-32B",
        title="Aviation Maintenance Technician Handbook - Powerplant",
        doc_type=DocType.HANDBOOK,
        url=f"{_FAA_HANDBOOKS}/amt_powerplant_handbook.pdf",
    ),
    SourceDocument(
        doc_id="FAA-H-8083-30B",
        title="Aviation Maintenance Technician Handbook - General",
        doc_type=DocType.HANDBOOK,
        url=f"{_FAA_HANDBOOKS}/amtg_handbook.pdf",
    ),
    SourceDocument(
        doc_id="FAA-H-8083-31B",
        title="Aviation Maintenance Technician Handbook - Airframe",
        doc_type=DocType.HANDBOOK,
        url=f"{_FAA_HANDBOOKS}/FAA-H-8083-31B_Aviation_Maintenance_Technician_Handbook.pdf",
    ),
)


def _is_pw_directive(title: str) -> bool:
    lowered = title.lower()
    return "airworthiness directives" in lowered and "pratt" in lowered


def fetch_airworthiness_directives(
    client: httpx.Client, max_docs: int = 60, per_page: int = 100
) -> Iterator[SourceDocument]:
    """Yield final-rule Pratt & Whitney ADs from the Federal Register API, newest first."""
    params: dict[str, str | int | list[str]] = {
        "conditions[term]": '"Pratt & Whitney"',
        "conditions[agencies][]": "federal-aviation-administration",
        "conditions[type][]": "RULE",
        "order": "newest",
        "per_page": per_page,
        "fields[]": ["document_number", "title", "pdf_url", "publication_date"],
    }
    url: str | None = FEDERAL_REGISTER_API
    found = 0
    while url and found < max_docs:
        response = client.get(url, params=params if url == FEDERAL_REGISTER_API else None)
        response.raise_for_status()
        payload = response.json()
        for item in payload.get("results", []):
            if not item.get("pdf_url") or not _is_pw_directive(item.get("title", "")):
                continue
            yield SourceDocument(
                doc_id=f"FR-{item['document_number']}",
                title=item["title"],
                doc_type=DocType.AIRWORTHINESS_DIRECTIVE,
                url=item["pdf_url"],
                published=date.fromisoformat(item["publication_date"]),
            )
            found += 1
            if found >= max_docs:
                return
        url = payload.get("next_page_url")  # already carries the query string
