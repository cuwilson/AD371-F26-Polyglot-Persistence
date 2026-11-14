# AI-Generated Database Architecture Audit

## Project Overview

This project compares two database approaches for a Projects and Tasks management application:

- **SQLite:** Relational database using normalized tables, primary keys, foreign keys, and cascading deletion.
- **MongoDB:** Document database using embedded tasks to retrieve a complete project in a single query.

The initial implementation was generated with assistance from ChatGPT. I reviewed the database schemas, tested the application, and corrected issues discovered during verification.

## Audit Findings

### 1. MongoDB Mock Compatibility

**Issue:** The original `get_task()` method used MongoDB positional projection (`{"tasks.$": 1}`) to retrieve an embedded task.

**Finding:** While this worked against the real MongoDB database, the automated pytest test failed because `mongomock` does not implement positional projection.

**Correction:** I updated `get_task()` to retrieve the project's embedded tasks in one query and locate the matching task in Python.

**Verification:** The automated test suite passed after this correction.

### 2. SQLite Foreign Key Enforcement

**Issue:** During direct SQLite testing, deleting a project initially left its associated tasks behind.

**Finding:** SQLite requires foreign key enforcement to be enabled separately for each database connection. The Flask application already enabled this, but my interactive SQLite terminal did not.

**Correction:** I enabled foreign key enforcement in the terminal using `PRAGMA foreign_keys = ON`.

**Verification:** After enabling enforcement, deleting a project automatically deleted its associated tasks.

### 3. Missing Foreign Key Test

**Issue:** The original automated test suite did not explicitly verify that SQLite rejects orphaned tasks.

**Correction:** I added `test_sql_foreign_key_constraint()` to `test_repos.py`.

**Verification:** The test passed, confirming that SQLite raises an `IntegrityError` when a task references a nonexistent project.

## Architecture Verification

**SQL:** The schema separates projects and tasks into normalized tables, uses parameterized queries, generates UUIDs, and defines foreign key constraints with `ON DELETE CASCADE`.

**MongoDB:** Each project embeds its associated tasks. This supports retrieving the complete project with a single `findOne()` query and allows atomic updates to embedded tasks.

## Conclusion

Both database approaches successfully support CRUD operations for this application. SQLite provides enforced relationships between projects and tasks, while MongoDB simplifies retrieval of a complete project through document embedding.

The testing process also demonstrated the importance of auditing AI-generated code rather than assuming that a working implementation has complete test coverage.