# Contributing to AI Wand

Thank you for your interest in contributing!

## Development Setup

- Python >= 3.9
- Create a virtualenv and install dependencies:
  - `python -m venv .venv && .venv\Scripts\activate`
  - `pip install -e .`
- Install dev tooling:
  - `pip install ruff black mypy pytest pytest-cov`

## Commands

- Format: `black .`
- Lint: `ruff check --fix .`
- Type-check: `mypy aiwand`
- Tests (headless):
  - PowerShell: `$env:QT_QPA_PLATFORM='offscreen'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -rA -vv`

## Code Style

- Follow Black and Ruff rules configured in `pyproject.toml`.
- Keep modules focused; avoid overly large files.
- UI components live under `aiwand/ui/`.
- Do not hardcode secrets; use `.env` (see `.env.example`).

## Pull Requests

- Create a feature branch.
- Keep PRs small; include before/after screenshots for UI changes.
- Ensure CI passes (lint, types, tests on Windows).
- Update README for user-facing changes.

## Reporting Issues

- Include repro steps, expected vs actual, and logs/screenshots.
