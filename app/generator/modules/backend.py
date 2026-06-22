from typing import Any

from app.generator.renderer import Renderer


def _pascal_case(snake: str) -> str:
    return "".join(word.capitalize() for word in snake.split("_"))


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
    ("backend/app/db/base.py.j2", "backend/app/db/base.py"),
    ("backend/app/db/session.py.j2", "backend/app/db/session.py"),
    ("backend/app/api/deps.py.j2", "backend/app/api/deps.py"),
    ("backend/app/api/router.py.j2", "backend/app/api/router.py"),
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

        for rel_path in _CORE_INIT_PATHS:
            renderer.write_file(rel_path, "")
            generated.append(rel_path)

        for template_name, output_path in _CORE_TEMPLATES:
            renderer.render_template(template_name, output_path, context)
            generated.append(output_path)

        for entity in context["entities"]:
            entity_name = entity["name"]
            entity_class_name = _pascal_case(entity_name)
            entity_context = {
                **context,
                "entity": entity,
                "entity_class_name": entity_class_name,
            }
            for template_name, output_pattern in _ENTITY_TEMPLATES:
                output_path = output_pattern.format(entity_name=entity_name)
                renderer.render_template(template_name, output_path, entity_context)
                generated.append(output_path)

        return generated
