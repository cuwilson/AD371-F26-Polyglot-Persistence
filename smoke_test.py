"""HTTP CRUD verification against both REAL databases. Run after starting the server."""
import os
import requests

BASE = os.getenv("API_URL", "http://127.0.0.1:5000")


def call(method, backend, path, expected, **kwargs):
    response = requests.request(method, f"{BASE}/api/{backend}{path}", timeout=5, **kwargs)
    assert response.status_code == expected, (method, path, response.status_code, response.text)
    return response.json() if response.content else None


def run(backend):
    print(f"Testing {backend}...")
    p = call("POST", backend, "/projects", 201, json={"name": "Demo project"})
    pid = p["id"]
    try:
        assert call("GET", backend, f"/projects/{pid}", 200)["tasks"] == []
        assert any(x["id"] == pid for x in call("GET", backend, "/projects", 200))
        p = call("PATCH", backend, f"/projects/{pid}", 200, json={"name": "Renamed project"})
        assert p["name"] == "Renamed project"
        t = call("POST", backend, f"/projects/{pid}/tasks", 201, json={"title": "Write tests"})
        tid = t["id"]
        assert call("GET", backend, f"/projects/{pid}/tasks/{tid}", 200)["title"] == "Write tests"
        assert len(call("GET", backend, f"/projects/{pid}/tasks", 200)) == 1
        assert len(call("GET", backend, f"/projects/{pid}", 200)["tasks"]) == 1
        t = call("PATCH", backend, f"/projects/{pid}/tasks/{tid}", 200, json={"status": "done"})
        assert t["status"] == "done"
        call("DELETE", backend, f"/projects/{pid}/tasks/{tid}", 204)
        assert call("GET", backend, f"/projects/{pid}/tasks", 200) == []
        # Verify cascading deletion / embedded document deletion with a new task.
        call("POST", backend, f"/projects/{pid}/tasks", 201, json={"title": "Deleted with project"})
        call("DELETE", backend, f"/projects/{pid}", 204)
        assert call("GET", backend, f"/projects/{pid}", 404)["error"]
        print(f"PASS: {backend}")
    finally:
        # Cleanup on failed tests; ignore 404 if already deleted.
        requests.delete(f"{BASE}/api/{backend}/projects/{pid}", timeout=5)


if __name__ == "__main__":
    for name in ("sql", "mongo"):
        run(name)
