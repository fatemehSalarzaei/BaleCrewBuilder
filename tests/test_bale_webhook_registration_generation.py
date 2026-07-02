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


def test_webhook_registration_helpers_are_generated(tmp_path: Path) -> None:
    _, output_dir, generated = _run(tmp_path)

    expected = [
        "bale/scripts/__init__.py",
        "bale/scripts/register_webhooks.py",
        "bale/scripts/delete_webhooks.py",
        "bale/tests/test_webhook_registration_config.py",
        "bale/tests/test_bale_integration_optional.py",
    ]
    for rel_path in expected:
        assert rel_path in generated
        assert (output_dir / rel_path).exists()


def test_registration_helper_contains_all_blueprint_bots(tmp_path: Path) -> None:
    blueprint, output_dir, _ = _run(tmp_path)

    content = (output_dir / "bale/scripts/register_webhooks.py").read_text()

    for bot in blueprint.bots:
        assert f'key="{bot.key}"' in content
        assert f'token_env="{bot.token_env}"' in content
        assert f'webhook_path="{bot.webhook_path}"' in content
        assert f"make_{bot.key}_client" in content


def test_registration_helper_keeps_user_and_admin_paths_separate(tmp_path: Path) -> None:
    blueprint, output_dir, _ = _run(tmp_path)

    content = (output_dir / "bale/scripts/register_webhooks.py").read_text()

    paths = [bot.webhook_path for bot in blueprint.bots]
    assert len(paths) == len(set(paths))
    for path in paths:
        assert content.count(path) == 1


def test_registration_helper_supports_dry_run_without_network(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)

    content = (output_dir / "bale/scripts/register_webhooks.py").read_text()

    assert "--dry-run" in content
    assert "if dry_run:" in content
    assert "client.set_webhook" in content


def test_delete_helper_supports_dry_run_without_network(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)

    content = (output_dir / "bale/scripts/delete_webhooks.py").read_text()

    assert "--dry-run" in content
    assert "if dry_run:" in content
    assert "client.delete_webhook" in content


def test_generated_registration_tests_skip_real_network_by_default(
    tmp_path: Path,
) -> None:
    _, output_dir, _ = _run(tmp_path)

    content = (output_dir / "bale/tests/test_bale_integration_optional.py").read_text()

    assert "RUN_BALE_INTEGRATION_TESTS" in content
    assert "skipif" in content
    assert "client.get_me" in content


def test_generated_helpers_do_not_hardcode_token_values(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)

    for rel_path in [
        "bale/scripts/register_webhooks.py",
        "bale/scripts/delete_webhooks.py",
        "bale/tests/test_bale_integration_optional.py",
    ]:
        content = (output_dir / rel_path).read_text()
        assert "your-token" not in content
        assert "secret-token" not in content
        assert "print(config.token_env)" not in content


def test_generated_registration_python_files_compile(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)

    for rel_path in [
        "bale/scripts/register_webhooks.py",
        "bale/scripts/delete_webhooks.py",
        "bale/tests/test_webhook_registration_config.py",
        "bale/tests/test_bale_integration_optional.py",
    ]:
        py_compile.compile(str(output_dir / rel_path), doraise=True)
