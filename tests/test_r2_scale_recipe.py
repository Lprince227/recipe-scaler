"""Tests for R2: scale a recipe to a new number of servings and show the adjustments."""
import pytest

from recipe_core import RecipeError, format_quantity, make_recipe, scale_recipe


@pytest.fixture
def pancakes():
    return make_recipe("Pancakes", "4", [("1 1/2", "cup", "flour"), ("2", "", "eggs")])


def test_r2_scales_quantities_by_factor(pancakes):
    """R2: every quantity is multiplied by new_servings / original_servings."""
    scaled = scale_recipe(pancakes, 10)
    assert scaled.factor == pytest.approx(2.5)
    assert scaled.servings == 10
    assert [i.quantity for i in scaled.ingredients] == pytest.approx([3.75, 5.0])


def test_r2_shows_original_and_scaled_with_unit_unchanged(pancakes):
    """R2: each adjustment shows the original quantity, scaled quantity, and the same unit."""
    flour = scale_recipe(pancakes, 2).ingredients[0]
    assert flour.name == "flour"
    assert flour.unit == "cup"
    assert flour.original == pytest.approx(1.5)
    assert flour.quantity == pytest.approx(0.75)


def test_r2_scaling_down_keeps_full_precision():
    """R2: rounding is for display only; calculations keep full precision."""
    recipe = make_recipe("Sauce", "3", [("1", "cup", "stock")])
    scaled = scale_recipe(recipe, 1)
    assert scaled.ingredients[0].quantity == pytest.approx(1 / 3)


def test_r2_does_not_modify_original_recipe(pancakes):
    """R2: scaling returns new values and leaves the saved recipe unchanged."""
    scale_recipe(pancakes, 8)
    assert pancakes.servings == 4
    assert pancakes.ingredients[0].quantity == pytest.approx(1.5)


@pytest.mark.parametrize("bad", [0, -3])
def test_r2_rejects_non_positive_servings(pancakes, bad):
    """R2: the new number of servings must be at least 1."""
    with pytest.raises(RecipeError):
        scale_recipe(pancakes, bad)


@pytest.mark.parametrize(
    "value, text",
    [(1 / 3, "0.33"), (1.5, "1.5"), (2.0, "2"), (3.75, "3.75"), (2.999, "3"), (0.004, "0")],
)
def test_r2_format_quantity_two_decimals_trailing_zeros_removed(value, text):
    """R2: scaled quantities are displayed with up to 2 decimals, trailing zeros dropped."""
    assert format_quantity(value) == text
