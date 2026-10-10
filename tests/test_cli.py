import json

from typer.testing import CliRunner

from lace.cli import app

runner = CliRunner()


def test_help_and_version() -> None:
    help_result = runner.invoke(app, ["--help"])
    version_result = runner.invoke(app, ["--version"])
    assert help_result.exit_code == 0
    assert "doctor" in help_result.stdout
    assert "validate" in help_result.stdout
    assert "scan" in help_result.stdout
    assert version_result.exit_code == 0
    assert version_result.stdout.startswith("lace 0.1.0")


def test_doctor_json() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["python"]["status"] == "ready"
    assert payload["git"]["status"] == "ready"
    assert payload["isolation"]["verified"] is False
    assert payload["m2_ready"] is True


def test_validate_json(git_repository, tmp_path, valid_patch: str) -> None:
    patch = tmp_path / "fix.patch"
    patch.write_text(valid_patch, encoding="utf-8")
    result = runner.invoke(app, ["validate", str(patch), "--repo", str(git_repository), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["allowed"] is True
    assert payload["original_unchanged"] is True


def test_scan_json(scanning_repository) -> None:
    result = runner.invoke(
        app,
        [
            "scan",
            "--repo",
            str(scanning_repository),
            "--task",
            "Fix incorrect discount calculation",
            "--max-context-chars",
            "10000",
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["repository"]["python_files"] == 3
    assert payload["selection"]["selected_files"][0]["path"] == "src/shop/discount.py"
    assert "context" not in payload["selection"]
