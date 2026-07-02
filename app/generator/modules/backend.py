import re
from typing import Any

from app.generator.renderer import Renderer


def _pascal_case(snake: str) -> str:
    return "".join(word.capitalize() for word in snake.split("_"))


# Service module names already generated as full implementations — avoid class name conflicts.
_CORE_SERVICE_MODULES: frozenset[str] = frozenset({
    "auth_service",
    "audit_service",
    "miniapp_auth_service",
})


def _service_class_for(module: str) -> str:
    if module in _CORE_SERVICE_MODULES:
        return "Bp" + _pascal_case(module)
    return _pascal_case(module)


def _extract_path_params(path: str) -> list[str]:
    return re.findall(r"\{(\w+)\}", path)


def _roles_repr(roles: list[str]) -> str:
    return "[" + ", ".join(f'"{role}"' for role in roles) + "]"


def _endpoint_signature_parts(ep: dict[str, Any], path_params: list[str]) -> list[str]:
    parts = [f"{param}: str" for param in path_params]

    if ep.get("request_schema"):
        parts.append("body: dict[str, Any]")

    if ep.get("auth_required"):
        parts.append("current_user: Annotated[dict[str, Any], Depends(get_current_user)]")

    allowed_roles = ep.get("allowed_roles") or []
    if allowed_roles:
        roles = _roles_repr(allowed_roles)
        parts.append(f"_rbac: Annotated[None, Depends(require_roles({roles}))]")

    parts.append("db: AsyncSession = Depends(get_db)")
    return parts


def _service_arg_names(ep: dict[str, Any], path_params: list[str]) -> list[str]:
    args = [*path_params]
    if ep.get("request_schema"):
        args.append("body")
    if ep.get("auth_required"):
        args.append("current_user")
    args.append("db")
    return args


def _service_signature_parts(ep: dict[str, Any], path_params: list[str]) -> list[str]:
    parts = [f"{param}: str" for param in path_params]
    if ep.get("request_schema"):
        parts.append("body: dict[str, Any]")
    if ep.get("auth_required"):
        parts.append("current_user: dict[str, Any]")
    parts.append("db: AsyncSession")
    return parts


def _service_method_spec(ep: dict[str, Any], fn: str) -> dict[str, Any]:
    path_params = _extract_path_params(ep.get("path", ""))
    service_arg_names = _service_arg_names(ep, path_params)
    service_signature_parts = _service_signature_parts(ep, path_params)
    return {
        "name": fn,
        "signature": ", ".join(service_signature_parts),
        "unused_tuple": ", ".join(service_arg_names),
    }


