"""Tests for Phase 6: Bale multi-bot generated templates."""
import py_compile
from pathlib import Path

import pytest
import yaml

from app.generator import GeneratorCore
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"

FORBIDDEN_DOMAINS = {"ticket", "appointment", "crm", "support_ticket"}

_BALE_SHARED_FILES = [
    "bale/__init__.py",
    "bale/shared/__init__.py",
    "bale/shared/client.py",
    "bale/shared/backend_client.py",
    "bale/shared/webhook.py",
    "bale/shared/idempotency.py",
    "bale/tests/__init__.py",
]


def _load_blueprint() -> BotBlueprint:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


def _run(tmp_path: Path) -> tuple[Path, list[str]]:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)
    return output_dir, result.generated_files


# ── Shared infrastructure ─────────────────────────────────────────────────────


def test_bale_shared_init_files_are_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    for rel_path in _BALE_SHARED_FILES:
        assert rel_path in generated, f"Missing bale shared file: {rel_path}"
        assert (output_dir / rel_path).exists()


def test_bale_shared_client_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "bale/shared/client.py" in generated
    assert (output_dir / "bale/shared/client.py").exists()


def test_bale_shared_backend_client_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "bale/shared/backend_client.py" in generated
    assert (output_dir / "bale/shared/backend_client.py").exists()


def test_bale_shared_webhook_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "bale/shared/webhook.py" in generated
    assert (output_dir / "bale/shared/webhook.py").exists()


# ── Shared client content ─────────────────────────────────────────────────────


