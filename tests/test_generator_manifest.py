import json
from pathlib import Path

import yaml

from app.generator import GeneratorCore
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_blueprint() -> BotBlueprint:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


def _generate_manifest(tmp_path: Path) -> dict:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(_load_blueprint(), output_dir)
    return json.loads((output_dir / "docs/generation_manifest.json").read_text())


def test_manifest_includes_contract_required_metadata(tmp_path: Path) -> None:
    manifest = _generate_manifest(tmp_path)

    assert manifest["template_version"] == "unversioned"
    assert manifest["validation_result"] == {"is_valid": True, "errors": []}
    assert manifest["test_command_results"] == []


def test_manifest_keeps_existing_fields_for_backward_compatibility(
    tmp_path: Path,
) -> None:
    manifest = _generate_manifest(tmp_path)

    assert manifest["blueprint_hash"]
    assert manifest["template_profile"] == "fastapi_react_bale_v1"
    assert isinstance(manifest["enabled_modules"], list)
    assert isinstance(manifest["custom_logic_blocks"], list)
    assert isinstance(manifest["generated_files"], list)
    assert manifest["generated_at"]


def test_manifest_generated_files_remain_sorted(tmp_path: Path) -> None:
    manifest = _generate_manifest(tmp_path)

    assert manifest["generated_files"] == sorted(manifest["generated_files"])
