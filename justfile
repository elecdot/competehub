# Before run `just pre-commit`, make sure sync backend dependencies,
# basically our Python dependencies, via `uv sync` under `apps/api`
pre-commit:
    uv run --project apps/api pre-commit install
    uv run --project apps/api pre-commit run --all-files
