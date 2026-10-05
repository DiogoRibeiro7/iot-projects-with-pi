# Continuous integration

Pull requests and pushes to `main` run the repository quality gate on
GitHub Actions.

## Checks

The workflow runs on Python 3.12 and performs:

1. Poetry dependency installation, including optional extras;
2. Ruff linting;
3. Ruff formatting verification;
4. strict mypy type checking;
5. pytest with the repository coverage threshold;
6. Poetry package build validation.

The workflow does not require Raspberry Pi hardware. Hardware-specific behavior
is exercised through fake and simulated adapters.

## Local equivalent

Run the same checks before opening a pull request:

```bash
poetry install --all-extras
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy src
poetry run pytest
poetry build
```

## Workflow reuse

Python and Poetry setup uses the supported `setup-poetry` action from
`DiogoRibeiro7/git-actions-collection@v1.4.0`. The individual project checks remain
explicit in this repository so failures are easy to diagnose.

## Coverage

The coverage threshold is configured in `pyproject.toml`. CI should not lower
that threshold to make a pull request pass; missing tests should be added
instead.


## Documentation

Documentation uses MkDocs Material with dependencies isolated from the runtime
package.

Install the docs dependencies:

```bash
python -m pip install -r requirements-docs.txt
```

Build locally with the same strict mode used in CI:

```bash
mkdocs build --strict
```

The pull-request CI validates the site build. A separate `Documentation`
workflow publishes the generated site to GitHub Pages after documentation changes
land on `main`.
