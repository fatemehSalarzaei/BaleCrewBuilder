"""Phase 8: End-to-end sample generation tests.

Verifies that the deterministic generator produces distinct, Blueprint-driven
projects from different sample Blueprints, and that bot generation correctly
reflects multi-bot vs user-only Blueprint configuration.

No hard-coded domain assumptions are permitted — all output differences must
derive from the Blueprint fixture data.
"""
import py_compile
from pathlib import Path
from typing import NamedTuple

import pytest
import yaml

from app.generator import GeneratorCore, GeneratorResult
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_blueprint(filename: str) -> BotBlueprint:
    with open(FIXTURES / filename) as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


class RunOutput(NamedTuple):
    blueprint: BotBlueprint
    output_dir: Path
    result: GeneratorResult


@pytest.fixture(scope="module")
def support_ticket_run(tmp_path_factory: pytest.TempPathFactory) -> RunOutput:
    blueprint = _load_blueprint("support_ticket_like.yaml")
    output_dir = tmp_path_factory.mktemp("support_ticket") / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)
    return RunOutput(blueprint=blueprint, output_dir=output_dir, result=result)


@pytest.fixture(scope="module")
def appointment_form_run(tmp_path_factory: pytest.TempPathFactory) -> RunOutput:
    blueprint = _load_blueprint("appointment_form_like.yaml")
    output_dir = tmp_path_factory.mktemp("appointment_form") / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)
    return RunOutput(blueprint=blueprint, output_dir=output_dir, result=result)


# ── Blueprint loading and validation ─────────────────────────────────────────


def test_support_ticket_blueprint_loads(support_ticket_run: RunOutput) -> None:
    assert support_ticket_run.blueprint.project.name == "Support Ticket Platform"


def test_appointment_form_blueprint_loads(appointment_form_run: RunOutput) -> None:
    assert appointment_form_run.blueprint.project.name == "Appointment Booking Platform"


def test_support_ticket_blueprint_is_multi_bot(support_ticket_run: RunOutput) -> None:
    bot_keys = {b.key for b in support_ticket_run.blueprint.bots}
    assert "user_bot" in bot_keys
    assert "admin_bot" in bot_keys


def test_appointment_form_blueprint_is_user_only(appointment_form_run: RunOutput) -> None:
    bot_keys = {b.key for b in appointment_form_run.blueprint.bots}
    assert "user_bot" in bot_keys
    assert "admin_bot" not in bot_keys


# ── Both projects generate successfully (manifest present) ───────────────────


def test_support_ticket_manifest_exists(support_ticket_run: RunOutput) -> None:
    assert (support_ticket_run.output_dir / "docs/generation_manifest.json").exists()
    assert "docs/generation_manifest.json" in support_ticket_run.result.generated_files


def test_appointment_form_manifest_exists(appointment_form_run: RunOutput) -> None:
    assert (appointment_form_run.output_dir / "docs/generation_manifest.json").exists()
    assert "docs/generation_manifest.json" in appointment_form_run.result.generated_files


def test_support_ticket_all_manifest_files_on_disk(support_ticket_run: RunOutput) -> None:
    for rel_path in support_ticket_run.result.generated_files:
        assert (support_ticket_run.output_dir / rel_path).exists(), (
            f"Manifest lists '{rel_path}' but file is missing from disk"
        )


def test_appointment_form_all_manifest_files_on_disk(appointment_form_run: RunOutput) -> None:
    for rel_path in appointment_form_run.result.generated_files:
        assert (appointment_form_run.output_dir / rel_path).exists(), (
            f"Manifest lists '{rel_path}' but file is missing from disk"
        )


# ── Backend output present ────────────────────────────────────────────────────


def test_support_ticket_has_backend_output(support_ticket_run: RunOutput) -> None:
    assert (support_ticket_run.output_dir / "backend/app/main.py").exists()
    assert "backend/app/main.py" in support_ticket_run.result.generated_files


def test_appointment_form_has_backend_output(appointment_form_run: RunOutput) -> None:
    assert (appointment_form_run.output_dir / "backend/app/main.py").exists()
    assert "backend/app/main.py" in appointment_form_run.result.generated_files


# ── Frontend output present (both fixtures enable miniapp) ───────────────────


def test_support_ticket_has_frontend_output(support_ticket_run: RunOutput) -> None:
    assert support_ticket_run.blueprint.miniapp.enabled
    assert (support_ticket_run.output_dir / "frontend/src/App.tsx").exists()
    assert "frontend/src/App.tsx" in support_ticket_run.result.generated_files


