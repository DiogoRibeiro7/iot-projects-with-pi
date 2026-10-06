"""Tests for release workflow structure."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/release.yml")


def test_release_workflow_contains_required_guards() -> None:
    """The release workflow should preserve the publication safety contract."""
    content = WORKFLOW.read_text(encoding="utf-8")

    assert "tags:" in content
    assert '"v*.*.*"' in content
    assert "fetch-depth: 0" in content
    assert "git merge-base --is-ancestor" in content
    assert "poetry check --lock" in content
    assert "poetry run ruff check ." in content
    assert "poetry run ruff format --check ." in content
    assert "poetry run mypy src" in content
    assert "poetry run pytest" in content
    assert "poetry build" in content
    assert "scripts/validate_release.py" in content
    assert "gh release create" in content
    assert "--verify-tag" in content
    assert "--generate-notes" in content
