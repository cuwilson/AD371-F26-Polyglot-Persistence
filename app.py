import os
from flask import Flask, jsonify, request
from common import validate, PROJECT_FIELDS, TASK_FIELDS
from sqlite_repo import SQLiteRepo


def create_app(sql_repo=None, mongo_repo=None):
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    sql_repo = sql_repo or SQLiteRepo(os.getenv("SQLITE_PATH", "tasks.sqlite3"))
    # MongoDB is lazy-loaded so the SQL API also works without MongoDB running.
    if mongo_repo is None:
        try:
            from mongo_repo import MongoRepo
            mongo_repo = MongoRepo.from_uri(os.getenv("MONGO_URI", "mongodb://localhost:27017"),
                                            os.getenv("MONGO_DB", "task_polyglot"))
        except Exception as exc:
            app.logger.warning("MongoDB unavailable: %s", exc)

    def get_repo(backend):
        return {"sql": sql_repo, "mongo": mongo_repo}.get(backend)

    @app.errorhandler(ValueError)
    def invalid(err):
        return jsonify(error=str(err)), 400

    @app.route("/api/<backend>/projects", methods=["GET", "POST"])
    def projects(backend):
        repo = get_repo(backend)
        if repo is None:
            return jsonify(error="Backend unavailable; use sql or start MongoDB for mongo"), 503
        if request.method == "GET":
            return jsonify(repo.list_projects())
        payload = validate(request.get_json(silent=True), PROJECT_FIELDS, ("name",))
        return jsonify(repo.create_project(payload)), 201

    @app.route("/api/<backend>/projects/<pid>", methods=["GET", "PATCH", "DELETE"])
    def project(backend, pid):
        repo = get_repo(backend)
        if repo is None:
            return jsonify(error="Backend unavailable"), 503
        if request.method == "GET":
            result = repo.get_project(pid)
        elif request.method == "PATCH":
            payload = validate(request.get_json(silent=True), PROJECT_FIELDS)
            result = repo.update_project(pid, payload)
        else:
            return ("", 204) if repo.delete_project(pid) else (jsonify(error="Project not found"), 404)
        return (jsonify(result), 200) if result is not None else (jsonify(error="Project not found"), 404)

    @app.route("/api/<backend>/projects/<pid>/tasks", methods=["GET", "POST"])
    def tasks(backend, pid):
        repo = get_repo(backend)
        if repo is None:
            return jsonify(error="Backend unavailable"), 503
        if request.method == "GET":
            result = repo.list_tasks(pid)
            return (jsonify(result), 200) if result is not None else (jsonify(error="Project not found"), 404)
        payload = validate(request.get_json(silent=True), TASK_FIELDS, ("title",))
        result = repo.create_task(pid, payload)
        return (jsonify(result), 201) if result is not None else (jsonify(error="Project not found"), 404)

    @app.route("/api/<backend>/projects/<pid>/tasks/<tid>", methods=["GET", "PATCH", "DELETE"])
    def task(backend, pid, tid):
        repo = get_repo(backend)
        if repo is None:
            return jsonify(error="Backend unavailable"), 503
        if request.method == "GET":
            result = repo.get_task(pid, tid)
        elif request.method == "PATCH":
            payload = validate(request.get_json(silent=True), TASK_FIELDS)
            result = repo.update_task(pid, tid, payload)
        else:
            return ("", 204) if repo.delete_task(pid, tid) else (jsonify(error="Task not found"), 404)
        return (jsonify(result), 200) if result is not None else (jsonify(error="Task not found"), 404)

    @app.get("/")
    def home():
        return "Task Polyglot API: GET /api/sql/projects or /api/mongo/projects\n"

    return app


if __name__ == "__main__":
    create_app().run(port=int(os.getenv("PORT", "5000")), debug=False)
