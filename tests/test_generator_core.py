"""Tests for Phase 6 Deterministic Generator Core."""
import ast
import json
import zipfile
from pathlib import Path

import pytest
import yaml

from app.generator import GeneratorCore
from app.generator.file_manifest import compute_blueprint_hash
from app.generator.packager import package_as_zip
from app.generator.template_registry import UnknownModuleError, UnknownTemplateProfileError
from app.generator.validators import PathTraversalError, assert_safe_path
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_valid_blueprint() -> BotBlueprint:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


# ── Registry rejection ────────────────────────────────────────────────────────


def test_unknown_template_profile_raises_error(tmp_path: Path) -> None:
    blueprint = _load_valid_blueprint()
    modified = blueprint.model_copy(
        update={
            "generation": blueprint.generation.model_copy(
                update={"template_profile": "nonexistent_profile_xyz"}
            )
        }
    )
    with pytest.raises(UnknownTemplateProfileError):
        GeneratorCore().run(modified, tmp_path)


def test_unknown_module_raises_error(tmp_path: Path) -> None:
    blueprint = _load_valid_blueprint()
    modified = blueprint.model_copy(
        update={
            "generation": blueprint.generation.model_copy(
                update={"enabled_modules": ["nonexistent_module_xyz"]}
            )
        }
    )
    with pytest.raises(UnknownModuleError):
        GeneratorCore().run(modified, tmp_path)


# ── Path safety ───────────────────────────────────────────────────────────────


def test_path_traversal_raises_error(tmp_path: Path) -> None:
    with pytest.raises(PathTraversalError):
        assert_safe_path("../../etc/passwd", tmp_path)


def test_absolute_path_raises_error(tmp_path: Path) -> None:
    with pytest.raises(PathTraversalError):
        assert_safe_path("/etc/passwd", tmp_path)


def test_null_byte_in_path_raises_error(tmp_path: Path) -> None:
    with pytest.raises(PathTraversalError):
        assert_safe_path("file\x00name.txt", tmp_path)


def test_safe_path_within_root_succeeds(tmp_path: Path) -> None:
    resolved = assert_safe_path("subdir/file.txt", tmp_path)
    assert resolved == (tmp_path / "subdir" / "file.txt").resolve()


# ── Determinism ───────────────────────────────────────────────────────────────


def test_blueprint_hash_is_deterministic() -> None:
    blueprint = _load_valid_blueprint()
    assert compute_blueprint_hash(blueprint) == compute_blueprint_hash(blueprint)


def test_two_equal_blueprints_produce_same_hash() -> None:
    bp1 = _load_valid_blueprint()
    bp2 = _load_valid_blueprint()
    assert compute_blueprint_hash(bp1) == compute_blueprint_hash(bp2)


def test_same_blueprint_produces_same_file_list(tmp_path: Path) -> None:
    blueprint = _load_valid_blueprint()
    out1 = tmp_path / "run1"
    out1.mkdir()
    out2 = tmp_path / "run2"
    out2.mkdir()
    result1 = GeneratorCore().run(blueprint, out1)
    result2 = GeneratorCore().run(blueprint, out2)
    assert result1.generated_files == result2.generated_files


# ── Manifest production ───────────────────────────────────────────────────────


def test_manifest_file_is_created(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(_load_valid_blueprint(), output_dir)
    assert (output_dir / "docs" / "generation_manifest.json").exists()


def test_manifest_contains_required_fields(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(_load_valid_blueprint(), output_dir)
    manifest = json.loads((output_dir / "docs" / "generation_manifest.json").read_text())
    assert "blueprint_hash" in manifest
    assert "generated_files" in manifest
    assert "template_profile" in manifest
    assert "enabled_modules" in manifest
    assert "generated_at" in manifest


def test_manifest_hash_matches_blueprint(tmp_path: Path) -> None:
    blueprint = _load_valid_blueprint()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(blueprint, output_dir)
    manifest = json.loads((output_dir / "docs" / "generation_manifest.json").read_text())
    assert manifest["blueprint_hash"] == compute_blueprint_hash(blueprint)


def test_all_manifest_files_exist_on_disk(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(_load_valid_blueprint(), output_dir)
    for rel_path in result.generated_files:
        assert (output_dir / rel_path).exists(), f"Missing generated file: {rel_path}"


# ── No LLM in generator ───────────────────────────────────────────────────────


def test_no_llm_imports_in_generator() -> None:
    generator_dir = Path(__file__).parent.parent / "app" / "generator"
    forbidden = {"openai", "anthropic", "crewai", "langchain"}
    for py_file in sorted(generator_dir.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in forbidden, (
                        f"{py_file.name} imports forbidden LLM library {top!r}"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top not in forbidden, (
                    f"{py_file.name} imports forbidden LLM library {top!r}"
                )


# ── ZIP packaging ─────────────────────────────────────────────────────────────


def test_zip_packaging_creates_valid_archive(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(_load_valid_blueprint(), output_dir)

    zip_path = tmp_path / "output.zip"
    result = package_as_zip(output_dir, zip_path)

    assert result.exists()
    assert zipfile.is_zipfile(result)


def test_zip_contains_all_generated_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    gen_result = GeneratorCore().run(_load_valid_blueprint(), output_dir)

    zip_path = tmp_path / "output.zip"
    package_as_zip(output_dir, zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
    for rel_path in gen_result.generated_files:
        assert rel_path in names, f"Missing from ZIP: {rel_path}"
