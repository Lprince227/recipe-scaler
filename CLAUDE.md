# CLAUDE.md — standing rules for this repository

## Stack
- The language is Python.
- The program is a Flask web app that runs locally. It has no login, needs no
  API keys, and uses no paid services or external network calls.
- Dependencies are listed in `requirements.txt` and installed into `.venv`.

## Running
- The app starts with one command: `py app.py`. It then serves at
  http://127.0.0.1:5000.
- Tests run with `py -m pytest`.

## Code layout
- All logic (entering/validating recipes, scaling, the pantry check, saving
  and loading) lives in `recipe_core.py`. It must not import Flask.
- `app.py` holds only the Flask routes and templates, which call into
  `recipe_core`.
- The requirements are defined in `spec.md` (R1–R4). Keep it up to date when
  behaviour changes.

## Tests
- Every test names the requirement it checks (for example R2) in its function
  name and its docstring, e.g. `test_r2_scales_quantities_by_factor`.
- Test the logic in `recipe_core.py`. Page layout is not tested.
- Tests must not touch the real `recipe_data.json`. They use pytest's
  `tmp_path`.

## Git
- Make small commits. Each message says what changed and why.
- Never commit `.venv/` or `*.jsonl` files, and never commit the saved data
  file `recipe_data.json`.
- Never undo or amend a commit. Fix mistakes with a new commit.
