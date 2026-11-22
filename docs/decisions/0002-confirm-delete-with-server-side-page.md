# 0002 — Confirm recipe deletion with a server-side page and a required flag

- Status: accepted
- Date: 2026-11-22
- Requirement: R5 (delete a recipe; ask if the user is sure first)

## Y-statement

In the context of **letting the user delete a saved recipe in a local Flask
app, where R5 requires asking "are you sure?" first**,
facing **the need for a confirmation that can't be skipped by accident (a
stray click, a browser with JavaScript off, a future caller of the code) and
that can be tested without a browser**,
we decided for **a separate confirmation page (GET shows "Delete <name>?
This cannot be undone" with *Yes, delete* and *Cancel*; only a POST carrying
`confirm=yes` deletes), backed by `recipe_core.delete_recipe(...,
confirmed=True)`, which refuses to delete unless `confirmed` is exactly
`True`**,
and neglected **a JavaScript `confirm()` pop-up on the Delete button, an
immediate delete with an Undo button (soft delete), and a pop-up with the page
as a fallback**,
to achieve **a confirmation rule that lives in the tested core module, works
in every browser, and fails safe, since a request without the confirmation
removes nothing**,
accepting that **deleting takes one more page load and click than a pop-up,
and that a mistaken confirmed delete can't be undone except by re-entering
the recipe**.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| **JavaScript `confirm()` pop-up** | Fewest clicks, but the check exists only in the browser. With JavaScript off, or for any direct POST, the delete happens with no question asked. It also can't be covered by the pytest tests of `recipe_core`. |
| **Delete at once, offer Undo** (soft delete) | Arguably friendlier, but R5 says to *ask before* deleting, not after. It also needs a "deleted" state in the data file (a change to ADR 0001's format) and rules for when undo expires. |
| **Pop-up plus page fallback** | Two code paths for the same rule, which is more to build and keep in sync for little gain in a single-user local app. |

## Consequences

- `delete_recipe` takes `confirmed` as a required keyword argument. Any new
  caller has to make the confirmation decision explicitly.
- `is_delete_confirmed` is the one place that reads the form answer. Only
  `"yes"` (any case, outer spaces ignored) counts.
- The delete route is `/delete-recipe/<key>`, not `/recipes/<key>/delete`,
  because the existing `/recipes/<path:key>` route would also match the
  `/delete` suffix.
- The "Deleted <name>." message is sent as a `?deleted=` query parameter
  instead of a Flask `flash`, so the app still needs no secret key.
