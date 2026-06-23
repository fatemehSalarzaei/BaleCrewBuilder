"""Tests for Phase 7: Frontend Mini App/Web Panel generated templates."""
from pathlib import Path

import pytest
import yaml

from app.generator import GeneratorCore
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"

_EXPECTED_FRONTEND_FILES = [
    "frontend/package.json",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    "frontend/index.html",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
    "frontend/src/lib/api-client.ts",
    "frontend/src/lib/bale-miniapp-auth.ts",
    "frontend/src/pages/WebPanel.tsx",
    # Phase 7b additions:
    "frontend/src/components/AdminGuard.tsx",
    "frontend/src/hooks/useApi.ts",
    "frontend/tests/frontend.test.ts",
]


def _load_blueprint() -> BotBlueprint:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


def _run(tmp_path: Path) -> tuple[Path, list[str]]:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)
    return output_dir, result.generated_files


# ── Frontend skeleton ─────────────────────────────────────────────────────────


def test_frontend_skeleton_all_files_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    for rel_path in _EXPECTED_FRONTEND_FILES:
        assert rel_path in generated, f"Missing frontend file: {rel_path}"
        assert (output_dir / rel_path).exists(), f"File not on disk: {rel_path}"


def test_frontend_package_json_has_project_slug(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/package.json").read_text()
    assert blueprint.project.slug in content, (
        f"package.json must reference project slug '{blueprint.project.slug}'"
    )


def test_frontend_package_json_has_project_name(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/package.json").read_text()
    assert blueprint.project.name in content, (
        f"package.json must reference project name '{blueprint.project.name}'"
    )


def test_frontend_package_json_has_react_dependency(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/package.json").read_text()
    assert '"react"' in content, "package.json must have react dependency"
    assert "react-router-dom" in content, "package.json must have react-router-dom dependency"


def test_frontend_tsconfig_has_jsx_react(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/tsconfig.json").read_text()
    assert "react-jsx" in content, "tsconfig.json must set jsx to react-jsx"
    assert "strict" in content, "tsconfig.json must enable strict mode"


def test_frontend_index_html_has_project_name(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/index.html").read_text()
    assert blueprint.project.name in content, (
        "index.html title must contain project name"
    )
    assert 'id="root"' in content, "index.html must have a #root element"


def test_frontend_main_tsx_has_project_slug(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/main.tsx").read_text()
    assert blueprint.project.slug in content, (
        "main.tsx must reference project slug"
    )


# ── App.tsx — Blueprint-driven routes ─────────────────────────────────────────


def test_app_tsx_has_blueprint_routes(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/App.tsx").read_text()
    for route in blueprint.miniapp.routes:
        assert route.path in content, (
            f"App.tsx must include route '{route.path}' from Blueprint"
        )


def test_app_tsx_has_miniapp_auth_endpoint_comment(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/App.tsx").read_text()
    assert blueprint.miniapp.auth_endpoint in content, (
        "App.tsx must reference the miniapp auth endpoint from Blueprint"
    )


def test_app_tsx_has_fallback_route(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/App.tsx").read_text()
    assert 'path="*"' in content, "App.tsx must have a fallback catch-all route"


def test_app_tsx_imports_admin_guard(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/App.tsx").read_text()
    assert "AdminGuard" in content, "App.tsx must import AdminGuard for admin route protection"


def test_app_tsx_imports_page_components(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/App.tsx").read_text()
    assert "UserDashboardPage" in content, "App.tsx must import UserDashboardPage"
    assert "AdminDashboardPage" in content, "App.tsx must import AdminDashboardPage"


def test_app_tsx_wraps_admin_routes_with_admin_guard(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/App.tsx").read_text()
    # Admin route /admin/dashboard must be wrapped with AdminGuard
    assert "AdminGuard" in content and "AdminDashboardPage" in content, (
        "Admin routes must use AdminGuard element wrapper in App.tsx"
    )
    # Verify AdminGuard wraps AdminDashboardPage (appears before it on same line or nearby)
    admin_guard_pos = content.find("AdminGuard")
    admin_page_pos = content.find("AdminDashboardPage")
    assert admin_guard_pos < admin_page_pos, (
        "AdminGuard must appear before AdminDashboardPage in App.tsx (wrapping it)"
    )


def test_app_tsx_does_not_wrap_user_routes_with_admin_guard(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/App.tsx").read_text()
    # Find the user route line — should not have AdminGuard on it
    lines = content.splitlines()
    for line in lines:
        if "UserDashboardPage" in line and "/user/dashboard" not in line:
            # It's the Route element line — must not contain AdminGuard
            assert "AdminGuard" not in line, (
                f"User route line must not be wrapped with AdminGuard: {line!r}"
            )


# ── Mini App auth bootstrap ───────────────────────────────────────────────────


def test_miniapp_auth_file_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "frontend/src/lib/bale-miniapp-auth.ts" in generated
    assert (output_dir / "frontend/src/lib/bale-miniapp-auth.ts").exists()


def test_miniapp_auth_sends_raw_init_data(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/lib/bale-miniapp-auth.ts").read_text()
    # Must use raw initData, not initDataUnsafe
    assert "initData" in content, "Auth file must reference initData"
    # Must send init_data field to backend
    assert "init_data" in content, (
        "Auth file must send 'init_data' field in the request body"
    )
    # Must actually call fetch/POST to the backend
    assert 'method: "POST"' in content, (
        "Auth file must POST raw initData to the backend"
    )


def test_miniapp_auth_uses_blueprint_auth_endpoint(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/lib/bale-miniapp-auth.ts").read_text()
    assert blueprint.miniapp.auth_endpoint in content, (
        f"Auth file must use Blueprint auth_endpoint '{blueprint.miniapp.auth_endpoint}'"
    )


def test_miniapp_auth_does_not_validate_hmac(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/lib/bale-miniapp-auth.ts").read_text()
    # Ensure no HMAC computation in frontend
    assert "hmac" not in content.lower() or "hmac" in content.lower() and "backend" in content.lower(), (
        "Auth file must not perform HMAC validation — that belongs on the backend"
    )
    # More specific: no crypto/hmac imports
    assert "crypto" not in content.lower(), (
        "Auth file must not import crypto — HMAC validation is backend-only"
    )
    assert "createHmac" not in content and "computeHmac" not in content, (
        "Auth file must not compute HMAC locally"
    )


def test_miniapp_auth_does_not_use_init_data_unsafe(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/lib/bale-miniapp-auth.ts").read_text()
    # initDataUnsafe may be declared as a type but must not be sent to backend
    assert "init_data_unsafe" not in content, (
        "Auth file must not send initDataUnsafe to backend — use raw initData only"
    )


def test_miniapp_auth_has_is_running_in_bale_helper(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/lib/bale-miniapp-auth.ts").read_text()
    assert "isRunningInBale" in content, (
        "Auth file must export isRunningInBale() helper"
    )


# ── API client ────────────────────────────────────────────────────────────────


def test_api_client_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "frontend/src/lib/api-client.ts" in generated
    assert (output_dir / "frontend/src/lib/api-client.ts").exists()


def test_api_client_has_blueprint_endpoint_functions(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/lib/api-client.ts").read_text()
    for endpoint in blueprint.api.endpoints:
        assert f"function {endpoint.name}" in content, (
            f"api-client.ts must export function '{endpoint.name}' for Blueprint endpoint"
        )


def test_api_client_uses_bearer_token(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/lib/api-client.ts").read_text()
    assert "Bearer" in content, (
        "api-client.ts must attach a Bearer token to authenticated requests"
    )
    assert "Authorization" in content, (
        "api-client.ts must set the Authorization header"
    )


def test_api_client_uses_project_slug_for_token_key(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/lib/api-client.ts").read_text()
    assert blueprint.project.slug in content, (
        "api-client.ts must use project slug in the token storage key"
    )


def test_api_client_has_vite_env_base_url(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/lib/api-client.ts").read_text()
    assert "VITE_API_BASE_URL" in content, (
        "api-client.ts must read API base URL from VITE_API_BASE_URL env var"
    )


def test_api_client_has_set_and_clear_token_functions(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/lib/api-client.ts").read_text()
    assert "setAccessToken" in content, "api-client.ts must export setAccessToken()"
    assert "getAccessToken" in content, "api-client.ts must export getAccessToken()"
    assert "clearAccessToken" in content, "api-client.ts must export clearAccessToken()"


# ── Web panel placeholder ─────────────────────────────────────────────────────


def test_web_panel_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "frontend/src/pages/WebPanel.tsx" in generated
    assert (output_dir / "frontend/src/pages/WebPanel.tsx").exists()


def test_web_panel_handles_bale_mode(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/pages/WebPanel.tsx").read_text()
    assert "isRunningInBale" in content, (
        "WebPanel must call isRunningInBale() to detect Bale WebView"
    )
    assert "authenticateWithBale" in content, (
        "WebPanel must call authenticateWithBale() when in Bale mode"
    )


def test_web_panel_handles_web_panel_mode(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/pages/WebPanel.tsx").read_text()
    assert "web panel" in content.lower() or "WebPanel" in content, (
        "WebPanel must include web panel mode handling"
    )


def test_web_panel_has_project_name(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/pages/WebPanel.tsx").read_text()
    assert blueprint.project.name in content, (
        "WebPanel must reference project name"
    )


def test_web_panel_stores_token_via_api_client(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/pages/WebPanel.tsx").read_text()
    assert "setAccessToken" in content, (
        "WebPanel must store the auth token via api-client setAccessToken()"
    )


# ── Manifest includes frontend ────────────────────────────────────────────────


def test_manifest_includes_frontend_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(_load_blueprint(), output_dir)

    for rel_path in _EXPECTED_FRONTEND_FILES:
        assert rel_path in result.generated_files, (
            f"Manifest must include frontend file: {rel_path}"
        )


# ── Determinism ───────────────────────────────────────────────────────────────


def test_same_blueprint_produces_stable_frontend_file_list(tmp_path: Path) -> None:
    blueprint = _load_blueprint()

    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = GeneratorCore().run(blueprint, out1)

    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = GeneratorCore().run(blueprint, out2)

    frontend1 = sorted(f for f in result1.generated_files if f.startswith("frontend/"))
    frontend2 = sorted(f for f in result2.generated_files if f.startswith("frontend/"))
    assert frontend1 == frontend2, "Same Blueprint must produce identical frontend file list"


def test_same_blueprint_produces_stable_frontend_content(tmp_path: Path) -> None:
    blueprint = _load_blueprint()

    out1 = tmp_path / "run1"
    out1.mkdir()
    GeneratorCore().run(blueprint, out1)

    out2 = tmp_path / "run2"
    out2.mkdir()
    GeneratorCore().run(blueprint, out2)

    for rel_path in _EXPECTED_FRONTEND_FILES:
        content1 = (out1 / rel_path).read_text()
        content2 = (out2 / rel_path).read_text()
        assert content1 == content2, (
            f"Same Blueprint must produce identical content for {rel_path}"
        )


# ── No forbidden domains ──────────────────────────────────────────────────────


FORBIDDEN_DOMAINS = {"ticket", "appointment", "crm", "support_ticket"}


def test_no_forbidden_domain_in_frontend_files(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    frontend_dir = output_dir / "frontend"
    for f in sorted(frontend_dir.rglob("*")):
        if not f.is_file():
            continue
        content = f.read_text().lower()
        for domain in FORBIDDEN_DOMAINS:
            assert domain not in content, (
                f"Forbidden domain keyword '{domain}' found in {f.relative_to(output_dir)}"
            )


# ── Per-route page generation ─────────────────────────────────────────────────


def test_per_route_pages_are_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "frontend/src/pages/UserDashboardPage.tsx" in generated, (
        "UserDashboardPage.tsx must be generated for /user/dashboard route"
    )
    assert "frontend/src/pages/AdminDashboardPage.tsx" in generated, (
        "AdminDashboardPage.tsx must be generated for /admin/dashboard route"
    )
    assert (output_dir / "frontend/src/pages/UserDashboardPage.tsx").exists()
    assert (output_dir / "frontend/src/pages/AdminDashboardPage.tsx").exists()


def test_per_route_pages_have_correct_component_names(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    user_page = (output_dir / "frontend/src/pages/UserDashboardPage.tsx").read_text()
    admin_page = (output_dir / "frontend/src/pages/AdminDashboardPage.tsx").read_text()
    assert "function UserDashboardPage" in user_page, (
        "UserDashboardPage.tsx must export function UserDashboardPage"
    )
    assert "function AdminDashboardPage" in admin_page, (
        "AdminDashboardPage.tsx must export function AdminDashboardPage"
    )


def test_per_route_pages_reference_route_path(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    user_page = (output_dir / "frontend/src/pages/UserDashboardPage.tsx").read_text()
    admin_page = (output_dir / "frontend/src/pages/AdminDashboardPage.tsx").read_text()
    assert "/user/dashboard" in user_page, (
        "UserDashboardPage must include data-route='/user/dashboard'"
    )
    assert "/admin/dashboard" in admin_page, (
        "AdminDashboardPage must include data-route='/admin/dashboard'"
    )


def test_per_route_pages_reference_api_dependencies(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    user_page = (output_dir / "frontend/src/pages/UserDashboardPage.tsx").read_text()
    admin_page = (output_dir / "frontend/src/pages/AdminDashboardPage.tsx").read_text()
    assert "get_member_dashboard" in user_page, (
        "UserDashboardPage must mention its api_dependencies from Blueprint"
    )
    assert "get_admin_dashboard" in admin_page, (
        "AdminDashboardPage must mention its api_dependencies from Blueprint"
    )


def test_admin_route_pages_marked_admin_only(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    admin_page = (output_dir / "frontend/src/pages/AdminDashboardPage.tsx").read_text()
    assert "Admin only:      True" in admin_page or "Admin only: True" in admin_page, (
        "AdminDashboardPage must have 'Admin only: True' in its header comment"
    )


def test_non_admin_route_pages_not_marked_admin_only(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    user_page = (output_dir / "frontend/src/pages/UserDashboardPage.tsx").read_text()
    assert "Admin only:      False" in user_page or "Admin only: False" in user_page, (
        "UserDashboardPage must have 'Admin only: False' in its header comment"
    )


def test_per_route_pages_not_in_static_expected_list(tmp_path: Path) -> None:
    """Per-route pages are dynamic — not in _EXPECTED_FRONTEND_FILES but must exist."""
    output_dir, generated = _run(tmp_path)
    dynamic_pages = [
        f for f in generated
        if f.startswith("frontend/src/pages/") and f not in _EXPECTED_FRONTEND_FILES
    ]
    assert len(dynamic_pages) >= 2, (
        "At least 2 dynamic per-route page files must be generated (one per Blueprint route)"
    )


# ── AdminGuard component ──────────────────────────────────────────────────────


def test_admin_guard_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "frontend/src/components/AdminGuard.tsx" in generated
    assert (output_dir / "frontend/src/components/AdminGuard.tsx").exists()


def test_admin_guard_has_role_check(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/components/AdminGuard.tsx").read_text()
    assert "hasAdminRole" in content, "AdminGuard must define a hasAdminRole() stub function"
    assert "permitted" in content, (
        "AdminGuard must use a permitted state to control rendering"
    )


def test_admin_guard_references_blueprint_admin_roles(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/components/AdminGuard.tsx").read_text()
    # Blueprint admin role key is "admin"
    assert "admin" in content, (
        "AdminGuard must reference Blueprint admin role keys (e.g. 'admin')"
    )


def test_admin_guard_shows_access_denied_for_non_admin(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/components/AdminGuard.tsx").read_text()
    assert "access-denied" in content or "Access Denied" in content, (
        "AdminGuard must render an access-denied message for non-admin users"
    )


def test_admin_guard_renders_children_for_admin(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/components/AdminGuard.tsx").read_text()
    assert "children" in content, (
        "AdminGuard must accept and render children for permitted admin users"
    )


# ── API hooks ─────────────────────────────────────────────────────────────────


def test_api_hooks_file_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "frontend/src/hooks/useApi.ts" in generated
    assert (output_dir / "frontend/src/hooks/useApi.ts").exists()


def test_api_hooks_has_hook_per_endpoint(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/hooks/useApi.ts").read_text()
    # pascal_case names for each endpoint
    expected_hooks = {
        "useHealthCheck",
        "useBaleMiniappAuth",
        "useGetMemberDashboard",
        "useListResources",
        "useGetAdminDashboard",
        "useCreateResource",
        "useDeleteResource",
    }
    for hook in expected_hooks:
        assert f"function {hook}" in content, (
            f"useApi.ts must export {hook}() hook for Blueprint endpoint"
        )


def test_api_hooks_get_endpoints_have_fetch_function(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/hooks/useApi.ts").read_text()
    # GET endpoints must return { data, loading, error, fetch }
    assert "useHealthCheck" in content
    # The fetch pattern: state + fetch callback
    assert "return { ...state, fetch }" in content, (
        "GET hooks must return { ...state, fetch } shape"
    )


def test_api_hooks_mutation_endpoints_have_execute_function(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/hooks/useApi.ts").read_text()
    # Non-GET endpoints must return { loading, error, execute }
    assert "return { loading, error, execute }" in content, (
        "Mutation hooks must return { loading, error, execute } shape"
    )


def test_api_hooks_reflect_auth_requirement(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/src/hooks/useApi.ts").read_text()
    # Each hook's JSDoc comment includes "Auth required: True/False"
    assert "Auth required: True" in content, (
        "useApi.ts must document auth_required: True for authenticated endpoints"
    )
    assert "Auth required: False" in content, (
        "useApi.ts must document auth_required: False for public endpoints"
    )


def test_api_hooks_reference_endpoint_paths(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/hooks/useApi.ts").read_text()
    for endpoint in blueprint.api.endpoints:
        assert endpoint.path in content, (
            f"useApi.ts must reference path '{endpoint.path}' for {endpoint.name} hook"
        )


def test_api_hooks_import_all_api_client_functions(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "frontend/src/hooks/useApi.ts").read_text()
    for endpoint in blueprint.api.endpoints:
        assert endpoint.name in content, (
            f"useApi.ts must import '{endpoint.name}' from api-client"
        )


# ── Frontend test stubs ───────────────────────────────────────────────────────


def test_frontend_test_stubs_are_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "frontend/tests/frontend.test.ts" in generated
    assert (output_dir / "frontend/tests/frontend.test.ts").exists()


def test_frontend_test_stubs_reference_all_routes(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/tests/frontend.test.ts").read_text()
    assert "UserDashboardPage" in content, (
        "frontend.test.ts must have stubs for UserDashboardPage route"
    )
    assert "AdminDashboardPage" in content, (
        "frontend.test.ts must have stubs for AdminDashboardPage route"
    )


def test_frontend_test_stubs_reference_all_hooks(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/tests/frontend.test.ts").read_text()
    expected_hooks = [
        "useHealthCheck",
        "useBaleMiniappAuth",
        "useGetMemberDashboard",
        "useListResources",
        "useGetAdminDashboard",
        "useCreateResource",
        "useDeleteResource",
    ]
    for hook in expected_hooks:
        assert hook in content, (
            f"frontend.test.ts must have a stub for {hook} hook"
        )


def test_frontend_test_stubs_use_it_todo(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/tests/frontend.test.ts").read_text()
    assert "it.todo(" in content, (
        "frontend.test.ts must use it.todo() stubs (not implemented tests)"
    )


def test_frontend_test_stubs_have_admin_guard_section(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/tests/frontend.test.ts").read_text()
    assert "AdminGuard" in content, (
        "frontend.test.ts must include AdminGuard test stubs"
    )
    assert "Admin routes are wrapped with AdminGuard" in content, (
        "frontend.test.ts must include admin guard route wrapping stub (has_admin_routes=True)"
    )


def test_frontend_test_stubs_have_miniapp_auth_section(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/tests/frontend.test.ts").read_text()
    assert "initData" in content, (
        "frontend.test.ts must include Mini App auth stubs referencing initData"
    )
    assert "HMAC" in content, (
        "frontend.test.ts must include stub asserting frontend never validates HMAC"
    )
