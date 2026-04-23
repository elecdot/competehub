# Tooling

This guide introduces the development tools used in this project.

## `just`

`just` is a command runner that encapsulates complex or multi-step commands into simple single-line invocations.

For example, here is a `justfile`:
```bash
pre-commit:
    uv run --project apps/api pre-commit install
    uv run --project apps/api pre-commit run --all-files
```
Then you type:
```bash
just pre-commit
```
Running the above is equivalent to executing:
```bash
uv run --project apps/api pre-commit install
uv run --project apps/api pre-commit run --all-files
```

---

### Quick Start

#### Installation

```pwsh
winget install --id Casey.Just --exact
```

---

## `uv`

We use `uv` to manage both the backend API package and the project's Python development dependencies.

- [GitHub Repo](https://github.com/astral-sh/uv?tab=readme-ov-file)
- [Official Doc](https://docs.astral.sh/uv/)

---

### Quick Start

#### Installation

Install uv with our standalone installers:

```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```
```pwsh
# On Windows.
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
#### Add dependencies

```bash
uv add requests
uv add 'requests==2.31.0'
uv add git+https://github.com/psf/requests
# If you're migrating from a `requirements.txt` file
uv add -r requirements.txt -c constraints.txt
```
Add a package to the `dev` group:
```bash
uv add --dev ipykernel
```

#### Run command in `uv` environment

```bash
uv run <command here>
```

#### Update the environment

This is done automatically prior to every `uv run`. You may only need this when you want activate the `venv` manually.
```bash
uv sync
source .venv/bin/activate
flask run -p 3000
python example.py
```