def test_appointment_form_has_frontend_output(appointment_form_run: RunOutput) -> None:
    assert appointment_form_run.blueprint.miniapp.enabled
    assert (appointment_form_run.output_dir / "frontend/src/App.tsx").exists()
    assert "frontend/src/App.tsx" in appointment_form_run.result.generated_files


# ── Multi-bot: support/ticket has BOTH User Bot and Admin Bot files ───────────


def test_support_ticket_has_user_bot_webhook(support_ticket_run: RunOutput) -> None:
    generated = support_ticket_run.result.generated_files
    assert "bale/user_bot/webhook.py" in generated
    assert (support_ticket_run.output_dir / "bale/user_bot/webhook.py").exists()


def test_support_ticket_has_user_bot_commands(support_ticket_run: RunOutput) -> None:
    generated = support_ticket_run.result.generated_files
    assert "bale/user_bot/commands.py" in generated
    assert (support_ticket_run.output_dir / "bale/user_bot/commands.py").exists()


def test_support_ticket_has_admin_bot_webhook(support_ticket_run: RunOutput) -> None:
    generated = support_ticket_run.result.generated_files
    assert "bale/admin_bot/webhook.py" in generated
    assert (support_ticket_run.output_dir / "bale/admin_bot/webhook.py").exists()


def test_support_ticket_has_admin_bot_commands(support_ticket_run: RunOutput) -> None:
    generated = support_ticket_run.result.generated_files
    assert "bale/admin_bot/commands.py" in generated
    assert (support_ticket_run.output_dir / "bale/admin_bot/commands.py").exists()


def test_support_ticket_has_both_bot_test_files(support_ticket_run: RunOutput) -> None:
    generated = support_ticket_run.result.generated_files
    assert "bale/tests/test_user_bot_webhook.py" in generated
    assert "bale/tests/test_admin_bot_webhook.py" in generated


# ── User-only: appointment/form has User Bot ONLY, no Admin Bot files ─────────


def test_appointment_form_has_user_bot_webhook(appointment_form_run: RunOutput) -> None:
    generated = appointment_form_run.result.generated_files
    assert "bale/user_bot/webhook.py" in generated
    assert (appointment_form_run.output_dir / "bale/user_bot/webhook.py").exists()


def test_appointment_form_has_user_bot_commands(appointment_form_run: RunOutput) -> None:
    generated = appointment_form_run.result.generated_files
    assert "bale/user_bot/commands.py" in generated
    assert (appointment_form_run.output_dir / "bale/user_bot/commands.py").exists()


def test_appointment_form_has_no_admin_bot_webhook(appointment_form_run: RunOutput) -> None:
    generated = appointment_form_run.result.generated_files
    assert "bale/admin_bot/webhook.py" not in generated
    assert not (appointment_form_run.output_dir / "bale/admin_bot/webhook.py").exists()


def test_appointment_form_has_no_admin_bot_commands(appointment_form_run: RunOutput) -> None:
    generated = appointment_form_run.result.generated_files
    assert "bale/admin_bot/commands.py" not in generated
    assert not (appointment_form_run.output_dir / "bale/admin_bot/commands.py").exists()


def test_appointment_form_has_no_admin_bot_test_file(appointment_form_run: RunOutput) -> None:
    generated = appointment_form_run.result.generated_files
    assert "bale/tests/test_admin_bot_webhook.py" not in generated


# ── Generated file lists differ between the two Blueprints ───────────────────


def test_generated_file_lists_differ(
    support_ticket_run: RunOutput, appointment_form_run: RunOutput
) -> None:
    support_files = set(support_ticket_run.result.generated_files)
    appt_files = set(appointment_form_run.result.generated_files)
    assert support_files != appt_files, (
        "Support/ticket and appointment/form generated file lists must differ; "
        "each Blueprint must produce distinct output"
    )


def test_support_ticket_has_more_files_due_to_admin_bot(
    support_ticket_run: RunOutput, appointment_form_run: RunOutput
) -> None:
    support_count = len(support_ticket_run.result.generated_files)
    appt_count = len(appointment_form_run.result.generated_files)
    assert support_count > appt_count, (
        f"Multi-bot support project ({support_count} files) must generate more files "
        f"than user-only appointment project ({appt_count} files)"
    )


