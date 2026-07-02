"""Tests for Phase 7: Backend Generated Project Templates."""
import py_compile
from pathlib import Path

import pytest
import yaml

from app.generator import GeneratorCore
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"

FORBIDDEN_DOMAINS = {"ticket", "appointment", "crm", "support_ticket"}

_CORE_BACKEND_FILES = [
    "backend/requirements.txt",
    "backend/alembic.ini",
    "backend/app/main.py",
    "backend/app/core/config.py",
    "backend/app/core/security.py",
    "backend/app/db/base.py",
    "backend/app/db/session.py",
    "backend/app/db/migrations/env.py",
    "backend/app/db/migrations/script.py.mako",
    "backend/app/db/migrations/versions/.gitkeep",
    "backend/app/api/deps.py",
    "backend/app/api/router.py",
    "backend/app/services/auth_service.py",
    "backend/app/services/audit_service.py",
    "backend/app/services/blueprint_service.py",
]

_CORE_INIT_FILES = [
    "backend/__init__.py",
    "backend/app/__init__.py",
    "backend/app/core/__init__.py",
    "backend/app/db/__init__.py",
    "backend/app/api/__init__.py",
    "backend/app/api/routes/__init__.py",
    "backend/app/models/__init__.py",
    "backend/app/schemas/__init__.py",
    "backend/app/services/__init__.py",
    "backend/tests/__init__.py",
]


def _load_blueprint() -> BotBlueprint:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


def _run(tmp_path: Path) -> tuple[GeneratorCore, list[str]]:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)
    return output_dir, result.generated_files


# ── Core backend files ────────────────────────────────────────────────────────


def test_core_backend_files_are_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    for rel_path in _CORE_BACKEND_FILES:
        assert rel_path in generated, f"Missing core backend file: {rel_path}"
        assert (output_dir / rel_path).exists()


def test_backend_init_files_are_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    for rel_path in _CORE_INIT_FILES:
        assert rel_path in generated, f"Missing __init__.py: {rel_path}"
        assert (output_dir / rel_path).exists()


# ── Per-entity file generation ────────────────────────────────────────────────


