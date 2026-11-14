from pymongo import MongoClient, ReturnDocument
from common import now, new_id

class MongoRepo:
    """One project document embeds its tasks; all task modifications are atomic within that document."""
    def __init__(self, collection):
        self.collection = collection
        self.collection.create_index("tasks.id")

    @classmethod
    def from_uri(cls, uri, db_name):
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        repo = cls(client[db_name]["projects"])
        repo.client = client
        return repo

    @staticmethod
    def clean(document):
        if document is None:
            return None
        # Expose identical JSON shapes for the two databases.
        return {"id": document["_id"], "name": document["name"],
                "description": document.get("description", ""),
                "created_at": document["created_at"], "updated_at": document["updated_at"],
                "tasks": document.get("tasks", [])}

    def list_projects(self):
        return [self.clean(doc) for doc in self.collection.find().sort([("created_at", 1), ("_id", 1)])]

    def get_project(self, pid):
        return self.clean(self.collection.find_one({"_id": pid}))

    def create_project(self, data):
        ts = now()
        doc = {"_id": new_id(), "name": data["name"], "description": data.get("description", ""),
               "created_at": ts, "updated_at": ts, "tasks": []}
        self.collection.insert_one(doc)
        return self.clean(doc)

    def update_project(self, pid, data):
        if not data:
            return self.get_project(pid)
        doc = self.collection.find_one_and_update({"_id": pid},
              {"$set": {**data, "updated_at": now()}}, return_document=ReturnDocument.AFTER)
        return self.clean(doc)

    def delete_project(self, pid):
        return self.collection.delete_one({"_id": pid}).deleted_count > 0

    def list_tasks(self, pid):
        project = self.get_project(pid)
        return None if project is None else project["tasks"]

    def get_task(self, pid, tid):
        doc = self.collection.find_one({"_id": pid}, {"tasks": 1})
    
        if not doc:
            return None
    
        return next(
            (task for task in doc.get("tasks", []) if task["id"] == tid),
            None
        )

    def create_task(self, pid, data):
        ts = now()
        task = {"id": new_id(), "title": data["title"], "description": data.get("description", ""),
                "status": data.get("status", "todo"), "due_at": data.get("due_at"),
                "created_at": ts, "updated_at": ts}
        result = self.collection.update_one({"_id": pid},
                   {"$push": {"tasks": task}, "$set": {"updated_at": ts}})
        return task if result.matched_count else None

    def update_task(self, pid, tid, data):
        if not data:
            return self.get_task(pid, tid)
        ts = now()
        updates = {"tasks.$." + key: value for key, value in data.items()}
        updates.update({"tasks.$.updated_at": ts, "updated_at": ts})
        result = self.collection.update_one({"_id": pid, "tasks.id": tid}, {"$set": updates})
        return self.get_task(pid, tid) if result.matched_count else None

    def delete_task(self, pid, tid):
        result = self.collection.update_one({"_id": pid, "tasks.id": tid},
                 {"$pull": {"tasks": {"id": tid}}, "$set": {"updated_at": now()}})
        return result.modified_count > 0
