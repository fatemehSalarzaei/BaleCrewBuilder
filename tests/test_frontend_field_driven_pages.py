"""Task 06: field-driven generated frontend pages."""
from pathlib import Path

import yaml

from app.generator import GeneratorCore
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_blueprint() -> BotBlueprint:
    with open(FIXTURES / "frontend_field_pages.yaml") as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


def _run(tmp_path: Path) -> tuple[Path, list[str]]:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(_load_blueprint(), output_dir)
    return output_dir, result.generated_files


def test_list_route_generates_table_markup(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    page = output_dir / "frontend/src/pages/ItemsPage.tsx"

    assert "frontend/src/pages/ItemsPage.tsx" in generated
    content = page.read_text()
    assert "<table>" in content
    assert "<thead>" in content
    assert "<tbody>" in content
    assert "Title" in content
    assert "Summary" in content
    assert "useListItems" in content


def test_form_route_generates_controlled_entity_inputs(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/pages/AdminItemsNewPage.tsx").read_text()

    assert "<form onSubmit={handleSubmit}>" in content
    assert 'name="title"' in content
    assert 'name="summary"' in content
    assert 'name="priority"' in content
    assert 'name="is_active"' in content
    assert 'type="checkbox"' in content
    assert "formState" in content
    assert "setFormState" in content
    assert "useCreateItem" in content


def test_detail_route_generates_detail_layout(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/pages/ItemsDetailPage.tsx").read_text()

    assert 'data-layout="detail"' in content
    assert "<dt>Title</dt>" in content
    assert "<dd>{formatValue(record[\"title\"])}</dd>" in content
    assert "useGetItem" in content


def test_admin_routes_remain_guarded_in_app_router(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/App.tsx").read_text()

    assert (
        '<Route path="/admin/items/new" element={<AdminGuard><AdminItemsNewPage /></AdminGuard>} />'
        in content
    )
    assert (
        '<Route path="/admin/report" element={<AdminGuard><AdminReportPage /></AdminGuard>} />'
        in content
    )


def test_pages_include_loading_error_and_empty_states(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    list_page = (output_dir / "frontend/src/pages/ItemsPage.tsx").read_text()
    detail_page = (output_dir / "frontend/src/pages/ItemsDetailPage.tsx").read_text()
    form_page = (output_dir / "frontend/src/pages/AdminItemsNewPage.tsx").read_text()

    assert 'role="status"' in list_page
    assert 'role="alert"' in list_page
    assert 'data-state="empty"' in list_page
    assert 'role="status"' in detail_page
    assert 'role="alert"' in detail_page
    assert 'data-state="empty"' in detail_page
    assert "submitError" in form_page
    assert "submitting" in form_page


def test_report_route_generates_structured_panels(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/pages/AdminReportPage.tsx").read_text()

    assert 'data-layout="report-panels"' in content
    assert "Connected APIs" in content
    assert "GET /api/v1/admin/items/report via useItemReport" in content


def test_generated_pages_delegate_to_api_hooks_without_direct_fetch(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)

    for page in (
        "ItemsPage.tsx",
        "AdminItemsNewPage.tsx",
        "ItemsDetailPage.tsx",
        "AdminReportPage.tsx",
    ):
        content = (output_dir / f"frontend/src/pages/{page}").read_text()
        assert "../hooks/useApi" in content
        assert "fetch(" not in content
        assert "apiRequest(" not in content
        assert "TODO: implement" not in content
