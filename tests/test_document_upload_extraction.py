"""Tests for Phase 2: Markdown/TXT upload metadata storage and text extraction.

Covers:
- .txt upload → metadata stored, text extracted
- .md upload → metadata stored, text extracted
- .markdown extension accepted
- unsupported extension rejected (422)
- missing project → 404
- store_as_document=True creates a ProjectDocument
- store_as_document=False skips document creation
- document kind: MARKDOWN for .md/.markdown, RAW_TEXT for .txt
- TextExtractionService unit tests (no DB needed)
"""
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.services.text_extraction_service import TextExtractionService, UnsupportedFileTypeError


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create_project(client: AsyncClient, name: str = "Upload Project") -> str:
    resp = await client.post("/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _upload(
    client: AsyncClient,
    project_id: str,
    filename: str,
    content: bytes,
    content_type: str = "text/plain",
    *,
    store_as_document: bool = True,
    title: str | None = None,
):
    params: dict = {"store_as_document": str(store_as_document).lower()}
    if title:
        params["title"] = title
    return await client.post(
        f"/projects/{project_id}/documents/upload",
        files={"file": (filename, content, content_type)},
        params=params,
    )


# ── TextExtractionService unit tests (no fixtures needed) ────────────────────


def test_extraction_service_txt_returns_decoded_string() -> None:
    svc = TextExtractionService()
    text = svc.extract("notes.txt", b"Hello world\n")
    assert text == "Hello world\n"


def test_extraction_service_md_returns_decoded_string() -> None:
    svc = TextExtractionService()
    text = svc.extract("readme.md", b"# Title\n\nContent.")
    assert text == "# Title\n\nContent."


def test_extraction_service_markdown_extension_accepted() -> None:
    svc = TextExtractionService()
    text = svc.extract("spec.markdown", b"Some **bold** text.")
    assert text == "Some **bold** text."


def test_extraction_service_uppercase_extension_rejected() -> None:
    svc = TextExtractionService()
    with pytest.raises(UnsupportedFileTypeError):
        svc.extract("doc.PDF", b"%PDF-1.4")


def test_extraction_service_pdf_raises_unsupported() -> None:
    svc = TextExtractionService()
    with pytest.raises(UnsupportedFileTypeError, match=r"\.pdf"):
        svc.extract("report.pdf", b"%PDF-1.4 binary")


def test_extraction_service_docx_raises_unsupported() -> None:
    svc = TextExtractionService()
    with pytest.raises(UnsupportedFileTypeError, match=r"\.docx"):
        svc.extract("document.docx", b"PK\x03\x04binary")


def test_extraction_service_no_extension_raises_unsupported() -> None:
    svc = TextExtractionService()
    with pytest.raises(UnsupportedFileTypeError):
        svc.extract("Makefile", b"all:\n\techo done")


def test_extraction_service_is_supported_true_for_txt() -> None:
    assert TextExtractionService().is_supported("file.txt") is True


def test_extraction_service_is_supported_true_for_md() -> None:
    assert TextExtractionService().is_supported("file.md") is True


def test_extraction_service_is_supported_true_for_markdown() -> None:
    assert TextExtractionService().is_supported("file.markdown") is True


def test_extraction_service_is_supported_false_for_pdf() -> None:
    assert TextExtractionService().is_supported("file.pdf") is False


def test_extraction_service_is_supported_false_for_docx() -> None:
    assert TextExtractionService().is_supported("file.docx") is False


