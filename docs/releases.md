# Releases

Stable releases use semantic-version tags that match the version declared in
`pyproject.toml`.

## Version source

The canonical project version is:

```toml
[project]
version = "0.1.0"
```

A release tag must therefore be:

```text
v0.1.0
```

The release validator rejects mismatched tags and artifacts.

## Release procedure

1. Update `pyproject.toml` to the intended release version.
2. Move notable changes from `[Unreleased]` in `CHANGELOG.md` into a dated
   release section.
3. Merge the version/changelog change to `main`.
4. Create and push the matching tag:

   ```bash
   git checkout main
   git pull --ff-only
   git tag v0.1.0
   git push origin v0.1.0
   ```

5. The `Release` workflow validates, builds, and creates the GitHub Release.

## Release validation

Before publishing, the workflow:

- verifies the tag exists;
- verifies the tagged commit is contained in `main`;
- checks `poetry.lock`;
- installs all optional extras;
- runs Ruff lint and formatting;
- runs strict mypy;
- runs the full pytest/coverage suite;
- builds the wheel and source distribution;
- reads package metadata from both artifacts;
- verifies artifact name and version against `pyproject.toml`;
- verifies the tag equals `v<project-version>`.

Normal pull-request CI also validates the built wheel and source distribution
against the current project version.

## GitHub Release

A successful release publishes:

- one wheel;
- one gzip-compressed source distribution;
- generated GitHub release notes.

The artifacts are also uploaded as a workflow artifact for the release run.

## Manual rerun

The workflow can be started manually for an **existing** tag through
`workflow_dispatch`. It does not create tags.

## Package indexes

Publishing to PyPI or another package index is intentionally out of scope. The
current workflow only creates GitHub Release artifacts.