def _safe_task_name(raw: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        normalized = "background_action"
    if normalized[0].isdigit():
        normalized = f"task_{normalized}"
    return normalized


def _celery_task_specs(
    flows: list[dict[str, Any]],
    custom_logic_blocks: list[str],
) -> list[dict[str, str]]:
    specs: dict[str, dict[str, str]] = {}
    for flow in flows:
        key = _safe_task_name(flow.get("key") or flow.get("name") or "flow")
        specs.setdefault(key, {
            "name": key,
            "title": flow.get("name") or key.replace("_", " ").title(),
            "source": "Blueprint flow",
        })

    for block in custom_logic_blocks:
        key = _safe_task_name(block)
        specs.setdefault(key, {
            "name": key,
            "title": block.replace("_", " ").title(),
            "source": "Blueprint custom_logic_blocks",
        })

    return list(specs.values())


def _enrich_endpoints(
    raw_endpoints: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Parse service_method on each endpoint and compute blueprint service structure.

    Returns:
        enriched_endpoints: original dicts plus svc_class_name, svc_fn_name, svc_call
        service_classes: list of {class_name, methods} for the blueprint_service template
        bare_fns: list of bare function names (no class prefix)
    """
    enriched: list[dict[str, Any]] = []
    class_methods: dict[str, dict[str, dict[str, Any]]] = {}
    bare_fn_specs: dict[str, dict[str, Any]] = {}
    seen_bare: set[str] = set()

    for ep in raw_endpoints:
        sm: str = ep.get("service_method", "")
        path_params = _extract_path_params(ep.get("path", ""))
        signature_parts = _endpoint_signature_parts(ep, path_params)
        service_arg_names = _service_arg_names(ep, path_params)
        service_args = ", ".join(service_arg_names)
        if "." in sm:
            module, fn = sm.split(".", 1)
            class_name = _service_class_for(module)
            enriched.append({
                **ep,
                "path_params": path_params,
                "signature": ", ".join(signature_parts),
                "service_args": service_args,
                "svc_class_name": class_name,
                "svc_fn_name": fn,
                "svc_is_bare": False,
                "svc_call": f"{class_name}().{fn}({service_args})",
            })
            if class_name not in class_methods:
                class_methods[class_name] = {}
            class_methods[class_name].setdefault(fn, _service_method_spec(ep, fn))
        else:
            fn = sm
            enriched.append({
                **ep,
                "path_params": path_params,
                "signature": ", ".join(signature_parts),
                "service_args": service_args,
                "svc_class_name": None,
                "svc_fn_name": fn,
                "svc_is_bare": True,
                "svc_call": f"svc_{fn}({service_args})",
            })
            if fn not in seen_bare:
                bare_fn_specs[fn] = _service_method_spec(ep, fn)
                seen_bare.add(fn)

    service_classes = [
        {"class_name": cls, "methods": list(methods.values())}
        for cls, methods in class_methods.items()
    ]
    bare_fns = list(bare_fn_specs.values())
    return enriched, service_classes, bare_fns


_PY_TYPES: dict[str, str] = {
    "uuid": "UUID",
    "string": "str",
    "boolean": "bool",
    "datetime": "datetime",
    "json": "dict | None",
    "integer": "int",
    "float": "float",
    "text": "str",
}

_CORE_INIT_PATHS = [
    "backend/__init__.py",
    "backend/app/__init__.py",
    "backend/app/core/__init__.py",
    "backend/app/db/__init__.py",
    "backend/app/db/migrations/__init__.py",
    "backend/app/db/migrations/versions/__init__.py",
    "backend/app/api/__init__.py",
    "backend/app/api/routes/__init__.py",
    "backend/app/models/__init__.py",
    "backend/app/schemas/__init__.py",
    "backend/app/services/__init__.py",
    "backend/tests/__init__.py",
]

_CORE_TEMPLATES: list[tuple[str, str]] = [
    ("backend/requirements.txt.j2", "backend/requirements.txt"),
    ("backend/alembic.ini.j2", "backend/alembic.ini"),
    ("backend/app/main.py.j2", "backend/app/main.py"),
    ("backend/app/core/config.py.j2", "backend/app/core/config.py"),
    ("backend/app/core/security.py.j2", "backend/app/core/security.py"),
    ("backend/app/db/base.py.j2", "backend/app/db/base.py"),
    ("backend/app/db/session.py.j2", "backend/app/db/session.py"),
    ("backend/app/db/migrations/env.py.j2", "backend/app/db/migrations/env.py"),
    (
        "backend/app/db/migrations/versions/.gitkeep.j2",
        "backend/app/db/migrations/versions/.gitkeep",
    ),
    (
        "backend/app/db/migrations/script.py.mako.j2",
        "backend/app/db/migrations/script.py.mako",
    ),
    ("backend/app/api/deps.py.j2", "backend/app/api/deps.py"),
    ("backend/app/api/router.py.j2", "backend/app/api/router.py"),
    ("backend/app/api/routes/endpoints.py.j2", "backend/app/api/routes/endpoints.py"),
    ("backend/app/services/auth_service.py.j2", "backend/app/services/auth_service.py"),
    (
        "backend/app/services/miniapp_auth_service.py.j2",
        "backend/app/services/miniapp_auth_service.py",
    ),
    ("backend/app/services/audit_service.py.j2", "backend/app/services/audit_service.py"),
    ("backend/app/services/blueprint_service.py.j2", "backend/app/services/blueprint_service.py"),
]

_CELERY_INIT_PATHS = [
    "backend/app/workers/__init__.py",
]

_CELERY_TEMPLATES: list[tuple[str, str]] = [
    ("backend/app/workers/celery_app.py.j2", "backend/app/workers/celery_app.py"),
    ("backend/app/workers/tasks.py.j2", "backend/app/workers/tasks.py"),
]

_ENTITY_TEMPLATES: list[tuple[str, str]] = [
    ("backend/app/models/entity.py.j2", "backend/app/models/{entity_name}.py"),
    ("backend/app/schemas/entity.py.j2", "backend/app/schemas/{entity_name}.py"),
    ("backend/app/services/entity_service.py.j2", "backend/app/services/{entity_name}_service.py"),
    ("backend/app/api/routes/entity.py.j2", "backend/app/api/routes/{entity_name}.py"),
    ("backend/tests/test_entity.py.j2", "backend/tests/test_{entity_name}.py"),
]


class BackendModule:
    def generate_pre_manifest(self, renderer: Renderer, context: dict[str, Any]) -> list[str]:
        generated: list[str] = []

        has_celery_worker = "celery_worker" in context["enabled_modules"]
        enriched_endpoints, service_classes, bare_fns = _enrich_endpoints(context["api_endpoints"])
        blueprint_service_imports: list[str] = [
            f"svc_{fn['name']}" for fn in bare_fns
        ] + [svc["class_name"] for svc in service_classes]
        context = {
            **context,
            "has_celery_worker": has_celery_worker,
            "celery_task_specs": _celery_task_specs(
                context["flows"],
                context["custom_logic_blocks"],
            ),
            "api_endpoints": enriched_endpoints,
            "blueprint_service_classes": service_classes,
            "blueprint_bare_fns": bare_fns,
            "blueprint_service_imports": blueprint_service_imports,
        }

        for rel_path in _CORE_INIT_PATHS:
            renderer.write_file(rel_path, "")
            generated.append(rel_path)

        for template_name, output_path in _CORE_TEMPLATES:
            renderer.render_template(template_name, output_path, context)
            generated.append(output_path)

        if has_celery_worker:
            for rel_path in _CELERY_INIT_PATHS:
                renderer.write_file(rel_path, "")
                generated.append(rel_path)

            for template_name, output_path in _CELERY_TEMPLATES:
                renderer.render_template(template_name, output_path, context)
                generated.append(output_path)

        for entity in context["entities"]:
            entity_name = entity["name"]
            entity_class_name = _pascal_case(entity_name)

            pk_fields = [f for f in entity["fields"] if f.get("primary_key")]
            entity_has_pk = bool(pk_fields)
            entity_pk_field = pk_fields[0] if pk_fields else None
            entity_pk_py_type = (
                _PY_TYPES.get(entity_pk_field["type"], "str") if entity_pk_field else None
            )
            field_types = {f["type"] for f in entity["fields"]}

            entity_context = {
                **context,
                "entity": entity,
                "entity_class_name": entity_class_name,
                "entity_has_pk": entity_has_pk,
                "entity_pk_field": entity_pk_field,
                "entity_pk_py_type": entity_pk_py_type,
                "entity_uses_uuid": "uuid" in field_types,
                "entity_uses_datetime": "datetime" in field_types,
                "entity_uses_json": "json" in field_types,
            }
            for template_name, output_pattern in _ENTITY_TEMPLATES:
                output_path = output_pattern.format(entity_name=entity_name)
                renderer.render_template(template_name, output_path, entity_context)
                generated.append(output_path)

        return generated
