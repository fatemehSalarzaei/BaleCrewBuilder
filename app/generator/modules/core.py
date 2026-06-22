from typing import Any

from app.generator.renderer import Renderer


class CoreModule:
    def generate_pre_manifest(self, renderer: Renderer, context: dict[str, Any]) -> list[str]:
        """Generate files that don't depend on the manifest (README.md stub)."""
        readme_rel = renderer.render_template("docs/README.md.j2", "README.md", context)
        return [readme_rel]