# ── Domain-specific entity files in the correct output only ──────────────────


def test_support_ticket_has_ticket_entity_files(support_ticket_run: RunOutput) -> None:
    generated = support_ticket_run.result.generated_files
    assert "backend/app/models/tickets.py" in generated
    assert "backend/app/models/ticket_comments.py" in generated
    assert (support_ticket_run.output_dir / "backend/app/models/tickets.py").exists()
    assert (support_ticket_run.output_dir / "backend/app/models/ticket_comments.py").exists()


def test_appointment_form_has_appointment_entity_files(appointment_form_run: RunOutput) -> None:
    generated = appointment_form_run.result.generated_files
    assert "backend/app/models/appointments.py" in generated
    assert "backend/app/models/appointment_slots.py" in generated
    assert (appointment_form_run.output_dir / "backend/app/models/appointments.py").exists()
    assert (appointment_form_run.output_dir / "backend/app/models/appointment_slots.py").exists()


def test_support_ticket_has_no_appointment_entity_files(support_ticket_run: RunOutput) -> None:
    generated = support_ticket_run.result.generated_files
    assert "backend/app/models/appointments.py" not in generated
    assert "backend/app/models/appointment_slots.py" not in generated


def test_appointment_form_has_no_ticket_entity_files(appointment_form_run: RunOutput) -> None:
    generated = appointment_form_run.result.generated_files
    assert "backend/app/models/tickets.py" not in generated
    assert "backend/app/models/ticket_comments.py" not in generated


# ── Domain isolation: no cross-contamination in generated .py content ─────────


def test_no_ticket_keyword_in_appointment_python_files(appointment_form_run: RunOutput) -> None:
    output_dir = appointment_form_run.output_dir
    for py_file in sorted(output_dir.rglob("*.py")):
        content = py_file.read_text(encoding="utf-8").lower()
        assert "ticket" not in content, (
            f"Forbidden keyword 'ticket' found in appointment output: "
            f"{py_file.relative_to(output_dir)}"
        )


def test_no_appointment_keyword_in_support_ticket_python_files(
    support_ticket_run: RunOutput,
) -> None:
    output_dir = support_ticket_run.output_dir
    for py_file in sorted(output_dir.rglob("*.py")):
        content = py_file.read_text(encoding="utf-8").lower()
        assert "appointment" not in content, (
            f"Forbidden keyword 'appointment' found in support_ticket output: "
            f"{py_file.relative_to(output_dir)}"
        )


# ── Domain content present in the correct output ─────────────────────────────


def test_ticket_keyword_present_in_support_python_files(support_ticket_run: RunOutput) -> None:
    output_dir = support_ticket_run.output_dir
    all_content = "".join(
        f.read_text(encoding="utf-8").lower() for f in output_dir.rglob("*.py")
    )
    assert "ticket" in all_content, (
        "The word 'ticket' must appear in support_ticket generated Python files"
    )


def test_appointment_keyword_present_in_appointment_python_files(
    appointment_form_run: RunOutput,
) -> None:
    output_dir = appointment_form_run.output_dir
    all_content = "".join(
        f.read_text(encoding="utf-8").lower() for f in output_dir.rglob("*.py")
    )
    assert "appointment" in all_content, (
        "The word 'appointment' must appear in appointment_form generated Python files"
    )


# ── Bot configuration follows Blueprint ──────────────────────────────────────


def test_support_ticket_config_has_both_bot_tokens(support_ticket_run: RunOutput) -> None:
    content = (support_ticket_run.output_dir / "backend/app/core/config.py").read_text()
    assert "user_bot_token" in content.lower()
    assert "admin_bot_token" in content.lower()


def test_appointment_form_config_has_user_bot_token_only(appointment_form_run: RunOutput) -> None:
    content = (appointment_form_run.output_dir / "backend/app/core/config.py").read_text()
    assert "user_bot_token" in content.lower()
    assert "admin_bot_token" not in content.lower()


def test_support_ticket_admin_webhook_path_in_admin_bot(support_ticket_run: RunOutput) -> None:
    content = (support_ticket_run.output_dir / "bale/admin_bot/webhook.py").read_text()
    assert "/webhook/admin" in content


def test_appointment_form_user_webhook_path_in_user_bot(appointment_form_run: RunOutput) -> None:
    content = (appointment_form_run.output_dir / "bale/user_bot/webhook.py").read_text()
    assert "/webhook/user" in content