def test_per_entity_model_files_are_generated(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    for entity in blueprint.database.entities:
        expected = f"backend/app/models/{entity.name}.py"
        assert expected in result.generated_files, f"Missing model: {expected}"
        assert (output_dir / expected).exists()


def test_per_entity_schema_files_are_generated(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    for entity in blueprint.database.entities:
        expected = f"backend/app/schemas/{entity.name}.py"
        assert expected in result.generated_files, f"Missing schema: {expected}"
        assert (output_dir / expected).exists()


def test_per_entity_service_files_are_generated(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    for entity in blueprint.database.entities:
        expected = f"backend/app/services/{entity.name}_service.py"
        assert expected in result.generated_files, f"Missing service: {expected}"
        assert (output_dir / expected).exists()


def test_per_entity_route_files_are_generated(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    for entity in blueprint.database.entities:
        expected = f"backend/app/api/routes/{entity.name}.py"
        assert expected in result.generated_files, f"Missing route: {expected}"
        assert (output_dir / expected).exists()


def test_per_entity_test_files_are_generated(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    for entity in blueprint.database.entities:
        expected = f"backend/tests/test_{entity.name}.py"
        assert expected in result.generated_files, f"Missing test: {expected}"
        assert (output_dir / expected).exists()


# ── Content: entity names appear in generated files ───────────────────────────


def test_entity_class_name_appears_in_schema(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for entity in blueprint.database.entities:
        class_name = "".join(w.capitalize() for w in entity.name.split("_"))
        schema_file = output_dir / f"backend/app/schemas/{entity.name}.py"
        content = schema_file.read_text()
        assert class_name in content, (
            f"PascalCase class name '{class_name}' not found in {schema_file.name}"
        )


def test_entity_class_name_appears_in_service(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for entity in blueprint.database.entities:
        class_name = "".join(w.capitalize() for w in entity.name.split("_"))
        svc_file = output_dir / f"backend/app/services/{entity.name}_service.py"
        content = svc_file.read_text()
        assert class_name in content, (
            f"PascalCase class name '{class_name}' not found in {svc_file.name}"
        )


def test_entity_table_name_appears_in_model(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for entity in blueprint.database.entities:
        model_file = output_dir / f"backend/app/models/{entity.name}.py"
        content = model_file.read_text()
        assert entity.table_name in content, (
            f"Table name '{entity.table_name}' not found in {model_file.name}"
        )


# ── Content: blueprint api endpoints reflected in router ──────────────────────


def test_bot_token_env_vars_appear_in_config(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    config_content = (output_dir / "backend/app/core/config.py").read_text()
    for bot in blueprint.bots:
        token_var = bot.token_env.lower()
        assert token_var in config_content, (
            f"Bot token env '{token_var}' not found in config.py"
        )


# ── Alembic scaffold ─────────────────────────────────────────────────────────


def test_generated_backend_includes_alembic_scaffold(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)

    expected = [
        "backend/alembic.ini",
        "backend/app/db/migrations/env.py",
        "backend/app/db/migrations/script.py.mako",
        "backend/app/db/migrations/versions/.gitkeep",
    ]
    for rel_path in expected:
        assert rel_path in generated, f"Missing Alembic scaffold file: {rel_path}"
        assert (output_dir / rel_path).exists()


def test_generated_alembic_ini_points_to_migrations_dir(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)

    content = (output_dir / "backend/alembic.ini").read_text()

    assert "script_location = app/db/migrations" in content


def test_generated_alembic_env_imports_base_metadata_and_models(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/db/migrations/env.py").read_text()

    assert "from app.db.base import Base" in content
    assert "target_metadata = Base.metadata" in content
    for entity in blueprint.database.entities:
        assert f"from app.models import {entity.name}" in content


def test_generated_backend_does_not_include_fake_initial_revision(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)

    generated_revisions = [
        rel_path
        for rel_path in generated
        if rel_path.startswith("backend/app/db/migrations/versions/")
        and rel_path.endswith(".py")
    ]

    assert generated_revisions == ["backend/app/db/migrations/versions/__init__.py"]
    revision_files = [
        path
        for path in (output_dir / "backend/app/db/migrations/versions").glob("*.py")
        if path.name != "__init__.py"
    ]
    assert revision_files == []


def test_generated_deployment_docs_describe_migration_workflow(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)

    assert "docs/deployment.md" in generated
    content = (output_dir / "docs/deployment.md").read_text()

    assert "alembic revision --autogenerate -m \"initial\"" in content
    assert "alembic upgrade head" in content
    assert "disposable database" in content
    assert "does not create a fake initial migration" in content


# ── No hard-coded domain ──────────────────────────────────────────────────────


def test_no_forbidden_domain_in_generated_backend(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    backend_dir = output_dir / "backend"
    for py_file in sorted(backend_dir.rglob("*.py")):
        content = py_file.read_text().lower()
        for domain in FORBIDDEN_DOMAINS:
            assert domain not in content, (
                f"Forbidden domain keyword '{domain}' found in generated file: {py_file.name}"
            )


# ── Determinism ───────────────────────────────────────────────────────────────


def test_same_blueprint_produces_stable_backend_file_list(tmp_path: Path) -> None:
    blueprint = _load_blueprint()

    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = GeneratorCore().run(blueprint, out1)

    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = GeneratorCore().run(blueprint, out2)

    assert result1.generated_files == result2.generated_files


def test_all_backend_files_on_disk_match_manifest(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    for rel_path in generated:
        assert (output_dir / rel_path).exists(), f"File in manifest missing on disk: {rel_path}"


# ── Blueprint API endpoints → endpoints.py ────────────────────────────────────


def test_blueprint_endpoints_file_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "backend/app/api/routes/endpoints.py" in generated
    assert (output_dir / "backend/app/api/routes/endpoints.py").exists()


def test_blueprint_api_endpoint_paths_in_endpoints_file(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    for endpoint in blueprint.api.endpoints:
        assert endpoint.path in content, (
            f"Blueprint endpoint path '{endpoint.path}' not found in endpoints.py"
        )


def test_blueprint_api_endpoint_names_in_endpoints_file(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    for endpoint in blueprint.api.endpoints:
        assert f"async def {endpoint.name}" in content, (
            f"Blueprint endpoint function '{endpoint.name}' not found in endpoints.py"
        )


def test_blueprint_api_endpoint_methods_in_endpoints_file(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    for endpoint in blueprint.api.endpoints:
        assert f"@router.{endpoint.method.lower()}" in content, (
            f"Blueprint endpoint method '@router.{endpoint.method.lower()}' not found in endpoints.py"
        )


def test_router_includes_blueprint_endpoints_router(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/router.py").read_text()
    assert "blueprint_endpoints_router" in content
    assert "from app.api.routes.endpoints import router as blueprint_endpoints_router" in content


def test_router_includes_all_entity_routers(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    router_content = (output_dir / "backend/app/api/router.py").read_text()
    assert "blueprint_endpoints_router" in router_content
    for entity in blueprint.database.entities:
        assert entity.name in router_content, (
            f"Entity '{entity.name}' not referenced in router.py"
        )


# ── Compile safety ────────────────────────────────────────────────────────────


def test_generated_python_files_compile(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    backend_dir = output_dir / "backend"
    for py_file in sorted(backend_dir.rglob("*.py")):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            pytest.fail(f"Syntax error in generated file {py_file.relative_to(output_dir)}: {exc}")


# ── Schema import correctness ─────────────────────────────────────────────────


def test_schema_uses_from_uuid_import_when_entity_has_uuid_fields(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for entity in blueprint.database.entities:
        has_uuid = any(f.type == "uuid" for f in entity.fields)
        schema_file = output_dir / f"backend/app/schemas/{entity.name}.py"
        content = schema_file.read_text()
        if has_uuid:
            assert "from uuid import UUID" in content, (
                f"Entity '{entity.name}' has uuid fields but schema missing 'from uuid import UUID'"
            )
        assert "from __future__ import annotations" not in content, (
            f"Schema for '{entity.name}' must not use 'from __future__ import annotations' (breaks Pydantic v2)"
        )


# ── No-PK entity composite primary key ───────────────────────────────────────


def test_no_pk_entity_model_uses_composite_primary_key(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    no_pk_entities = [
        e for e in blueprint.database.entities
        if not any(f.primary_key for f in e.fields)
    ]
    assert no_pk_entities, "Fixture must have at least one entity without a primary key field"

    for entity in no_pk_entities:
        model_file = output_dir / f"backend/app/models/{entity.name}.py"
        content = model_file.read_text()
        assert "primary_key=True" in content, (
            f"No-PK entity '{entity.name}' model must declare composite primary_key=True"
        )
        assert "Association table" in content, (
            f"No-PK entity '{entity.name}' model should have association table comment"
        )


# ── Phase 5: Auth / RBAC / Audit skeleton generation ─────────────────────────


def test_security_file_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "backend/app/core/security.py" in generated
    assert (output_dir / "backend/app/core/security.py").exists()


def test_auth_service_file_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "backend/app/services/auth_service.py" in generated
    assert (output_dir / "backend/app/services/auth_service.py").exists()


def test_audit_service_file_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "backend/app/services/audit_service.py" in generated
    assert (output_dir / "backend/app/services/audit_service.py").exists()


def test_security_file_has_required_functions(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/core/security.py").read_text()
    for fn in ("verify_password", "get_password_hash", "create_access_token", "decode_access_token"):
        assert fn in content, f"security.py missing function: {fn}"


def test_deps_has_get_current_user(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/deps.py").read_text()
    assert "get_current_user" in content


def test_deps_has_require_roles(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/deps.py").read_text()
    assert "require_roles" in content


def test_deps_has_oauth2_bearer(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/deps.py").read_text()
    assert "OAuth2PasswordBearer" in content


def test_admin_endpoints_include_role_guard(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    assert 'require_roles(["admin"])' in content


def test_auth_endpoints_include_get_current_user(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    assert "Depends(get_current_user)" in content


def test_audit_endpoints_call_audit_service(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    assert "AuditService.log_action" in content


def test_audit_call_includes_current_user(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    assert "AuditService.log_action(current_user," in content


def test_miniapp_auth_endpoint_exists_in_endpoints(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    miniapp_path = blueprint.miniapp.auth_endpoint
    assert miniapp_path, "Fixture must define miniapp.auth_endpoint"
    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    assert miniapp_path in content, (
        f"miniapp.auth_endpoint '{miniapp_path}' not found in endpoints.py"
    )


def test_unauthenticated_endpoints_have_no_current_user(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "async def health_check(" in line or "async def bale_miniapp_auth(" in line:
            assert "get_current_user" not in line, (
                f"Unauthenticated endpoint at line {i + 1} must not have get_current_user"
            )


def test_auth_service_has_authenticate_and_login(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/services/auth_service.py").read_text()
    assert "async def authenticate" in content
    assert "async def login" in content


def test_auth_service_mentions_blueprint_roles(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/services/auth_service.py").read_text()
    for role in blueprint.roles:
        assert role.key in content, (
            f"auth_service.py should reference Blueprint role '{role.key}'"
        )


def test_auth_service_has_miniapp_method_when_enabled(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    assert blueprint.miniapp.enabled, "Fixture must have miniapp.enabled=True"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/services/auth_service.py").read_text()
    assert "verify_miniapp_token" in content


def test_audit_service_has_log_action_method(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/services/audit_service.py").read_text()
    assert "def log_action" in content


def test_audit_service_full_stub_when_audit_enabled(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    assert blueprint.security.audit_log_enabled, "Fixture must have security.audit_log_enabled=True"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/services/audit_service.py").read_text()
    assert "resource_type" in content, "Full audit stub should include resource_type param"


# ── Phase 5: Blueprint service stubs (no raise NotImplementedError in routes) ─


def test_no_raise_not_implemented_in_endpoints_file(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    assert "raise NotImplementedError" not in content, (
        "Generated endpoints.py must not contain 'raise NotImplementedError' — "
        "routes must delegate to service stubs"
    )


def test_blueprint_service_stub_file_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "backend/app/services/blueprint_service.py" in generated, (
        "blueprint_service.py must appear in the generation manifest"
    )
    assert (output_dir / "backend/app/services/blueprint_service.py").exists()


def test_blueprint_service_has_all_service_method_names(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/services/blueprint_service.py").read_text()
    for endpoint in blueprint.api.endpoints:
        sm = endpoint.service_method
        fn = sm.split(".", 1)[-1]  # last segment is always the method/function name
        assert fn in content, (
            f"blueprint_service.py must contain method/function '{fn}' "
            f"derived from service_method '{sm}'"
        )


def test_blueprint_service_uses_http_exception_not_not_implemented(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/services/blueprint_service.py").read_text()
    assert "HTTPException" in content, (
        "blueprint_service.py must raise HTTPException(501) not NotImplementedError"
    )
    assert "status_code=501" in content, (
        "blueprint_service.py must use status_code=501 for placeholder responses"
    )
    assert "raise NotImplementedError" not in content, (
        "blueprint_service.py must not contain raw 'raise NotImplementedError'"
    )


def test_endpoints_import_from_blueprint_service(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    assert "from app.services.blueprint_service import" in content, (
        "endpoints.py must import from blueprint_service"
    )


def test_endpoints_call_service_stubs(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    for endpoint in blueprint.api.endpoints:
        sm = endpoint.service_method
        fn = sm.split(".", 1)[-1]
        assert fn in content, (
            f"endpoints.py must reference service function/method '{fn}' "
            f"from Blueprint endpoint '{endpoint.name}'"
        )


def test_endpoints_use_await_for_service_calls(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    assert "return await " in content, (
        "endpoints.py must use 'return await' to call async service stubs"
    )


def test_audit_required_endpoints_still_call_audit_service_after_refactor(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    audit_endpoints = [ep for ep in blueprint.api.endpoints if ep.audit_required]
    assert audit_endpoints, "Fixture must have at least one audit_required endpoint"
    assert "AuditService.log_action" in content, (
        "endpoints.py must still call AuditService.log_action for audit-required endpoints"
    )
    for ep in audit_endpoints:
        assert ep.name in content, (
            f"Audit-required endpoint '{ep.name}' must appear in endpoints.py"
        )


def test_role_protected_endpoints_still_include_role_guard_after_refactor(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/api/routes/endpoints.py").read_text()
    assert 'require_roles(["admin"])' in content, (
        "Admin-only endpoints must still include require_roles after service stub refactor"
    )


def test_blueprint_service_has_no_forbidden_domain(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/services/blueprint_service.py").read_text().lower()
    for domain in FORBIDDEN_DOMAINS:
        assert domain not in content, (
            f"Forbidden domain keyword '{domain}' found in blueprint_service.py"
        )
