from typing import Any

from app.generator.renderer import Renderer


def _pascal_case(snake: str) -> str:
    return "".join(word.capitalize() for word in snake.split("_"))


# Service module names already generated as full implementations — avoid class name conflicts.
_CORE_SERVICE_MODULES: frozenset[str] = frozenset({"auth_service", "audit_service"})


def _service_class_for(module: str) -> str:
    if module in _CORE_SERVICE_MODULES:
        return "Bp" + _pascal_case(module)
    return _pascal_case(module)


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
    class_methods: dict[str, list[str]] = {}
    bare_fns: list[str] = []
    seen_bare: set[str] = set()

    for ep in raw_endpoints:
        sm: str = ep.get("service_method", "")
        if "." in sm:
            module, fn = sm.split(".", 1)
            class_name = _service_class_for(module)
            enriched.append({
                **ep,
                "svc_class_name": class_name,
                "svc_fn_name": fn,
                "svc_is_bare": False,
                "svc_call": f"{class_name}().{fn}()",
            })
            if class_name not in class_methods:
                class_methods[class_name] = []
            if fn not in class_methods[class_name]:
                class_methods[class_name].append(fn)
        else:
            fn = sm
            enriched.append({
                **ep,
                "svc_class_name": None,
                "svc_fn_name": fn,
                "svc_is_bare": True,
                "svc_call": f"svc_{fn}()",
            })
            if fn not in seen_bare:
                bare_fns.append(fn)
                seen_bare.add(fn)

    service_classes = [
        {"class_name": cls, "methods": list(methods)}
        for cls, methods in class_methods.items()
    ]
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
    "backend/app/api/__init__.py",
    "backend/app/api/routes/__init__.py",
    "backend/app/models/__init__.py",
    "backend/app/schemas/__init__.py",
    "backend/app/services/__init__.py",
    "backend/tests/__init__.py",
]

_CORE_TEMPLATES: list[tuple[str, str]] = [
    ("backend/app/main.py.j2", "backend/app/main.py"),
    ("backend/app/core/config.py.j2", "backend/app/core/config.py"),
    ("backend/app/core/security.py.j2", "backend/app/core/security.py"),
    ("backend/app/db/base.py.j2", "backend/app/db/base.py"),
    ("backend/app/db/session.py.j2", "backend/app/db/session.py"),
    ("backend/app/api/deps.py.j2", "backend/app/api/deps.py"),
    ("backend/app/api/router.py.j2", "backend/app/api/router.py"),
    ("backend/app/api/routes/endpoints.py.j2", "backend/app/api/routes/endpoints.py"),
    ("backend/app/services/auth_service.py.j2", "backend/app/services/auth_service.py"),
    ("backend/app/services/audit_service.py.j2", "backend/app/services/audit_service.py"),
    ("backend/app/services/blueprint_service.py.j2", "backend/app/services/blueprint_service.py"),
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

        enriched_endpoints, service_classes, bare_fns = _enrich_endpoints(context["api_endpoints"])
        blueprint_service_imports: list[str] = [
            f"svc_{fn}" for fn in bare_fns
        ] + [svc["class_name"] for svc in service_classes]
        context = {
            **context,
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
