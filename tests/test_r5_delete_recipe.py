"""Tests for R5: delete a recipe from the saved data, after confirmation."""
import pytest

from recipe_core import (
    RecipeError,
    add_recipe,
    delete_recipe,
    is_delete_confirmed,
    load_data,
    make_pantry_item,
    make_recipe,
    save_data,
    set_pantry_item,
)


def _recipes(*names):
    recipes = {}
    for name in names:
        add_recipe(recipes, make_recipe(name, "4", [("1", "cup", "flour")]))
    return recipes


def test_r5_confirmed_delete_removes_recipe_and_returns_it():
    """R5: a confirmed delete removes the recipe and returns what was removed."""
    recipes = _recipes("Pancakes", "Waffles")
    removed = delete_recipe(recipes, "Pancakes", confirmed=True)
    assert removed is not None and removed.name == "Pancakes"
    assert [r.name for r in recipes.values()] == ["Waffles"]


@pytest.mark.parametrize("confirmed", [False, None, "yes", 1])
def test_r5_delete_without_confirmation_is_refused(confirmed):
    """R5: without an explicit confirmation nothing is deleted and an error is raised."""
    recipes = _recipes("Pancakes")
    with pytest.raises(RecipeError, match="confirm"):
        delete_recipe(recipes, "Pancakes", confirmed=confirmed)
    assert [r.name for r in recipes.values()] == ["Pancakes"]


def test_r5_delete_matches_name_ignoring_case_and_whitespace():
    """R5: the recipe to delete is found like R1 names: case and outer spaces ignored."""
    recipes = _recipes("Banana Bread")
    assert delete_recipe(recipes, "  banana BREAD ", confirmed=True).name == "Banana Bread"
    assert recipes == {}


def test_r5_delete_missing_recipe_changes_nothing():
    """R5: deleting a recipe that doesn't exist returns None and leaves the others."""
    recipes = _recipes("Pancakes")
    assert delete_recipe(recipes, "Lasagna", confirmed=True) is None
    assert [r.name for r in recipes.values()] == ["Pancakes"]


def test_r5_delete_removes_only_that_recipe_and_not_the_pantry():
    """R5: only the named recipe goes; other recipes and the pantry are unchanged."""
    recipes = _recipes("Pancakes", "Waffles", "Crepes")
    pantry = {}
    set_pantry_item(pantry, make_pantry_item("flour", "5", "cup"))
    pantry_before = dict(pantry)

    delete_recipe(recipes, "Waffles", confirmed=True)

    assert sorted(r.name for r in recipes.values()) == ["Crepes", "Pancakes"]
    assert pantry == pantry_before


def test_r5_deleted_recipe_stays_gone_after_save_and_reload(tmp_path):
    """R5: after a delete is saved (R4), reloading the file does not bring it back."""
    path = tmp_path / "data.json"
    recipes = _recipes("Pancakes", "Waffles")
    save_data(path, recipes, {})

    delete_recipe(recipes, "Pancakes", confirmed=True)
    save_data(path, recipes, {})

    loaded_recipes, _ = load_data(path)
    assert [r.name for r in loaded_recipes.values()] == ["Waffles"]


@pytest.mark.parametrize(
    "value, expected",
    [("yes", True), ("YES ", True), ("", False), (None, False), ("no", False), ("on", False)],
)
def test_r5_is_delete_confirmed_only_accepts_yes(value, expected):
    """R5: only the confirmation page's 'yes' answer counts as confirming a delete."""
    assert is_delete_confirmed(value) is expected
