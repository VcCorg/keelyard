"""Thin SQLite wrapper around the shared tracker.db.

This module reads/writes the same database that the agentic CLI uses
(~/.agent-cli-agentic/tracker.db). Schema is owned by agentic_cli.tracker;
this module only performs queries and inserts — never DDL.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional


class TrackerDB:
    """Read/write access to the shared tracker SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Products ──────────────────────────────────────────────────────────

    def product_create(self, name: str, description: str = "", tags: list[str] | None = None) -> dict:
        now = self._now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO products (name, description, tags, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, description, json.dumps(tags or []), now, now),
            )
        return {"name": name, "created_at": now}

    def product_list(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def product_get(self, name: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM products WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

    # ── Domains ───────────────────────────────────────────────────────────

    def domain_create(
        self,
        slug: str,
        product: str,
        domain_label: str,
        description: str = "",
        jira: str = "",
        bb: str = "",
        confluence: str = "",
    ) -> dict:
        now = self._now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO domains (name, product, domain, description, "
                "jira_project, bitbucket_project, confluence_space, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (slug, product, domain_label, description, jira, bb, confluence, now, now),
            )
        return {"slug": slug, "product": product, "created_at": now}

    def domain_list(self, product: str | None = None) -> list[dict]:
        with self._conn() as conn:
            if product:
                rows = conn.execute(
                    "SELECT * FROM domains WHERE product = ? ORDER BY name", (product,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM domains ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def domain_get(self, slug: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM domains WHERE name = ?", (slug,)).fetchone()
        return dict(row) if row else None

    # ── Domain Repos ──────────────────────────────────────────────────────

    def domain_link_repo(self, domain_slug: str, repo_slug: str, clone_url: str = "") -> dict:
        with self._conn() as conn:
            domain = conn.execute(
                "SELECT id FROM domains WHERE name = ?", (domain_slug,)
            ).fetchone()
            if not domain:
                raise ValueError(f"Domain '{domain_slug}' not found")
            conn.execute(
                "INSERT OR REPLACE INTO domain_repos (domain_id, repo_slug, clone_url) "
                "VALUES (?, ?, ?)",
                (domain["id"], repo_slug, clone_url),
            )
        return {"domain": domain_slug, "repo_slug": repo_slug}

    def domain_unlink_repo(self, domain_slug: str, repo_slug: str) -> bool:
        with self._conn() as conn:
            domain = conn.execute(
                "SELECT id FROM domains WHERE name = ?", (domain_slug,)
            ).fetchone()
            if not domain:
                return False
            cur = conn.execute(
                "DELETE FROM domain_repos WHERE domain_id = ? AND repo_slug = ?",
                (domain["id"], repo_slug),
            )
        return cur.rowcount > 0

    def domain_list_repos(self, domain_slug: str) -> list[dict]:
        with self._conn() as conn:
            domain = conn.execute(
                "SELECT id FROM domains WHERE name = ?", (domain_slug,)
            ).fetchone()
            if not domain:
                return []
            rows = conn.execute(
                "SELECT * FROM domain_repos WHERE domain_id = ?", (domain["id"],)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Domain Docs ───────────────────────────────────────────────────────

    def domain_add_doc(
        self, domain_slug: str, page_id: str, space_key: str = "", title: str = ""
    ) -> dict:
        with self._conn() as conn:
            domain = conn.execute(
                "SELECT id FROM domains WHERE name = ?", (domain_slug,)
            ).fetchone()
            if not domain:
                raise ValueError(f"Domain '{domain_slug}' not found")
            conn.execute(
                "INSERT OR REPLACE INTO domain_docs (domain_id, source_page_id, "
                "source_space_key, title) VALUES (?, ?, ?, ?)",
                (domain["id"], page_id, space_key, title),
            )
        return {"domain": domain_slug, "page_id": page_id}

    def domain_list_docs(self, domain_slug: str) -> list[dict]:
        with self._conn() as conn:
            domain = conn.execute(
                "SELECT id FROM domains WHERE name = ?", (domain_slug,)
            ).fetchone()
            if not domain:
                return []
            rows = conn.execute(
                "SELECT * FROM domain_docs WHERE domain_id = ?", (domain["id"],)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Repos (onboarded) ─────────────────────────────────────────────────

    def repo_register(
        self,
        name: str,
        path: str,
        repo_url: str = "",
        languages: list[str] | None = None,
        frameworks: list[str] | None = None,
        build_tools: list[str] | None = None,
        test_frameworks: list[str] | None = None,
        databases: list[str] | None = None,
        dependencies: int = 0,
        skills_installed: list[str] | None = None,
        has_docker: bool = False,
    ) -> dict:
        now = self._now()
        with self._conn() as conn:
            existing = conn.execute("SELECT id FROM repos WHERE path = ?", (path,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE repos SET name=?, repo_url=?, languages=?, frameworks=?, "
                    "build_tools=?, test_frameworks=?, databases=?, dependencies=?, "
                    "skills_installed=?, has_docker=?, last_updated_at=? WHERE path=?",
                    (
                        name, repo_url, json.dumps(languages or []),
                        json.dumps(frameworks or []), json.dumps(build_tools or []),
                        json.dumps(test_frameworks or []), json.dumps(databases or []),
                        dependencies, json.dumps(skills_installed or []),
                        int(has_docker), now, path,
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO repos (name, path, repo_url, languages, frameworks, "
                    "build_tools, test_frameworks, databases, dependencies, skills_installed, "
                    "has_docker, onboarded_at, last_updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        name, path, repo_url, json.dumps(languages or []),
                        json.dumps(frameworks or []), json.dumps(build_tools or []),
                        json.dumps(test_frameworks or []), json.dumps(databases or []),
                        dependencies, json.dumps(skills_installed or []),
                        int(has_docker), now, now,
                    ),
                )
        return {"name": name, "path": path, "registered_at": now}

    def repo_list(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM repos ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def repo_get(self, path: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM repos WHERE path = ?", (path,)).fetchone()
        return dict(row) if row else None

    # ── Activity Log ──────────────────────────────────────────────────────

    def activity_log(
        self,
        command: str,
        subcommand: str = "",
        status: str = "success",
        duration_ms: int = 0,
        args: dict | None = None,
        details: dict | None = None,
        repo_path: str = "",
    ) -> dict:
        ts = self._now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO activity_log (timestamp, command, subcommand, status, "
                "duration_ms, args, details, repo_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ts, command, subcommand, status, duration_ms,
                    json.dumps(args or {}), json.dumps(details or {}), repo_path,
                ),
            )
        return {"timestamp": ts, "command": command, "subcommand": subcommand}

    def activity_recent(self, limit: int = 25) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def activity_summary(self) -> dict:
        with self._conn() as conn:
            repo_count = conn.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
            project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            product_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            domain_count = conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
            activity_count = conn.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]
        return {
            "repos": repo_count,
            "projects": project_count,
            "products": product_count,
            "domains": domain_count,
            "total_activities": activity_count,
        }
