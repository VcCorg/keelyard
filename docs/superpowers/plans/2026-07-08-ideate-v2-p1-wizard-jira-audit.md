# Ideate v2 — Phase 1 (Wizard shell + Rich Jira Cards + Field Mapping + Audit) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Ideate into a 5-step guided wizard that produces rich, editable Jira action-item cards, maps them to real Jira fields on push (with graceful degradation), and audits every created issue.

**Architecture:** Backend stays stateless for wizard state; the frontend owns wizard state and posts it per call. Story drafting still uses the existing `draft_stories()` (no new agent engine in P1). Push maps each card to real Jira fields discovered via `createmeta`, and records one audit row per create (success and failure) through the existing `agentic_cli.tracker` audit trail.

**Tech Stack:** FastAPI + Pydantic (backend), httpx (Jira REST v2), pytest + pytest-asyncio (tests), React + TypeScript + Tailwind (frontend, raw `fetch` per existing `Ideate.tsx`), lucide-react icons.

**Spec:** `docs/superpowers/specs/2026-07-08-ideate-v2-design.md`

---

## File Structure

**Backend (create):**
- `dashboard/backend/tests/__init__.py`, `conftest.py`, `test_smoke.py`, `test_jira_fields.py`, `test_ideate_push.py`, `test_ideate_api.py`
- `dashboard/backend/src/services/ideate_audit.py` — audit wrapper over `agentic_cli.tracker`.

**Backend (modify):**
- `src/services/ideate_service.py` — extend `Story`; add `push_stories()`.
- `src/services/jira_service.py` — `CreateMeta`/`JiraEpic` models, `_parse_create_meta`, `_build_issue_fields`, `_client`, `get_create_meta`, `list_issue_types`, `list_epics`, extend `create_issue`.
- `src/api/ideate.py` — extend `PushStory`/`PushRequest`; rewrite `/push`; add `/jira-meta`, `/audit`.

**Frontend (create):** `src/pages/ideate/{types.ts,StoryCard.tsx,ActivityPanel.tsx,StepScope.tsx,StepGather.tsx,StepDraft.tsx,StepReview.tsx,StepPush.tsx}`
**Frontend (modify):** `src/pages/Ideate.tsx` → wizard shell.

**Run commands:**
- Backend tests: `cd dashboard/backend && python -m pytest tests -v`
- Frontend build/typecheck: `cd dashboard/frontend && npm run build`

---

## Task 1: Test scaffolding

**Files:** Create `dashboard/backend/tests/__init__.py`, `conftest.py`, `test_smoke.py`

- [ ] **Step 1:** Create empty `dashboard/backend/tests/__init__.py`.
- [ ] **Step 2:** Create `dashboard/backend/tests/conftest.py`:

```python
"""Pytest bootstrap: make `import src...` work from the backend root."""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
```

- [ ] **Step 3:** Create `dashboard/backend/tests/test_smoke.py`:

```python
def test_imports():
    from src.services import ideate_service, jira_service  # noqa: F401
```

- [ ] **Step 4:** Run `cd dashboard/backend && python -m pytest tests/test_smoke.py -v` — Expected: PASS.
- [ ] **Step 5:** Commit:

```bash
git add dashboard/backend/tests/
git commit -m "test: bootstrap dashboard backend pytest scaffolding"
```

---

## Task 2: Extend the `Story` model

**Files:** Modify `src/services/ideate_service.py:19-25`; Test `tests/test_smoke.py`

- [ ] **Step 1:** Append to `tests/test_smoke.py`:

```python
def test_story_extended_fields():
    from src.services.ideate_service import Story
    s = Story(title="X", issue_type="Task", epic_key="ABC-1",
              story_points=3, assignee="jdoe", components=["api"])
    assert (s.issue_type, s.epic_key, s.story_points, s.assignee, s.components) == \
           ("Task", "ABC-1", 3, "jdoe", ["api"])

def test_story_defaults():
    from src.services.ideate_service import Story
    s = Story(title="X")
    assert s.issue_type == "Story" and s.epic_key is None and s.story_points is None
    assert s.assignee is None and s.components == []
```

- [ ] **Step 2:** Run `cd dashboard/backend && python -m pytest tests/test_smoke.py -k story -v` — Expected: FAIL.
- [ ] **Step 3:** Replace the `Story` class (lines 19-25) in `src/services/ideate_service.py`:

```python
class Story(BaseModel):
    title: str
    description: str = ""
    acceptance_criteria: List[str] = []
    priority: str = "Medium"
    labels: List[str] = []
    issue_type: str = "Story"
    epic_key: Optional[str] = None
    story_points: Optional[float] = None
    assignee: Optional[str] = None
    components: List[str] = []
```

- [ ] **Step 4:** Run the same test — Expected: PASS.
- [ ] **Step 5:** Commit:

```bash
git add dashboard/backend/src/services/ideate_service.py dashboard/backend/tests/test_smoke.py
git commit -m "feat: extend Ideate Story model with Jira fields"
```

---

## Task 3: Parse Jira `createmeta`

**Files:** Modify `src/services/jira_service.py`; Test `tests/test_jira_fields.py`

- [ ] **Step 1:** Create `dashboard/backend/tests/test_jira_fields.py`:

```python
from src.services.jira_service import _parse_create_meta, CreateMeta

SAMPLE = {"projects": [{"key": "CGF", "issuetypes": [
    {"name": "Story", "fields": {
        "summary": {"name": "Summary"}, "priority": {"name": "Priority"},
        "components": {"name": "Components"}, "assignee": {"name": "Assignee"},
        "customfield_10008": {"name": "Epic Link"},
        "customfield_10004": {"name": "Story Points"},
        "customfield_10100": {"name": "Acceptance Criteria"}}},
    {"name": "Task", "fields": {"summary": {"name": "Summary"}}}]}]}

def test_parse_meta_discovers_fields():
    m = _parse_create_meta(SAMPLE, "CGF")
    assert isinstance(m, CreateMeta)
    assert m.issue_types == ["Story", "Task"]
    assert m.epic_link_field == "customfield_10008"
    assert m.story_points_field == "customfield_10004"
    assert m.acceptance_criteria_field == "customfield_10100"
    assert m.has_components and m.has_assignee and m.has_priority

def test_parse_meta_missing_project():
    m = _parse_create_meta({"projects": []}, "NOPE")
    assert m.issue_types == [] and m.epic_link_field is None and m.has_components is False
```

- [ ] **Step 2:** Run `cd dashboard/backend && python -m pytest tests/test_jira_fields.py -v` — Expected: FAIL.
- [ ] **Step 3:** In `src/services/jira_service.py`, add after the `JiraStatus` class (~line 29):

```python
class CreateMeta(BaseModel):
    project_key: str
    issue_types: list[str] = []
    epic_link_field: Optional[str] = None
    story_points_field: Optional[str] = None
    acceptance_criteria_field: Optional[str] = None
    has_components: bool = False
    has_assignee: bool = False
    has_priority: bool = False


class JiraEpic(BaseModel):
    key: str
    summary: str = ""
```

Then add at module scope:

