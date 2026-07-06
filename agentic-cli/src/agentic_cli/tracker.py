"""Centralized activity tracker for Agent-CLI Agentic Platform.

Uses SQLite to record all CLI command executions, onboarded repos,
created projects, and other tracked resources. Agents can query this
database to understand the user's environment and history.

Database location: ~/.agent-cli-agentic/tracker.db
"""

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


DB_DIR = Path.home() / ".agent-cli-agentic"
DB_PATH = DB_DIR / "tracker.db"

_SCHEMA_VERSION = 13

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- All CLI command executions
CREATE TABLE IF NOT EXISTS activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,  -- ISO 8601 UTC
    command     TEXT    NOT NULL,  -- top-level command group (kg, code, project, ...)
    subcommand  TEXT,              -- subcommand (onboard, create, ingest, ...)
    status      TEXT    NOT NULL DEFAULT 'success',  -- success | error
    duration_ms INTEGER,          -- wall-clock milliseconds
    args        TEXT,              -- JSON dict of significant arguments
    details     TEXT,              -- JSON dict of result details / error message
    repo_path   TEXT,             -- associated repo/project path if applicable
    correlation_id TEXT,          -- links a chain of actions across features
    entity_type    TEXT,          -- entity kind: project|skill|retriever|story|...
    entity_id      TEXT,          -- entity identifier (path/name/key)
    source         TEXT DEFAULT 'cli',  -- origin of the action: cli|dashboard
    actor          TEXT           -- authenticated principal (email/subject) if known
);

-- Central registry of onboarded repositories
CREATE TABLE IF NOT EXISTS repos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    path            TEXT    NOT NULL UNIQUE,
    repo_url        TEXT,
    languages       TEXT,   -- JSON list
    frameworks      TEXT,   -- JSON list
    build_tools     TEXT,   -- JSON list
    test_frameworks TEXT,   -- JSON list
    databases       TEXT,   -- JSON list
    dependencies    INTEGER DEFAULT 0,
    skills_installed TEXT,  -- JSON list
    has_docker      INTEGER DEFAULT 0,
    onboarded_at    TEXT    NOT NULL,
    last_updated_at TEXT    NOT NULL
);

-- Created agent projects
CREATE TABLE IF NOT EXISTS projects (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT    NOT NULL,
    path                    TEXT    NOT NULL UNIQUE,
    framework               TEXT,
    use_case                TEXT,
    tools                   TEXT,   -- JSON list
    working_location        TEXT,   -- Working directory for project (e.g., /workspace)
    google_project_id       TEXT,   -- GCP project ID
    google_location         TEXT,   -- GCP location (e.g., us-central1)
    vertex_ai_model         TEXT,   -- Vertex AI model name
    google_credentials_path TEXT,   -- Path to service account key
    domain_name             TEXT,   -- Associated domain slug
    created_at              TEXT    NOT NULL,
    updated_at              TEXT
);

-- Products: top-level grouping (e.g. CWOW, IMTO)
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,  -- e.g. 'CWOW'
    description TEXT,
    tags        TEXT,                      -- JSON list
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

-- Domains: scoped area within a product (e.g. Facility, Patient)
CREATE TABLE IF NOT EXISTS domains (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT    NOT NULL UNIQUE,  -- slug, e.g. 'cwow-facility'
    product                 TEXT    NOT NULL,          -- FK-like ref to products.name
    domain                  TEXT    NOT NULL,          -- domain label, e.g. 'Facility'
    description             TEXT,
    jira_project            TEXT,                      -- Jira project key, e.g. 'CWOW'
    jira_board              TEXT,                      -- Jira board name/ID
    bitbucket_project       TEXT,                      -- Bitbucket project key, e.g. 'CGF'
    bitbucket_url           TEXT,                      -- Bitbucket project/repo URL
    confluence_space        TEXT,                      -- source Confluence space, e.g. 'MTT'
    managed_confluence_space TEXT,                     -- agent-owned space, e.g. 'DVACWOWFAC'
    jira_dashboard          TEXT,                      -- Jira dashboard URL
    confluence_url          TEXT,                      -- Confluence page/space URL
    tags                    TEXT,                      -- JSON list of extra tags
    kg_ingested             INTEGER DEFAULT 0,         -- 1 if KG ingestion completed
    created_at              TEXT    NOT NULL,
    updated_at              TEXT    NOT NULL
);

-- Repos linked to a domain (selected by user from bitbucket project)
CREATE TABLE IF NOT EXISTS domain_repos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id   INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    repo_slug   TEXT    NOT NULL,
    repo_name   TEXT,
    clone_url   TEXT,
    onboarded   INTEGER DEFAULT 0,  -- 1 if onboarded via agent-cli code onboard
    onboarded_at TEXT,
    UNIQUE(domain_id, repo_slug)
);

-- Confluence doc sources tracked per domain
CREATE TABLE IF NOT EXISTS domain_docs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id         INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    source_page_id    TEXT    NOT NULL,
    source_space_key  TEXT,
    title             TEXT,
    managed_page_id   TEXT,                 -- page ID in managed space (after republish)
    source_version    INTEGER DEFAULT 0,    -- version at time of last sync
    synced_at         TEXT,
    UNIQUE(domain_id, source_page_id)
);

