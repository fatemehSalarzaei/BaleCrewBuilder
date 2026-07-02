from typing import Any

from app.generator.renderer import Renderer


class CoreModule:
    def generate_pre_manifest(self, renderer: Renderer, context: dict[str, Any]) -> list[str]:
        """Generate project-level files that don't depend on the manifest."""
        enriched = {
            **context,
            "has_admin_bot": any(bot.get("audience") == "admins" for bot in context["bots"]),
            "has_celery_worker": "celery_worker" in context["enabled_modules"],
        }
        templates = [
            ("docs/README.md.j2", "README.md"),
            ("backend/Dockerfile.j2", "backend/Dockerfile"),
            ("frontend/Dockerfile.j2", "frontend/Dockerfile"),
            ("deploy/docker-compose.prod.yml.j2", "deploy/docker-compose.prod.yml"),
            ("deploy/env.example.j2", "deploy/.env.example"),
            ("docs/deployment.md.j2", "docs/deployment.md"),
        ]

        generated: list[str] = []
        for template_name, output_path in templates:
            generated.append(renderer.render_template(template_name, output_path, enriched))
        return generated
