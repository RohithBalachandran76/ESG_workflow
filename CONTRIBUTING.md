# Contributing to ESG Workflow

Thank you for your interest in contributing! This document outlines the process for getting involved.

## Getting Started

1. **Fork** the repository and clone your fork
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Set up your local environment:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

## Development Workflow

### Making changes

- Keep changes focused — one feature or fix per PR
- Follow existing code style (enforced by `ruff`)
- Add or update tests for any changed behaviour

### Before submitting

```bash
# Lint
python -m ruff check src/ tests/

# Tests — all must pass
python -m pytest tests/ -v
```

### Commit messages

Use conventional commits:
```
feat: add sector-normalised benchmarking
fix: handle missing renewable_energy_pct gracefully
docs: update API reference for /rag/query
test: add coverage for governance pillar scoring
```

## Areas to Contribute

- **New data sources** — add an adapter in `src/ingestion/` following the pattern in `finance_fetcher.py`
- **Scoring rules** — propose changes to `config/scoring_rules.yaml` with justification from CSRD/ESRS standards
- **New API endpoints** — add routes in `src/api/routes.py` with matching Pydantic schemas
- **Dashboard pages** — extend `src/dashboard/app.py` with new visualisations
- **Tests** — increase coverage in the `tests/` directory

## Submitting a Pull Request

1. Push your branch to your fork
2. Open a PR against the `main` branch
3. Fill in the PR template describing what changed and why
4. Ensure CI passes (lint + tests + docker build)

## Code Style

- Python 3.11+, type hints throughout
- Ruff for linting (configuration in `pyproject.toml` if added, otherwise defaults)
- No comments unless the *why* is non-obvious
- Prefer editing existing files over creating new ones

## Questions?

Open a [GitHub Issue](https://github.com/RohithBalachandran76/ESG_workflow/issues) with the `question` label.