-- Persona-scoped development workspaces across tiers (repo/domain/product).
-- Records which persona opened which root, the canonical store, and the set of
-- repos present (either as editable worktrees or graph-only references).
CREATE TABLE IF NOT EXISTS workspaces (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tier        TEXT    NOT NULL,          -- repo | domain | product
    persona     TEXT    NOT NULL,          -- dev | tech-lead | solutions-architect | ...
    root_path   TEXT    NOT NULL UNIQUE,   -- workspace root the persona opens
    product     TEXT,
    domain      TEXT,
    store_path  TEXT,                       -- canonical store base (worktrees + graphs)
    repos       TEXT,                       -- JSON list of {slug, mode, branch, path}
    created_at  TEXT    NOT NULL,
    last_active TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_activity_timestamp   ON activity_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_command     ON activity_log(command);
CREATE INDEX IF NOT EXISTS idx_repos_name         ON repos(name);
CREATE INDEX IF NOT EXISTS idx_projects_name      ON projects(name);
CREATE INDEX IF NOT EXISTS idx_products_name      ON products(name);
CREATE INDEX IF NOT EXISTS idx_domains_product    ON domains(product);
CREATE INDEX IF NOT EXISTS idx_domains_name       ON domains(name);
CREATE INDEX IF NOT EXISTS idx_domain_repos_did   ON domain_repos(domain_id);
CREATE INDEX IF NOT EXISTS idx_domain_docs_did    ON domain_docs(domain_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_tier    ON workspaces(tier);
CREATE INDEX IF NOT EXISTS idx_workspaces_domain  ON workspaces(domain);
"""

_MIGRATION_V2 = """
-- v2: Add domain registry tables
CREATE TABLE IF NOT EXISTS domains (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT    NOT NULL UNIQUE,
    product                 TEXT    NOT NULL,
    domain                  TEXT    NOT NULL,
    description             TEXT,
    jira_project            TEXT,
    bitbucket_project       TEXT,
    confluence_space        TEXT,
    managed_confluence_space TEXT,
    tags                    TEXT,
    created_at              TEXT    NOT NULL,
    updated_at              TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS domain_repos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id   INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    repo_slug   TEXT    NOT NULL,
    repo_name   TEXT,
    clone_url   TEXT,
    onboarded   INTEGER DEFAULT 0,
    onboarded_at TEXT,
    UNIQUE(domain_id, repo_slug)
);
CREATE TABLE IF NOT EXISTS domain_docs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id         INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    source_page_id    TEXT    NOT NULL,
    source_space_key  TEXT,
    title             TEXT,
    managed_page_id   TEXT,
    source_version    INTEGER DEFAULT 0,
    synced_at         TEXT,
    UNIQUE(domain_id, source_page_id)
);
CREATE INDEX IF NOT EXISTS idx_domains_product  ON domains(product);
CREATE INDEX IF NOT EXISTS idx_domains_name     ON domains(name);
CREATE INDEX IF NOT EXISTS idx_domain_repos_did ON domain_repos(domain_id);
CREATE INDEX IF NOT EXISTS idx_domain_docs_did  ON domain_docs(domain_id);
"""

_MIGRATION_V3 = """
-- v3: Add products table (first-class product entity)
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT,
    tags        TEXT,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
-- Backfill: create product rows from existing domains
INSERT OR IGNORE INTO products (name, description, tags, created_at, updated_at)
    SELECT DISTINCT product, NULL, NULL, MIN(created_at), MAX(updated_at)
    FROM domains;
"""

_MIGRATION_V4 = """
-- v4: Add jira_dashboard column to domains
ALTER TABLE domains ADD COLUMN jira_dashboard TEXT;
"""

_MIGRATION_V5 = """
-- v5: Add confluence_url column to domains
ALTER TABLE domains ADD COLUMN confluence_url TEXT;
"""

_MIGRATION_V6 = """
-- v6: Add GCP and runtime config columns to projects
ALTER TABLE projects ADD COLUMN google_project_id TEXT;
ALTER TABLE projects ADD COLUMN google_location TEXT;
ALTER TABLE projects ADD COLUMN vertex_ai_model TEXT;
ALTER TABLE projects ADD COLUMN google_credentials_path TEXT;
ALTER TABLE projects ADD COLUMN domain_name TEXT;
ALTER TABLE projects ADD COLUMN updated_at TEXT;
"""

_MIGRATION_V7 = """
-- v7: Add working_location column to projects
ALTER TABLE projects ADD COLUMN working_location TEXT;
"""

_MIGRATION_V11 = """
-- v11: Add persona-scoped workspaces registry
CREATE TABLE IF NOT EXISTS workspaces (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tier        TEXT    NOT NULL,
    persona     TEXT    NOT NULL,
    root_path   TEXT    NOT NULL UNIQUE,
    product     TEXT,
    domain      TEXT,
    store_path  TEXT,
    repos       TEXT,
    created_at  TEXT    NOT NULL,
    last_active TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_workspaces_tier   ON workspaces(tier);
CREATE INDEX IF NOT EXISTS idx_workspaces_domain ON workspaces(domain);
"""

_MIGRATION_V12 = """
-- v12: Audit-linking columns so actions can be correlated across features.
ALTER TABLE activity_log ADD COLUMN correlation_id TEXT;
ALTER TABLE activity_log ADD COLUMN entity_type TEXT;
ALTER TABLE activity_log ADD COLUMN entity_id TEXT;
ALTER TABLE activity_log ADD COLUMN source TEXT DEFAULT 'cli';
CREATE INDEX IF NOT EXISTS idx_activity_correlation ON activity_log(correlation_id);
CREATE INDEX IF NOT EXISTS idx_activity_entity      ON activity_log(entity_type, entity_id);
"""

_MIGRATION_V13 = """
-- v13: record the authenticated principal behind an action (enterprise auth).
ALTER TABLE activity_log ADD COLUMN actor TEXT;
CREATE INDEX IF NOT EXISTS idx_activity_actor ON activity_log(actor);
"""

# Indexes that depend on columns added in v12/v13 migrations.  These are safe
# to run after all migrations have completed (IF NOT EXISTS makes them no-ops
# when already present).  They are NOT part of _SCHEMA_SQL to avoid a crash on
# existing databases that haven't yet been migrated to v12.
_POST_MIGRATION_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_activity_correlation ON activity_log(correlation_id);
CREATE INDEX IF NOT EXISTS idx_activity_entity      ON activity_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_activity_actor       ON activity_log(actor);
"""


def _ensure_db() -> Path:
    """Create the database and schema if they don't exist. Run migrations."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(_SCHEMA_SQL)
        # Check/set schema version and run migrations
        cur = conn.execute("SELECT version FROM schema_version LIMIT 1")
        row = cur.fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (_SCHEMA_VERSION,))
        else:
            current_version = row[0]
            if current_version < 2:
                conn.executescript(_MIGRATION_V2)
                conn.execute("UPDATE schema_version SET version = 2")
                current_version = 2
            if current_version < 3:
                conn.executescript(_MIGRATION_V3)
                conn.execute("UPDATE schema_version SET version = 3")
                current_version = 3
            if current_version < 4:
                conn.executescript(_MIGRATION_V4)
                conn.execute("UPDATE schema_version SET version = 4")
                current_version = 4
            if current_version < 5:
                conn.executescript(_MIGRATION_V5)
                conn.execute("UPDATE schema_version SET version = 5")
                current_version = 5
            if current_version < 6:
                conn.executescript(_MIGRATION_V6)
                conn.execute("UPDATE schema_version SET version = 6")
                current_version = 6
            if current_version < 7:
                conn.executescript(_MIGRATION_V7)
                conn.execute("UPDATE schema_version SET version = 7")
                current_version = 7
            if current_version < 8:
                # Add jira_board column to domains table
                conn.execute("ALTER TABLE domains ADD COLUMN jira_board TEXT")
                conn.execute("UPDATE schema_version SET version = 8")
                current_version = 8
            if current_version < 9:
                # Add kg_ingested column to domains table
                conn.execute("ALTER TABLE domains ADD COLUMN kg_ingested INTEGER DEFAULT 0")
                conn.execute("UPDATE schema_version SET version = 9")
                current_version = 9
            if current_version < 10:
                # Add bitbucket_url column to domains table
                conn.execute("ALTER TABLE domains ADD COLUMN bitbucket_url TEXT")
                conn.execute("UPDATE schema_version SET version = 10")
                current_version = 10
            if current_version < 11:
                conn.executescript(_MIGRATION_V11)
                conn.execute("UPDATE schema_version SET version = 11")
                current_version = 11
            if current_version < 12:
                conn.executescript(_MIGRATION_V12)
                conn.execute("UPDATE schema_version SET version = 12")
                current_version = 12
            if current_version < 13:
                conn.executescript(_MIGRATION_V13)
                conn.execute("UPDATE schema_version SET version = 13")
                current_version = 13
            # Ensure post-migration indexes exist (safe no-ops if already present)
            conn.executescript(_POST_MIGRATION_INDEXES)
        conn.commit()
    finally:
        conn.close()
    return DB_PATH


@contextmanager
def _get_conn():
    """Context manager for a database connection."""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now_iso() -> str:
    """Current UTC timestamp in ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(obj: Any) -> Optional[str]:
    """Serialize to JSON string, or None if obj is None/empty."""
    if obj is None:
        return None
    if isinstance(obj, (list, dict)):
        return json.dumps(obj) if obj else None
    return str(obj)


# ---------------------------------------------------------------------------
# Activity Log
# ---------------------------------------------------------------------------

class ActivityTimer:
    """Context manager that records a command execution to the activity log."""

    def __init__(self, command: str, subcommand: str = None, args: dict = None, repo_path: str = None):
        self.command = command
        self.subcommand = subcommand
        self.args = args
        self.repo_path = repo_path
        self._start: float = 0
        self._details: dict = {}
        self._status = "success"

    def set_details(self, **kwargs):
        """Set result details to be stored."""
        self._details.update(kwargs)

    def set_error(self, error: str):
        """Mark this execution as failed."""
        self._status = "error"
        self._details["error"] = error

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.monotonic() - self._start) * 1000)
        if exc_type is not None and self._status != "error":
            self._status = "error"
            self._details["error"] = str(exc_val)
        try:
            record_activity(
                command=self.command,
                subcommand=self.subcommand,
                status=self._status,
                duration_ms=duration_ms,
                args=self.args,
                details=self._details or None,
                repo_path=self.repo_path,
            )
        except Exception:
            pass  # Never let tracking failures break the CLI
        return False  # Don't suppress exceptions


