"""Core logic for the recipe scaler: entering recipes (R1), scaling (R2),
pantry checks (R3), and saving/loading (R4).

This module deliberately does not import Flask so it can be tested without a
browser or web server.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction


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
