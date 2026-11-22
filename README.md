# Recipe Scaler

Recipe Scaler is a small local web app for home cooks who need to make a recipe
for more (or fewer) people than it was written for.

- **Enter recipes** with a name, the number of servings, and ingredients. Each
  ingredient has a quantity, unit, and name. Quantities can be typed as `2`,
  `0.5`, `1/2`, or `1 1/2`.
- **Scale** a recipe to any number of servings. The page shows the original and
  scaled quantity of every ingredient. Units stay as entered, and amounts are
  rounded to 2 decimals.
- **Keep a pantry** of what you have on hand, with amounts. When you view a
  scaled recipe, the app warns you about ingredients that are missing, that
  you don't have enough of, or that are stored in a different unit than the
  recipe uses.
- **Delete recipes** you no longer need, using the Delete recipe button on a
  recipe's page. The app asks if you are sure first, and a deleted recipe
  can't be restored.
- **Saves automatically.** Recipes and the pantry are stored in
  `recipe_data.json` next to `app.py`, so they are still there after a restart.

It runs only on your computer. There is no login, no API keys, and no paid
services.

## Setup (Windows, once)

You need Python 3.10 or newer.

```
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
```

On macOS/Linux, activate with `source .venv/bin/activate` and use `python3`
instead of `py`.

## Run

With the virtual environment activated:

```
py app.py
```

Then open **http://127.0.0.1:5000** in your browser. Press Ctrl+C in the
terminal to stop.

To keep your data somewhere else, set the `RECIPE_DATA_FILE` environment
variable to a file path before starting the app.

## Test

```
py -m pytest
```

The tests cover the logic in `recipe_core.py`: entering recipes (R1), scaling
(R2), the pantry check (R3), saving/loading (R4), and deleting recipes (R5). Each test names the
requirement it checks. See `spec.md` for the full requirements.

## Project layout

| File | Purpose |
|---|---|
| `recipe_core.py` | All logic, with no Flask dependency |
| `app.py`, `templates/` | Flask routes and pages |
| `tests/` | pytest tests, one file per requirement |
| `spec.md` | Requirements R1–R5 |
| `docs/decisions/` | Architecture decision records |