def record_activity(
    command: str,
    subcommand: str = None,
    status: str = "success",
    duration_ms: int = None,
    args: dict = None,
    details: dict = None,
    repo_path: str = None,
    correlation_id: str = None,
    entity_type: str = None,
    entity_id: str = None,
    source: str = "cli",
    actor: str = None,
) -> None:
    """Insert a row into the activity log (the central audit trail).

    The ``correlation_id`` links a chain of actions across features, and
    ``entity_type``/``entity_id`` tag the thing acted upon so audits can be
    correlated (e.g. every action on a given project). ``source`` records
    whether the action originated from the CLI or the dashboard; ``actor``
    records the authenticated principal (email/subject) when known.
    """
    try:
        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO activity_log
                   (timestamp, command, subcommand, status, duration_ms, args,
                    details, repo_path, correlation_id, entity_type, entity_id, source, actor)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    _now_iso(),
                    command,
                    subcommand,
                    status,
                    duration_ms,
                    _json_dumps(args),
                    _json_dumps(details),
                    repo_path,
                    correlation_id,
                    entity_type,
                    entity_id,
                    source or "cli",
                    actor,
                ),
            )
    except Exception:
        pass  # Never break the CLI


def new_correlation_id() -> str:
    """Mint a correlation id for linking a chain of actions across features."""
    import uuid

    return uuid.uuid4().hex[:16]


