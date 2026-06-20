import subprocess
import sys


def test_seed_script_runs_from_project_root() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/seed_db.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Loaded" in result.stdout


def test_index_kb_script_runs_from_project_root() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/index_kb.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Indexed" in result.stdout
