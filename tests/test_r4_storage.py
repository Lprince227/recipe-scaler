"""Tests for R4: save the recipes and pantry data."""
import json

import pytest

from recipe_core import (
    StorageError,
    add_recipe,
    load_data,
    make_pantry_item,
    make_recipe,
    save_data,
    set_pantry_item,
)


def test_r4_save_then_load_round_trip(tmp_path):
    """R4: recipes and pantry saved to a file load back identical."""
    path = tmp_path / "data.json"
    recipes, pantry = {}, {}
    add_recipe(recipes, make_recipe("Pancakes", "4", [("1 1/2", "cup", "flour"), ("2", "", "eggs")]))
    set_pantry_item(pantry, make_pantry_item("Flour", "3", "cup"))

    save_data(path, recipes, pantry)
    loaded_recipes, loaded_pantry = load_data(path)

    assert loaded_recipes == recipes
    assert loaded_pantry == pantry


def test_r4_saved_file_is_json(tmp_path):
    """R4: data is stored as readable JSON."""
    path = tmp_path / "data.json"
    recipes = {}
    add_recipe(recipes, make_recipe("Toast", "1", [("2", "slice", "bread")]))
    save_data(path, recipes, {})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["recipes"][0]["name"] == "Toast"
    assert data["pantry"] == []


def test_r4_missing_file_loads_empty(tmp_path):
    """R4: on first run (no file yet) there are no recipes and an empty pantry."""
    assert load_data(tmp_path / "nope.json") == ({}, {})


@pytest.mark.parametrize(
    "content",
    ["not json", '{"recipes": "oops"}', '{"recipes": [{"name": "x"}]}', "[]"],
)
def test_r4_corrupt_file_raises_and_is_not_overwritten(tmp_path, content):
    """R4: an unreadable file raises StorageError and is left untouched."""
    path = tmp_path / "data.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(StorageError):
        load_data(path)
    assert path.read_text(encoding="utf-8") == content


def test_r4_save_overwrites_previous_data(tmp_path):
    """R4: each save replaces the file with the current state."""
    path = tmp_path / "data.json"
    pantry = {}
    set_pantry_item(pantry, make_pantry_item("salt", "1", "tsp"))
    save_data(path, {}, pantry)
    save_data(path, {}, {})
    assert load_data(path) == ({}, {})