def test_extraction_service_error_message_lists_supported_types() -> None:
    svc = TextExtractionService()
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        svc.extract("slides.pptx", b"binary")
    msg = str(exc_info.value)
    assert ".md" in msg
    assert ".txt" in msg


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_txt_upload_returns_201(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(client, project_id, "notes.txt", b"Hello\nworld")
    assert resp.status_code == 201


async def test_txt_upload_metadata_stored(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    content = b"Plain text content."
    resp = await _upload(client, project_id, "notes.txt", content)
    data = resp.json()
    uf = data["uploaded_file"]
    assert uf["filename"] == "notes.txt"
    assert uf["size_bytes"] == len(content)
    assert uf["project_id"] == project_id
    assert uf["id"]
    assert uf["storage_path"].startswith("uploads/")
    assert "notes.txt" in uf["storage_path"]
    assert uf["created_at"]


async def test_md_upload_metadata_stored(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    content = b"# Requirements\n\nBuild a bot."
    resp = await _upload(client, project_id, "spec.md", content, "text/markdown")
    assert resp.status_code == 201
    uf = resp.json()["uploaded_file"]
    assert uf["filename"] == "spec.md"
    assert uf["size_bytes"] == len(content)
    assert uf["content_type"] == "text/markdown"


async def test_markdown_extension_upload_accepted(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(client, project_id, "spec.markdown", b"# Spec", "text/markdown")
    assert resp.status_code == 201
    assert resp.json()["uploaded_file"]["filename"] == "spec.markdown"


async def test_txt_extraction_output_is_correct(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    content = b"Line one\nLine two\n"
    resp = await _upload(client, project_id, "lines.txt", content)
    assert resp.json()["extracted_text"] == "Line one\nLine two\n"


async def test_md_extraction_output_is_correct(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    content = b"# Title\n\nParagraph with **bold**.\n"
    resp = await _upload(client, project_id, "doc.md", content, "text/markdown")
    assert resp.json()["extracted_text"] == "# Title\n\nParagraph with **bold**.\n"


async def test_unsupported_pdf_extension_rejected(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(client, project_id, "report.pdf", b"%PDF-1.4", "application/pdf")
    assert resp.status_code == 422
    assert ".pdf" in resp.json()["detail"]


async def test_unsupported_docx_extension_rejected(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(
        client, project_id, "document.docx", b"PK\x03\x04binary",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert resp.status_code == 422
    assert ".docx" in resp.json()["detail"]


async def test_unsupported_extension_error_lists_supported(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(client, project_id, "image.png", b"\x89PNG", "image/png")
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert ".md" in detail
    assert ".txt" in detail


async def test_missing_project_returns_404(client: AsyncClient) -> None:
    resp = await _upload(
        client,
        "00000000-0000-0000-0000-000000000099",
        "notes.txt",
        b"content",
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_store_as_document_true_creates_document(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(
        client, project_id, "spec.md", b"# Bot spec", store_as_document=True
    )
    assert resp.status_code == 201
    doc = resp.json()["document"]
    assert doc is not None
    assert doc["project_id"] == project_id
    assert doc["id"]
    assert len(doc["content"]) > 0


async def test_store_as_document_false_skips_document(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(
        client, project_id, "spec.md", b"# Bot spec", store_as_document=False
    )
    assert resp.status_code == 201
    assert resp.json()["document"] is None


async def test_md_document_kind_is_markdown(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(client, project_id, "spec.md", b"# Markdown")
    assert resp.json()["document"]["kind"] == "MARKDOWN"


async def test_markdown_extension_document_kind_is_markdown(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(client, project_id, "spec.markdown", b"# Markdown ext")
    assert resp.json()["document"]["kind"] == "MARKDOWN"


async def test_txt_document_kind_is_raw_text(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(client, project_id, "notes.txt", b"Plain text")
    assert resp.json()["document"]["kind"] == "RAW_TEXT"


async def test_custom_title_overrides_filename_stem(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(
        client, project_id, "spec.md", b"# Content", title="My Custom Title"
    )
    assert resp.json()["document"]["title"] == "My Custom Title"


async def test_default_title_uses_filename_stem(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(client, project_id, "project-spec.md", b"# Content")
    assert resp.json()["document"]["title"] == "project-spec"


async def test_response_shape_has_all_fields(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(client, project_id, "notes.txt", b"hello")
    data = resp.json()
    assert "uploaded_file" in data
    assert "extracted_text" in data
    assert "document" in data


async def test_uploaded_file_storage_path_includes_project_id(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _upload(client, project_id, "notes.txt", b"hello")
    assert project_id in resp.json()["uploaded_file"]["storage_path"]


async def test_size_bytes_matches_actual_content_length(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    content = b"exactly twenty bytes"
    resp = await _upload(client, project_id, "notes.txt", content)
    assert resp.json()["uploaded_file"]["size_bytes"] == len(content)


async def test_two_uploads_to_same_project_both_stored(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp1 = await _upload(client, project_id, "a.txt", b"first")
    resp2 = await _upload(client, project_id, "b.md", b"second")
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    id1 = resp1.json()["uploaded_file"]["id"]
    id2 = resp2.json()["uploaded_file"]["id"]
    assert id1 != id2


async def test_upload_does_not_change_project_status(client: AsyncClient) -> None:
    """Upload should not auto-transition project status."""
    project_id = await _create_project(client)
    await _upload(client, project_id, "spec.md", b"# Spec")
    resp = await client.get(f"/projects/{project_id}")
    assert resp.json()["status"] == "DRAFT_CREATED"
