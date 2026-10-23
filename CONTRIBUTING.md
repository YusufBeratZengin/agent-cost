# Contributing

Thanks for helping. Principles: zero runtime dependencies, fully typed, cross-platform, and tests built only from synthetic data (never real session logs).

## Setup

```bash
git clone https://github.com/YusufBeratZengin/agent-cost.git
cd agent-cost
python -m pip install -e ".[dev]"
```

## Checks

```bash
ruff check .
ruff format --check .
mypy
pytest          # coverage must stay at or above 85%
```

## Adding a reader

A reader is a class with a `name` and `parse(obj, ctx) -> Record | None` (see `src/agent_cost/readers/`). Register it in `readers/__init__.py`, add synthetic fixtures built inside the test, and document the format in the README.

## Commits

Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`), small and focused.

## Releasing

1. Update `CHANGELOG.md`, bump `version` in `pyproject.toml` and `__version__` in `src/agent_cost/__init__.py`.
2. Commit `chore(release): vX.Y.Z`.
3. Dry run: `python -m build && twine check dist/*`.
4. `git tag vX.Y.Z` and push the tag. The Publish workflow uploads to PyPI through trusted publishing (configure a pending publisher for this repo, workflow `publish.yml`, environment `pypi`); no token is stored.
