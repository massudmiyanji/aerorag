"""Download one file reliably: retries, streaming, atomic writes and a content hash."""

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

USER_AGENT = "aerorag/0.1 (portfolio RAG project; https://github.com/massudmiyanji/aerorag)"
_CHUNK_BYTES = 1 << 16


class DownloadResult(BaseModel):
    url: str
    path: Path
    sha256: str
    size_bytes: int
    downloaded_at: datetime
    skipped: bool = False


def safe_filename(url: str) -> str:
    """Turn the last URL path segment into a filesystem-safe name."""
    name = unquote(Path(urlparse(url).path).name) or "download"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(_CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_retryable(exc: BaseException) -> bool:
    """Retry network failures and server errors; fail fast on 4xx such as 404."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    reraise=True,
)
def download_file(
    client: httpx.Client, url: str, dest_dir: Path, filename: str | None = None
) -> DownloadResult:
    """Download url into dest_dir. An existing file is reused, so re-runs are cheap."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (filename or safe_filename(url))

    if dest.exists():
        return DownloadResult(
            url=url,
            path=dest,
            sha256=sha256_of(dest),
            size_bytes=dest.stat().st_size,
            downloaded_at=datetime.fromtimestamp(dest.stat().st_mtime, tz=UTC),
            skipped=True,
        )

    partial = dest.with_name(dest.name + ".part")
    digest = hashlib.sha256()
    size = 0
    try:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with partial.open("wb") as f:
                for block in response.iter_bytes(_CHUNK_BYTES):
                    f.write(block)
                    digest.update(block)
                    size += len(block)
        partial.replace(dest)  # atomic: a crash never leaves a "finished" half-file
    finally:
        partial.unlink(missing_ok=True)

    return DownloadResult(
        url=url,
        path=dest,
        sha256=digest.hexdigest(),
        size_bytes=size,
        downloaded_at=datetime.now(UTC),
    )


def make_client() -> httpx.Client:
    """An HTTP client with polite defaults, shared across all downloads."""
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(30.0, read=120.0),
        follow_redirects=True,
    )
