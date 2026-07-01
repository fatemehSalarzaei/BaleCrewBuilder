import re

from app.ai.blueprint_flow import BlueprintFlow, BlueprintFlowInput
from app.schemas.blueprint import (
    ApiEndpointSpec,
    BotBlueprint,
    EntityFieldSpec,
    EntitySpec,
    FlowSpec,
    FlowStepSpec,
    HttpMethod,
    MiniAppRouteSpec,
    PageType,
)
from app.services.blueprint_service import (
    _PLACEHOLDER_CORE_ENTITY_NAMES,
    _heading_to_safe_key,
    build_placeholder_blueprint,
)

_ENTITY_SECTION_TITLES = {"data entities", "entities", "database entities"}
_API_SECTION_TITLES = {"api endpoints", "endpoints", "backend api endpoints"}
_HTTP_METHODS = {method.value for method in HttpMethod}


class FallbackBlueprintFlow(BlueprintFlow):
    """Deterministic Blueprint proposal flow for tests and local development.

    This flow makes no LLM calls and writes no files. It enriches the existing
    placeholder Blueprint with structured entity and API hints extracted from
    reviewed document sections.
    """

    async def run(self, input_data: BlueprintFlowInput) -> BotBlueprint:
        blueprint = build_placeholder_blueprint(
            project_name=input_data.project_name,
            document_title=input_data.document_title,
            document_content=input_data.document_content,
        )

        entity_names = _extract_section_items(
            input_data.document_content,
            _ENTITY_SECTION_TITLES,
        )
        endpoint_lines = _extract_section_items(
            input_data.document_content,
            _API_SECTION_TITLES,
        )

        core_names = set(_PLACEHOLDER_CORE_ENTITY_NAMES)
        existing_entities = {entity.name for entity in blueprint.database.entities}
        project_entities: list[EntitySpec] = []
        for item in entity_names:
            entity_name = _normalise_identifier(item)
            if (
                not entity_name
                or entity_name in core_names
                or entity_name in existing_entities
            ):
                continue
            entity = EntitySpec(
                name=entity_name,
                table_name=entity_name,
                fields=[
                    EntityFieldSpec(
                        name="id",
                        type="uuid",
                        nullable=False,
                        primary_key=True,
                    ),
                    EntityFieldSpec(name="name", type="str", nullable=False),
                    EntityFieldSpec(name="status", type="str", nullable=True),
                ],
                audit=True,
            )
            project_entities.append(entity)
            existing_entities.add(entity.name)

        blueprint.database.entities.extend(project_entities)

        endpoints: list[ApiEndpointSpec] = []
        seen_paths: set[tuple[str, str]] = set()
        for line in endpoint_lines:
            parsed = _parse_endpoint_line(line)
            if parsed is None:
                continue
            method, path = parsed
            key = (method.value, path)
            if key in seen_paths:
                continue
            seen_paths.add(key)
            admin_only = path.startswith("/admin") or "/admin/" in path
            roles = ["admin"] if admin_only else ["member", "admin"]
            resource_key = _normalise_identifier(path.strip("/").split("/")[-1] or "endpoint")
            endpoint_name = f"{method.value.lower()}_{resource_key}"
            endpoints.append(
                ApiEndpointSpec(
                    name=endpoint_name,
                    method=method,
                    path=path,
                    auth_required=True,
                    allowed_roles=roles,
                    request_schema=None,
                    response_schema=None,
                    service_method=f"{resource_key}_service.handle_{method.value.lower()}",
                    audit_required=admin_only,
                )
            )

        blueprint.api.endpoints.extend(endpoints)

        for entity in project_entities[:5]:
            route_path = f"/admin/{entity.name}"
            if not any(route.path == route_path for route in blueprint.miniapp.routes):
                blueprint.miniapp.routes.append(
                    MiniAppRouteSpec(
                        path=route_path,
                        allowed_roles=["admin"],
                        page_type=PageType.LIST,
                        api_dependencies=[
                            endpoint.path
                            for endpoint in endpoints
                            if entity.name in endpoint.path
                        ],
                    )
                )

        for entity in project_entities[:5]:
            flow_key = f"manage_{entity.name}"
            if any(flow.key == flow_key for flow in blueprint.flows):
                continue
            blueprint.flows.append(
                FlowSpec(
                    key=flow_key,
                    name=f"Manage {entity.name.replace('_', ' ').title()}",
                    trigger=f"Document entity: {entity.name}",
                    steps=[
                        FlowStepSpec(step=1, action="submit", actor="user", target=entity.name),
                        FlowStepSpec(step=2, action="review", actor="admin", target=entity.name),
                    ],
                    bots_involved=["user_bot", "admin_bot"],
                    api_calls=[
                        endpoint.path
                        for endpoint in endpoints
                        if entity.name in endpoint.path
                    ],
                )
            )

        return blueprint


def _extract_section_items(content: str, section_titles: set[str]) -> list[str]:
    items: list[str] = []
    in_section = False
    for line in content.splitlines():
        stripped = line.strip()
        heading = _heading_text(stripped)
        if heading is not None:
            in_section = heading.lower() in section_titles
            continue

        if not in_section or not stripped:
            continue

        item = _list_item_text(stripped)
        if item:
            items.append(item)

    return items


def _heading_text(line: str) -> str | None:
    if not line.startswith("#"):
        return None
    return line.lstrip("#").strip()


def _list_item_text(line: str) -> str | None:
    match = re.match(r"^(?:[-*]|\d+[.)])\s+(?P<item>.+)$", line)
    if not match:
        return None
    item = match.group("item").strip()
    endpoint_match = re.search(r"\b(?:GET|POST|PUT|PATCH|DELETE)\b\s+\S+", item)
    if endpoint_match:
        return item
    item = re.split(r":|\s+-\s+|\s+\(", item, maxsplit=1)[0].strip()
    return item or None


def _parse_endpoint_line(line: str) -> tuple[HttpMethod, str] | None:
    match = re.search(
        r"\b(?P<method>GET|POST|PUT|PATCH|DELETE)\b\s+(?P<path>/[^\s,;]+)",
        line,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    method_value = match.group("method").upper()
    if method_value not in _HTTP_METHODS:
        return None
    return HttpMethod(method_value), match.group("path")


def _normalise_identifier(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\b(create|read|update|delete|list|manage|approve|reject)\b", "", text)
    key = _heading_to_safe_key(text)
    if key.endswith("ies"):
        key = f"{key[:-3]}y"
    elif key.endswith("s") and not key.endswith("ss"):
        key = key[:-1]
    return key
