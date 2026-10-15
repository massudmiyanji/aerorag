import hashlib
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from aerorag.ingestion.download import download_file, safe_filename

PDF_BYTES = b"%PDF-1.7 fake pdf body" * 1000
Handler = Callable[[httpx.Request], httpx.Response]


def client_for(handler: Handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_downloads_file_and_hashes_content(tmp_path: Path) -> None:
    with client_for(lambda _: httpx.Response(200, content=PDF_BYTES)) as client:
        result = download_file(client, "https://example.gov/docs/manual.pdf", tmp_path)

    assert result.path == tmp_path / "manual.pdf"
    assert result.path.read_bytes() == PDF_BYTES
    assert result.sha256 == hashlib.sha256(PDF_BYTES).hexdigest()
    assert result.size_bytes == len(PDF_BYTES)
    assert not result.skipped
    assert not list(tmp_path.glob("*.part"))


def test_second_call_skips_existing_file(tmp_path: Path) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=PDF_BYTES)

    with client_for(handler) as client:
        first = download_file(client, "https://example.gov/a.pdf", tmp_path)
        second = download_file(client, "https://example.gov/a.pdf", tmp_path)

    assert calls == 1
    assert second.skipped
    assert second.sha256 == first.sha256


def test_404_fails_without_retrying(tmp_path: Path) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404)

    with client_for(handler) as client, pytest.raises(httpx.HTTPStatusError):
        download_file(client, "https://example.gov/missing.pdf", tmp_path)

    assert calls == 1
    assert not (tmp_path / "missing.pdf").exists()


def test_server_error_is_retried_then_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("time.sleep", lambda _: None)  # skip tenacity backoff
    responses = iter([httpx.Response(503), httpx.Response(200, content=PDF_BYTES)])

    with client_for(lambda _: next(responses)) as client:
        result = download_file(client, "https://example.gov/flaky.pdf", tmp_path)

    assert result.size_bytes == len(PDF_BYTES)


def test_safe_filename_strips_unsafe_characters() -> None:
    assert safe_filename("https://x.gov/a%20b/Some File (v2).pdf") == "Some_File_v2_.pdf"
