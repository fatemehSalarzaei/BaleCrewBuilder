import re
from typing import Any

from app.generator.renderer import Renderer


def _route_to_component_name(path: str) -> str:
    """"/user/dashboard" → "UserDashboardPage"; handles hyphens and underscores."""
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return "HomePage"
    result = ""
    for part in parts:
        sub_parts = re.split(r"[-_]", part)
        result += "".join(sp.capitalize() for sp in sub_parts if sp)
    return result + "Page"


def _is_admin_only(route: dict[str, Any], admin_role_keys: set[str]) -> bool:
    roles = route.get("allowed_roles", [])
    return bool(roles) and all(r in admin_role_keys for r in roles)


# Static templates — rendered once per generation run.
_STATIC_FRONTEND_TEMPLATES: list[tuple[str, str]] = [
    ("frontend/package.json.j2", "frontend/package.json"),
    ("frontend/tsconfig.json.j2", "frontend/tsconfig.json"),
    ("frontend/vite.config.ts.j2", "frontend/vite.config.ts"),
    ("frontend/index.html.j2", "frontend/index.html"),
    ("frontend/src/main.tsx.j2", "frontend/src/main.tsx"),
    ("frontend/src/App.tsx.j2", "frontend/src/App.tsx"),
    ("frontend/src/lib/api-client.ts.j2", "frontend/src/lib/api-client.ts"),
    ("frontend/src/lib/bale-miniapp-auth.ts.j2", "frontend/src/lib/bale-miniapp-auth.ts"),
    ("frontend/src/pages/WebPanel.tsx.j2", "frontend/src/pages/WebPanel.tsx"),
    ("frontend/src/components/AdminGuard.tsx.j2", "frontend/src/components/AdminGuard.tsx"),
    ("frontend/src/hooks/useApi.ts.j2", "frontend/src/hooks/useApi.ts"),
    ("frontend/tests/frontend.test.ts.j2", "frontend/tests/frontend.test.ts"),
]

# Per-route template — rendered once per Blueprint miniapp.route.
_PAGE_TEMPLATE = "frontend/src/pages/page.tsx.j2"
_PAGE_OUTPUT_PATTERN = "frontend/src/pages/{component_name}.tsx"


class FrontendModule:
    def generate_pre_manifest(self, renderer: Renderer, context: dict[str, Any]) -> list[str]:
        generated: list[str] = []

        admin_role_keys: set[str] = {
            r["key"] for r in context["roles"] if r.get("is_admin", False)
        }
        routes_with_meta: list[dict[str, Any]] = [
            {
                **route,
                "component_name": _route_to_component_name(route["path"]),
                "is_admin_only": _is_admin_only(route, admin_role_keys),
            }
            for route in context["miniapp"]["routes"]
        ]
        enriched: dict[str, Any] = {
            **context,
            "routes_with_meta": routes_with_meta,
            "admin_role_keys": sorted(admin_role_keys),
            "has_admin_routes": any(r["is_admin_only"] for r in routes_with_meta),
        }

        for template_name, output_path in _STATIC_FRONTEND_TEMPLATES:
            renderer.render_template(template_name, output_path, enriched)
            generated.append(output_path)

        for route in routes_with_meta:
            route_context = {**enriched, "route": route}
            output_path = _PAGE_OUTPUT_PATTERN.format(component_name=route["component_name"])
            renderer.render_template(_PAGE_TEMPLATE, output_path, route_context)
            generated.append(output_path)

        return generated
