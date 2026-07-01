import py_compile
from pathlib import Path

import yaml

from app.generator import GeneratorCore
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_blueprint() -> BotBlueprint:
    with open(FIXTURES / "endpoint_wiring.yaml") as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


def _run(tmp_path: Path) -> Path:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(_load_blueprint(), output_dir)
    return output_dir


def _endpoints_content(output_dir: Path) -> str:
    return (output_dir / "backend/app/api/routes/endpoints.py").read_text()


def _service_content(output_dir: Path) -> str:
    return (output_dir / "backend/app/services/blueprint_service.py").read_text()


def test_generated_endpoint_with_body_accepts_body_and_passes_to_service(
    tmp_path: Path,
) -> None:
    content = _endpoints_content(_run(tmp_path))

    assert (
        "async def create_item(body: dict[str, Any], "
        "current_user: Annotated[dict[str, Any], Depends(get_current_user)], "
        '_rbac: Annotated[None, Depends(require_roles(["member", "admin"]))], '
        "db: AsyncSession = Depends(get_db)) -> Any:"
    ) in content
    assert "return await ItemService().create_item(body, current_user, db)" in content


def test_generated_endpoint_with_path_param_passes_path_param_to_service(
    tmp_path: Path,
) -> None:
    content = _endpoints_content(_run(tmp_path))

    assert "async def get_item(item_id: str," in content
    assert "return await ItemService().get_item(item_id, current_user, db)" in content


def test_generated_endpoint_with_body_and_path_params_passes_all_to_service(
    tmp_path: Path,
) -> None:
    content = _endpoints_content(_run(tmp_path))

    assert "async def update_item(item_id: str, body: dict[str, Any]," in content
    assert "return await ItemService().update_item(item_id, body, current_user, db)" in content


def test_generated_public_endpoint_has_no_auth_but_passes_db(tmp_path: Path) -> None:
    content = _endpoints_content(_run(tmp_path))

    assert "async def public_ping(db: AsyncSession = Depends(get_db)) -> Any:" in content
    assert "return await svc_public_ping(db)" in content
    public_block = content.split("async def public_ping", 1)[1].split("@router.", 1)[0]
    assert "get_current_user" not in public_block
    assert "require_roles" not in public_block


def test_generated_admin_audit_endpoint_keeps_rbac_and_audit(tmp_path: Path) -> None:
    content = _endpoints_content(_run(tmp_path))

    assert '@router.delete("/api/v1/admin/items/{item_id}")' in content
    assert '_rbac: Annotated[None, Depends(require_roles(["admin"]))]' in content
    assert 'AuditService.log_action(current_user, "admin_delete_item")' in content
    assert "return await ItemService().admin_delete_item(item_id, current_user, db)" in content


def test_generated_service_stubs_have_realistic_signatures(tmp_path: Path) -> None:
    content = _service_content(_run(tmp_path))

    assert "async def svc_public_ping(db: AsyncSession) -> Any:" in content
    assert (
        "async def create_item("
        "self, body: dict[str, Any], current_user: dict[str, Any], db: AsyncSession"
        ") -> Any:"
    ) in content
    assert (
        "async def get_item("
        "self, item_id: str, current_user: dict[str, Any], db: AsyncSession"
        ") -> Any:"
    ) in content
    assert (
        "async def update_item("
        "self, item_id: str, body: dict[str, Any], "
        "current_user: dict[str, Any], db: AsyncSession"
        ") -> Any:"
    ) in content
    assert (
        "async def admin_delete_item("
        "self, item_id: str, current_user: dict[str, Any], db: AsyncSession"
        ") -> Any:"
    ) in content


def test_generated_endpoint_wiring_python_files_compile(tmp_path: Path) -> None:
    output_dir = _run(tmp_path)

    for py_file in sorted((output_dir / "backend").rglob("*.py")):
        py_compile.compile(str(py_file), doraise=True)
