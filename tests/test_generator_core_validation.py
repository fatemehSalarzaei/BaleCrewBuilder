from pathlib import Path

import pytest
import yaml

from app.generator import GeneratorCore
from app.generator.validators import InvalidBlueprintForGenerationError
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_blueprint(filename: str) -> BotBlueprint:
    with open(FIXTURES / filename) as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


def _assert_rejected_before_writing(
    blueprint: BotBlueprint,
    output_dir: Path,
    expected_message: str,
) -> None:
    with pytest.raises(InvalidBlueprintForGenerationError) as exc_info:
        GeneratorCore().run(blueprint, output_dir)

    assert expected_message in str(exc_info.value)
    assert not (output_dir / "docs/generation_manifest.json").exists()
    assert not output_dir.exists() or not any(output_dir.rglob("*"))


def test_missing_core_entities_rejected_before_writing(tmp_path: Path) -> None:
    blueprint = _load_blueprint("valid_multi_bot.yaml")
    modified = blueprint.model_copy(
        deep=True,
        update={
            "database": blueprint.database.model_copy(
                update={"entities": blueprint.database.entities[:3]}
            )
        },
    )

    _assert_rejected_before_writing(
        modified,
        tmp_path / "output",
        "Database is missing required core entities",
    )


def test_duplicate_bot_token_env_rejected_before_writing(tmp_path: Path) -> None:
    blueprint = _load_blueprint("valid_multi_bot.yaml")
    bots = list(blueprint.bots)
    bots[1] = bots[1].model_copy(update={"token_env": bots[0].token_env})
    modified = blueprint.model_copy(deep=True, update={"bots": bots})

    _assert_rejected_before_writing(
        modified,
        tmp_path / "output",
        "share token_env",
    )


def test_duplicate_webhook_path_rejected_before_writing(tmp_path: Path) -> None:
    blueprint = _load_blueprint("valid_multi_bot.yaml")
    bots = list(blueprint.bots)
    bots[1] = bots[1].model_copy(update={"webhook_path": bots[0].webhook_path})
    modified = blueprint.model_copy(deep=True, update={"bots": bots})

    _assert_rejected_before_writing(
        modified,
        tmp_path / "output",
        "share webhook_path",
    )


def test_admin_route_with_non_admin_role_rejected_before_writing(
    tmp_path: Path,
) -> None:
    blueprint = _load_blueprint("valid_multi_bot.yaml")
    routes = list(blueprint.miniapp.routes)
    routes[0] = routes[0].model_copy(
        update={"path": "/admin/user-visible", "allowed_roles": ["member"]}
    )
    modified = blueprint.model_copy(
        deep=True,
        update={
            "miniapp": blueprint.miniapp.model_copy(update={"routes": routes})
        },
    )

    _assert_rejected_before_writing(
        modified,
        tmp_path / "output",
        "non-admin roles",
    )


def test_generator_error_message_includes_all_validation_errors(
    tmp_path: Path,
) -> None:
    blueprint = _load_blueprint("valid_multi_bot.yaml")
    bots = list(blueprint.bots)
    bots[1] = bots[1].model_copy(
        update={
            "token_env": bots[0].token_env,
            "webhook_path": bots[0].webhook_path,
        }
    )
    modified = blueprint.model_copy(deep=True, update={"bots": bots})

    with pytest.raises(InvalidBlueprintForGenerationError) as exc_info:
        GeneratorCore().run(modified, tmp_path / "output")

    message = str(exc_info.value)
    assert "share token_env" in message
    assert "share webhook_path" in message
    assert not (tmp_path / "output" / "docs/generation_manifest.json").exists()


def test_valid_support_ticket_fixture_still_generates(tmp_path: Path) -> None:
    output_dir = tmp_path / "support"

    result = GeneratorCore().run(_load_blueprint("support_ticket_like.yaml"), output_dir)

    assert "docs/generation_manifest.json" in result.generated_files


def test_valid_appointment_form_fixture_still_generates(tmp_path: Path) -> None:
    output_dir = tmp_path / "appointment"

    result = GeneratorCore().run(_load_blueprint("appointment_form_like.yaml"), output_dir)

    assert "docs/generation_manifest.json" in result.generated_files


def test_generator_validation_does_not_mutate_blueprint(tmp_path: Path) -> None:
    blueprint = _load_blueprint("valid_multi_bot.yaml")
    before = blueprint.model_dump(mode="json")

    GeneratorCore().run(blueprint, tmp_path / "output")

    assert blueprint.model_dump(mode="json") == before