def test_support_ticket_admin_bot_has_admin_commands(support_ticket_run: RunOutput) -> None:
    content = (support_ticket_run.output_dir / "bale/admin_bot/commands.py").read_text()
    assert "admin_handle_pending_tickets" in content
    assert "admin_handle_close_ticket" in content


def test_appointment_form_user_bot_has_appointment_commands(
    appointment_form_run: RunOutput,
) -> None:
    content = (appointment_form_run.output_dir / "bale/user_bot/commands.py").read_text()
    assert "handle_my_appointments" in content
    assert "handle_book_appointment" in content


# ── Blueprint API endpoints reflected in generated routes ────────────────────


def test_support_ticket_api_endpoints_in_routes(support_ticket_run: RunOutput) -> None:
    content = (
        support_ticket_run.output_dir / "backend/app/api/routes/endpoints.py"
    ).read_text()
    for ep in support_ticket_run.blueprint.api.endpoints:
        assert ep.path in content, f"Endpoint path '{ep.path}' missing from endpoints.py"
        assert f"async def {ep.name}" in content, (
            f"Endpoint function '{ep.name}' missing from endpoints.py"
        )


def test_appointment_form_api_endpoints_in_routes(appointment_form_run: RunOutput) -> None:
    content = (
        appointment_form_run.output_dir / "backend/app/api/routes/endpoints.py"
    ).read_text()
    for ep in appointment_form_run.blueprint.api.endpoints:
        assert ep.path in content, f"Endpoint path '{ep.path}' missing from endpoints.py"
        assert f"async def {ep.name}" in content, (
            f"Endpoint function '{ep.name}' missing from endpoints.py"
        )


def test_support_ticket_no_raise_not_implemented_in_endpoints(
    support_ticket_run: RunOutput,
) -> None:
    content = (
        support_ticket_run.output_dir / "backend/app/api/routes/endpoints.py"
    ).read_text()
    assert "raise NotImplementedError" not in content


def test_appointment_form_no_raise_not_implemented_in_endpoints(
    appointment_form_run: RunOutput,
) -> None:
    content = (
        appointment_form_run.output_dir / "backend/app/api/routes/endpoints.py"
    ).read_text()
    assert "raise NotImplementedError" not in content


# ── Project name reflected in docs ───────────────────────────────────────────


def test_support_ticket_project_name_in_readme(support_ticket_run: RunOutput) -> None:
    readme = support_ticket_run.output_dir / "README.md"
    assert readme.exists()
    assert "Support Ticket Platform" in readme.read_text()


def test_appointment_form_project_name_in_readme(appointment_form_run: RunOutput) -> None:
    readme = appointment_form_run.output_dir / "README.md"
    assert readme.exists()
    assert "Appointment Booking Platform" in readme.read_text()


# ── Generated Python files compile ────────────────────────────────────────────


def test_support_ticket_python_files_compile(support_ticket_run: RunOutput) -> None:
    output_dir = support_ticket_run.output_dir
    for py_file in sorted(output_dir.rglob("*.py")):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            pytest.fail(
                f"Syntax error in support_ticket generated file "
                f"{py_file.relative_to(output_dir)}: {exc}"
            )


def test_appointment_form_python_files_compile(appointment_form_run: RunOutput) -> None:
    output_dir = appointment_form_run.output_dir
    for py_file in sorted(output_dir.rglob("*.py")):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            pytest.fail(
                f"Syntax error in appointment_form generated file "
                f"{py_file.relative_to(output_dir)}: {exc}"
            )


# ── Determinism: same Blueprint always produces the same file list ────────────


def test_support_ticket_same_blueprint_same_file_list(tmp_path: Path) -> None:
    blueprint = _load_blueprint("support_ticket_like.yaml")

    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = GeneratorCore().run(blueprint, out1)

    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = GeneratorCore().run(blueprint, out2)

    assert result1.generated_files == result2.generated_files, (
        "support_ticket_like.yaml must produce an identical file list on every run"
    )


def test_appointment_form_same_blueprint_same_file_list(tmp_path: Path) -> None:
    blueprint = _load_blueprint("appointment_form_like.yaml")

    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = GeneratorCore().run(blueprint, out1)

    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = GeneratorCore().run(blueprint, out2)

    assert result1.generated_files == result2.generated_files, (
        "appointment_form_like.yaml must produce an identical file list on every run"
    )