```python
def _parse_create_meta(data: dict, project_key: str) -> CreateMeta:
    """Turn a Jira /issue/createmeta payload into a typed CreateMeta.

    Detects custom-field ids for Epic Link, Story Points, and Acceptance
    Criteria by name; records whether components/assignee/priority are on the
    create screen.
    """
    project = next((p for p in (data.get("projects") or []) if p.get("key") == project_key), None)
    if not project:
        return CreateMeta(project_key=project_key)

    issue_types = [it.get("name", "") for it in project.get("issuetypes", []) if it.get("name")]
    epic = points = ac = None
    has_components = has_assignee = has_priority = False
    for it in project.get("issuetypes", []):
        for fid, meta in (it.get("fields") or {}).items():
            name = (meta.get("name") or "").strip().lower()
            if fid == "components":
                has_components = True
            elif fid == "assignee":
                has_assignee = True
            elif fid == "priority":
                has_priority = True
            elif name == "epic link" and not epic:
                epic = fid
            elif name == "story points" and not points:
                points = fid
            elif name == "acceptance criteria" and not ac:
                ac = fid
    return CreateMeta(
        project_key=project_key, issue_types=issue_types,
        epic_link_field=epic, story_points_field=points,
        acceptance_criteria_field=ac, has_components=has_components,
        has_assignee=has_assignee, has_priority=has_priority,
    )
```

- [ ] **Step 4:** Run the test — Expected: PASS.
- [ ] **Step 5:** Commit:

```bash
git add dashboard/backend/src/services/jira_service.py dashboard/backend/tests/test_jira_fields.py
git commit -m "feat: parse Jira createmeta into typed CreateMeta"
```

---

## Task 4: Build issue fields with graceful degradation

**Files:** Modify `src/services/jira_service.py`; Test `tests/test_jira_fields.py`

- [ ] **Step 1:** Append to `tests/test_jira_fields.py`:

```python
from src.services.jira_service import _build_issue_fields

FULL = CreateMeta(project_key="CGF", issue_types=["Story"],
    epic_link_field="customfield_10008", story_points_field="customfield_10004",
    acceptance_criteria_field="customfield_10100",
    has_components=True, has_assignee=True, has_priority=True)

def test_build_fields_full():
    f = _build_issue_fields(project_key="CGF", summary="S", description="D",
        issue_type="Story", labels=["a b"], priority="High", epic_key="CGF-1",
        story_points=5, assignee="jdoe", components=["api"],
        acceptance_criteria=["ac1", "ac2"], meta=FULL)
    assert f["project"] == {"key": "CGF"} and f["issuetype"] == {"name": "Story"}
    assert f["labels"] == ["a-b"] and f["priority"] == {"name": "High"}
    assert f["customfield_10008"] == "CGF-1" and f["customfield_10004"] == 5
    assert f["assignee"] == {"name": "jdoe"} and f["components"] == [{"name": "api"}]
    assert f["customfield_10100"] == "ac1\nac2"
    assert "Acceptance criteria" not in f["description"]

def test_build_fields_degrade():
    bare = CreateMeta(project_key="CGF", issue_types=["Story"])
    f = _build_issue_fields(project_key="CGF", summary="S", description="D",
        issue_type="Story", labels=[], priority="High", epic_key="CGF-1",
        story_points=5, assignee="jdoe", components=["api"],
        acceptance_criteria=["ac1"], meta=bare)
    for k in ("customfield_10008", "customfield_10004", "assignee", "components", "priority"):
        assert k not in f
    assert "Acceptance criteria:" in f["description"] and "- ac1" in f["description"]

def test_build_fields_no_meta_permissive():
    f = _build_issue_fields(project_key="CGF", summary="S", description="D",
        issue_type="Story", labels=[], priority="High", epic_key=None,
        story_points=None, assignee=None, components=[], acceptance_criteria=[], meta=None)
    assert f["priority"] == {"name": "High"}
```

- [ ] **Step 2:** Run `cd dashboard/backend && python -m pytest tests/test_jira_fields.py -k build -v` — Expected: FAIL.
- [ ] **Step 3:** Add to `src/services/jira_service.py` at module scope:

```python
def _build_issue_fields(
    project_key: str, summary: str, description: str = "", issue_type: str = "Story",
    labels: Optional[list[str]] = None, priority: Optional[str] = None,
    epic_key: Optional[str] = None, story_points: Optional[float] = None,
    assignee: Optional[str] = None, components: Optional[list[str]] = None,
    acceptance_criteria: Optional[list[str]] = None, meta: Optional[CreateMeta] = None,
) -> dict:
    """Assemble the Jira `fields` dict, mapping real fields when supported and
    degrading gracefully. meta=None → permissive for standard fields; custom
    fields omitted (AC appended to description)."""
    labels = labels or []
    components = components or []
    acceptance_criteria = [a for a in (acceptance_criteria or []) if a]
    fields: dict = {"project": {"key": project_key}, "summary": summary[:255],
                    "issuetype": {"name": issue_type or "Story"}}

    def ok(flag: bool) -> bool:
        return flag if meta is not None else True

    if labels:
        fields["labels"] = [l.replace(" ", "-") for l in labels if l]
    if priority and ok(getattr(meta, "has_priority", False)):
        fields["priority"] = {"name": priority}
    if assignee and ok(getattr(meta, "has_assignee", False)):
        fields["assignee"] = {"name": assignee}
    if components and ok(getattr(meta, "has_components", False)):
        fields["components"] = [{"name": c} for c in components if c]
    if epic_key and getattr(meta, "epic_link_field", None):
        fields[meta.epic_link_field] = epic_key
    if story_points is not None and getattr(meta, "story_points_field", None):
        fields[meta.story_points_field] = story_points

    ac_field = getattr(meta, "acceptance_criteria_field", None)
    desc = description or ""
    if acceptance_criteria:
        if ac_field:
            fields[ac_field] = "\n".join(acceptance_criteria)
        else:
            desc = (desc + "\n\nAcceptance criteria:\n"
                    + "\n".join(f"- {a}" for a in acceptance_criteria)).strip()
    if desc:
        fields["description"] = desc
    return fields
```

- [ ] **Step 4:** Run `python -m pytest tests/test_jira_fields.py -v` — Expected: PASS.
- [ ] **Step 5:** Commit:

```bash
git add dashboard/backend/src/services/jira_service.py dashboard/backend/tests/test_jira_fields.py
git commit -m "feat: build Jira issue fields with real mapping + degradation"
```

---

## Task 5: createmeta/epics fetchers + refactor `create_issue`

**Files:** Modify `src/services/jira_service.py`; Test `tests/test_jira_fields.py`

- [ ] **Step 1:** Append to `tests/test_jira_fields.py`:

```python
import src.services.jira_service as js

class _Resp:
    status_code = 201
    text = ""
    def json(self): return {"key": "CGF-42"}

class _Client:
    captured = {}
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def post(self, path, json): _Client.captured = json; return _Resp()

def test_create_issue_sends_mapped_fields(monkeypatch):
    monkeypatch.setattr(js, "is_configured", lambda: True)
    monkeypatch.setattr(js, "_server_url", lambda: "https://jira.example")
    monkeypatch.setattr(js, "_token", lambda: "tok")
    monkeypatch.setattr(js.httpx, "Client", _Client)
    monkeypatch.setattr(js, "get_create_meta", lambda pk: FULL)
    out = js.create_issue(project_key="CGF", summary="S", description="D",
        issue_type="Story", labels=["x"], priority="High", epic_key="CGF-1",
        story_points=3, assignee="jdoe", components=["api"], acceptance_criteria=["ac1"])
    sent = _Client.captured["fields"]
    assert sent["customfield_10008"] == "CGF-1" and sent["customfield_10100"] == "ac1"
    assert out == {"key": "CGF-42", "url": "https://jira.example/browse/CGF-42"}
```

- [ ] **Step 2:** Run `cd dashboard/backend && python -m pytest tests/test_jira_fields.py -k create_issue -v` — Expected: FAIL.
- [ ] **Step 3:** In `src/services/jira_service.py` add at module scope:

```python
def _client() -> httpx.Client:
    return httpx.Client(
        base_url=f"{_server_url()}/rest/api/2",
        headers={"Authorization": f"Bearer {_token()}", "Accept": "application/json",
                 "Content-Type": "application/json"},
        verify=_verify_ssl(), timeout=30.0)


def get_create_meta(project_key: str) -> CreateMeta:
    """Fetch+parse create screen metadata; empty CreateMeta on any error."""
    if not is_configured() or not project_key:
        return CreateMeta(project_key=project_key)
    try:
        with _client() as c:
            resp = c.get("/issue/createmeta",
                         params={"projectKeys": project_key, "expand": "projects.issuetypes.fields"})
            resp.raise_for_status()
            return _parse_create_meta(resp.json(), project_key)
    except Exception:  # noqa: BLE001
        return CreateMeta(project_key=project_key)


def list_issue_types(project_key: str) -> list[str]:
    return get_create_meta(project_key).issue_types


def list_epics(project_key: str, max_results: int = 100) -> list[JiraEpic]:
    """List open epics (key + summary) for the epic picker."""
    if not is_configured() or not project_key:
        return []
    jql = f'project = "{project_key}" AND issuetype = Epic AND statusCategory != Done ORDER BY updated DESC'
    try:
        with _client() as c:
            resp = c.get("/search", params={"jql": jql, "maxResults": max_results, "fields": "summary"})
            resp.raise_for_status()
            data = resp.json()
    except Exception:  # noqa: BLE001
        return []
    return [JiraEpic(key=i.get("key", ""), summary=(i.get("fields") or {}).get("summary", ""))
            for i in data.get("issues", [])]
```

Then replace the body of `create_issue` (lines ~101-148) with:

```python
def create_issue(
    project_key: str, summary: str, description: str = "", issue_type: str = "Story",
    labels: Optional[list[str]] = None, priority: Optional[str] = None,
    epic_key: Optional[str] = None, story_points: Optional[float] = None,
    assignee: Optional[str] = None, components: Optional[list[str]] = None,
    acceptance_criteria: Optional[list[str]] = None, meta: Optional[CreateMeta] = None,
) -> dict:
    """Create a Jira issue with real field mapping. Returns {key, url}. Raises on failure."""
    if not is_configured():
        raise RuntimeError("Jira is not configured. Set JIRA_SERVER_URL and "
                           "JIRA_PERSONAL_ACCESS_TOKEN on the dashboard backend.")
    if not project_key:
        raise ValueError("A Jira project key is required")
    if not summary:
        raise ValueError("A summary is required")
    if meta is None:
        meta = get_create_meta(project_key)
    fields = _build_issue_fields(
        project_key=project_key, summary=summary, description=description,
        issue_type=issue_type, labels=labels, priority=priority, epic_key=epic_key,
        story_points=story_points, assignee=assignee, components=components,
        acceptance_criteria=acceptance_criteria, meta=meta)
    with _client() as c:
        resp = c.post("/issue", json={"fields": fields})
        if resp.status_code >= 300:
            raise RuntimeError(f"Jira create failed ({resp.status_code}): {resp.text[:300]}")
        key = resp.json().get("key", "")
    return {"key": key, "url": f"{_server_url()}/browse/{key}" if key else ""}
```

- [ ] **Step 4:** Run `python -m pytest tests/test_jira_fields.py -v` — Expected: PASS.
- [ ] **Step 5:** Commit:

```bash
git add dashboard/backend/src/services/jira_service.py dashboard/backend/tests/test_jira_fields.py
git commit -m "feat: Jira createmeta/epics fetchers + field-mapped create_issue"
```

---

## Task 6: Audit wrapper

**Files:** Create `src/services/ideate_audit.py`; Test `tests/test_ideate_push.py`

- [ ] **Step 1:** Create `dashboard/backend/tests/test_ideate_push.py`:

```python
import src.services.ideate_audit as audit

def test_record_success(monkeypatch):
    calls = {}
    monkeypatch.setattr(audit, "_tracker_record_action",
                        lambda feature, action, **kw: calls.update({"f": feature, "a": action, **kw}))
    audit.record_jira_create(project_key="CGF", key="CGF-1", url="u", ok=True,
                             title="S", actor="jdoe@x.com", correlation_id="c1")
    assert calls["f"] == "ideate" and calls["a"] == "jira_create"
    assert calls["status"] == "success" and calls["entity_type"] == "jira_issue"
    assert calls["entity_id"] == "CGF-1" and calls["actor"] == "jdoe@x.com"
    assert calls["source"] == "dashboard" and calls["correlation_id"] == "c1"
    assert calls["details"]["title"] == "S"

def test_record_failure(monkeypatch):
    seen = {}
    monkeypatch.setattr(audit, "_tracker_record_action",
                        lambda feature, action, **kw: seen.update(kw))
    audit.record_jira_create(project_key="CGF", key="", url="", ok=False,
                             title="S", error="boom", actor=None, correlation_id="c1")
    assert seen["status"] == "error" and seen["entity_id"] == "CGF"
    assert seen["details"]["error"] == "boom"
```

- [ ] **Step 2:** Run `cd dashboard/backend && python -m pytest tests/test_ideate_push.py -k record -v` — Expected: FAIL.
- [ ] **Step 3:** Create `src/services/ideate_audit.py`:

```python
"""Ideate audit — records mutating actions to the central audit trail.

Thin wrapper over agentic_cli.tracker.record_action so every Jira issue created
from Ideate is traceable: who, what, target, status, correlation id.
"""
from __future__ import annotations

from typing import Optional

try:
    from agentic_cli.tracker import record_action as _tracker_record_action
    from agentic_cli.tracker import new_correlation_id as _new_correlation_id
except Exception:  # noqa: BLE001 - never break the request path
    def _tracker_record_action(feature, action, **kwargs):  # type: ignore
        return None

    def _new_correlation_id() -> str:  # type: ignore
        import uuid
        return uuid.uuid4().hex[:16]


def new_correlation_id() -> str:
    """Mint a correlation id to link a push batch's audit rows."""
    return _new_correlation_id()


def record_jira_create(*, project_key: str, key: str, url: str, ok: bool, title: str,
                       error: Optional[str] = None, actor: Optional[str] = None,
                       correlation_id: Optional[str] = None) -> None:
    """Audit a single Jira issue creation (success or failure)."""
    _tracker_record_action(
        "ideate", "jira_create",
        status="success" if ok else "error",
        entity_type="jira_issue", entity_id=key or project_key,
        source="dashboard", actor=actor, correlation_id=correlation_id,
        details={"title": title, "project": project_key, "url": url, "error": error})
```

