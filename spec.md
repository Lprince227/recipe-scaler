# Recipe Scaler — Specification (round 1)

## Purpose

Home cooks often need a recipe for a different number of people than it was
written for. Converting the amounts by hand is slow and easy to get wrong. This
program stores recipes, scales them to a new number of servings, checks the
scaled amounts against a pantry, and saves everything between runs.

It is a local Flask web app. It has no login, needs no API keys, and uses no
paid services.

## Requirements

### R1 — Enter a recipe

The user enters a recipe with a **name**, a number of **servings**, and one or
more **ingredients**. Each ingredient has a **quantity**, a **unit**, and a
**name**.

- The recipe name must not be blank (surrounding whitespace is ignored).
- Servings must be a whole number of at least 1.
- A recipe needs at least one ingredient.
- Ingredient name must not be blank.
- The quantity must be greater than 0. It can be typed as:
  - a whole number or decimal: `2`, `0.5`, `1.25`
  - a fraction: `1/2`, `3/4`
  - a mixed number: `1 1/2`
- The unit can be any text, such as `cup`, `g`, or `tbsp`. It can be blank for
  things that are counted, like `3 eggs`.
- The page has a fixed number of ingredient rows. Rows that are completely
  blank are skipped. A row that is only partly filled in is an error.
- Invalid input is rejected with a message that names the problem. Nothing is
  saved in that case.
- Saving a recipe with the same name as an existing one (ignoring case)
  replaces the existing one.

### R2 — Scale a recipe and show the adjustments

The user picks a saved recipe and enters a new number of servings, which must
be a whole number of at least 1.

- Scale factor = new servings ÷ original servings.
- Every ingredient quantity is multiplied by the factor.
- Units stay exactly as entered. There is no unit conversion.
- For each ingredient the page shows the original quantity, the scaled
  quantity, and the unit, along with the scale factor.
- Quantities are shown rounded to 2 decimal places, with trailing zeros
  dropped: `1.333…` → `1.33`, `1.50` → `1.5`, `2.00` → `2`. Rounding happens
  only for display. Calculations use the full value.

### R3 — Pantry list and missing-ingredient alerts

The user keeps a pantry list. Each item has a **name**, a **quantity**
(at least 0), and a **unit**.

- The user can add a pantry item, update one (adding an item with an existing
  name replaces it), and remove one.
- When a recipe is shown at some number of servings, each scaled ingredient is
  checked against the pantry:
  - **missing**: no pantry item has that name.
  - **not enough**: a pantry item has the same name and unit but a smaller
    quantity than needed. The alert shows how much is needed, how much is on
    hand, and the shortfall.
  - **unit mismatch**: a pantry item has that name but a different unit, so
    the amounts can't be compared (units are not converted). The user is told
    to check it by hand.
  - Otherwise the ingredient is **available** and gets no alert.
- Names and units are matched ignoring case and surrounding whitespace.
- If the same ingredient (same name and unit) appears more than once in a
  recipe, its quantities are added together before the check.

### R4 — Save recipes and pantry data

- Recipes and the pantry are saved to one JSON file, `recipe_data.json` by
  default, after every change.
- Data is loaded from that file when the app starts, so it survives restarts.
- If the file doesn't exist yet, the app starts with no recipes and an empty
  pantry.
- If the file exists but can't be read as valid data, the app stops with a
  clear error and does not overwrite the file, so nothing is lost silently.
- The file location can be changed with the `RECIPE_DATA_FILE` environment
  variable. The tests use this to work with temporary files.

## Architecture

- `recipe_core.py` holds all logic: parsing and validation (R1), scaling and
  formatting (R2), the pantry check (R3), and save/load (R4). It does not
  import Flask, so it can be tested without a browser.
- `app.py` holds the Flask routes and HTML templates. It only passes form data
  to `recipe_core` and renders the results.
- `tests/` holds pytest tests for `recipe_core`. Every test names the
  requirement it checks.

## Out of scope for round 1

- Unit conversion (for example, tsp to cup or g to kg).
- Editing a single ingredient in place. Re-entering the recipe under the same
  name replaces it.
- Deleting recipes.
- Using a recipe to subtract amounts from the pantry.
- Multiple users or accounts.
