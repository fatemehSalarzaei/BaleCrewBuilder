from typing import Any

from app.schemas.blueprint import BotBlueprint


def build_context(blueprint: BotBlueprint) -> dict[str, Any]:
    return {
        "project": blueprint.project.model_dump(),
        "workflow": blueprint.workflow.model_dump(),
        "bots": [b.model_dump() for b in blueprint.bots],
        "actors": [a.model_dump() for a in blueprint.actors],
        "roles": [r.model_dump() for r in blueprint.roles],
        "permissions": [p.model_dump() for p in blueprint.permissions],
        "entities": [e.model_dump() for e in blueprint.database.entities],
        "api_endpoints": [ep.model_dump() for ep in blueprint.api.endpoints],
        "flows": [f.model_dump() for f in blueprint.flows],
        "miniapp": blueprint.miniapp.model_dump(),
        "security": blueprint.security.model_dump(),
        "testing": blueprint.testing.model_dump(),
        "backend": blueprint.backend.model_dump(),
        "enabled_modules": blueprint.generation.enabled_modules,
        "custom_logic_blocks": blueprint.generation.custom_logic_blocks,
        "template_profile": blueprint.generation.template_profile,
        "output_format": blueprint.generation.output_format.value,
    }
