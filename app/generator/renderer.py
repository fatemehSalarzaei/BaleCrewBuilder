from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.generator.validators import assert_safe_path

_SA_TYPES: dict[str, str] = {
    "uuid": "UUID",
    "string": "String",
    "boolean": "Boolean",
    "datetime": "DateTime",
    "json": "JSON",
    "integer": "Integer",
    "float": "Float",
    "text": "Text",
}

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


def _pascal_case(value: str) -> str:
    return "".join(word.capitalize() for word in value.split("_"))


class Renderer:
    def __init__(self, output_root: Path, templates_dir: Path | None = None) -> None:
        self.output_root = output_root.resolve()
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._env.filters["pascal_case"] = _pascal_case
        self._env.filters["sa_type"] = lambda t: _SA_TYPES.get(t, "String")
        self._env.filters["py_type"] = lambda t: _PY_TYPES.get(t, "Any")

    def write_file(self, relative_path: str, content: str) -> str:
        target = assert_safe_path(relative_path, self.output_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return relative_path

    def render_template(self, template_name: str, output_path: str, context: dict[str, Any]) -> str:
        template = self._env.get_template(template_name)
        content = template.render(**context)
        return self.write_file(output_path, content)
