import os
import subprocess
import sys
import textwrap
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


def _run_generated_backend_code(output_dir: Path, code: str) -> subprocess.CompletedProcess[str]:
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


def test_generated_backend_requirements_include_security_dependencies(
    tmp_path: Path,
) -> None:
    output_dir = _run_generation(tmp_path)

    requirements = (output_dir / "backend/requirements.txt").read_text()

    assert "bcrypt" in requirements
    assert "PyJWT" in requirements


def test_generated_password_hash_verifies_correct_password(tmp_path: Path) -> None:
    output_dir = _run_generation(tmp_path)

    result = _run_generated_backend_code(
        output_dir,
        """
        from app.core.security import get_password_hash, verify_password

        hashed = get_password_hash("correct horse battery staple")
        assert hashed != "correct horse battery staple"
        assert verify_password("correct horse battery staple", hashed) is True
        """,
    )

    assert result.returncode == 0, result.stderr


def test_generated_password_hash_rejects_wrong_password(tmp_path: Path) -> None:
    output_dir = _run_generation(tmp_path)

    result = _run_generated_backend_code(
        output_dir,
        """
        from app.core.security import get_password_hash, verify_password

        hashed = get_password_hash("correct-password")
        assert verify_password("wrong-password", hashed) is False
        """,
    )

    assert result.returncode == 0, result.stderr


def test_generated_jwt_decode_succeeds_for_valid_token(tmp_path: Path) -> None:
    output_dir = _run_generation(tmp_path)

    result = _run_generated_backend_code(
        output_dir,
        """
        from app.core.security import create_access_token, decode_access_token

        token = create_access_token({"sub": "user-1", "roles": ["member"]})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-1"
        assert payload["roles"] == ["member"]
        assert "exp" in payload
        """,
    )

    assert result.returncode == 0, result.stderr


def test_generated_jwt_decode_returns_none_for_invalid_token(tmp_path: Path) -> None:
    output_dir = _run_generation(tmp_path)

    result = _run_generated_backend_code(
        output_dir,
        """
        from app.core.security import decode_access_token

        assert decode_access_token("not-a-valid-token") is None
        """,
    )

    assert result.returncode == 0, result.stderr


def test_generated_api_dependency_rejects_invalid_token(tmp_path: Path) -> None:
    output_dir = _run_generation(tmp_path)

    result = _run_generated_backend_code(
        output_dir,
        """
        import asyncio
        from fastapi import HTTPException
        from app.api.deps import get_current_user

        async def main():
            try:
                await get_current_user("invalid-token")
            except HTTPException as exc:
                assert exc.status_code == 401
                assert exc.detail == "Invalid or expired token"
                return
            raise AssertionError("Invalid token was accepted")

        asyncio.run(main())
        """,
    )

    assert result.returncode == 0, result.stderr


def test_generated_auth_service_miniapp_verification_fails_closed(
    tmp_path: Path,
) -> None:
    output_dir = _run_generation(tmp_path)

    result = _run_generated_backend_code(
        output_dir,
        """
        import asyncio
        from app.services.auth_service import AuthService

        async def main():
            service = AuthService(db=None)
            try:
                await service.verify_miniapp_token("unsafe-init-data")
            except ValueError as exc:
                assert "not configured" in str(exc)
                return
            raise AssertionError("Mini App initData was accepted")

        asyncio.run(main())
        """,
    )

    assert result.returncode == 0, result.stderr
