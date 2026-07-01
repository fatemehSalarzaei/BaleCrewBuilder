import asyncio
import json
import re
import textwrap

from app.ai.blueprint_flow import BlueprintFlow, BlueprintFlowInput
from app.schemas.blueprint import BotBlueprint


class CrewAIBlueprintFlow(BlueprintFlow):
    """CrewAI-backed Blueprint proposal flow.

    This flow proposes structured Blueprint JSON only. It never writes files,
    never calls the deterministic generator, and does not validate or approve
    the Blueprint. The normal store and validation endpoints remain mandatory.
    """

    async def run(self, input_data: BlueprintFlowInput) -> BotBlueprint:
        try:
            from crewai import Agent, Crew, Process, Task
        except ImportError as exc:
            raise RuntimeError(
                "CrewAI is not installed. Install optional AI dependencies with: "
                "pip install 'bale-bot-builder[ai]'"
            ) from exc

        def _run_crew() -> str:
            architect = Agent(
                role="Bot Blueprint Architect",
                goal="Propose valid BotBlueprint JSON from an approved project document",
                backstory=textwrap.dedent("""
                    You design structured Bale bot project Blueprints from approved
                    documents. You never write code, create files, or call generators.
                    Your output is reviewed, stored, and validated before generation.
                """).strip(),
                allow_delegation=False,
                verbose=False,
            )

            task = Task(
                description=textwrap.dedent(f"""
                    Produce a BotBlueprint JSON object for this approved project document.

                    Project Name: {input_data.project_name}
                    Document Title: {input_data.document_title}
                    Additional Context: {input_data.additional_context or "None provided."}

                    Approved Document:
                    {input_data.document_content}

                    Requirements:
                    - Output JSON only.
                    - Include required BotBlueprint top-level sections.
                    - Keep workflow.document_status as DOCUMENT_APPROVED.
                    - Include separate user_bot and admin_bot unless the document clearly
                      requires a single user-only bot.
                    - Include core database entities required for RBAC, audit, Bale account
                      mapping, and idempotency.
                    - Do not write files or code.
                    - Do not call the deterministic generator.
                """).strip(),
                agent=architect,
                expected_output="A JSON object that can be parsed as BotBlueprint.",
            )

            crew = Crew(
                agents=[architect],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )
            result = crew.kickoff()
            return str(result)

        raw_output = await asyncio.to_thread(_run_crew)
        return BotBlueprint.model_validate(_extract_json_object(raw_output))


def _extract_json_object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError("CrewAI Blueprint output was not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise ValueError("CrewAI Blueprint output must be a JSON object")
    return parsed
