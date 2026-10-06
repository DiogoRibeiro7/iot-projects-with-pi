"""Tests for supply-chain evidence workflow structure."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/security.yml")
REQUIREMENTS = Path("requirements-security.txt")


def test_security_workflow_contains_required_evidence_controls() -> None:
    """The workflow should preserve the intended evidence and policy contract."""
    content = WORKFLOW.read_text(encoding="utf-8")

    assert "cyclonedx-py environment" in content
    assert "poetry env info --executable" in content
    assert "--pyproject pyproject.toml" in content
    assert "--output-reproducible" in content
    assert "security-evidence/sbom.cdx.json" in content
    assert "pip-audit" in content
    assert "--format json" in content
    assert "pip-audit-exit-code.txt" in content
    assert 'if [ "$status" -eq 1 ]' in content
    assert "actions/upload-artifact@v4" in content
    assert "tags:" in content
    assert '"v*.*.*"' in content


def test_security_tool_versions_are_pinned() -> None:
    """Supply-chain tooling should be reproducible but remain outside Poetry."""
    lines = [
        line.strip()
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert lines == [
        "pip-audit==2.10.1",
        "cyclonedx-bom==7.5.0",
    ]