- [ ] **Step 4:** Run the test — Expected: PASS.
- [ ] **Step 5:** Commit:

```bash
git add dashboard/backend/src/services/ideate_audit.py dashboard/backend/tests/test_ideate_push.py
git commit -m "feat: Ideate audit wrapper over central tracker"
```

---

## Task 7: `push_stories()`

**Files:** Modify `src/services/ideate_service.py`; Test `tests/test_ideate_push.py`

- [ ] **Step 1:** Append to `tests/test_ideate_push.py`:

```python
import src.services.ideate_service as isvc
from src.services.ideate_service import Story

def test_push_creates_and_audits(monkeypatch):
    created, audits = [], []
    import src.services.jira_service as js
    monkeypatch.setattr(js, "create_issue", lambda **kw: created.append(kw) or {"key": "CGF-100", "url": "u"})
    monkeypatch.setattr(js, "get_create_meta", lambda pk: None)
    monkeypatch.setattr(audit, "record_jira_create", lambda **kw: audits.append(kw))
    out = isvc.push_stories("CGF", [Story(title="A", acceptance_criteria=["x"], epic_key="CGF-1")], actor="jdoe@x.com")
    assert out["created"] == 1 and out["results"][0]["ok"] and out["results"][0]["key"] == "CGF-100"
    assert created[0]["epic_key"] == "CGF-1" and created[0]["acceptance_criteria"] == ["x"]
    assert len(audits) == 1 and audits[0]["ok"] and audits[0]["actor"] == "jdoe@x.com"

def test_push_audits_failures(monkeypatch):
    audits = []
    import src.services.jira_service as js
    def boom(**kw): raise RuntimeError("nope")
    monkeypatch.setattr(js, "create_issue", boom)
    monkeypatch.setattr(js, "get_create_meta", lambda pk: None)
    monkeypatch.setattr(audit, "record_jira_create", lambda **kw: audits.append(kw))
    out = isvc.push_stories("CGF", [Story(title="A")], actor=None)
    assert out["created"] == 0 and out["results"][0]["ok"] is False
    assert "nope" in out["results"][0]["error"] and audits[0]["ok"] is False
```

- [ ] **Step 2:** Run `cd dashboard/backend && python -m pytest tests/test_ideate_push.py -k push -v` — Expected: FAIL.
- [ ] **Step 3:** Add to `src/services/ideate_service.py` at module scope:

```python
def push_stories(project_key: str, stories: List["Story"], actor: Optional[str] = None) -> Dict[str, Any]:
    """Create approved stories as Jira issues with real field mapping + audit.

    Fetches createmeta once per batch; records one audit row per issue (success
    and failure) under a shared correlation id. Never aborts on a single failure.
    """
    from src.services import ideate_audit, jira_service
    if not project_key:
        raise ValueError("A Jira project key is required")
    correlation_id = ideate_audit.new_correlation_id()
    meta = jira_service.get_create_meta(project_key)
    results: List[Dict[str, Any]] = []
    for s in stories:
        try:
            created = jira_service.create_issue(
                project_key=project_key, summary=s.title, description=s.description,
                issue_type=s.issue_type or "Story", labels=s.labels, priority=s.priority,
                epic_key=s.epic_key, story_points=s.story_points, assignee=s.assignee,
                components=s.components, acceptance_criteria=s.acceptance_criteria, meta=meta)
            results.append({"title": s.title, "ok": True, **created})
            ideate_audit.record_jira_create(project_key=project_key, key=created.get("key", ""),
                url=created.get("url", ""), ok=True, title=s.title, actor=actor,
                correlation_id=correlation_id)
        except Exception as e:  # noqa: BLE001
            results.append({"title": s.title, "ok": False, "error": str(e)})
            ideate_audit.record_jira_create(project_key=project_key, key="", url="", ok=False,
                title=s.title, error=str(e), actor=actor, correlation_id=correlation_id)
    return {"results": results, "created": sum(1 for r in results if r.get("ok")),
            "correlation_id": correlation_id}
```

- [ ] **Step 4:** Run `python -m pytest tests/test_ideate_push.py -v` — Expected: PASS.
- [ ] **Step 5:** Commit:

```bash
git add dashboard/backend/src/services/ideate_service.py dashboard/backend/tests/test_ideate_push.py
git commit -m "feat: push_stories maps fields, creates, and audits each result"
```

---

## Task 8: API — push, jira-meta, audit

**Files:** Modify `src/api/ideate.py`; Test `tests/test_ideate_api.py`

- [ ] **Step 1:** Create `dashboard/backend/tests/test_ideate_api.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
import src.api.ideate as ideate_api

def _client():
    app = FastAPI(); app.include_router(ideate_api.router); return TestClient(app)

def test_push_endpoint(monkeypatch):
    seen = {}
    def fake(project_key, stories, actor=None):
        seen.update({"project": project_key, "n": len(stories), "actor": actor, "epic": stories[0].epic_key})
        return {"results": [{"title": "A", "ok": True, "key": "CGF-1"}], "created": 1, "correlation_id": "c1"}
    monkeypatch.setattr(ideate_api.svc, "push_stories", fake)
    r = _client().post("/api/ideate/push", json={"project_key": "CGF",
        "stories": [{"title": "A", "issue_type": "Story", "epic_key": "CGF-9", "acceptance_criteria": ["ac1"]}]},
        headers={"x-auth-request-email": "jdoe@x.com"})
    assert r.status_code == 200 and r.json()["created"] == 1
    assert seen["project"] == "CGF" and seen["epic"] == "CGF-9" and seen["actor"] == "jdoe@x.com"

def test_jira_meta_endpoint(monkeypatch):
    from src.services.jira_service import CreateMeta, JiraEpic
    import src.services.jira_service as js
    monkeypatch.setattr(js, "get_create_meta", lambda pk: CreateMeta(project_key=pk, issue_types=["Story", "Task"]))
    monkeypatch.setattr(js, "list_epics", lambda pk: [JiraEpic(key="CGF-1", summary="Epic One")])
    r = _client().get("/api/ideate/jira-meta?project=CGF")
    assert r.status_code == 200
    assert r.json()["issue_types"] == ["Story", "Task"] and r.json()["epics"][0]["key"] == "CGF-1"

def test_audit_endpoint(monkeypatch):
    monkeypatch.setattr(ideate_api, "_get_activity",
                        lambda command, limit: [{"subcommand": "jira_create", "status": "success"}])
    r = _client().get("/api/ideate/audit?limit=10")
    assert r.status_code == 200 and r.json()["actions"][0]["subcommand"] == "jira_create"
```

- [ ] **Step 2:** Run `cd dashboard/backend && python -m pytest tests/test_ideate_api.py -v` — Expected: FAIL.
- [ ] **Step 3:** In `src/api/ideate.py`, after `_forwarded_user_token` (line 31) add:

```python
def _forwarded_user_email(request: Request) -> Optional[str]:
    """The signed-in user's email forwarded by the SSO proxy, if present."""
    h = request.headers
    email = h.get("x-auth-request-email") or h.get("x-forwarded-email")
    return email.strip() if email else None


def _get_activity(command: str, limit: int):
    """Query the central audit trail; empty list if unavailable."""
    try:
        from agentic_cli.tracker import get_activity
        return get_activity(command=command, limit=limit)
    except Exception:  # noqa: BLE001
        return []
```

Replace `PushStory` and `PushRequest` (lines 87-98):

```python
class PushStory(BaseModel):
    title: str
    description: str = ""
    acceptance_criteria: List[str] = []
    priority: Optional[str] = None
    labels: List[str] = []
    issue_type: str = "Story"
    epic_key: Optional[str] = None
    story_points: Optional[float] = None
    assignee: Optional[str] = None
    components: List[str] = []


class PushRequest(BaseModel):
    project_key: str
    stories: List[PushStory]
```

Replace the `/push` handler (lines 110-139):

```python
@router.post("/push")
async def push(req: PushRequest, request: Request):
    """Create approved stories as Jira issues with real field mapping + audit."""
    if not req.stories:
        raise HTTPException(status_code=400, detail="No stories to push")
    if not req.project_key:
        raise HTTPException(status_code=400, detail="A Jira project key is required")
    actor = _forwarded_user_email(request)
    stories = [svc.Story(title=s.title, description=s.description,
        acceptance_criteria=s.acceptance_criteria, priority=s.priority or "Medium",
        labels=s.labels, issue_type=s.issue_type, epic_key=s.epic_key,
        story_points=s.story_points, assignee=s.assignee, components=s.components)
        for s in req.stories]
    return svc.push_stories(req.project_key, stories, actor=actor)
```

Append at end of file:

```python
@router.get("/jira-meta")
async def jira_meta(project: str):
    """Issue types, epics, and available custom fields for a project."""
    from src.services import jira_service
    if not project:
        raise HTTPException(status_code=400, detail="A project key is required")
    meta = jira_service.get_create_meta(project)
    epics = jira_service.list_epics(project)
    return {"project": project,
            "issue_types": meta.issue_types or ["Story", "Task", "Bug", "Spike"],
            "epics": [e.model_dump() for e in epics],
            "fields": {"epic_link": meta.epic_link_field is not None,
                       "story_points": meta.story_points_field is not None,
                       "acceptance_criteria": meta.acceptance_criteria_field is not None,
                       "components": meta.has_components, "assignee": meta.has_assignee,
                       "priority": meta.has_priority}}


@router.get("/audit")
async def audit(limit: int = 50):
    """Recent Ideate mutating actions from the central audit trail."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return {"actions": _get_activity(command="ideate", limit=limit)}
```

- [ ] **Step 4:** Run `python -m pytest tests/test_ideate_api.py -v` — Expected: PASS.
- [ ] **Step 5:** Run the full suite `cd dashboard/backend && python -m pytest tests -v` — Expected: PASS.
- [ ] **Step 6:** Commit:

```bash
git add dashboard/backend/src/api/ideate.py dashboard/backend/tests/test_ideate_api.py
git commit -m "feat: Ideate API field-mapped push + jira-meta + audit endpoints"
```

---

## Task 9: Frontend shared types + upgraded StoryCard

> No frontend test runner exists; verify with `npm run build` (or `npx tsc --noEmit`) + manual check in Task 13.

**Files:** Create `src/pages/ideate/types.ts`, `src/pages/ideate/StoryCard.tsx`

- [ ] **Step 1:** Create `dashboard/frontend/src/pages/ideate/types.ts`:

```typescript
export interface Story {
  title: string;
  description: string;
  acceptance_criteria: string[];
  priority: string;
  labels: string[];
  issue_type: string;
  epic_key: string | null;
  story_points: number | null;
  assignee: string | null;
  components: string[];
}

export interface EditableStory extends Story {
  _id: string;
  keep: boolean;
}

export interface JiraMeta {
  project: string;
  issue_types: string[];
  epics: { key: string; summary: string }[];
  fields: {
    epic_link: boolean;
    story_points: boolean;
    acceptance_criteria: boolean;
    components: boolean;
    assignee: boolean;
    priority: boolean;
  };
}

export interface PushResult {
  title: string;
  ok: boolean;
  key?: string;
  url?: string;
  error?: string;
}

export const PRIORITIES = ["High", "Medium", "Low"];
export const DEFAULT_ISSUE_TYPES = ["Story", "Task", "Bug", "Spike"];

export function newStory(partial: Partial<Story> = {}): Story {
  return {
    title: "", description: "", acceptance_criteria: [], priority: "Medium",
    labels: [], issue_type: "Story", epic_key: null, story_points: null,
    assignee: null, components: [], ...partial,
  };
}
```

- [ ] **Step 2:** Create `dashboard/frontend/src/pages/ideate/StoryCard.tsx`:

```tsx
import { Trash2, Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { EditableStory, JiraMeta, PushResult, PRIORITIES, DEFAULT_ISSUE_TYPES } from "./types";

const PRIORITY_CHIP: Record<string, string> = {
  High: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300",
  Medium: "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300",
  Low: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
};

export function StoryCard({
  story, meta, onChange, onRemove, onPushOne, onDuplicate, pushed,
}: {
  story: EditableStory;
  meta: JiraMeta | null;
  onChange: (patch: Partial<EditableStory>) => void;
  onRemove: () => void;
  onPushOne?: () => void;
  onDuplicate?: () => void;
  pushed?: PushResult;
}) {
  const issueTypes = meta?.issue_types?.length ? meta.issue_types : DEFAULT_ISSUE_TYPES;
  const show = meta?.fields;
  const setAc = (i: number, val: string) => {
    const ac = [...story.acceptance_criteria]; ac[i] = val; onChange({ acceptance_criteria: ac });
  };
  const addAc = () => onChange({ acceptance_criteria: [...story.acceptance_criteria, ""] });
  const removeAc = (i: number) =>
    onChange({ acceptance_criteria: story.acceptance_criteria.filter((_, j) => j !== i) });

  return (
    <div className={cn("rounded-xl border p-3 bg-white dark:bg-gray-900 transition-opacity",
      story.keep ? "border-gray-200 dark:border-gray-800" : "border-gray-200 dark:border-gray-800 opacity-50")}>
      <div className="flex items-center gap-2">
        <input type="checkbox" checked={story.keep} onChange={(e) => onChange({ keep: e.target.checked })}
          className="h-4 w-4 accent-blue-600" title="Keep this story" />
        <select value={story.issue_type} onChange={(e) => onChange({ issue_type: e.target.value })}
          className="text-[10px] font-semibold rounded px-1.5 py-0.5 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 outline-none">
          {issueTypes.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <input value={story.title} onChange={(e) => onChange({ title: e.target.value })}
          className="flex-1 text-sm font-medium bg-transparent outline-none border-b border-transparent focus:border-gray-300 dark:focus:border-gray-700" />
        {(!show || show.priority) && (
          <select value={story.priority} onChange={(e) => onChange({ priority: e.target.value })}
            className={cn("text-[10px] font-semibold rounded px-1.5 py-0.5 outline-none", PRIORITY_CHIP[story.priority] ?? PRIORITY_CHIP.Medium)}>
            {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        )}
        <button onClick={onRemove} className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20" title="Remove">
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="mt-2 flex flex-wrap gap-2">
        {(!show || show.epic_link) && (
          <select value={story.epic_key ?? ""} onChange={(e) => onChange({ epic_key: e.target.value || null })}
            className="text-[11px] rounded border border-gray-200 dark:border-gray-800 bg-transparent px-1.5 py-0.5 outline-none" title="Epic">
            <option value="">No epic</option>
            {(meta?.epics ?? []).map((ep) => <option key={ep.key} value={ep.key}>{ep.key} · {ep.summary}</option>)}
          </select>
        )}
        {(!show || show.story_points) && (
          <input type="number" value={story.story_points ?? ""} placeholder="pts"
            onChange={(e) => onChange({ story_points: e.target.value === "" ? null : Number(e.target.value) })}
            className="w-14 text-[11px] rounded border border-gray-200 dark:border-gray-800 bg-transparent px-1.5 py-0.5 outline-none" />
        )}
        {(!show || show.assignee) && (
          <input value={story.assignee ?? ""} placeholder="assignee"
            onChange={(e) => onChange({ assignee: e.target.value || null })}
            className="w-28 text-[11px] rounded border border-gray-200 dark:border-gray-800 bg-transparent px-1.5 py-0.5 outline-none" />
        )}
      </div>

      <textarea value={story.description} onChange={(e) => onChange({ description: e.target.value })} rows={2}
        className="mt-2 w-full text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800 px-2 py-1.5 outline-none" />

      <div className="mt-2">
        <div className="text-[11px] font-semibold text-gray-500 mb-1">Acceptance criteria</div>
        <div className="space-y-1">
          {story.acceptance_criteria.map((ac, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <input value={ac} onChange={(e) => setAc(i, e.target.value)}
                className="flex-1 text-[11px] rounded border border-gray-200 dark:border-gray-800 bg-transparent px-1.5 py-0.5 outline-none" />
              <button onClick={() => removeAc(i)} className="text-gray-400 hover:text-red-600" title="Remove criterion">
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
          <button onClick={addAc} className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-700">
            <Plus className="h-3 w-3" /> add criterion
          </button>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-2 border-t border-gray-100 dark:border-gray-800 pt-2">
        {onDuplicate && <button onClick={onDuplicate} className="text-[11px] text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">Duplicate</button>}
        {onPushOne && !pushed?.ok && <button onClick={onPushOne} className="text-[11px] font-medium text-emerald-700 hover:text-emerald-800">Push this</button>}
        {pushed?.ok && pushed.url && <a href={pushed.url} target="_blank" rel="noopener" className="text-[11px] font-medium text-blue-600 hover:underline">Created {pushed.key} ↗</a>}
        {pushed && !pushed.ok && <span className="text-[11px] text-red-600">{pushed.error}</span>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3:** Run `cd dashboard/frontend && npm run build` — Expected: build succeeds (no TS errors).
- [ ] **Step 4:** Commit:

```bash
git add dashboard/frontend/src/pages/ideate/types.ts dashboard/frontend/src/pages/ideate/StoryCard.tsx
git commit -m "feat: upgraded Jira action-item StoryCard + shared Ideate types"
```

---

## Task 10: ActivityPanel (audit feed)

**Files:** Create `src/pages/ideate/ActivityPanel.tsx`

- [ ] **Step 1:** Create `dashboard/frontend/src/pages/ideate/ActivityPanel.tsx`:

```tsx
import { useCallback, useEffect, useState } from "react";
import { History, CheckCircle2, XCircle } from "lucide-react";

interface AuditRow {
  timestamp?: string;
  subcommand?: string;
  status?: string;
  entity_id?: string;
  actor?: string;
  details?: string;
}

