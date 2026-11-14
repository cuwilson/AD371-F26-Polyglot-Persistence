# Projects & Tasks: SQL vs. MongoDB

Minimal Flask application exposing **the same REST API** over two persistence models:
- **SQLite (SQL, normalized 3NF):** `projects` + `tasks` tables, a foreign key, and `ON DELETE CASCADE`.
- **MongoDB (NoSQL):** one `projects` document per project, with an embedded `tasks` array.

This is an original educational demo inspired by a Google Tasks-style interface, not an integration with Google Tasks or Calendar.

## Install and run

Prerequisites: Python 3.10+ and, for real MongoDB testing, Docker Desktop with `docker compose`.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d mongo
python app.py
```

The default SQLite path is `tasks.sqlite3` (created automatically); the default Mongo URI is `mongodb://localhost:27017` and database is `task_polyglot`. Configuration environment variables: `SQLITE_PATH`, `MONGO_URI`, `MONGO_DB`, and `PORT`. If MongoDB is offline, SQL endpoints still work and `/api/mongo/...` returns HTTP 503. `docker compose down` stops Mongo; `docker compose down -v` **deletes its demo data**.

In another terminal:
```bash
python smoke_test.py
pytest -q
```

`smoke_test.py` uses HTTP against **both actual databases**. `pytest` tests SQLite and an in-memory MongoDB-compatible mock (mongomock), and does not replace a real MongoDB integration test.

## REST API (same paths for `sql` and `mongo`)

| Method | URL | Purpose |
| --- | --- | --- |
| POST | `/api/{backend}/projects` | Create project, JSON `{ "name": "Site", "description": "..." }` |
| GET | `/api/{backend}/projects` | List projects (includes tasks) |
| GET | `/api/{backend}/projects/{id}` | Read complete project with tasks |
| PATCH | `/api/{backend}/projects/{id}` | Update `name` or `description` |
| DELETE | `/api/{backend}/projects/{id}` | Delete project and tasks |
| POST | `/api/{backend}/projects/{id}/tasks` | Create task, JSON `{ "title": "Plan", "status": "todo" }` |
| GET | `/api/{backend}/projects/{id}/tasks` | List tasks |
| GET | `/api/{backend}/projects/{id}/tasks/{task_id}` | Read one task |
| PATCH | `/api/{backend}/projects/{id}/tasks/{task_id}` | Update `title`, `description`, `status`, or `due_at` |
| DELETE | `/api/{backend}/projects/{id}/tasks/{task_id}` | Delete task |

Task status is `todo`, `in_progress`, or `done`. `due_at` is nullable and, when set, must be an ISO 8601 timestamp with a timezone. Dates are stored as UTC ISO strings in this demo to keep output identical across backends. MongoDB production systems commonly use BSON Date types instead.

Example (PowerShell-friendly `curl.exe`):
```bash
curl.exe -X POST http://127.0.0.1:5000/api/sql/projects -H "Content-Type: application/json" -d '{"name":"Website"}'
```

Or use Postman to post JSON; copy the returned project ID for subsequent calls.

## Modeling tradeoffs

**SQL:** `projects` and `tasks` are separate, so each fact is stored once; `tasks.project_id` references `projects.id`; deleting a parent cascades to child rows; fetching a complete project involves two indexed queries in this implementation (or could use a join). The table/index schema is in `schema.sql`.

**MongoDB:** `projects` stores a `tasks` array. `find_one({_id: id})` loads the complete project with its tasks in a single query; `$push`, `$set` with positional `$`, and `$pull` modify the nested array atomically within its parent document. Deleting a project inherently removes its embedded tasks. An example extended-JSON document is in `mongo_schema.json`.

**Constraints:** MongoDB documents have a 16 MiB maximum size, so embedding works best for modest task counts. Consider a separate `tasks` collection with a `project_id` index if task arrays can grow very large or tasks must be queried frequently across projects. The included `tasks.id` multikey index is optional for this demo; `_id` already handles project retrieval, and nested task lookup is scoped to the project. Both backends need application-level authorization in a real multi-user environment.

**Caveats:** For teaching clarity, the demo does not implement authentication, pagination, concurrent write conflict handling, migration tooling, or production deployment configuration. `SQLITE_PATH=:memory:` is not supported here because the repository opens separate SQLite connections.
