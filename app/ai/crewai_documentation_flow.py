import asyncio
import textwrap

from app.ai.documentation_flow import DocumentationFlow
from app.schemas.ai import DocumentationFlowInput, DocumentationFlowOutput


class CrewAIDocumentationFlow(DocumentationFlow):
    """CrewAI-backed documentation flow.

    CrewAI is imported lazily inside run() so the class is importable even when
    the 'crewai' package is not installed (e.g. in test environments).

    Constraints (non-negotiable per CLAUDE.md):
    - Must not write any project files.
    - Must not call the deterministic Generator.
    - Must not bypass approval or Blueprint validation gates.
    - Returns document draft data only.
    """

    async def run(self, input_data: DocumentationFlowInput) -> DocumentationFlowOutput:
        try:
            from crewai import Agent, Crew, Process, Task
        except ImportError as exc:
            raise RuntimeError(
                "CrewAI is not installed. Install optional AI dependencies with: "
                "pip install 'bale-bot-builder[ai]'"
            ) from exc

        def _run_crew() -> str:
            analyst = Agent(
                role="Project Requirements Analyst",
                goal="Analyze raw project requirements and extract structured information",
                backstory=textwrap.dedent("""
                    You are an expert in analyzing project requirements for Bale messenger bot
                    projects. You identify actors, roles, data entities, and workflows from raw
                    text. You never write project code or generate project files.
                """).strip(),
                allow_delegation=False,
                verbose=False,
            )
            writer = Agent(
                role="Project Bot Document Writer",
                goal=(
                    "Produce a clear, structured Project Bot Document draft "
                    "from the analyzed requirements"
                ),
                backstory=textwrap.dedent("""
                    You are an expert technical writer for Bale bot projects.
                    You produce structured Markdown documentation that will be reviewed by
                    humans before any code is generated. You never write project code or
                    generate project files.
                """).strip(),
                allow_delegation=False,
                verbose=False,
            )

            analysis_task = Task(
                description=textwrap.dedent(f"""
                    Analyze the following project requirements for a Bale messenger bot project.

                    Project Name: {input_data.project_name}

                    Raw Requirements:
                    {input_data.raw_requirements}

                    Additional Context:
                    {input_data.additional_context or "None provided."}

                    Extract and list:
                    1. Target users and roles
                    2. Key workflows
                    3. Required data entities
                    4. Bot commands needed (User Bot and Admin Bot if applicable)
                    5. API endpoints needed
                    6. Assumptions and risks
                """).strip(),
                agent=analyst,
                expected_output=(
                    "Structured analysis of project requirements covering actors, "
                    "workflows, entities, bot commands, API endpoints, and risks."
                ),
            )
            writing_task = Task(
                description=textwrap.dedent(f"""
                    Write a Project Bot Document draft for the project named
                    '{input_data.project_name}'.
                    Use the analysis from the previous task.
                    Format the output as Markdown with clear sections.

                    IMPORTANT:
                    - Do NOT generate code.
                    - Do NOT create or write any files.
                    - Produce documentation only.

                    Required sections:
                    - Project Overview
                    - Target Users and Roles
                    - Key Workflows
                    - Bot Commands
                    - API Endpoints
                    - Data Entities
                    - Assumptions
                    - Risks
                    - Suggested Next Steps
                """).strip(),
                agent=writer,
                expected_output="Complete Project Bot Document draft in Markdown format.",
                context=[analysis_task],
            )

            crew = Crew(
                agents=[analyst, writer],
                tasks=[analysis_task, writing_task],
                process=Process.sequential,
                verbose=False,
            )
            result = crew.kickoff()
            return str(result)

        raw_output = await asyncio.to_thread(_run_crew)

        title = f"Project Bot Document: {input_data.project_name}"
        return DocumentationFlowOutput(
            title=title,
            content=raw_output,
            assumptions=[],
            risks=[],
            suggested_next_steps=["Review the document and request changes or approve it."],
            metadata={"provider": "crewai"},
        )
