"""Core logic for the recipe scaler: entering recipes (R1), scaling (R2),
pantry checks (R3), saving/loading (R4), and deleting recipes (R5).

This module deliberately does not import Flask so it can be tested without a
browser or web server.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path


class RecipeError(ValueError):
    """Raised when user input for a recipe or pantry item is invalid."""


def normalize(text: str) -> str:
    """Key used to match names/units: ignores case and surrounding whitespace."""
    return text.strip().casefold()


# ---------------------------------------------------------------- R1: entry

@dataclass
class Ingredient:
    name: str
    quantity: float
    unit: str


@dataclass
class Recipe:
    name: str
    servings: int
    ingredients: list[Ingredient] = field(default_factory=list)


def _parse_number(text: str) -> Fraction:
    """Parse '2', '0.5', '1/2' or '1 1/2' into an exact Fraction."""
    parts = text.split()
    try:
        if len(parts) == 1:
            return Fraction(parts[0])
        if len(parts) == 2 and parts[0].isdigit() and "/" in parts[1]:
            return int(parts[0]) + Fraction(parts[1])
    except (ValueError, ZeroDivisionError):
        pass
    raise RecipeError(f"'{text.strip()}' is not a valid quantity (try 2, 0.5, 1/2 or 1 1/2)")


def parse_quantity(text: str, allow_zero: bool = False) -> float:
    """Parse a quantity typed by the user. It must be > 0 (or >= 0 if allow_zero)."""
    if not text or not text.strip():
        raise RecipeError("Quantity is required")
    value = _parse_number(text)
    if value < 0 or (value == 0 and not allow_zero):
        limit = "0 or more" if allow_zero else "greater than 0"
        raise RecipeError(f"Quantity must be {limit}, got '{text.strip()}'")
    return float(value)


def parse_servings(text: str | int) -> int:
    """Parse a number of servings: a whole number >= 1."""
    raw = str(text).strip()
    if not raw.isdigit() or int(raw) < 1:
        raise RecipeError(f"Servings must be a whole number of at least 1, got '{raw}'")
    return int(raw)


def make_recipe(name: str, servings: str | int, rows) -> Recipe:
    """Build a validated Recipe from form input.

    rows is an iterable of (quantity, unit, ingredient_name) strings. Rows that
    are entirely blank are skipped; partially filled rows are an error.
    """
    name = (name or "").strip()
    if not name:
        raise RecipeError("Recipe name is required")
    servings_value = parse_servings(servings)

    ingredients = []
    for number, (qty, unit, ing_name) in enumerate(rows, start=1):
        qty, unit, ing_name = (qty or "").strip(), (unit or "").strip(), (ing_name or "").strip()
        if not (qty or unit or ing_name):
            continue
        if not ing_name:
            raise RecipeError(f"Ingredient row {number}: name is required")
        try:
            quantity = parse_quantity(qty)
        except RecipeError as exc:
            raise RecipeError(f"Ingredient row {number} ({ing_name}): {exc}") from None
        ingredients.append(Ingredient(name=ing_name, quantity=quantity, unit=unit))

    if not ingredients:
        raise RecipeError("A recipe needs at least one ingredient")
    return Recipe(name=name, servings=servings_value, ingredients=ingredients)


def add_recipe(recipes: dict[str, Recipe], recipe: Recipe) -> None:
    """Add a recipe, replacing any existing recipe with the same name (any case)."""
    recipes[normalize(recipe.name)] = recipe


# ---------------------------------------------------------------- R5: delete

# The value the confirmation page sends when the user clicks "Yes, delete".
CONFIRM_DELETE_VALUE = "yes"


def is_delete_confirmed(value) -> bool:
    """True only if a form value is the confirmation page's 'yes' answer."""
    return isinstance(value, str) and value.strip().casefold() == CONFIRM_DELETE_VALUE


def delete_recipe(recipes: dict[str, Recipe], name: str, *, confirmed: bool) -> Recipe | None:
    """Delete the recipe with this name (case and outer spaces ignored).

    The delete only happens if confirmed is exactly True. Anything else raises
    RecipeError and leaves the recipes unchanged. Returns the removed recipe,
    or None if no recipe has that name.
    """
    if confirmed is not True:
        raise RecipeError("Please confirm that you want to delete this recipe")
    return recipes.pop(normalize(name), None)


# ---------------------------------------------------------------- R2: scaling

@dataclass
class ScaledIngredient:
    name: str
    unit: str
    original: float
    quantity: float  # the scaled amount


@dataclass
class ScaledRecipe:
    recipe: Recipe
    servings: int
    factor: float
    ingredients: list[ScaledIngredient]


def scale_recipe(recipe: Recipe, new_servings: int) -> ScaledRecipe:
    """Scale every quantity by new_servings / recipe.servings. Units are unchanged."""
    if new_servings < 1:
        raise RecipeError("Servings must be at least 1")
    factor = new_servings / recipe.servings
    scaled = [
        ScaledIngredient(name=i.name, unit=i.unit, original=i.quantity, quantity=i.quantity * factor)
        for i in recipe.ingredients
    ]
    return ScaledRecipe(recipe=recipe, servings=new_servings, factor=factor, ingredients=scaled)


