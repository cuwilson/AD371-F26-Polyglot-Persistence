"""Automated contract tests: SQLite + MongoDB-compatible in-memory mock."""
import mongomock
import pytest
from app import create_app
from sqlite_repo import SQLiteRepo
from mongo_repo import MongoRepo

@pytest.mark.parametrize("backend", ["sql", "mongo"])
def test_full_crud_and_project_delete(tmp_path, backend):
    app = create_app(SQLiteRepo(tmp_path / "test.sqlite3"),
                     MongoRepo(mongomock.MongoClient().test.projects))
    client = app.test_client()
    root = f"/api/{backend}/projects"
    p = client.post(root, json={"name": "Original"})
    assert p.status_code == 201
    pid = p.json["id"]
    assert client.get(root).status_code == 200
    assert client.get(f"{root}/{pid}").json["tasks"] == []
    assert client.patch(f"{root}/{pid}", json={"name": "Updated"}).json["name"] == "Updated"
    t = client.post(f"{root}/{pid}/tasks", json={"title": "First"})
    assert t.status_code == 201
    tid = t.json["id"]
    assert client.get(f"{root}/{pid}/tasks/{tid}").json["title"] == "First"
    assert len(client.get(f"{root}/{pid}/tasks").json) == 1
    assert client.patch(f"{root}/{pid}/tasks/{tid}", json={"status": "done"}).json["status"] == "done"
    assert len(client.get(f"{root}/{pid}").json["tasks"]) == 1
    assert client.delete(f"{root}/{pid}/tasks/{tid}").status_code == 204
    assert client.get(f"{root}/{pid}/tasks").json == []
    another = client.post(f"{root}/{pid}/tasks", json={"title": "Cascade"}).json["id"]
    assert client.delete(f"{root}/{pid}").status_code == 204
    assert client.get(f"{root}/{pid}").status_code == 404
    assert client.get(f"{root}/{pid}/tasks/{another}").status_code == 404

@pytest.mark.parametrize("backend", ["sql", "mongo"])
def test_validation(tmp_path, backend):
    app = create_app(SQLiteRepo(tmp_path / "test.sqlite3"),
                     MongoRepo(mongomock.MongoClient().test.projects))
    client = app.test_client()
    root = f"/api/{backend}/projects"
    assert client.post(root, json={"name": "  "}).status_code == 400
    pid = client.post(root, json={"name": "Valid"}).json["id"]
    assert client.post(f"{root}/{pid}/tasks", json={"title": "task", "status": "invalid"}).status_code == 400
    assert client.patch(f"{root}/{pid}", json={"id": "malicious"}).status_code == 400


def test_sql_foreign_key_constraint(tmp_path):
    import sqlite3

    repo = SQLiteRepo(tmp_path / "test_fk.sqlite3")

    with pytest.raises(sqlite3.IntegrityError):
        with repo.connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks
                (id, project_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "invalid-task-id",
                    "nonexistent-project-id",
                    "Orphaned Task",
                    "2026-11-13T12:00:00Z",
                    "2026-11-13T12:00:00Z",
                ),
            )