import os
import shutil
import subprocess
import tempfile

import pytest


def get_sh_path():
    # On Windows, prefer Git sh.exe over Windows System32 WSL relay bash.exe
    candidates = [
        r"C:\Program Files\Git\bin\sh.exe",
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\sh.exe",
        r"C:\Program Files (x86)\Git\bin\sh.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    sh = shutil.which("sh")
    if sh and not sh.lower().endswith("system32\\bash.exe"):
        return sh
    bash = shutil.which("bash")
    if bash and not bash.lower().endswith("system32\\bash.exe"):
        return bash
    return None


def test_entrypoint_fails_immediately_on_alembic_migration_error():
    """Verify scripts/entrypoint.sh exits with non-zero status and never starts Uvicorn

    or prints success when alembic migration fails.
    """
    sh_path = get_sh_path()
    if not sh_path:
        pytest.skip("Shell interpreter (sh/bash) not available in current test environment.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Mock alembic failing with exit code 1
        alembic_script = os.path.join(tmp_dir, "alembic")
        with open(alembic_script, "w", newline="\n") as f:
            f.write("#!/bin/sh\necho 'MOCK ALEMBIC: Migration connection failed'\nexit 1\n")
        os.chmod(alembic_script, 0o755)

        # Mock uvicorn that marks execution
        marker_file = os.path.join(tmp_dir, "uvicorn_started.flag")
        uvicorn_script = os.path.join(tmp_dir, "uvicorn")
        with open(uvicorn_script, "w", newline="\n") as f:
            f.write(f"#!/bin/sh\ntouch '{marker_file}'\necho 'MOCK UVICORN STARTED'\nexit 0\n")
        os.chmod(uvicorn_script, 0o755)

        env = dict(os.environ)
        env["PATH"] = f"{tmp_dir}{os.pathsep}{env.get('PATH', '')}"

        proc = subprocess.run(
            [sh_path, "scripts/entrypoint.sh"],
            env=env,
            capture_output=True,
            text=True,
        )

        assert proc.returncode != 0, f"Expected non-zero exit code, got {proc.returncode}"
        assert "Database migration step completed" not in proc.stdout
        assert "Starting SlotBack production server" not in proc.stdout
        assert "MOCK UVICORN STARTED" not in proc.stdout
        assert not os.path.exists(marker_file)


def test_entrypoint_succeeds_and_starts_uvicorn_when_migration_passes():
    """Verify scripts/entrypoint.sh proceeds to start Uvicorn when migrations succeed."""
    sh_path = get_sh_path()
    if not sh_path:
        pytest.skip("Shell interpreter (sh/bash) not available in current test environment.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        alembic_script = os.path.join(tmp_dir, "alembic")
        with open(alembic_script, "w", newline="\n") as f:
            f.write("#!/bin/sh\necho 'MOCK ALEMBIC: Migration passed'\nexit 0\n")
        os.chmod(alembic_script, 0o755)

        marker_file = os.path.join(tmp_dir, "uvicorn_started.flag")
        uvicorn_script = os.path.join(tmp_dir, "uvicorn")
        with open(uvicorn_script, "w", newline="\n") as f:
            f.write(f"#!/bin/sh\ntouch '{marker_file}'\necho 'MOCK UVICORN STARTED'\nexit 0\n")
        os.chmod(uvicorn_script, 0o755)

        env = dict(os.environ)
        env["PATH"] = f"{tmp_dir}{os.pathsep}{env.get('PATH', '')}"

        proc = subprocess.run(
            [sh_path, "scripts/entrypoint.sh"],
            env=env,
            capture_output=True,
            text=True,
        )

        assert proc.returncode == 0
        assert "Database migration step completed successfully." in proc.stdout
        assert "Starting SlotBack production server" in proc.stdout
        assert "MOCK UVICORN STARTED" in proc.stdout
        assert os.path.exists(marker_file)