def record_action(
    feature: str,
    action: str,
    *,
    entity_type: str = None,
    entity_id: str = None,
    correlation_id: str = None,
    source: str = "cli",
    status: str = "success",
    details: dict = None,
    repo_path: str = None,
    actor: str = None,
) -> None:
    """Auditor entry point: record a feature action in the central audit trail.

    ``feature`` is the top-level area (e.g. "project", "skill", "retriever",
    "ideate"); ``action`` is the verb (e.g. "manifest", "scan", "create",
    "push"). ``actor`` records the authenticated principal when known. This is
    a thin, intention-revealing wrapper over record_activity.
    """
    record_activity(
        command=feature,
        subcommand=action,
        status=status,
        args=None,
        details=details,
        repo_path=repo_path,
        correlation_id=correlation_id,
        entity_type=entity_type,
        entity_id=entity_id,
        source=source,
        actor=actor,
    )


def get_action_chain(correlation_id: str, limit: int = 200) -> list[dict]:
    """Return every audited action sharing a correlation id, oldest first."""
    if not correlation_id:
        return []
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM activity_log WHERE correlation_id = ? ORDER BY id ASC LIMIT ?",
            (correlation_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_activity(
    command: str = None,
    subcommand: str = None,
    status: str = None,
    limit: int = 50,
    since: str = None,
) -> list[dict]:
    """Query the activity log with optional filters."""
    clauses = []
    params = []

    if command:
        clauses.append("command = ?")
        params.append(command)
    if subcommand:
        clauses.append("subcommand = ?")
        params.append(subcommand)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if since:
        clauses.append("timestamp >= ?")
        params.append(since)

    where = " AND ".join(clauses)
    sql = "SELECT * FROM activity_log"
    if where:
        sql += " WHERE " + where
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with _get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_activity_summary() -> dict:
    """Get aggregate stats from the activity log."""
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]
        errors = conn.execute("SELECT COUNT(*) FROM activity_log WHERE status = 'error'").fetchone()[0]
        commands = conn.execute(
            "SELECT command, COUNT(*) as cnt FROM activity_log GROUP BY command ORDER BY cnt DESC"
        ).fetchall()
        recent = conn.execute(
            "SELECT timestamp FROM activity_log ORDER BY id DESC LIMIT 1"
        ).fetchone()

    return {
        "total_actions": total,
        "errors": errors,
        "success_rate": f"{((total - errors) / total * 100):.1f}%" if total else "N/A",
        "commands": {r["command"]: r["cnt"] for r in commands},
        "last_activity": recent["timestamp"] if recent else None,
    }


# ---------------------------------------------------------------------------
# Repos Registry
# ---------------------------------------------------------------------------

