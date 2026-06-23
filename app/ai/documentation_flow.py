from abc import ABC, abstractmethod

from app.schemas.ai import DocumentationFlowInput, DocumentationFlowOutput


class DocumentationFlow(ABC):
    @abstractmethod
    async def run(self, input_data: DocumentationFlowInput) -> DocumentationFlowOutput:
        ...


def get_documentation_flow(provider: str | None = None) -> DocumentationFlow:
    if provider is None:
        from app.core.config import settings
        provider = settings.ai_documentation_provider

    if provider == "crewai":
        from app.ai.crewai_documentation_flow import CrewAIDocumentationFlow
        return CrewAIDocumentationFlow()

    from app.ai.fallback_documentation_flow import FallbackDocumentationFlow
    return FallbackDocumentationFlow()
