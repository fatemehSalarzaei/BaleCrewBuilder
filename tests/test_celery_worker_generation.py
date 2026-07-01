"""Task 07: Celery worker generation is opt-in via Blueprint modules."""
import py_compile
from pathlib import Path

import yaml

from app.generator import GeneratorCore
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_blueprint(*, celery_enabled: bool) -> BotBlueprint:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        raw = yaml.safe_load(f)

    modules = raw["generation"]["enabled_modules"]
    if celery_enabled and "celery_worker" not in modules:
        modules.append("celery_worker")
    if celery_enabled:
        raw["generation"]["custom_logic_blocks"] = ["sync_external_index"]
    return BotBlueprint.model_validate(raw)


def _run(tmp_path: Path, *, celery_enabled: bool) -> tuple[Path, list[str]]:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = GeneratorCore().run(_load_blueprint(celery_enabled=celery_enabled), output_dir)
    return output_dir, result.generated_files


def test_worker_files_generated_when_celery_module_enabled(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path, celery_enabled=True)

    expected = [
        "backend/app/workers/__init__.py",
        "backend/app/workers/celery_app.py",
        "backend/app/workers/tasks.py",
    ]
    for rel_path in expected:
        assert rel_path in generated
        assert (output_dir / rel_path).exists()


def test_worker_files_not_generated_when_celery_module_disabled(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path, celery_enabled=False)

    assert "backend/app/workers/__init__.py" not in generated
    assert "backend/app/workers/celery_app.py" not in generated
    assert "backend/app/workers/tasks.py" not in generated
    assert not (output_dir / "backend/app/workers").exists()


def test_config_contains_celery_settings_when_enabled(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path, celery_enabled=True)
    content = (output_dir / "backend/app/core/config.py").read_text()

    assert "CELERY_BROKER_URL" in content
    assert "CELERY_RESULT_BACKEND" in content
    assert "celery_broker_url" in content
    assert "celery_result_backend" in content
    assert "redis://localhost:6379/0" in content


def test_config_omits_celery_settings_when_disabled(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path, celery_enabled=False)
    content = (output_dir / "backend/app/core/config.py").read_text()

    assert "CELERY_BROKER_URL" not in content
    assert "CELERY_RESULT_BACKEND" not in content
    assert "celery_broker_url" not in content
    assert "celery_result_backend" not in content


def test_requirements_include_celery_dependencies_when_enabled(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path, celery_enabled=True)
    content = (output_dir / "backend/requirements.txt").read_text()

    assert "celery>=" in content
    assert "redis>=" in content


def test_requirements_omit_celery_dependencies_when_disabled(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path, celery_enabled=False)
    content = (output_dir / "backend/requirements.txt").read_text()

    assert "celery>=" not in content
    assert "redis>=" not in content


def test_worker_tasks_are_service_layer_stubs_without_business_logic(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path, celery_enabled=True)
    content = (output_dir / "backend/app/workers/tasks.py").read_text()

    assert "run_background_action" in content
    assert "view_resources_flow" in content
    assert "sync_external_index" in content
    assert "TODO: call the matching backend service method" in content
    assert "Do not implement business rules directly" in content
    assert "raise NotImplementedError" not in content


def test_worker_files_do_not_hardcode_broker_credentials(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path, celery_enabled=True)

    for rel_path in (
        "backend/app/core/config.py",
        "backend/app/workers/celery_app.py",
        "backend/app/workers/tasks.py",
    ):
        content = (output_dir / rel_path).read_text().lower()
        assert "password" not in content
        assert "secret" not in content or rel_path.endswith("config.py")
        assert "redis://:/" not in content


def test_generated_worker_python_files_compile(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path, celery_enabled=True)

    for rel_path in (
        "backend/app/workers/celery_app.py",
        "backend/app/workers/tasks.py",
    ):
        py_compile.compile(str(output_dir / rel_path), doraise=True)