def register_repo(
    name: str,
    path: str,
    repo_url: str = None,
    languages: list = None,
    frameworks: list = None,
    build_tools: list = None,
    test_frameworks: list = None,
    databases: list = None,
    dependencies: int = 0,
    skills_installed: list = None,
    has_docker: bool = False,
) -> None:
    """Register or update an onboarded repo in the central registry."""
    now = _now_iso()
    with _get_conn() as conn:
        existing = conn.execute("SELECT id FROM repos WHERE path = ?", (path,)).fetchone()
        if existing:
            conn.execute(
                """UPDATE repos SET
                       name=?, repo_url=?, languages=?, frameworks=?, build_tools=?,
                       test_frameworks=?, databases=?, dependencies=?,
                       skills_installed=?, has_docker=?, last_updated_at=?
                   WHERE path=?""",
                (
                    name,
                    repo_url,
                    _json_dumps(languages),
                    _json_dumps(frameworks),
                    _json_dumps(build_tools),
                    _json_dumps(test_frameworks),
                    _json_dumps(databases),
                    dependencies,
                    _json_dumps(skills_installed),
                    1 if has_docker else 0,
                    now,
                    path,
                ),
            )
        else:
            conn.execute(
                """INSERT INTO repos
                   (name, path, repo_url, languages, frameworks, build_tools,
                    test_frameworks, databases, dependencies, skills_installed,
                    has_docker, onboarded_at, last_updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    name,
                    path,
                    repo_url,
                    _json_dumps(languages),
                    _json_dumps(frameworks),
                    _json_dumps(build_tools),
                    _json_dumps(test_frameworks),
                    _json_dumps(databases),
                    dependencies,
                    _json_dumps(skills_installed),
                    1 if has_docker else 0,
                    now,
                    now,
                ),
            )


def get_repos(name: str = None, check_exists: bool = False) -> list[dict]:
    """Query onboarded repos.

    Args:
        name: Filter by project name (substring match)
        check_exists: If True, add 'exists' field indicating if path exists on disk
    """
    with _get_conn() as conn:
        if name:
            rows = conn.execute("SELECT * FROM repos WHERE name LIKE ?", (f"%{name}%",)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM repos ORDER BY last_updated_at DESC").fetchall()
    results = []
    for r in rows:
        d = dict(r)
        for field in ("languages", "frameworks", "build_tools", "test_frameworks", "databases", "skills_installed"):
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        if check_exists:
            d["exists"] = Path(d["path"]).exists()
        results.append(d)
    return results


def remove_repo(path: str) -> bool:
    """Remove a repo from the central registry."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM repos WHERE path = ?", (path,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Projects Registry
# ---------------------------------------------------------------------------

def register_project(
    name: str,
    path: str,
    framework: str = None,
    use_case: str = None,
    tools: list = None,
    working_location: str = None,
) -> None:
    """Register a created agent project."""
    with _get_conn() as conn:
        existing = conn.execute("SELECT id FROM projects WHERE path = ?", (path,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE projects SET name=?, framework=?, use_case=?, tools=?, working_location=?, updated_at=? WHERE path=?",
                (name, framework, use_case, _json_dumps(tools), working_location, _now_iso(), path),
            )
        else:
            conn.execute(
                "INSERT INTO projects (name, path, framework, use_case, tools, working_location, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, path, framework, use_case, _json_dumps(tools), working_location, _now_iso(), _now_iso()),
            )


def update_project(
    name: str,
    working_location: str = None,
    google_project_id: str = None,
    google_location: str = None,
    vertex_ai_model: str = None,
    google_credentials_path: str = None,
    domain_name: str = None,
) -> bool:
    """Update project configuration (working location, GCP, domain, etc.).
    
    Returns True if project was updated, False if not found.
    """
    with _get_conn() as conn:
        existing = conn.execute("SELECT id FROM projects WHERE name = ?", (name,)).fetchone()
        if not existing:
            return False
        
        updates = []
        params = []
        
        if working_location is not None:
            updates.append("working_location = ?")
            params.append(working_location)
        if google_project_id is not None:
            updates.append("google_project_id = ?")
            params.append(google_project_id)
        if google_location is not None:
            updates.append("google_location = ?")
            params.append(google_location)
        if vertex_ai_model is not None:
            updates.append("vertex_ai_model = ?")
            params.append(vertex_ai_model)
        if google_credentials_path is not None:
            updates.append("google_credentials_path = ?")
            params.append(google_credentials_path)
        if domain_name is not None:
            updates.append("domain_name = ?")
            params.append(domain_name)
        
        if updates:
            updates.append("updated_at = ?")
            params.append(_now_iso())
            params.append(name)
            
            sql = f"UPDATE projects SET {', '.join(updates)} WHERE name = ?"
            conn.execute(sql, params)
            return True
        
        return False


def get_projects() -> list[dict]:
    """Query created projects."""
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("tools"):
            try:
                d["tools"] = json.loads(d["tools"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(d)
    return results


def get_project(name: str) -> dict | None:
    """Get a single project by name."""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("tools"):
        try:
            d["tools"] = json.loads(d["tools"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


def remove_project(name: str) -> bool:
    """Remove a project from the registry."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM projects WHERE name = ?", (name,))
    return cur.rowcount > 0


def validate_project(path: str, use_case: str | None = None) -> dict:
    """Run file-existence validation checks on a project path.

    Returns dict with boolean checks, score, and total.
    """
    from pathlib import Path as _Path
    p = _Path(path)
    checks = {
        "path_exists": p.exists(),
        "has_src": (p / "src").exists(),
        "has_pyproject": (p / "pyproject.toml").exists(),
        "has_env": (p / ".env").exists(),
        "has_domain_context": (p / ".domain-context.json").exists(),
        "has_persona_skills": (p / ".skills" / "domain").exists(),
    }
    if use_case == "scrum-master":
        checks["has_mcp_clients"] = (p / "src" / "mcp_clients.py").exists()
        checks["has_sprint_manager"] = (p / "src" / "sprint_manager.py").exists()
        checks["has_standup_generator"] = (p / "src" / "standup_generator.py").exists()
        checks["has_domain_loader"] = (p / "src" / "domain_loader.py").exists()
    elif use_case == "pr-reviewer":
        checks["has_watcher"] = (p / "src" / "watcher.py").exists()
        checks["has_reviewer"] = (p / "src" / "reviewer.py").exists()

    score = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {**checks, "score": score, "total": total}


# ---------------------------------------------------------------------------
# Product Registry
# ---------------------------------------------------------------------------

def register_product(
    name: str,
    description: str = None,
    tags: list = None,
) -> int:
    """Register or update a product. Returns the product id."""
    name_upper = name.upper()
    now = _now_iso()
    with _get_conn() as conn:
        existing = conn.execute("SELECT id FROM products WHERE name = ?", (name_upper,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE products SET description=?, tags=?, updated_at=? WHERE name=?",
                (description, _json_dumps(tags), now, name_upper),
            )
            return existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO products (name, description, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (name_upper, description, _json_dumps(tags), now, now),
            )
            return cur.lastrowid


def get_product(name: str) -> Optional[dict]:
    """Get a single product by name."""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE name = ?", (name.upper(),)).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("tags"):
        try:
            d["tags"] = json.loads(d["tags"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


def get_products() -> list[dict]:
    """List all products."""
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("tags"):
            try:
                d["tags"] = json.loads(d["tags"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(d)
    return results


def remove_product(name: str) -> bool:
    """Remove a product. Does NOT cascade-delete domains — caller should check first."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM products WHERE name = ?", (name.upper(),))
        return cur.rowcount > 0


def update_product(name: str, **fields) -> bool:
    """Update specific fields on a product."""
    allowed = {"description", "tags"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    if "tags" in updates and isinstance(updates["tags"], list):
        updates["tags"] = _json_dumps(updates["tags"])
    updates["updated_at"] = _now_iso()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    params = list(updates.values()) + [name.upper()]
    with _get_conn() as conn:
        cur = conn.execute(f"UPDATE products SET {set_clause} WHERE name=?", params)
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Domain Registry
# ---------------------------------------------------------------------------

def register_domain(
    name: str,
    product: str,
    domain: str,
    description: str = None,
    jira_project: str = None,
    jira_board: str = None,
    bitbucket_project: str = None,
    bitbucket_url: str = None,
    confluence_space: str = None,
    managed_confluence_space: str = None,
    jira_dashboard: str = None,
    confluence_url: str = None,
    tags: list = None,
    kg_ingested: int = 0,
) -> int:
    """Register or update a domain. Returns the domain id."""
    now = _now_iso()
    with _get_conn() as conn:
        existing = conn.execute("SELECT id FROM domains WHERE name = ?", (name,)).fetchone()
        if existing:
            conn.execute(
                """UPDATE domains SET
                       product=?, domain=?, description=?,
                       jira_project=?, jira_board=?, bitbucket_project=?, bitbucket_url=?,
                       confluence_space=?, managed_confluence_space=?,
                       jira_dashboard=?, confluence_url=?, tags=?, kg_ingested=?, updated_at=?
                   WHERE name=?""",
                (
                    product, domain, description,
                    jira_project, jira_board, bitbucket_project, bitbucket_url,
                    confluence_space, managed_confluence_space,
                    jira_dashboard, confluence_url, _json_dumps(tags), kg_ingested, now, name,
                ),
            )
            return existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO domains
                   (name, product, domain, description, jira_project, jira_board,
                    bitbucket_project, bitbucket_url, confluence_space, managed_confluence_space,
                    jira_dashboard, confluence_url, tags, kg_ingested, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    name, product, domain, description,
                    jira_project, jira_board, bitbucket_project, bitbucket_url,
                    confluence_space, managed_confluence_space,
                    jira_dashboard, confluence_url, _json_dumps(tags), kg_ingested, now, now,
                ),
            )
            return cur.lastrowid


def get_domain(name: str) -> Optional[dict]:
    """Get a single domain by name (slug)."""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM domains WHERE name = ?", (name,)).fetchone()
    if not row:
        return None
    return _parse_domain_row(row)


def get_domains(product: str = None) -> list[dict]:
    """List domains, optionally filtered by product."""
    with _get_conn() as conn:
        if product:
            rows = conn.execute(
                "SELECT * FROM domains WHERE product = ? ORDER BY product, domain",
                (product,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM domains ORDER BY product, domain"
            ).fetchall()
    return [_parse_domain_row(r) for r in rows]


def remove_domain(name: str) -> bool:
    """Remove a domain and its linked repos/docs (CASCADE)."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM domains WHERE name = ?", (name,))
        return cur.rowcount > 0


def update_domain(name: str, **fields) -> bool:
    """Update specific fields on a domain."""
    allowed = {
        "product", "domain", "description", "jira_project", "jira_board",
        "bitbucket_project", "bitbucket_url", "confluence_space", "managed_confluence_space",
        "jira_dashboard", "confluence_url", "tags", "kg_ingested",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    if "tags" in updates and isinstance(updates["tags"], list):
        updates["tags"] = _json_dumps(updates["tags"])
    updates["updated_at"] = _now_iso()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    params = list(updates.values()) + [name]
    with _get_conn() as conn:
        cur = conn.execute(f"UPDATE domains SET {set_clause} WHERE name=?", params)
        return cur.rowcount > 0


def mark_domain_ingested(name: str) -> bool:
    """Mark a domain as having KG ingestion completed."""
    return update_domain(name, kg_ingested=1)


def _parse_domain_row(row) -> dict:
    """Parse a domain row, deserializing JSON fields."""
    d = dict(row)
    if d.get("tags"):
        try:
            d["tags"] = json.loads(d["tags"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


# ---------------------------------------------------------------------------
# Domain Repos
# ---------------------------------------------------------------------------

def link_repo_to_domain(domain_name: str, repo_slug: str, repo_name: str = None, clone_url: str = None) -> bool:
    """Link a repo to a domain. Returns True if added, False if already exists."""
    
    # Convert Bitbucket web URL to git clone URL if needed
    if clone_url:
        clone_url = _normalize_bitbucket_clone_url(clone_url)
    
    with _get_conn() as conn:
        dom = conn.execute("SELECT id FROM domains WHERE name = ?", (domain_name,)).fetchone()
        if not dom:
            return False
        try:
            conn.execute(
                "INSERT INTO domain_repos (domain_id, repo_slug, repo_name, clone_url) VALUES (?, ?, ?, ?)",
                (dom["id"], repo_slug, repo_name, clone_url),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def _normalize_bitbucket_clone_url(url: str) -> str:
    """
    Convert Bitbucket Server web URLs to git clone (SCM) URLs.

    Works with any Bitbucket Server host (the scheme + host are preserved).

    Examples:
        https://bitbucket.example.com/projects/CGF/repos/my-repo
        -> https://bitbucket.example.com/scm/CGF/my-repo.git

        https://bitbucket.example.com/projects/CGF/repos/my-repo.git
        -> https://bitbucket.example.com/scm/CGF/my-repo.git
    """
    if not url:
        return url

    # Pattern: <scheme>://<host>/projects/{PROJECT}/repos/{REPO}
    # Convert to: <scheme>://<host>/scm/{PROJECT}/{REPO}.git
    import re
    pattern = r'^(https?://[^/]+)/projects/([^/]+)/repos/([^/?#]+?)(?:\.git)?/?$'
    match = re.match(pattern, url)

    if match:
        base = match.group(1)
        project = match.group(2)
        repo = match.group(3)
        return f"{base}/scm/{project}/{repo}.git"

    return url


def unlink_repo_from_domain(domain_name: str, repo_slug: str) -> bool:
    """Remove a repo link from a domain."""
    with _get_conn() as conn:
        dom = conn.execute("SELECT id FROM domains WHERE name = ?", (domain_name,)).fetchone()
        if not dom:
            return False
        cur = conn.execute(
            "DELETE FROM domain_repos WHERE domain_id = ? AND repo_slug = ?",
            (dom["id"], repo_slug),
        )
        return cur.rowcount > 0


def update_domain_repo_url(domain_name: str, repo_slug: str, clone_url: str) -> bool:
    """Update the clone URL for a domain repo."""
    # Normalize the URL before updating
    clone_url = _normalize_bitbucket_clone_url(clone_url)
    
    with _get_conn() as conn:
        dom = conn.execute("SELECT id FROM domains WHERE name = ?", (domain_name,)).fetchone()
        if not dom:
            return False
        cur = conn.execute(
            "UPDATE domain_repos SET clone_url = ? WHERE domain_id = ? AND repo_slug = ?",
            (clone_url, dom["id"], repo_slug),
        )
        return cur.rowcount > 0


def mark_domain_repo_onboarded(domain_name: str, repo_slug: str) -> bool:
    """Mark a domain repo as onboarded."""
    with _get_conn() as conn:
        dom = conn.execute("SELECT id FROM domains WHERE name = ?", (domain_name,)).fetchone()
        if not dom:
            return False
        cur = conn.execute(
            "UPDATE domain_repos SET onboarded = 1, onboarded_at = ? WHERE domain_id = ? AND repo_slug = ?",
            (_now_iso(), dom["id"], repo_slug),
        )
        return cur.rowcount > 0


def get_domain_repos(domain_name: str) -> list[dict]:
    """Get repos linked to a domain."""
    with _get_conn() as conn:
        dom = conn.execute("SELECT id FROM domains WHERE name = ?", (domain_name,)).fetchone()
        if not dom:
            return []
        rows = conn.execute(
            "SELECT * FROM domain_repos WHERE domain_id = ? ORDER BY repo_slug",
            (dom["id"],),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Domain Docs
# ---------------------------------------------------------------------------

def add_domain_doc(
    domain_name: str,
    source_page_id: str,
    source_space_key: str = None,
    title: str = None,
    managed_page_id: str = None,
    source_version: int = 0,
) -> bool:
    """Track a Confluence doc source for a domain."""
    with _get_conn() as conn:
        dom = conn.execute("SELECT id FROM domains WHERE name = ?", (domain_name,)).fetchone()
        if not dom:
            return False
        try:
            conn.execute(
                """INSERT INTO domain_docs
                   (domain_id, source_page_id, source_space_key, title,
                    managed_page_id, source_version, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (dom["id"], source_page_id, source_space_key, title,
                 managed_page_id, source_version, _now_iso()),
            )
            return True
        except sqlite3.IntegrityError:
            # Update existing
            conn.execute(
                """UPDATE domain_docs SET
                       source_space_key=?, title=?, managed_page_id=?,
                       source_version=?, synced_at=?
                   WHERE domain_id=? AND source_page_id=?""",
                (source_space_key, title, managed_page_id,
                 source_version, _now_iso(), dom["id"], source_page_id),
            )
            return True


def get_domain_docs(domain_name: str) -> list[dict]:
    """Get tracked doc sources for a domain."""
    with _get_conn() as conn:
        dom = conn.execute("SELECT id FROM domains WHERE name = ?", (domain_name,)).fetchone()
        if not dom:
            return []
        rows = conn.execute(
            "SELECT * FROM domain_docs WHERE domain_id = ? ORDER BY title",
            (dom["id"],),
        ).fetchall()
    return [dict(r) for r in rows]


def remove_domain_doc(domain_name: str, source_page_id: str) -> bool:
    """Remove a tracked Confluence doc from a domain."""
    with _get_conn() as conn:
        dom = conn.execute("SELECT id FROM domains WHERE name = ?", (domain_name,)).fetchone()
        if not dom:
            return False
        cursor = conn.execute(
            "DELETE FROM domain_docs WHERE domain_id = ? AND source_page_id = ?",
            (dom["id"], source_page_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Persona-scoped Workspaces
# ---------------------------------------------------------------------------

def register_workspace(
    tier: str,
    persona: str,
    root_path: str,
    product: Optional[str] = None,
    domain: Optional[str] = None,
    store_path: Optional[str] = None,
    repos: Optional[list[dict]] = None,
) -> int:
    """Register (or upsert by root_path) a persona-scoped workspace.

    Args:
        tier: One of ``repo`` | ``domain`` | ``product``.
        persona: Persona id (e.g. ``dev``, ``tech-lead``, ``solutions-architect``).
        root_path: Absolute path of the folder the persona opens.
        product: Product name (optional).
        domain: Domain slug (optional).
        store_path: Canonical store base used for worktrees/graphs (optional).
        repos: List of ``{slug, mode, branch, path}`` dicts (optional). ``mode``
            is ``code`` (editable worktree/clone) or ``graph-ref`` (graph only).

    Returns:
        The workspace row id.
    """
    now = _now_iso()
    repos_json = _json_dumps(repos)
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM workspaces WHERE root_path = ?", (root_path,)
        ).fetchone()
        if row:
            conn.execute(
                """UPDATE workspaces SET
                       tier=?, persona=?, product=?, domain=?,
                       store_path=?, repos=?, last_active=?
                   WHERE id=?""",
                (tier, persona, product, domain, store_path,
                 repos_json, now, row["id"]),
            )
            return row["id"]
        cur = conn.execute(
            """INSERT INTO workspaces
                   (tier, persona, root_path, product, domain,
                    store_path, repos, created_at, last_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tier, persona, root_path, product, domain,
             store_path, repos_json, now, now),
        )
        return cur.lastrowid


def get_workspaces(
    tier: Optional[str] = None,
    domain: Optional[str] = None,
    product: Optional[str] = None,
    persona: Optional[str] = None,
) -> list[dict]:
    """List registered workspaces, optionally filtered. Parses ``repos`` JSON."""
    clauses, params = [], []
    if tier:
        clauses.append("tier = ?"); params.append(tier)
    if domain:
        clauses.append("domain = ?"); params.append(domain)
    if product:
        clauses.append("product = ?"); params.append(product)
    if persona:
        clauses.append("persona = ?"); params.append(persona)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with _get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM workspaces{where} ORDER BY last_active DESC", params
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["repos"] = json.loads(d["repos"]) if d.get("repos") else []
        except (json.JSONDecodeError, TypeError):
            d["repos"] = []
        result.append(d)
    return result


def touch_workspace(root_path: str) -> bool:
    """Bump a workspace's last_active timestamp."""
    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE workspaces SET last_active = ? WHERE root_path = ?",
            (_now_iso(), root_path),
        )
        return cur.rowcount > 0


def remove_workspace(root_path: str) -> bool:
    """Remove a workspace registration by root_path."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM workspaces WHERE root_path = ?", (root_path,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Export for Agents
# ---------------------------------------------------------------------------

def get_full_context() -> dict:
    """
    Export the full tracked context as a dict.

    This is designed for agents to consume — gives them a snapshot of
    onboarded repos, created projects, domains, and recent activity.
    """
    return {
        "products": get_products(),
        "repos": get_repos(),
        "projects": get_projects(),
        "domains": get_domains(),
        "activity_summary": get_activity_summary(),
        "recent_activity": get_activity(limit=20),
    }


# ---------------------------------------------------------------------------
# Platform reset (admin)
# ---------------------------------------------------------------------------

# Logical groups of tables an admin can clear. Children are listed before
# parents so deletes are safe regardless of foreign-key state.
RESET_TABLE_GROUPS: dict[str, list[str]] = {
    "activity": ["activity_log"],
    "catalog": [
        "domain_docs", "domain_repos", "domains",
        "projects", "products", "repos", "workspaces",
    ],
}


def table_counts(tables: list[str]) -> dict[str, int]:
    """Return current row counts for the given tables (0 if missing)."""
    out: dict[str, int] = {}
    with _get_conn() as conn:
        for t in tables:
            try:
                out[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:  # noqa: BLE001 - table may not exist
                out[t] = 0
    return out


def clear_tables(tables: list[str]) -> dict[str, int]:
    """Delete all rows from the given tables. Returns rows deleted per table."""
    deleted: dict[str, int] = {}
    with _get_conn() as conn:
        for t in tables:
            try:
                before = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                conn.execute(f"DELETE FROM {t}")
                deleted[t] = before
            except Exception:  # noqa: BLE001
                deleted[t] = 0
    return deleted
