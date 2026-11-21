# 0001 — Store recipes and pantry in a single JSON file

- Status: accepted
- Date: 2026-11-20
- Requirement: R4 (save the recipes and pantry data)

## Y-statement

In the context of **saving recipes and pantry data for a single-user Flask
app that runs locally**,
facing **the need for data that survives restarts, is easy to inspect and
back up, needs no setup or server, and can be tested with temporary files**,
we decided for **one JSON file (`recipe_data.json`), rewritten in full on
every change through a temporary file and an atomic `os.replace`**,
and neglected **SQLite, an append-only JSON Lines (`.jsonl`) log, and CSV
files**,
to achieve **simple code that reads and writes whole Python dataclasses with
the standard library, a file a person can open and read, and no risk of a
half-written file after a crash**,
accepting that **every save rewrites the whole file, two app processes
writing at once would overwrite each other's changes, and changing the data
shape later will need a small migration step**.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| **SQLite** (`sqlite3`, standard library) | Handles concurrent writes and large data well, but needs a schema, SQL, and a mapping from rows to nested recipes and ingredients. That is more code than R4 needs for one user with a few dozen recipes, and the file can't be read without a tool. |
| **JSON Lines log** (`.jsonl`) | Fast appends, but loading means replaying the whole log, and deleting or replacing items needs compaction. `*.jsonl` is also ignored by git in this repo for other purposes, so using it would mix two meanings. |
| **CSV files** | Readable in a spreadsheet, but recipes are nested (a recipe has many ingredients), so it would take two linked files plus hand-written type conversion. |

## Consequences

- `recipe_core.save_data` and `load_data` are the only code that knows the
  file format. Switching to SQLite later would change only those two
  functions.
- If the file is invalid, `load_data` raises `StorageError` and the app
  refuses to start, so a corrupt file is never silently replaced with empty
  data.
- The data file is listed in `.gitignore` because it holds the user's data,
  not source code.
