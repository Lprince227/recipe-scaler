"""Tests for R1: enter a recipe with ingredients, quantities, units, and servings."""
import pytest

from recipe_core import (
    Ingredient,
    RecipeError,
    add_recipe,
    make_recipe,
    parse_quantity,
    parse_servings,
)


@pytest.mark.parametrize(
    "text, expected",
    [("2", 2.0), ("0.5", 0.5), (" 1.25 ", 1.25), ("1/2", 0.5), ("3/4", 0.75), ("1 1/2", 1.5)],
)
def test_r1_parse_quantity_accepts_numbers_fractions_and_mixed(text, expected):
    """R1: quantities may be decimals, fractions, or mixed numbers."""
    assert parse_quantity(text) == pytest.approx(expected)


@pytest.mark.parametrize(
    "text", ["", "   ", "abc", "1/0", "0", "-2", "1 1/2 3", "1/2/3", "1.5 1/2", "nan", "inf"]
)
def test_r1_parse_quantity_rejects_invalid_or_non_positive(text):
    """R1: blank, non-numeric, zero, negative and malformed quantities are rejected."""
    with pytest.raises(RecipeError):
        parse_quantity(text)


def test_r1_parse_servings_accepts_positive_whole_number():
    """R1: servings is a whole number >= 1."""
    assert parse_servings(" 4 ") == 4


@pytest.mark.parametrize("text", ["", "0", "-1", "2.5", "four"])
def test_r1_parse_servings_rejects_invalid(text):
    """R1: servings that are not whole numbers >= 1 are rejected."""
    with pytest.raises(RecipeError):
        parse_servings(text)


def test_r1_make_recipe_builds_recipe_from_rows():
    """R1: a recipe is built from name, servings and (quantity, unit, name) rows."""
    recipe = make_recipe(
        "  Pancakes ",
        "4",
        [("1 1/2", "cup", "flour"), ("2", "", "eggs"), ("", "", "")],
    )
    assert recipe.name == "Pancakes"
    assert recipe.servings == 4
    assert recipe.ingredients == [
        Ingredient(name="flour", quantity=1.5, unit="cup"),
        Ingredient(name="eggs", quantity=2.0, unit=""),
    ]


def test_r1_make_recipe_rejects_blank_name():
    """R1: a recipe needs a name."""
    with pytest.raises(RecipeError):
        make_recipe("   ", "4", [("1", "cup", "flour")])


def test_r1_make_recipe_rejects_no_ingredients():
    """R1: a recipe needs at least one ingredient (blank rows don't count)."""
    with pytest.raises(RecipeError):
        make_recipe("Toast", "1", [("", "", ""), ("  ", " ", "")])


def test_r1_make_recipe_rejects_partial_row():
    """R1: a row with some fields filled but no name or quantity is an error."""
    with pytest.raises(RecipeError):
        make_recipe("Toast", "1", [("2", "slice", "")])
    with pytest.raises(RecipeError):
        make_recipe("Toast", "1", [("", "slice", "bread")])


def test_r1_make_recipe_error_names_the_row():
    """R1: the error message tells the user which ingredient row is wrong."""
    with pytest.raises(RecipeError, match="row 2"):
        make_recipe("Toast", "1", [("2", "slice", "bread"), ("x", "tbsp", "butter")])


def test_r1_add_recipe_replaces_same_name_ignoring_case():
    """R1: saving a recipe with an existing name (any case) replaces it."""
    recipes = {}
    add_recipe(recipes, make_recipe("Pancakes", "4", [("1", "cup", "flour")]))
    add_recipe(recipes, make_recipe("pancakes", "2", [("3", "cup", "flour")]))
    assert len(recipes) == 1
    (only,) = recipes.values()
    assert only.name == "pancakes"
    assert only.servings == 2
