# UV Migration Guide

Migration Instructions from `pip` + `requirements.txt` to `uv` (~10-100x faster dependency management and builds)

## 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 2. Project Setup

Navigate to the `backend-api` directory and sync dependencies using `uv sync`. This will automatically create the virtual environment (`.venv`) and install locked versions.

```bash
cd backend-api
uv sync
```

## 3. Running the App

Use `uv run` to execute commands within the project's environment. You do **not** need to manually activate the virtual environment.

```bash
# Run Migrations
uv run python manage.py migrate

# Start Server
uv run python manage.py runserver
```

## 4. Managing Dependencies

Instead of `pip install`, use `uv` to ensure `pyproject.toml` and `uv.lock` stay in sync.

```bash
# Add a package
uv add requests

# Remove a package
uv remove requests

# Add a dev dependency (e.g., pytest)
uv add --dev pytest
```

## 5. Editor Setup

Include a `.vscode/settings.json` file that automatically configures the editor to:
1. Use the `uv` virtual environment.
2. Resolve imports correctly from the `backend-api` root.

In case of import errors:
1. Run **Python: Select Interpreter**.
2. Choose the environment inside `backend-api/.venv`.
3. Run **Developer: Reload Window**.
