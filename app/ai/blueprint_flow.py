from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.schemas.blueprint import BotBlueprint


class BlueprintFlowInput(BaseModel):
    project_name: str = Field(min_length=1)
    document_title: str = Field(min_length=1)
    document_content: str = Field(min_length=1)
    additional_context: str | None = None


class BlueprintFlow(ABC):
    @abstractmethod
    async def run(self, input_data: BlueprintFlowInput) -> BotBlueprint:
        ...


def get_blueprint_flow(provider: str | None = None) -> BlueprintFlow:
    if provider is None:
        from app.core.config import settings

        provider = settings.ai_blueprint_provider

    if provider == "crewai":
        from app.ai.crewai_blueprint_flow import CrewAIBlueprintFlow

        return CrewAIBlueprintFlow()

    from app.ai.fallback_blueprint_flow import FallbackBlueprintFlow

    return FallbackBlueprintFlow()
