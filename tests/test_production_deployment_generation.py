"""Generated production deployment template tests."""
from pathlib import Path

import yaml

from app.generator import GeneratorCore
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"

DEPLOYMENT_FILES = [
    "backend/Dockerfile",
    "frontend/Dockerfile",
    "deploy/docker-compose.prod.yml",
    "deploy/.env.example",
    "docs/deployment.md",
]


def _load_blueprint(filename: str, *, celery_enabled: bool = False) -> BotBlueprint:
    with open(FIXTURES / filename) as f:
        raw = yaml.safe_load(f)
    if celery_enabled and "celery_worker" not in raw["generation"]["enabled_modules"]:
        raw["generation"]["enabled_modules"].append("celery_worker")
    return BotBlueprint.model_validate(raw)


def _run(
    tmp_path: Path,
    filename: str = "valid_multi_bot.yaml",
    *,
    celery_enabled: bool = False,
) -> tuple[Path, list[str]]:
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)
    result = GeneratorCore().run(
        _load_blueprint(filename, celery_enabled=celery_enabled),
        output_dir,
    )
    return output_dir, result.generated_files


def test_deployment_files_are_generated(tmp_path: Path) -> None:
    output_dir, generated = _run(tmp_path)

    for rel_path in DEPLOYMENT_FILES:
        assert rel_path in generated
        assert (output_dir / rel_path).exists()


def test_backend_dockerfile_uses_python_312_and_requirements(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/Dockerfile").read_text()

    assert "FROM python:3.12-slim" in content
    assert "COPY requirements.txt" in content
    assert "pip install --no-cache-dir -r requirements.txt" in content
    assert "uvicorn" in content
    assert "SECRET_KEY" not in content


def test_frontend_dockerfile_builds_vite_and_serves_with_nginx(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "frontend/Dockerfile").read_text()

    assert "FROM node:20-alpine AS build" in content
    assert "ARG VITE_API_BASE_URL" in content
    assert "npm run build" in content
    assert "FROM nginx:1.27-alpine" in content
    assert "/usr/share/nginx/html" in content


def test_prod_compose_has_core_services_without_celery_by_default(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "deploy/docker-compose.prod.yml").read_text()

    assert "backend:" in content
    assert "frontend:" in content
    assert "postgres:" in content
    assert "redis:" in content
    assert "celery_worker:" not in content
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD}" in content


def test_prod_compose_includes_celery_only_when_enabled(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path, celery_enabled=True)
    content = (output_dir / "deploy/docker-compose.prod.yml").read_text()

    assert "celery_worker:" in content
    assert "celery_app.celery_app" in content


def test_env_example_includes_admin_token_only_for_admin_bot(tmp_path: Path) -> None:
    multi_output, _ = _run(tmp_path / "multi", "valid_multi_bot.yaml")
    single_output, _ = _run(tmp_path / "single", "valid_single_user_bot.yaml")

    multi_env = (multi_output / "deploy/.env.example").read_text()
    single_env = (single_output / "deploy/.env.example").read_text()

    assert "USER_BOT_TOKEN=" in multi_env
    assert "ADMIN_BOT_TOKEN=" in multi_env
    assert "USER_BOT_TOKEN=" in single_env
    assert "ADMIN_BOT_TOKEN=" not in single_env


def test_env_example_has_required_runtime_variables(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "deploy/.env.example").read_text()

    for key in (
        "DATABASE_URL=",
        "REDIS_URL=",
        "SECRET_KEY=",
        "BACKEND_BASE_URL=",
        "BACKEND_SERVICE_TOKEN=",
        "VITE_API_BASE_URL=",
        "USER_BOT_WEBHOOK_URL=",
        "ADMIN_BOT_WEBHOOK_URL=",
    ):
        assert key in content


def test_env_example_includes_celery_settings_only_when_enabled(tmp_path: Path) -> None:
    disabled_output, _ = _run(tmp_path / "disabled")
    enabled_output, _ = _run(tmp_path / "enabled", celery_enabled=True)

    disabled_env = (disabled_output / "deploy/.env.example").read_text()
    enabled_env = (enabled_output / "deploy/.env.example").read_text()

    assert "CELERY_BROKER_URL=" not in disabled_env
    assert "CELERY_RESULT_BACKEND=" not in disabled_env
    assert "CELERY_BROKER_URL=" in enabled_env
    assert "CELERY_RESULT_BACKEND=" in enabled_env


def test_deployment_guide_documents_required_steps(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path, celery_enabled=True)
    content = (output_dir / "docs/deployment.md").read_text()

    assert "docker compose -f deploy/docker-compose.prod.yml" in content
    assert "Database migration" in content
    assert 'alembic revision --autogenerate -m "initial"' in content
    assert "Bale webhook registration" in content
    assert "Health checks" in content
    assert "celery_worker" in content


def test_deployment_templates_do_not_contain_real_secret_values(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path, celery_enabled=True)

    for rel_path in DEPLOYMENT_FILES:
        content = (output_dir / rel_path).read_text().lower()
        assert "hard-coded-secret" not in content
        assert "real-secret" not in content
        assert "123456" not in content
        assert "admin_bot_token=replace" in content or "admin_bot_token=" not in content

    env_content = (output_dir / "deploy/.env.example").read_text().lower()
    assert "replace-with" in env_content


def test_generated_project_readme_references_deployment_guide(tmp_path: Path) -> None:
    output_dir, _ = _run(tmp_path)
    content = (output_dir / "README.md").read_text()

    assert "docs/deployment.md" in content
    assert "deploy/docker-compose.prod.yml" in content