def test_bale_client_uses_httpx(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/client.py").read_text()
    assert "import httpx" in content


def test_bale_client_has_bale_client_class(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/client.py").read_text()
    assert "class BaleClient" in content


def test_bale_client_has_send_message(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/client.py").read_text()
    assert "async def send_message" in content


def test_bale_client_has_set_webhook(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/client.py").read_text()
    assert "async def set_webhook" in content


def test_bale_client_has_per_bot_factory_functions(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "bale/shared/client.py").read_text()
    for bot in blueprint.bots:
        assert f"make_{bot.key}_client" in content, (
            f"client.py missing factory function for bot '{bot.key}'"
        )


def test_bale_client_references_bot_token_envs(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "bale/shared/client.py").read_text()
    for bot in blueprint.bots:
        assert bot.token_env in content, (
            f"client.py must reference token_env '{bot.token_env}' for bot '{bot.key}'"
        )


def test_bale_client_does_not_hardcode_tokens(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/client.py").read_text()
    assert "os.environ" in content or "_make_client" in content, (
        "client.py must load tokens from environment at runtime"
    )
    assert "secret" not in content.lower() or "secret_token" in content, (
        "client.py must not reference hardcoded secrets (only set_webhook optional param)"
    )


# ── Shared webhook content ────────────────────────────────────────────────────


def test_bale_webhook_has_verify_function(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/webhook.py").read_text()
    assert "def verify_webhook_signature" in content


def test_bale_webhook_has_parse_update(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/webhook.py").read_text()
    assert "def parse_update" in content


def test_bale_webhook_uses_hmac(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/webhook.py").read_text()
    assert "import hmac" in content


def test_bale_webhook_has_verification_error_class(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/webhook.py").read_text()
    assert "WebhookVerificationError" in content


# ── Per-bot file generation ───────────────────────────────────────────────────


def test_per_bot_init_files_are_generated(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        expected = f"bale/{bot.key}/__init__.py"
        assert (output_dir / expected).exists(), f"Missing: {expected}"


def test_per_bot_webhook_files_are_generated(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        expected = f"bale/{bot.key}/webhook.py"
        assert expected in result.generated_files, f"Missing webhook file: {expected}"
        assert (output_dir / expected).exists()


def test_per_bot_commands_files_are_generated(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        expected = f"bale/{bot.key}/commands.py"
        assert expected in result.generated_files, f"Missing commands file: {expected}"
        assert (output_dir / expected).exists()


def test_per_bot_test_files_are_generated(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        expected = f"bale/tests/test_{bot.key}_webhook.py"
        assert expected in result.generated_files, f"Missing test file: {expected}"
        assert (output_dir / expected).exists()


def test_user_bot_and_admin_bot_generate_separate_files(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    bot_keys = {bot.key for bot in blueprint.bots}
    assert "user_bot" in bot_keys and "admin_bot" in bot_keys, (
        "Fixture must define both user_bot and admin_bot"
    )

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    assert (output_dir / "bale/user_bot/webhook.py").exists()
    assert (output_dir / "bale/admin_bot/webhook.py").exists()
    assert (output_dir / "bale/user_bot/commands.py").exists()
    assert (output_dir / "bale/admin_bot/commands.py").exists()

    user_wh = (output_dir / "bale/user_bot/webhook.py").read_text()
    admin_wh = (output_dir / "bale/admin_bot/webhook.py").read_text()
    assert user_wh != admin_wh, "user_bot and admin_bot webhook files must differ"


# ── Per-bot webhook content ───────────────────────────────────────────────────


def test_bot_webhook_path_in_webhook_file(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        content = (output_dir / f"bale/{bot.key}/webhook.py").read_text()
        assert bot.webhook_path in content, (
            f"webhook.py for '{bot.key}' must contain webhook_path '{bot.webhook_path}'"
        )


def test_bot_webhook_has_signature_verification_when_enabled(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    assert blueprint.security.bot_webhook_secret, "Fixture must have bot_webhook_secret=True"

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        content = (output_dir / f"bale/{bot.key}/webhook.py").read_text()
        assert "verify_webhook_signature" in content, (
            f"webhook.py for '{bot.key}' must call verify_webhook_signature"
        )
        assert "X-Bale-Signature" in content, (
            f"webhook.py for '{bot.key}' must check X-Bale-Signature header"
        )


def test_bot_webhook_uses_separate_secret_envs(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    secret_envs = set()
    for bot in blueprint.bots:
        content = (output_dir / f"bale/{bot.key}/webhook.py").read_text()
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith('_WEBHOOK_SECRET_ENV = "'):
                secret_envs.add(stripped)
    assert len(secret_envs) == len(blueprint.bots), (
        "Each bot must reference a distinct webhook secret env var"
    )


def test_bot_webhook_calls_dispatch(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        content = (output_dir / f"bale/{bot.key}/webhook.py").read_text()
        assert "await dispatch(update)" in content, (
            f"webhook.py for '{bot.key}' must call dispatch(update)"
        )


# ── Per-bot commands content ──────────────────────────────────────────────────


def test_bot_commands_in_dispatch_function(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        for cmd in bot.commands:
            assert cmd.command in content, (
                f"commands.py for '{bot.key}' missing command '{cmd.command}'"
            )
            assert cmd.handler in content, (
                f"commands.py for '{bot.key}' missing handler '{cmd.handler}'"
            )


def test_bot_commands_dispatch_is_async(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        assert "async def dispatch" in content


# ── Router integration ────────────────────────────────────────────────────────


def test_router_includes_bot_webhook_routers(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/api/router.py").read_text()
    for bot in blueprint.bots:
        assert f"{bot.key}_webhook_router" in content, (
            f"router.py must include {bot.key}_webhook_router"
        )
        assert f"from bale.{bot.key}.webhook import router" in content, (
            f"router.py must import {bot.key} webhook router"
        )


def test_router_bots_use_separate_webhook_routers(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / "backend/app/api/router.py").read_text()
    router_imports = [l for l in content.splitlines() if "webhook_router" in l and "import" in l]
    assert len(router_imports) == len(blueprint.bots), (
        f"router.py must import one webhook router per bot; "
        f"expected {len(blueprint.bots)}, found {len(router_imports)}"
    )


# ── Compile safety ────────────────────────────────────────────────────────────


def test_generated_bale_files_compile(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    bale_dir = output_dir / "bale"
    for py_file in sorted(bale_dir.rglob("*.py")):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            pytest.fail(
                f"Syntax error in generated file {py_file.relative_to(output_dir)}: {exc}"
            )


# ── Determinism ───────────────────────────────────────────────────────────────


def test_same_blueprint_produces_stable_bale_file_list(tmp_path: Path) -> None:
    blueprint = _load_blueprint()

    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = GeneratorCore().run(blueprint, out1)

    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = GeneratorCore().run(blueprint, out2)

    bale1 = [f for f in result1.generated_files if f.startswith("bale/")]
    bale2 = [f for f in result2.generated_files if f.startswith("bale/")]
    assert bale1 == bale2


# ── No forbidden domains ──────────────────────────────────────────────────────


def test_no_forbidden_domain_in_generated_bale_files(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    bale_dir = output_dir / "bale"
    for py_file in sorted(bale_dir.rglob("*.py")):
        content = py_file.read_text().lower()
        for domain in FORBIDDEN_DOMAINS:
            assert domain not in content, (
                f"Forbidden domain keyword '{domain}' found in generated file: {py_file.name}"
            )


# ── Manifest includes Bale files ──────────────────────────────────────────────


def test_manifest_includes_bale_shared_files(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    assert "bale/shared/client.py" in result.generated_files
    assert "bale/shared/backend_client.py" in result.generated_files
    assert "bale/shared/webhook.py" in result.generated_files
    assert "bale/shared/idempotency.py" in result.generated_files


def test_manifest_includes_per_bot_files(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        assert f"bale/{bot.key}/webhook.py" in result.generated_files
        assert f"bale/{bot.key}/commands.py" in result.generated_files
        assert f"bale/tests/test_{bot.key}_webhook.py" in result.generated_files


# ── Audience-specific template selection ──────────────────────────────────────


def test_user_bot_commands_have_registered_user_check(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    user_bots = [b for b in blueprint.bots if b.audience.value == "users"]
    assert user_bots, "Fixture must have at least one user-audience bot"

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in user_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        assert "_check_registered_user" in content, (
            f"User bot '{bot.key}' commands.py must define _check_registered_user()"
        )


def test_user_bot_dispatch_enforces_registration_when_required(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    user_bots = [b for b in blueprint.bots if b.audience.value == "users"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in user_bots:
        if not bot.security_policy.require_registered_user:
            continue
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        assert "_check_registered_user(update)" in content, (
            f"User bot '{bot.key}' dispatch() must call _check_registered_user when "
            "require_registered_user=True"
        )


def test_admin_bot_commands_have_role_verification(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [b for b in blueprint.bots if b.audience.value == "admins"]
    assert admin_bots, "Fixture must have at least one admin-audience bot"

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        assert "_verify_admin_role" in content, (
            f"Admin bot '{bot.key}' commands.py must define _verify_admin_role()"
        )


def test_admin_bot_dispatch_checks_role_before_routing(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [b for b in blueprint.bots if b.audience.value == "admins"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        dispatch_body = content[content.index("async def dispatch"):]
        verify_pos = dispatch_body.find("_verify_admin_role")
        first_cmd_pos = min(
            (dispatch_body.find(f'"{cmd.command}"') for cmd in bot.commands),
            default=len(dispatch_body),
        )
        assert 0 < verify_pos < first_cmd_pos, (
            f"Admin bot '{bot.key}' dispatch() must call _verify_admin_role() "
            "BEFORE routing to any command handler"
        )


def test_admin_bot_handlers_call_backend_audit_when_enabled(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [
        b for b in blueprint.bots
        if b.audience.value == "admins" and b.security_policy.audit_sensitive_callbacks
    ]
    assert admin_bots, "Fixture must have an admin bot with audit_sensitive_callbacks=True"

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        assert "make_backend_client" in content, (
            f"Admin bot '{bot.key}' must call backend audit client "
            "when audit_sensitive_callbacks=True"
        )
        assert "log_bot_audit" in content, (
            f"Admin bot '{bot.key}' handlers must call backend log_bot_audit()"
        )


def test_admin_bot_audit_call_present_in_each_handler(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [
        b for b in blueprint.bots
        if b.audience.value == "admins" and b.security_policy.audit_sensitive_callbacks
    ]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        for cmd in bot.commands:
            handler_start = content.find(f"async def {cmd.handler}")
            assert handler_start != -1, f"Handler '{cmd.handler}' not found"
            handler_body = content[handler_start:]
            next_def = handler_body.find("async def ", len("async def "))
            handler_body = handler_body[:next_def] if next_def != -1 else handler_body
            assert "log_bot_audit" in handler_body, (
                f"Handler '{cmd.handler}' in admin bot '{bot.key}' must call "
                "backend log_bot_audit()"
            )


def test_user_bot_commands_do_not_include_admin_checks(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    user_bots = [b for b in blueprint.bots if b.audience.value == "users"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in user_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        assert "_verify_admin_role" not in content, (
            f"User bot '{bot.key}' commands.py must not contain admin role verification"
        )


def test_admin_bot_commands_do_not_include_registration_check(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [b for b in blueprint.bots if b.audience.value == "admins"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        assert "_check_registered_user" not in content, (
            f"Admin bot '{bot.key}' commands.py must not contain user registration check"
        )


def test_user_bot_and_admin_bot_commands_are_genuinely_different(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    user_bots = {b.key: b for b in blueprint.bots if b.audience.value == "users"}
    admin_bots = {b.key: b for b in blueprint.bots if b.audience.value == "admins"}
    assert user_bots and admin_bots, "Fixture must have both user and admin bots"

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    user_key = next(iter(user_bots))
    admin_key = next(iter(admin_bots))
    user_content = (output_dir / f"bale/{user_key}/commands.py").read_text()
    admin_content = (output_dir / f"bale/{admin_key}/commands.py").read_text()
    assert user_content != admin_content, (
        "User bot and admin bot commands.py must have different content"
    )


# ── Test stub audience-specific content ───────────────────────────────────────


def test_user_bot_test_stub_has_registration_test(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    user_bots = [
        b for b in blueprint.bots
        if b.audience.value == "users" and b.security_policy.require_registered_user
    ]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in user_bots:
        content = (output_dir / f"bale/tests/test_{bot.key}_webhook.py").read_text()
        assert "test_unregistered_user_is_rejected" in content, (
            f"User bot test stub must include test_unregistered_user_is_rejected"
        )


def test_admin_bot_test_stub_has_role_rejection_test(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [b for b in blueprint.bots if b.audience.value == "admins"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/tests/test_{bot.key}_webhook.py").read_text()
        assert "test_non_admin_sender_is_rejected" in content, (
            f"Admin bot test stub must include test_non_admin_sender_is_rejected"
        )


def test_admin_bot_test_stub_has_audit_log_test_when_enabled(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [
        b for b in blueprint.bots
        if b.audience.value == "admins" and b.security_policy.audit_sensitive_callbacks
    ]
    assert admin_bots, "Fixture must have admin bot with audit_sensitive_callbacks=True"

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/tests/test_{bot.key}_webhook.py").read_text()
        assert "test_admin_command_writes_audit_log" in content, (
            f"Admin bot test stub must include test_admin_command_writes_audit_log"
        )


# ── Single-bot Blueprint: only that bot's files generated ────────────────────


def _load_single_bot_blueprint() -> BotBlueprint:
    with open(FIXTURES / "valid_single_user_bot.yaml") as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


def test_single_bot_blueprint_generates_only_one_bot(tmp_path: Path) -> None:
    blueprint = _load_single_bot_blueprint()
    assert len(blueprint.bots) == 1, "Single-bot fixture must define exactly one bot"

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    bot_dirs = [
        p.name for p in (output_dir / "bale").iterdir()
        if p.is_dir() and p.name not in ("shared", "tests")
    ]
    assert len(bot_dirs) == 1, (
        f"Single-bot Blueprint must generate exactly one bot directory; got: {bot_dirs}"
    )
    assert bot_dirs[0] == blueprint.bots[0].key


def test_single_user_bot_uses_user_bot_template(tmp_path: Path) -> None:
    blueprint = _load_single_bot_blueprint()
    bot = blueprint.bots[0]
    assert bot.audience.value == "users"

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
    assert "_check_registered_user" in content, (
        "Single user bot must use user_bot template (has _check_registered_user)"
    )
    assert "_verify_admin_role" not in content, (
        "Single user bot must not have admin role check"
    )


def test_single_bot_admin_bot_file_not_generated(tmp_path: Path) -> None:
    blueprint = _load_single_bot_blueprint()

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    assert "bale/admin_bot/webhook.py" not in result.generated_files
    assert "bale/admin_bot/commands.py" not in result.generated_files
    assert not (output_dir / "bale/admin_bot").exists()


def test_single_bot_generated_files_compile(tmp_path: Path) -> None:
    blueprint = _load_single_bot_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for py_file in sorted((output_dir / "bale").rglob("*.py")):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            pytest.fail(
                f"Syntax error in single-bot generated file "
                f"{py_file.relative_to(output_dir)}: {exc}"
            )


def test_single_bot_manifest_contains_only_that_bot(tmp_path: Path) -> None:
    blueprint = _load_single_bot_blueprint()
    bot_key = blueprint.bots[0].key

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)

    bale_bot_files = [
        f for f in result.generated_files
        if f.startswith("bale/") and "shared" not in f and "tests" not in f and "__init__" not in f
    ]
    assert all(bot_key in f for f in bale_bot_files), (
        f"Manifest must only contain files for '{bot_key}', got: {bale_bot_files}"
    )


# ── Phase 6c: Idempotency helpers ─────────────────────────────────────────────


def test_bale_idempotency_helper_is_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)
    assert "bale/shared/idempotency.py" in generated
    assert (output_dir / "bale/shared/idempotency.py").exists()


def test_idempotency_helper_has_expected_functions(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/idempotency.py").read_text()
    assert "def extract_update_id" in content, "idempotency.py must define extract_update_id()"
    assert "async def is_duplicate_update" in content, (
        "idempotency.py must define is_duplicate_update()"
    )
    assert "async def mark_update_processed" in content, (
        "idempotency.py must define mark_update_processed()"
    )


def test_idempotency_helper_references_processed_updates_table(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/idempotency.py").read_text()
    assert "processed_updates" in content, (
        "idempotency.py must reference the processed_updates table"
    )


def test_idempotency_helper_compiles(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    idempotency_file = output_dir / "bale/shared/idempotency.py"
    try:
        py_compile.compile(str(idempotency_file), doraise=True)
    except py_compile.PyCompileError as exc:
        pytest.fail(f"Syntax error in bale/shared/idempotency.py: {exc}")


# ── Phase 6c: Webhook idempotency calls ───────────────────────────────────────


def test_user_webhook_imports_idempotency(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    user_bots = [b for b in blueprint.bots if b.audience.value == "users"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in user_bots:
        content = (output_dir / f"bale/{bot.key}/webhook.py").read_text()
        assert "from bale.shared.idempotency import" in content, (
            f"User bot '{bot.key}' webhook.py must import from bale.shared.idempotency"
        )


def test_admin_webhook_imports_idempotency(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [b for b in blueprint.bots if b.audience.value == "admins"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/{bot.key}/webhook.py").read_text()
        assert "from bale.shared.idempotency import" in content, (
            f"Admin bot '{bot.key}' webhook.py must import from bale.shared.idempotency"
        )


def test_user_webhook_calls_idempotency_check(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    user_bots = [b for b in blueprint.bots if b.audience.value == "users"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in user_bots:
        content = (output_dir / f"bale/{bot.key}/webhook.py").read_text()
        assert "is_duplicate_update" in content, (
            f"User bot '{bot.key}' webhook.py must call is_duplicate_update()"
        )
        assert "extract_update_id" in content, (
            f"User bot '{bot.key}' webhook.py must call extract_update_id()"
        )


def test_admin_webhook_calls_idempotency_check(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [b for b in blueprint.bots if b.audience.value == "admins"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/{bot.key}/webhook.py").read_text()
        assert "is_duplicate_update" in content, (
            f"Admin bot '{bot.key}' webhook.py must call is_duplicate_update()"
        )
        assert "extract_update_id" in content, (
            f"Admin bot '{bot.key}' webhook.py must call extract_update_id()"
        )


def test_webhooks_mark_update_processed_after_dispatch(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        content = (output_dir / f"bale/{bot.key}/webhook.py").read_text()
        assert "await mark_update_processed(" in content, (
            f"Bot '{bot.key}' webhook.py must call mark_update_processed() after dispatch"
        )
        dispatch_pos = content.find("await dispatch(update)")
        mark_pos = content.find("await mark_update_processed(")
        assert dispatch_pos != -1 and mark_pos != -1, (
            f"Bot '{bot.key}' webhook.py must contain both dispatch() and mark_update_processed()"
        )
        assert dispatch_pos < mark_pos, (
            f"Bot '{bot.key}' webhook.py must call mark_update_processed() AFTER dispatch()"
        )


def test_idempotency_check_before_dispatch_in_webhooks(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in blueprint.bots:
        content = (output_dir / f"bale/{bot.key}/webhook.py").read_text()
        duplicate_pos = content.find("is_duplicate_update")
        dispatch_pos = content.find("await dispatch(update)")
        assert duplicate_pos != -1 and dispatch_pos != -1
        assert duplicate_pos < dispatch_pos, (
            f"Bot '{bot.key}' webhook.py must check is_duplicate_update() BEFORE dispatch()"
        )


# ── Phase 6c: Admin permission check stubs ────────────────────────────────────


def test_admin_commands_have_permission_check_helper(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [b for b in blueprint.bots if b.audience.value == "admins"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        assert "async def _check_permission" in content, (
            f"Admin bot '{bot.key}' commands.py must define _check_permission()"
        )


def test_admin_handler_calls_permission_check_per_command(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [b for b in blueprint.bots if b.audience.value == "admins"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        for cmd in bot.commands:
            handler_start = content.find(f"async def {cmd.handler}")
            assert handler_start != -1, f"Handler '{cmd.handler}' not found"
            handler_body = content[handler_start:]
            next_def = handler_body.find("async def ", len("async def "))
            handler_body = handler_body[:next_def] if next_def != -1 else handler_body
            assert "_check_permission" in handler_body, (
                f"Handler '{cmd.handler}' in admin bot '{bot.key}' must call _check_permission()"
            )


def test_admin_permission_check_before_audit_in_handlers(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    admin_bots = [
        b for b in blueprint.bots
        if b.audience.value == "admins" and b.security_policy.audit_sensitive_callbacks
    ]
    assert admin_bots, "Fixture must have an admin bot with audit_sensitive_callbacks=True"

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in admin_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        for cmd in bot.commands:
            handler_start = content.find(f"async def {cmd.handler}")
            assert handler_start != -1
            handler_body = content[handler_start:]
            next_def = handler_body.find("async def ", len("async def "))
            handler_body = handler_body[:next_def] if next_def != -1 else handler_body

            perm_pos = handler_body.find("_check_permission")
            audit_pos = handler_body.find("log_bot_audit")
            assert perm_pos != -1 and audit_pos != -1, (
                f"Handler '{cmd.handler}' must have both _check_permission and log_bot_audit"
            )
            assert perm_pos < audit_pos, (
                f"Handler '{cmd.handler}' must call _check_permission() BEFORE log_bot_audit()"
            )


def test_user_commands_do_not_have_permission_check_helper(tmp_path: Path) -> None:
    blueprint = _load_blueprint()
    user_bots = [b for b in blueprint.bots if b.audience.value == "users"]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)

    for bot in user_bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        assert "_check_permission" not in content, (
            f"User bot '{bot.key}' commands.py must not define admin _check_permission()"
        )
