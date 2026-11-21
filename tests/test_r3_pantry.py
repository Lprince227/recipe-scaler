"""Tests for R3: keep a pantry list and alert when ingredients aren't available."""
import pytest

from recipe_core import (
    PantryItem,
    RecipeError,
    check_pantry,
    make_pantry_item,
    make_recipe,
    remove_pantry_item,
    scale_recipe,
    set_pantry_item,
)


def _pantry(*items):
    pantry = {}
    for name, qty, unit in items:
        set_pantry_item(pantry, make_pantry_item(name, qty, unit))
    return pantry


def test_r3_make_pantry_item_allows_zero_and_fractions():
    """R3: pantry quantities may be 0 (run out) and may be typed as fractions."""
    assert make_pantry_item(" Flour ", "1 1/2", " cup ") == PantryItem("Flour", 1.5, "cup")
    assert make_pantry_item("salt", "0", "tsp").quantity == 0


@pytest.mark.parametrize("name, qty", [("", "1"), ("flour", "-1"), ("flour", "lots")])
def test_r3_make_pantry_item_rejects_invalid(name, qty):
    """R3: pantry items need a name and a quantity >= 0."""
    with pytest.raises(RecipeError):
        make_pantry_item(name, qty, "cup")


def test_r3_set_pantry_item_replaces_same_name_ignoring_case():
    """R3: adding an item whose name already exists updates it."""
    pantry = _pantry(("Flour", "1", "cup"), ("flour", "5", "cup"))
    assert list(pantry.values()) == [PantryItem("flour", 5.0, "cup")]


def test_r3_remove_pantry_item():
    """R3: items can be removed from the pantry, matched ignoring case."""
    pantry = _pantry(("Flour", "1", "cup"))
    assert remove_pantry_item(pantry, " FLOUR ") is True
    assert pantry == {}
    assert remove_pantry_item(pantry, "flour") is False


def test_r3_no_alerts_when_everything_available():
    """R3: no alerts when the pantry has enough of every ingredient."""
    recipe = make_recipe("Pancakes", "4", [("1", "cup", "flour"), ("2", "", "eggs")])
    pantry = _pantry(("FLOUR", "3", "Cup"), ("eggs", "12", ""))
    assert check_pantry(scale_recipe(recipe, 4).ingredients, pantry) == []


def test_r3_alerts_missing_ingredient():
    """R3: an ingredient not in the pantry produces a 'missing' alert."""
    recipe = make_recipe("Pancakes", "4", [("1", "cup", "flour"), ("2", "", "eggs")])
    pantry = _pantry(("flour", "3", "cup"))
    alerts = check_pantry(scale_recipe(recipe, 4).ingredients, pantry)
    assert [(a.name, a.status) for a in alerts] == [("eggs", "missing")]


def test_r3_alerts_not_enough_using_scaled_quantity():
    """R3: the check uses the scaled amount and reports the shortfall."""
    recipe = make_recipe("Pancakes", "4", [("1", "cup", "flour")])
    pantry = _pantry(("flour", "2", "cup"))
    assert check_pantry(scale_recipe(recipe, 8).ingredients, pantry) == []  # needs exactly 2
    alerts = check_pantry(scale_recipe(recipe, 12).ingredients, pantry)  # needs 3
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.status == "not_enough"
    assert alert.needed == pytest.approx(3)
    assert alert.on_hand == pytest.approx(2)
    assert alert.shortfall == pytest.approx(1)


def test_r3_alerts_unit_mismatch():
    """R3: same name but different unit can't be compared, so the user is told to check."""
    recipe = make_recipe("Cake", "1", [("200", "g", "sugar")])
    pantry = _pantry(("sugar", "2", "cup"))
    alerts = check_pantry(recipe.ingredients, pantry)
    assert len(alerts) == 1
    assert alerts[0].status == "unit_mismatch"
    assert alerts[0].on_hand_unit == "cup"


def test_r3_duplicate_ingredients_are_combined():
    """R3: the same ingredient listed twice is summed before checking the pantry."""
    recipe = make_recipe("Cake", "1", [("1", "cup", "sugar"), ("1", "cup", "Sugar")])
    pantry = _pantry(("sugar", "1.5", "cup"))
    alerts = check_pantry(recipe.ingredients, pantry)
    assert len(alerts) == 1
    assert alerts[0].status == "not_enough"
    assert alerts[0].needed == pytest.approx(2)
