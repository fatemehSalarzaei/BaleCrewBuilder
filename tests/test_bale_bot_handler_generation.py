"""Task 05: generated Bale bot handlers delegate to backend clients."""
import py_compile
from pathlib import Path

import yaml

from app.generator import GeneratorCore
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_blueprint() -> BotBlueprint:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


def _run(tmp_path: Path) -> tuple[BotBlueprint, Path, list[str]]:
    blueprint = _load_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(blueprint, output_dir)
    return blueprint, output_dir, result.generated_files


def test_backend_client_file_is_generated(tmp_path: Path) -> None:
    _, output_dir, generated = _run(tmp_path)

    assert "bale/shared/backend_client.py" in generated
    content = (output_dir / "bale/shared/backend_client.py").read_text()
    assert "class BackendClient" in content
    assert "BACKEND_BASE_URL" in content
    assert "BACKEND_SERVICE_TOKEN" in content
    assert "httpx.AsyncClient" in content


def test_command_dispatch_calls_expected_handlers(tmp_path: Path) -> None:
    blueprint, output_dir, _ = _run(tmp_path)

    for bot in blueprint.bots:
        content = (output_dir / f"bale/{bot.key}/commands.py").read_text()
        for command in bot.commands:
            assert f'if text.startswith("{command.command}")' in content
            assert f"await {command.handler}(update)" in content


def test_user_bot_handlers_delegate_to_backend_client(tmp_path: Path) -> None:
    blueprint, output_dir, _ = _run(tmp_path)
    user_bot = next(bot for bot in blueprint.bots if bot.audience.value == "users")
    content = (output_dir / f"bale/{user_bot.key}/commands.py").read_text()

    assert "from bale.shared.backend_client import BackendClient, make_backend_client" in content
    assert "verify_registered_user(update, _BOT_KEY)" in content
    assert "return True" not in content
    assert "call_service_action(" in content
    assert "make_user_bot_client().send_message" in content
    assert "raise NotImplementedError" not in content


def test_user_bot_does_not_include_admin_only_paths(tmp_path: Path) -> None:
    blueprint, output_dir, _ = _run(tmp_path)
    user_bot = next(bot for bot in blueprint.bots if bot.audience.value == "users")
    admin_bot = next(bot for bot in blueprint.bots if bot.audience.value == "admins")
    content = (output_dir / f"bale/{user_bot.key}/commands.py").read_text()

    assert "_verify_admin_role" not in content
    assert "_check_permission" not in content
    for command in admin_bot.commands:
        if command.command not in {cmd.command for cmd in user_bot.commands}:
            assert command.command not in content
        assert command.handler not in content


def test_admin_bot_uses_backend_authorization_and_audit(tmp_path: Path) -> None:
    blueprint, output_dir, _ = _run(tmp_path)
    admin_bot = next(bot for bot in blueprint.bots if bot.audience.value == "admins")
    content = (output_dir / f"bale/{admin_bot.key}/commands.py").read_text()

    assert "verify_admin_role(update, _BOT_KEY)" in content
    assert "check_permission(update, _BOT_KEY, permission_key)" in content
    assert "log_bot_audit(" in content
    assert "call_service_action(" in content
    assert "make_admin_bot_client().send_message" in content
    assert "raise NotImplementedError" not in content


def test_backend_client_fails_closed_for_unavailable_backend(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)
    content = (output_dir / "bale/shared/backend_client.py").read_text()

    assert "return False" in content
    assert "return None" in content
    assert "except httpx.HTTPError" in content


def test_generated_bale_handler_files_do_not_hardcode_token_values(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)

    for rel_path in (
        "bale/shared/backend_client.py",
        "bale/user_bot/commands.py",
        "bale/admin_bot/commands.py",
    ):
        content = (output_dir / rel_path).read_text()
        assert "USER_BOT_TOKEN =" not in content
        assert "ADMIN_BOT_TOKEN =" not in content
        assert "BACKEND_SERVICE_TOKEN =" not in content


def test_generated_bale_handler_files_compile(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)

    for rel_path in (
        "bale/shared/backend_client.py",
        "bale/user_bot/commands.py",
        "bale/admin_bot/commands.py",
    ):
        py_compile.compile(str(output_dir / rel_path), doraise=True)
