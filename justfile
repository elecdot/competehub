# Sync backend uv environment and run pre-commit git hooks
pre-commit:
    uv run --project apps/api pre-commit install
    uv run --project apps/api pre-commit run --all-files
