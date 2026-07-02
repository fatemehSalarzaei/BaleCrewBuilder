import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import yaml

from app.generator import GeneratorCore
from app.schemas.blueprint import BotBlueprint

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_blueprint() -> BotBlueprint:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        return BotBlueprint.model_validate(yaml.safe_load(f))


def _run_generation(tmp_path: Path) -> Path:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    GeneratorCore().run(_load_blueprint(), output_dir)
    return output_dir


def _run_generated_backend_code(
    output_dir: Path,
    code: str,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PYTHONPATH": str(output_dir / "backend"),
    }
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        check=False,
        cwd=output_dir,
        env=env,
        text=True,
        capture_output=True,
    )


def test_generated_miniapp_auth_service_file_is_generated(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = GeneratorCore().run(_load_blueprint(), output_dir)

    assert "backend/app/services/miniapp_auth_service.py" in result.generated_files
    assert (output_dir / "backend/app/services/miniapp_auth_service.py").exists()


def test_generated_miniapp_auth_rejects_unsafe_init_data_object(
    tmp_path: Path,
) -> None:
    output_dir = _run_generation(tmp_path)

    result = _run_generated_backend_code(
        output_dir,
        """
        from app.services.miniapp_auth_service import (
            MiniAppAuthService,
            MiniAppAuthVerificationError,
        )

        try:
            MiniAppAuthService().verify_init_data('{"user": {"id": 123}}')
        except MiniAppAuthVerificationError as exc:
            assert "initDataUnsafe is not accepted" in str(exc)
        else:
            raise AssertionError("initDataUnsafe-like payload was accepted")
        """,
    )

    assert result.returncode == 0, result.stderr


def test_generated_miniapp_auth_rejects_missing_hash_or_signature(
    tmp_path: Path,
) -> None:
    output_dir = _run_generation(tmp_path)
    now = int(time.time())

    result = _run_generated_backend_code(
        output_dir,
        f"""
        from app.services.miniapp_auth_service import (
            MiniAppAuthService,
            MiniAppAuthVerificationError,
        )

        try:
            MiniAppAuthService().verify_init_data("auth_date={now}&user={{}}")
        except MiniAppAuthVerificationError as exc:
            assert "missing hash/signature" in str(exc)
        else:
            raise AssertionError("Unsigned initData was accepted")
        """,
    )

    assert result.returncode == 0, result.stderr


def test_generated_miniapp_auth_rejects_expired_auth_date(tmp_path: Path) -> None:
    output_dir = _run_generation(tmp_path)
    expired = int(time.time()) - 90000

    result = _run_generated_backend_code(
        output_dir,
        f"""
        from app.services.miniapp_auth_service import (
            MiniAppAuthService,
            MiniAppAuthVerificationError,
        )

        try:
            MiniAppAuthService().verify_init_data(
                "auth_date={expired}&user={{}}&hash=abc123"
            )
        except MiniAppAuthVerificationError as exc:
            assert "auth_date is expired" in str(exc)
        else:
            raise AssertionError("Expired initData was accepted")
        """,
    )

    assert result.returncode == 0, result.stderr


def test_generated_miniapp_auth_rejects_invalid_signature_until_contract_confirmed(
    tmp_path: Path,
) -> None:
    output_dir = _run_generation(tmp_path)
    now = int(time.time())

    result = _run_generated_backend_code(
        output_dir,
        f"""
        from app.services.miniapp_auth_service import (
            MiniAppAuthService,
            MiniAppAuthVerificationError,
        )

        try:
            MiniAppAuthService().verify_init_data(
                "auth_date={now}&user={{}}&hash=invalid"
            )
        except MiniAppAuthVerificationError as exc:
            assert "HMAC verification contract is not configured" in str(exc)
        else:
            raise AssertionError("Structurally signed initData was accepted")
        """,
    )

    assert result.returncode == 0, result.stderr


def test_generated_auth_service_delegates_to_fail_closed_verifier(
    tmp_path: Path,
) -> None:
    output_dir = _run_generation(tmp_path)
    now = int(time.time())

    result = _run_generated_backend_code(
        output_dir,
        f"""
        import asyncio

        from app.services.auth_service import AuthService

        async def main():
            service = AuthService(db=None)
            try:
                await service.verify_miniapp_token(
                    "auth_date={now}&user={{}}&hash=invalid"
                )
            except ValueError as exc:
                assert "HMAC verification contract is not configured" in str(exc)
                return
            raise AssertionError("Mini App initData was accepted")

        asyncio.run(main())
        """,
    )

    assert result.returncode == 0, result.stderr


def test_generated_miniapp_auth_config_contains_freshness_setting(
    tmp_path: Path,
) -> None:
    output_dir = _run_generation(tmp_path)

    config = (output_dir / "backend/app/core/config.py").read_text()

    assert "miniapp_auth_max_age_seconds" in config
