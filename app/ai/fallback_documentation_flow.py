from app.ai.documentation_flow import DocumentationFlow
from app.schemas.ai import DocumentationFlowInput, DocumentationFlowOutput


class FallbackDocumentationFlow(DocumentationFlow):
    """Deterministic fallback — no LLM required.

    Produces a structured Markdown template from the raw requirements text.
    Used in tests and local development when CrewAI or API keys are unavailable.
    """

    async def run(self, input_data: DocumentationFlowInput) -> DocumentationFlowOutput:
        title = f"Project Bot Document: {input_data.project_name}"

        lines: list[str] = [
            f"# {title}",
            "",
            "## Project Overview",
            "",
            input_data.raw_requirements,
        ]

        if input_data.additional_context:
            lines += [
                "",
                "## Additional Context",
                "",
                input_data.additional_context,
            ]

        lines += [
            "",
            "## Proposed Bot Architecture",
            "",
            "This section will be refined after human review and Blueprint generation.",
            "",
            "## Required Roles and Permissions",
            "",
            "- Define user roles based on project requirements.",
            "- Define admin roles if an Admin Bot is required.",
            "",
            "## Data Entities",
            "",
            "- Define entities based on project requirements.",
            "",
            "## Bot Commands",
            "",
            "- Define User Bot and Admin Bot commands based on project requirements.",
            "",
            "## API Endpoints",
            "",
            "- Define API endpoints based on project requirements.",
            "",
            "## Suggested Next Steps",
            "",
            "1. Review this document and request changes or approve it.",
            "2. After approval, proceed to Bot Blueprint generation.",
            "3. Validate the Blueprint before generating the project.",
        ]

        content = "\n".join(lines)

        return DocumentationFlowOutput(
            title=title,
            content=content,
            assumptions=[
                "Requirements are taken as provided without modification.",
                "A multi-bot architecture (User Bot + Admin Bot) may be needed.",
                "Frontend will run as both a Web Panel and a Bale Mini App.",
            ],
            risks=[
                "Requirements may be incomplete or ambiguous.",
                "Scope may expand during the review process.",
            ],
            suggested_next_steps=[
                "Review and approve the generated document.",
                "Request changes if requirements are incomplete.",
                "Proceed to Blueprint generation after approval.",
            ],
            metadata={"provider": "fallback"},
        )