def format_quantity(value: float) -> str:
    """Display a quantity with up to 2 decimals, dropping trailing zeros."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


# ---------------------------------------------------------------- R3: pantry

@dataclass
class PantryItem:
    name: str
    quantity: float
    unit: str


def make_pantry_item(name: str, quantity: str, unit: str) -> PantryItem:
    """Build a validated pantry item. Quantity may be 0 (run out)."""
    name = (name or "").strip()
    if not name:
        raise RecipeError("Pantry item name is required")
    return PantryItem(name=name, quantity=parse_quantity(quantity, allow_zero=True), unit=(unit or "").strip())


def set_pantry_item(pantry: dict[str, PantryItem], item: PantryItem) -> None:
    """Add or update a pantry item (matched by name, ignoring case)."""
    pantry[normalize(item.name)] = item


def remove_pantry_item(pantry: dict[str, PantryItem], name: str) -> bool:
    """Remove a pantry item by name. Returns True if something was removed."""
    return pantry.pop(normalize(name), None) is not None


MISSING = "missing"
NOT_ENOUGH = "not_enough"
UNIT_MISMATCH = "unit_mismatch"

# Tolerance so floating-point noise (e.g. 2.0000000001) doesn't raise a false alert.
_EPSILON = 1e-9


@dataclass
class PantryAlert:
    name: str
    unit: str
    status: str  # MISSING, NOT_ENOUGH or UNIT_MISMATCH
    needed: float
    on_hand: float = 0.0
    on_hand_unit: str = ""

    @property
    def shortfall(self) -> float:
        return max(self.needed - self.on_hand, 0.0)


def check_pantry(ingredients, pantry: dict[str, PantryItem]) -> list[PantryAlert]:
    """Compare needed ingredients with the pantry and return alerts.

    ingredients is any sequence of objects with name, quantity and unit
    (Ingredient or ScaledIngredient). Lines with the same name and unit are
    summed first. Ingredients that are available produce no alert.
    """
    needs: dict[tuple[str, str], list] = {}
    for ing in ingredients:
        key = (normalize(ing.name), normalize(ing.unit))
        if key in needs:
            needs[key][2] += ing.quantity
        else:
            needs[key] = [ing.name, ing.unit, ing.quantity]

    alerts = []
    for (name_key, unit_key), (name, unit, needed) in needs.items():
        item = pantry.get(name_key)
        if item is None:
            alerts.append(PantryAlert(name, unit, MISSING, needed))
        elif normalize(item.unit) != unit_key:
            alerts.append(PantryAlert(name, unit, UNIT_MISMATCH, needed, item.quantity, item.unit))
        elif item.quantity + _EPSILON < needed:
            alerts.append(PantryAlert(name, unit, NOT_ENOUGH, needed, item.quantity, item.unit))
    return alerts


# ---------------------------------------------------------------- R4: storage

class StorageError(Exception):
    """Raised when the saved data file exists but cannot be read."""


def save_data(path, recipes: dict[str, Recipe], pantry: dict[str, PantryItem]) -> None:
    """Write recipes and pantry to a JSON file.

    Writes to a temporary file first and then replaces the target, so a crash
    mid-write never leaves a half-written data file.
    """
    path = Path(path)
    data = {
        "recipes": [asdict(r) for r in recipes.values()],
        "pantry": [asdict(p) for p in pantry.values()],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise


def _number(value, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StorageError(f"{what} must be a number")
    return float(value)


def _text(value, what: str) -> str:
    if not isinstance(value, str):
        raise StorageError(f"{what} must be text")
    return value


def load_data(path) -> tuple[dict[str, Recipe], dict[str, PantryItem]]:
    """Load recipes and pantry from a JSON file.

    A missing file means a first run and returns empty data. A file that exists
    but is invalid raises StorageError, and the file is not modified.
    """
    path = Path(path)
    if not path.exists():
        return {}, {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise StorageError("top level must be an object")
        raw_recipes = data.get("recipes", [])
        raw_pantry = data.get("pantry", [])
        if not isinstance(raw_recipes, list) or not isinstance(raw_pantry, list):
            raise StorageError("'recipes' and 'pantry' must be lists")

        recipes: dict[str, Recipe] = {}
        for r in raw_recipes:
            servings = r["servings"]
            if isinstance(servings, bool) or not isinstance(servings, int) or servings < 1:
                raise StorageError("recipe servings must be a whole number >= 1")
            ingredients = [
                Ingredient(
                    name=_text(i["name"], "ingredient name"),
                    quantity=_number(i["quantity"], "ingredient quantity"),
                    unit=_text(i["unit"], "ingredient unit"),
                )
                for i in r["ingredients"]
            ]
            add_recipe(recipes, Recipe(_text(r["name"], "recipe name"), servings, ingredients))

        pantry: dict[str, PantryItem] = {}
        for p in raw_pantry:
            set_pantry_item(
                pantry,
                PantryItem(
                    name=_text(p["name"], "pantry name"),
                    quantity=_number(p["quantity"], "pantry quantity"),
                    unit=_text(p["unit"], "pantry unit"),
                ),
            )
    except StorageError as exc:
        raise StorageError(f"Could not read {path}: {exc}") from None
    except (ValueError, KeyError, TypeError) as exc:
        raise StorageError(f"Could not read {path}: {exc!r}") from None
    return recipes, pantry
