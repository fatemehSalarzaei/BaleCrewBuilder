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
    output_dir.mkdir(parents=True)
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


def test_deployment_config_includes_worker_only_when_enabled(tmp_path: Path) -> None:
    enabled_dir, _ = _run(tmp_path / "enabled", celery_enabled=True)
    disabled_dir, _ = _run(tmp_path / "disabled", celery_enabled=False)

    enabled_compose = (enabled_dir / "deploy/docker-compose.prod.yml").read_text()
    disabled_compose = (disabled_dir / "deploy/docker-compose.prod.yml").read_text()

    assert "celery_worker:" in enabled_compose
    assert "app.workers.celery_app.celery_app" in enabled_compose
    assert "celery_worker:" not in disabled_compose
    assert "app.workers.celery_app.celery_app" not in disabled_compose


def test_env_example_includes_celery_vars_only_when_enabled(tmp_path: Path) -> None:
    enabled_dir, _ = _run(tmp_path / "enabled", celery_enabled=True)
    disabled_dir, _ = _run(tmp_path / "disabled", celery_enabled=False)

    enabled_env = (enabled_dir / "deploy/.env.example").read_text()
    disabled_env = (disabled_dir / "deploy/.env.example").read_text()

    assert "CELERY_BROKER_URL=redis://redis:6379/0" in enabled_env
    assert "CELERY_RESULT_BACKEND=redis://redis:6379/1" in enabled_env
    assert "CELERY_BROKER_URL" not in disabled_env
    assert "CELERY_RESULT_BACKEND" not in disabled_env


def test_deployment_docs_mention_worker_only_when_enabled(tmp_path: Path) -> None:
    enabled_dir, _ = _run(tmp_path / "enabled", celery_enabled=True)
    disabled_dir, _ = _run(tmp_path / "disabled", celery_enabled=False)

    enabled_docs = (enabled_dir / "docs/deployment.md").read_text()
    disabled_docs = (disabled_dir / "docs/deployment.md").read_text()

    assert "CELERY_BROKER_URL" in enabled_docs
    assert "`celery_worker`: Celery worker using the generated backend image" in enabled_docs
    assert "CELERY_BROKER_URL" not in disabled_docs
    assert "`celery_worker`: Celery worker using the generated backend image" not in disabled_docs


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
