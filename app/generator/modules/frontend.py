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


def _singular(value: str) -> str:
    if value.endswith("ies"):
        return value[:-3] + "y"
    if value.endswith("s") and not value.endswith("ss"):
        return value[:-1]
    return value


def _humanize(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[_\-\s]+", value) if part)


def _pascal_case(value: str) -> str:
    return "".join(part.capitalize() for part in value.split("_") if part)


def _input_type(field_type: str) -> str:
    normalized = field_type.lower()
    if normalized in {"integer", "float"}:
        return "number"
    if normalized == "boolean":
        return "checkbox"
    if normalized == "datetime":
        return "datetime-local"
    return "text"


def _field_meta(field: dict[str, Any]) -> dict[str, Any]:
    return {
        **field,
        "label": _humanize(field["name"]),
        "input_type": _input_type(field.get("type", "string")),
        "is_editable": not field.get("primary_key", False),
    }


def _dependency_key(raw_dependency: str) -> str:
    stripped = raw_dependency.strip()
    if " " in stripped:
        return stripped.rsplit(" ", maxsplit=1)[-1]
    return stripped


def _endpoint_matches_dependency(endpoint: dict[str, Any], dependency: str) -> bool:
    key = _dependency_key(dependency)
    method_path = f"{endpoint['method']} {endpoint['path']}"
    return key in {endpoint["name"], endpoint["path"], method_path}


def _endpoint_meta(endpoint: dict[str, Any]) -> dict[str, Any]:
    return {
        **endpoint,
        "hook_name": f"use{_pascal_case(endpoint['name'])}",
        "is_query": endpoint["method"] == "GET",
        "is_mutation": endpoint["method"] != "GET",
    }


def _infer_entity(
    route: dict[str, Any],
    dependencies: list[dict[str, Any]],
    entities: list[dict[str, Any]],
) -> dict[str, Any] | None:
    haystack = " ".join(
        [
            route["path"],
            *route.get("api_dependencies", []),
            *(dep["name"] for dep in dependencies),
            *(dep["path"] for dep in dependencies),
            *(dep.get("service_method", "") for dep in dependencies),
        ]
    ).lower()

    best: dict[str, Any] | None = None
    best_score = 0
    for entity in entities:
        names = {
            entity["name"].lower(),
            entity["table_name"].lower(),
            _singular(entity["name"].lower()),
            _singular(entity["table_name"].lower()),
        }
        score = sum(1 for name in names if name and name in haystack)
        if score > best_score:
            best = entity
            best_score = score
    return best


def _enrich_route(
    route: dict[str, Any],
    *,
    admin_role_keys: set[str],
    entities: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
) -> dict[str, Any]:
    dependencies = [
        _endpoint_meta(endpoint)
        for dependency in route.get("api_dependencies", [])
        for endpoint in endpoints
        if _endpoint_matches_dependency(endpoint, dependency)
    ]
    entity = _infer_entity(route, dependencies, entities)
    fields = [_field_meta(field) for field in entity.get("fields", [])] if entity else []
    editable_fields = [field for field in fields if field["is_editable"]]
    query_dependencies = [dep for dep in dependencies if dep["is_query"]]
    mutation_dependencies = [dep for dep in dependencies if dep["is_mutation"]]

    return {
        **route,
        "component_name": _route_to_component_name(route["path"]),
        "is_admin_only": _is_admin_only(route, admin_role_keys),
        "api_dependency_specs": dependencies,
        "query_dependencies": query_dependencies,
        "mutation_dependencies": mutation_dependencies,
        "primary_query": query_dependencies[0] if query_dependencies else None,
        "primary_mutation": mutation_dependencies[0] if mutation_dependencies else None,
        "entity": entity,
        "entity_name": entity["name"] if entity else None,
        "entity_title": _humanize(entity["name"]) if entity else "Record",
        "fields": fields,
        "editable_fields": editable_fields,
        "display_fields": fields[:6],
    }


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
            _enrich_route(
                route,
                admin_role_keys=admin_role_keys,
                entities=context["entities"],
                endpoints=context["api_endpoints"],
            )
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
