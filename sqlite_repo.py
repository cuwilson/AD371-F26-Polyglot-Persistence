import sqlite3
from pathlib import Path
from common import now, new_id

SCHEMA = Path(__file__).with_name("schema.sql")

class SQLiteRepo:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as conn:
            conn.executescript(SCHEMA.read_text(encoding="utf-8"))

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")  # Must be enabled PER connection.
        return conn

    def list_projects(self):
        with self.connect() as conn:
            ids = [r["id"] for r in conn.execute("SELECT id FROM projects ORDER BY created_at, id")]
        return [self.get_project(pid) for pid in ids]

    def get_project(self, pid):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
            if not row:
                return None
            obj = dict(row)
            obj["tasks"] = [dict(t) for t in conn.execute(
                "SELECT id, title, description, status, due_at, created_at, updated_at "
                "FROM tasks WHERE project_id = ? ORDER BY created_at, id", (pid,))]
            return obj

    def create_project(self, data):
        pid, ts = new_id(), now()
        with self.connect() as conn:
            conn.execute("INSERT INTO projects (id, name, description, created_at, updated_at) "
                         "VALUES (?, ?, ?, ?, ?)",
                         (pid, data["name"], data.get("description", ""), ts, ts))
        return self.get_project(pid)

    def update_project(self, pid, data):
        with self.connect() as conn:
            if not conn.execute("SELECT 1 FROM projects WHERE id = ?", (pid,)).fetchone():
                return None
            if data:
                changes = {**data, "updated_at": now()}
                sql = "UPDATE projects SET " + ", ".join(f"{key} = ?" for key in changes) + " WHERE id = ?"
                conn.execute(sql, (*changes.values(), pid))
        return self.get_project(pid)

    def delete_project(self, pid):
        with self.connect() as conn:
            return conn.execute("DELETE FROM projects WHERE id = ?", (pid,)).rowcount > 0

    def list_tasks(self, pid):
        project = self.get_project(pid)
        return None if project is None else project["tasks"]

    def get_task(self, pid, tid):
        with self.connect() as conn:
            row = conn.execute("SELECT id, title, description, status, due_at, created_at, updated_at "
                               "FROM tasks WHERE id = ? AND project_id = ?", (tid, pid)).fetchone()
        return dict(row) if row else None

    def create_task(self, pid, data):
        tid, ts = new_id(), now()
        with self.connect() as conn:
            if not conn.execute("SELECT 1 FROM projects WHERE id = ?", (pid,)).fetchone():
                return None
            conn.execute("INSERT INTO tasks (id, project_id, title, description, status, due_at, created_at, updated_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (tid, pid, data["title"], data.get("description", ""),
                          data.get("status", "todo"), data.get("due_at"), ts, ts))
        return self.get_task(pid, tid)

    def update_task(self, pid, tid, data):
        with self.connect() as conn:
            if not conn.execute("SELECT 1 FROM tasks WHERE id = ? AND project_id = ?", (tid, pid)).fetchone():
                return None
            if data:
                changes = {**data, "updated_at": now()}
                sql = "UPDATE tasks SET " + ", ".join(f"{key} = ?" for key in changes) + " WHERE id = ? AND project_id = ?"
                conn.execute(sql, (*changes.values(), tid, pid))
                conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now(), pid))
        return self.get_task(pid, tid)

    def delete_task(self, pid, tid):
        with self.connect() as conn:
            result = conn.execute("DELETE FROM tasks WHERE id = ? AND project_id = ?", (tid, pid))
            if result.rowcount:
                conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now(), pid))
            return result.rowcount > 0
