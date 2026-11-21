"""Flask web front end for the recipe scaler.

Run with:  py app.py   then open http://127.0.0.1:5000

All logic lives in recipe_core; this file only maps web requests to it.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

import recipe_core as core

INGREDIENT_ROWS = 12
DEFAULT_DATA_FILE = Path(__file__).resolve().parent / "recipe_data.json"


def create_app(data_file: str | os.PathLike | None = None) -> Flask:
    data_path = Path(data_file or os.environ.get("RECIPE_DATA_FILE") or DEFAULT_DATA_FILE)
    recipes, pantry = core.load_data(data_path)  # raises StorageError if the file is invalid
    lock = threading.Lock()

    app = Flask(__name__)
    app.jinja_env.filters["qty"] = core.format_quantity

    def save() -> None:
        core.save_data(data_path, recipes, pantry)

    @app.get("/")
    def index():
        ordered = sorted(recipes.items(), key=lambda kv: kv[1].name.casefold())
        return render_template("index.html", recipes=ordered)

    @app.route("/recipes/new", methods=["GET", "POST"])
    def new_recipe():
        form = request.form
        rows = [
            (form.get(f"qty{i}", ""), form.get(f"unit{i}", ""), form.get(f"name{i}", ""))
            for i in range(INGREDIENT_ROWS)
        ]
        if request.method == "POST":
            try:
                recipe = core.make_recipe(form.get("name", ""), form.get("servings", ""), rows)
            except core.RecipeError as exc:
                return render_template("new_recipe.html", error=str(exc), form=form, rows=rows), 400
            with lock:
                core.add_recipe(recipes, recipe)
                save()
            return redirect(url_for("view_recipe", key=core.normalize(recipe.name)))
        return render_template("new_recipe.html", error=None, form=form, rows=rows)

    @app.get("/recipes/<path:key>")
    def view_recipe(key: str):
        recipe = recipes.get(key)
        if recipe is None:
            abort(404)
        error = None
        servings = recipe.servings
        raw = request.args.get("servings")
        if raw is not None:
            try:
                servings = core.parse_servings(raw)
            except core.RecipeError as exc:
                error = str(exc)
        scaled = core.scale_recipe(recipe, servings)
        alerts = core.check_pantry(scaled.ingredients, pantry)
        return render_template(
            "recipe.html", key=key, recipe=recipe, scaled=scaled, alerts=alerts, error=error, core=core
        )

    @app.route("/pantry", methods=["GET", "POST"])
    def pantry_page():
        error = None
        if request.method == "POST":
            form = request.form
            try:
                item = core.make_pantry_item(form.get("name", ""), form.get("quantity", ""), form.get("unit", ""))
            except core.RecipeError as exc:
                error = str(exc)
            else:
                with lock:
                    core.set_pantry_item(pantry, item)
                    save()
                return redirect(url_for("pantry_page"))
        items = sorted(pantry.values(), key=lambda p: p.name.casefold())
        return render_template("pantry.html", items=items, error=error), (400 if error else 200)

    @app.post("/pantry/remove")
    def remove_pantry():
        with lock:
            if core.remove_pantry_item(pantry, request.form.get("name", "")):
                save()
        return redirect(url_for("pantry_page"))

    return app


if __name__ == "__main__":
    try:
        application = create_app()
    except core.StorageError as exc:
        sys.exit(f"Error: {exc}\nFix or move the data file, then start again. It was not changed.")
    print("Recipe Scaler running at http://127.0.0.1:5000  (Ctrl+C to stop)")
    application.run(host="127.0.0.1", port=5000, debug=False)
