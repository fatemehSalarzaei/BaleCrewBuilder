"""Generated Alembic scaffold tests."""
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


def test_alembic_scaffold_files_are_generated(tmp_path: Path) -> None:
    _, output_dir, generated = _run(tmp_path)

    expected = [
        "backend/alembic.ini",
        "backend/app/db/migrations/__init__.py",
        "backend/app/db/migrations/env.py",
        "backend/app/db/migrations/script.py.mako",
        "backend/app/db/migrations/versions/__init__.py",
    ]
    for rel_path in expected:
        assert rel_path in generated
        assert (output_dir / rel_path).exists()


def test_alembic_env_references_base_metadata(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/db/migrations/env.py").read_text()

    assert "from app.db.base import Base" in content
    assert "target_metadata = Base.metadata" in content
    assert "target_metadata=target_metadata" in content


def test_alembic_env_imports_generated_model_modules(tmp_path: Path) -> None:
    blueprint, output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/db/migrations/env.py").read_text()

    for entity in blueprint.database.entities:
        assert f"from app.models import {entity.name}" in content


def test_alembic_env_uses_generated_settings_database_url(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/db/migrations/env.py").read_text()

    assert "from app.core.config import settings" in content
    assert 'config.set_main_option("sqlalchemy.url", settings.database_url)' in content
    assert "url=settings.database_url" in content


def test_alembic_env_uses_async_engine_setup(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/db/migrations/env.py").read_text()

    assert "async_engine_from_config" in content
    assert "await connection.run_sync(do_run_migrations)" in content
    assert "asyncio.run(run_migrations_online())" in content


def test_alembic_ini_documents_autogenerate_commands(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/alembic.ini").read_text()

    assert 'alembic revision --autogenerate -m "initial"' in content
    assert "alembic upgrade head" in content
    assert "script_location = app/db/migrations" in content


def test_script_template_is_scaffold_only(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)
    content = (output_dir / "backend/app/db/migrations/script.py.mako").read_text()

    assert "def upgrade() -> None:" in content
    assert "def downgrade() -> None:" in content
    assert "${upgrades" in content
    assert "${downgrades" in content
    assert "op.create_table(" not in content


def test_alembic_scaffold_has_no_hardcoded_database_credentials(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)

    for rel_path in (
        "backend/alembic.ini",
        "backend/app/db/migrations/env.py",
        "backend/app/db/migrations/script.py.mako",
    ):
        content = (output_dir / rel_path).read_text().lower()
        assert "postgresql://user:password" not in content
        assert "postgresql+asyncpg://user:password" not in content
        assert "password@" not in content
        assert "secret" not in content


def test_alembic_env_python_compiles(tmp_path: Path) -> None:
    _, output_dir, _ = _run(tmp_path)

    py_compile.compile(
        str(output_dir / "backend/app/db/migrations/env.py"),
        doraise=True,
    )