export function ActivityPanel({ refreshKey }: { refreshKey?: number }) {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/ideate/audit?limit=25");
      if (res.ok) setRows((await res.json()).actions ?? []);
    } catch {
      /* non-fatal */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load, refreshKey]);

  const parseTitle = (d?: string) => {
    if (!d) return "";
    try { return JSON.parse(d).title ?? ""; } catch { return ""; }
  };

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-center gap-2 mb-3">
        <History className="h-4 w-4 text-gray-400" />
        <h3 className="text-sm font-semibold">Activity</h3>
        {loading && <span className="text-xs text-gray-400">loading…</span>}
      </div>
      {rows.length === 0 ? (
        <p className="text-xs text-gray-400">No recorded actions yet.</p>
      ) : (
        <ul className="space-y-1.5">
          {rows.map((r, i) => (
            <li key={i} className="flex items-center gap-2 text-xs">
              {r.status === "success"
                ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                : <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />}
              <span className="font-mono text-gray-500">{r.entity_id}</span>
              <span className="text-gray-600 dark:text-gray-300 truncate">{parseTitle(r.details)}</span>
              {r.actor && <span className="ml-auto text-gray-400">{r.actor}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2:** Run `cd dashboard/frontend && npm run build` — Expected: build succeeds.
- [ ] **Step 3:** Commit:

```bash
git add dashboard/frontend/src/pages/ideate/ActivityPanel.tsx
git commit -m "feat: Ideate audit Activity panel"
```

---

## Task 11: Wizard step components

> Presentational only — all state/handlers come from the shell (Task 12).

**Files:** Create `StepScope.tsx`, `StepGather.tsx`, `StepDraft.tsx`, `StepReview.tsx`, `StepPush.tsx` under `src/pages/ideate/`

- [ ] **Step 1:** Create `dashboard/frontend/src/pages/ideate/StepScope.tsx`:

```tsx
export function StepScope({ projects, project, onProject }: {
  projects: string[]; project: string; onProject: (p: string) => void;
}) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-sm font-medium">Target Jira project</label>
        <p className="text-xs text-gray-500">Where approved stories are created; determines available fields/epics.</p>
      </div>
      {projects.length ? (
        <select value={project} onChange={(e) => onProject(e.target.value)}
          className="w-full max-w-sm text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none">
          {projects.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      ) : (
        <p className="text-xs text-amber-600">No onboarded Jira projects found. You can still draft; set a project before pushing.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2:** Create `dashboard/frontend/src/pages/ideate/StepGather.tsx`:

```tsx
import { useRef } from "react";
import { FileUp, Search, Loader2 } from "lucide-react";

export function StepGather({
  context, onContext, searchSource, onSearchSource, searchQuery, onSearchQuery,
  onSearch, searching, onUpload, uploading,
}: {
  context: string; onContext: (v: string) => void;
  searchSource: "glean" | "confluence"; onSearchSource: (s: "glean" | "confluence") => void;
  searchQuery: string; onSearchQuery: (q: string) => void;
  onSearch: () => void; searching: boolean;
  onUpload: (file: File) => void; uploading: boolean;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select value={searchSource} onChange={(e) => onSearchSource(e.target.value as "glean" | "confluence")}
          className="text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none">
          <option value="glean">Glean</option>
          <option value="confluence">Confluence</option>
        </select>
        <input value={searchQuery} onChange={(e) => onSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearch()} placeholder="Search enterprise knowledge…"
          className="flex-1 min-w-[200px] text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-1.5 outline-none" />
        <button onClick={onSearch} disabled={searching || !searchQuery.trim()}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-50 dark:bg-blue-900/30 dark:text-blue-300">
          {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />} Search
        </button>
        <button onClick={() => fileRef.current?.click()} disabled={uploading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50 dark:bg-gray-800 dark:text-gray-300">
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />} Upload
        </button>
        <input ref={fileRef} type="file" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f); e.target.value = ""; }} />
      </div>
      <textarea value={context} onChange={(e) => onContext(e.target.value)} rows={10}
        placeholder="Paste or gather requirements here…"
        className="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 px-3 py-2 outline-none" />
    </div>
  );
}
```

- [ ] **Step 3:** Create `dashboard/frontend/src/pages/ideate/StepDraft.tsx`:

```tsx
import { Sparkles, Loader2 } from "lucide-react";

export function StepDraft({ count, onCount, onDraft, drafting, source }: {
  count: number; onCount: (n: number) => void; onDraft: () => void;
  drafting: boolean; source: "llm" | "heuristic" | null;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium">How many stories</label>
        <input type="number" min={1} max={20} value={count}
          onChange={(e) => onCount(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
          className="w-16 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none" />
        <button onClick={onDraft} disabled={drafting}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
          {drafting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Draft stories
        </button>
      </div>
      {source && (
        <p className="text-xs text-gray-500">
          Drafted via {source === "llm" ? "the configured LLM" : "a deterministic heuristic (no LLM configured)"}.
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4:** Create `dashboard/frontend/src/pages/ideate/StepReview.tsx`:

```tsx
import { EditableStory, JiraMeta, PushResult, newStory } from "./types";
import { StoryCard } from "./StoryCard";

export function StepReview({ stories, meta, onStories, pushResults, onPushOne }: {
  stories: EditableStory[]; meta: JiraMeta | null;
  onStories: (s: EditableStory[]) => void;
  pushResults: Record<string, PushResult>;
  onPushOne: (story: EditableStory) => void;
}) {
  const patch = (id: string, p: Partial<EditableStory>) =>
    onStories(stories.map((s) => (s._id === id ? { ...s, ...p } : s)));
  const remove = (id: string) => onStories(stories.filter((s) => s._id !== id));
  const duplicate = (s: EditableStory) =>
    onStories([...stories, { ...newStory(s), _id: `s${Date.now()}`, keep: true, title: `${s.title} (copy)` } as EditableStory]);

  if (!stories.length) return <p className="text-sm text-gray-400">No stories yet — draft some in the previous step.</p>;
  return (
    <div className="space-y-3">
      {stories.map((s) => (
        <StoryCard key={s._id} story={s} meta={meta}
          onChange={(p) => patch(s._id, p)} onRemove={() => remove(s._id)}
          onDuplicate={() => duplicate(s)} onPushOne={() => onPushOne(s)}
          pushed={pushResults[s._id]} />
      ))}
    </div>
  );
}
```

- [ ] **Step 5:** Create `dashboard/frontend/src/pages/ideate/StepPush.tsx`:

```tsx
import { Send, Loader2 } from "lucide-react";
import { ActivityPanel } from "./ActivityPanel";

export function StepPush({ project, keepCount, pushing, onPushAll, refreshKey }: {
  project: string; keepCount: number; pushing: boolean;
  onPushAll: () => void; refreshKey: number;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-sm">Push <b>{keepCount}</b> kept {keepCount === 1 ? "story" : "stories"} to <b>{project || "—"}</b>.</span>
        <button onClick={onPushAll} disabled={pushing || !keepCount || !project}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50">
          {pushing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Push all
        </button>
      </div>
      <ActivityPanel refreshKey={refreshKey} />
    </div>
  );
}
```

- [ ] **Step 6:** Run `cd dashboard/frontend && npm run build` — Expected: build succeeds.
- [ ] **Step 7:** Commit:

```bash
git add dashboard/frontend/src/pages/ideate/Step*.tsx
git commit -m "feat: Ideate wizard step components"
```

---

## Task 12: Wizard shell (rewrite `Ideate.tsx`)

**Files:** Modify `dashboard/frontend/src/pages/Ideate.tsx` (full replacement)

- [ ] **Step 1:** Replace the entire contents of `dashboard/frontend/src/pages/Ideate.tsx` with:

```tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import { Lightbulb, ChevronLeft, ChevronRight, AlertCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { EditableStory, JiraMeta, PushResult, Story, newStory } from "./ideate/types";
import { StepScope } from "./ideate/StepScope";
import { StepGather } from "./ideate/StepGather";
import { StepDraft } from "./ideate/StepDraft";
import { StepReview } from "./ideate/StepReview";
import { StepPush } from "./ideate/StepPush";

type Toast = { type: "success" | "error"; message: string };
const STEPS = ["Scope", "Gather", "Draft", "Review", "Push"] as const;

let _sid = 0;
const nextId = () => `s${Date.now()}_${_sid++}`;

export function Ideate() {
  const [step, setStep] = useState(0);
  const [maxStep, setMaxStep] = useState(0);

  const [context, setContext] = useState("");
  const [count, setCount] = useState(5);
  const [stories, setStories] = useState<EditableStory[]>([]);
  const [source, setSource] = useState<"llm" | "heuristic" | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [searchSource, setSearchSource] = useState<"glean" | "confluence">("glean");
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);

  const [jira, setJira] = useState<{ configured: boolean; projects: string[] } | null>(null);
  const [project, setProject] = useState("");
  const [meta, setMeta] = useState<JiraMeta | null>(null);
  const [pushing, setPushing] = useState(false);
  const [pushResults, setPushResults] = useState<Record<string, PushResult>>({});
  const [auditRefresh, setAuditRefresh] = useState(0);

  const [toast, setToast] = useState<Toast | null>(null);
  const showToast = useCallback((t: Toast) => {
    setToast(t); window.setTimeout(() => setToast(null), 3500);
  }, []);

  const goto = (i: number) => { setStep(i); setMaxStep((m) => Math.max(m, i)); };

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/ideate/jira-status");
        if (res.ok) {
          const d = await res.json();
          setJira(d);
          if (d.projects?.length) setProject(d.projects[0]);
        }
      } catch { /* non-fatal */ }
    })();
  }, []);

  // Fetch createmeta whenever the project changes.
  useEffect(() => {
    if (!project) { setMeta(null); return; }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`/api/ideate/jira-meta?project=${encodeURIComponent(project)}`);
        if (res.ok && !cancelled) setMeta(await res.json());
      } catch { /* non-fatal */ }
    })();
    return () => { cancelled = true; };
  }, [project]);

  const runSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch("/api/ideate/search", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: searchSource, query: searchQuery }),
      });
      const data = await res.json();
      if (res.ok && data.text) {
        setContext((c) => (c ? `${c}\n\n--- ${searchSource}: ${searchQuery} ---\n${data.text}` : data.text));
        showToast({ type: "success", message: `Added ${data.chars} chars from ${searchSource}` });
      } else {
        showToast({ type: "error", message: data.detail || "No results from " + searchSource });
      }
    } catch { showToast({ type: "error", message: "Search failed" }); }
    finally { setSearching(false); }
  };

  const uploadFile = async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const res = await fetch("/api/ideate/upload", { method: "POST", body: fd });
      const data = await res.json();
      if (res.ok && data.text) {
        setContext((c) => (c ? `${c}\n\n--- ${file.name} ---\n${data.text}` : data.text));
        showToast({ type: "success", message: `Added ${data.chars} chars from ${file.name}` });
      } else {
        showToast({ type: "error", message: data.detail || "Upload failed" });
      }
    } catch { showToast({ type: "error", message: "Upload failed" }); }
    finally { setUploading(false); }
  };

  const draft = async () => {
    if (!context.trim()) { showToast({ type: "error", message: "Gather some requirements first" }); return; }
    setDrafting(true);
    try {
      const res = await fetch("/api/ideate/draft", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ context, count }),
      });
      const data = await res.json();
      if (res.ok) {
        setSource(data.source);
        setStories((data.stories as Story[]).map((s) => ({
          ...newStory(s), ...s, _id: nextId(), keep: true,
        })));
        goto(3);
      } else {
        showToast({ type: "error", message: data.detail || "Draft failed" });
      }
    } catch { showToast({ type: "error", message: "Draft failed" }); }
    finally { setDrafting(false); }
  };

  const pushStories = async (subset: EditableStory[]) => {
    if (!project) { showToast({ type: "error", message: "Pick a Jira project (Scope step)" }); return; }
    if (!subset.length) { showToast({ type: "error", message: "Nothing to push" }); return; }
    setPushing(true);
    try {
      const res = await fetch("/api/ideate/push", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_key: project,
          stories: subset.map(({ _id, keep, ...s }) => s),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        const byIndex: Record<string, PushResult> = { ...pushResults };
        subset.forEach((s, i) => { byIndex[s._id] = data.results[i]; });
        setPushResults(byIndex);
        setAuditRefresh((n) => n + 1);
        showToast({ type: "success", message: `Created ${data.created} of ${subset.length}` });
      } else {
        showToast({ type: "error", message: data.detail || "Push failed" });
      }
    } catch { showToast({ type: "error", message: "Push failed" }); }
    finally { setPushing(false); }
  };

  const kept = useMemo(() => stories.filter((s) => s.keep), [stories]);

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-2">
        <Lightbulb className="h-5 w-5 text-amber-500" />
        <h1 className="text-lg font-semibold">Ideate</h1>
      </div>

      {/* Stepper */}
      <div className="flex flex-wrap gap-2">
        {STEPS.map((label, i) => (
          <button key={label} onClick={() => i <= maxStep && setStep(i)} disabled={i > maxStep}
            className={cn("text-xs rounded-full px-3 py-1 transition-colors",
              i === step ? "bg-blue-600 text-white"
                : i < step ? "bg-emerald-600 text-white"
                : i <= maxStep ? "bg-gray-200 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
                : "bg-gray-100 dark:bg-gray-900 text-gray-400 cursor-not-allowed")}>
            {i + 1} {label}{i < step ? " ✓" : ""}
          </button>
        ))}
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        {step === 0 && <StepScope projects={jira?.projects ?? []} project={project} onProject={setProject} />}
        {step === 1 && (
          <StepGather context={context} onContext={setContext} searchSource={searchSource}
            onSearchSource={setSearchSource} searchQuery={searchQuery} onSearchQuery={setSearchQuery}
            onSearch={runSearch} searching={searching} onUpload={uploadFile} uploading={uploading} />
        )}
        {step === 2 && <StepDraft count={count} onCount={setCount} onDraft={draft} drafting={drafting} source={source} />}
        {step === 3 && (
          <StepReview stories={stories} meta={meta} onStories={setStories}
            pushResults={pushResults} onPushOne={(s) => pushStories([s])} />
        )}
        {step === 4 && (
          <StepPush project={project} keepCount={kept.length} pushing={pushing}
            onPushAll={() => pushStories(kept)} refreshKey={auditRefresh} />
        )}
      </div>

      {/* Nav */}
      <div className="flex justify-between">
        <button onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 disabled:opacity-40">
          <ChevronLeft className="h-4 w-4" /> Back
        </button>
        {step < STEPS.length - 1 && (
          <button onClick={() => goto(step + 1)}
            className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700">
            Next <ChevronRight className="h-4 w-4" />
          </button>
        )}
      </div>

      {toast && (
        <div className={cn("fixed bottom-6 right-6 flex items-center gap-2 rounded-lg px-4 py-2 text-sm shadow-lg",
          toast.type === "success" ? "bg-emerald-600 text-white" : "bg-red-600 text-white")}>
          {toast.type === "success" ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {toast.message}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2:** Run `cd dashboard/frontend && npm run build` — Expected: build succeeds (no unused-import or type errors). If `Ideate` is a default export elsewhere, keep the named export and check the route import in `src/App.tsx` still matches (it already imports `{ Ideate }`).
- [ ] **Step 3:** Commit:

```bash
git add dashboard/frontend/src/pages/Ideate.tsx
git commit -m "feat: Ideate 5-step wizard shell wired to steps + field-mapped push + audit"
```

---

## Task 13: End-to-end verification

**Files:** none (verification only)

- [ ] **Step 1:** Run the full backend suite:

Run: `cd dashboard/backend && python -m pytest tests -v`
Expected: all tests PASS.

- [ ] **Step 2:** Build the frontend:

Run: `cd dashboard/frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3:** Manual smoke (dashboard running):

  1. Open Ideate. Step 1: select a project (createmeta loads).
  2. Step 2: paste requirements (or search Glean/Confluence).
  3. Step 3: draft stories → lands on Review.
  4. Step 4: confirm each card shows issue-type, epic (if available), points, assignee, editable AC checklist; edit an AC; use Duplicate.
  5. Step 5: Push all → toast reports created count; Activity panel lists one row per created issue with the actor and links.
  6. Verify in Jira that AC landed in the AC field (or description if the project lacks one) and epic link/points are set when supported.

- [ ] **Step 4:** Confirm audit trail persisted:

Run: `python -c "from agentic_cli.tracker import get_activity; import json; print(json.dumps(get_activity(command='ideate', limit=5), indent=2))"`
Expected: recent `jira_create` rows with `entity_id`, `actor`, `source=dashboard`, and `details.title`.

- [ ] **Step 5:** Final commit (if any doc/tweaks):

```bash
git add -A
git commit -m "chore: Ideate v2 P1 verification pass"
```

---

## Notes for P2/P3 (not in this plan)

- **P2:** `ideate_agent.py` ReAct loop + `ideate_tools.py` (Glean/Confluence/Jira/MCP as tools), SSE `/agent/run`, collapsible `AgentWindow.tsx`; mutating-tool auditing via the tool registry.
- **P3:** agents-as-tools registry (built/imported agents), drafting-agent picker on Step 3, per-card agent refine.
