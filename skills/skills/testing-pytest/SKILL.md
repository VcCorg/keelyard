---
name: testing-pytest
description: >-
  pytest patterns, fixtures, parametrize, conftest, coverage.
  Use this skill when writing or modifying tests in a Python project.
---

# pytest Testing

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── test_api.py           # API/endpoint tests
├── test_service.py       # Service layer unit tests
├── test_repository.py    # Data access tests
└── integration/
    └── test_e2e.py       # End-to-end tests
```

## Key Patterns

### Basic Test

```python
def test_create_resource():
    service = ResourceService()
    result = service.create(name="test")
    assert result.name == "test"
    assert result.id is not None
```

### Fixtures

```python
# conftest.py
import pytest

@pytest.fixture
def db_session():
    session = create_test_session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def service(db_session):
    return ResourceService(db=db_session)

# test file
def test_find_by_id(service):
    result = service.find_by_id("id-1")
    assert result is not None
```

### Parametrize

```python
@pytest.mark.parametrize("input,expected", [
    ("valid-id", True),
    ("", False),
    (None, False),
])
def test_validate_id(input, expected):
    assert validate_id(input) == expected
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_fetch():
    result = await fetch_data("key")
    assert result is not None
```

### Mocking

```python
from unittest.mock import AsyncMock, patch, MagicMock

def test_with_mock():
    mock_repo = MagicMock()
    mock_repo.find_by_id.return_value = Resource(id="1", name="test")
    service = ResourceService(repo=mock_repo)
    result = service.get("1")
    assert result.name == "test"
    mock_repo.find_by_id.assert_called_once_with("1")

@pytest.mark.asyncio
async def test_async_mock():
    mock_client = AsyncMock()
    mock_client.call_tool.return_value = '{"key": "value"}'
    result = await mock_client.call_tool("get_issue", {"issue_key": "CGP-123"})
    assert "key" in result
```

## Commands

```bash
pytest                          # Run all tests
pytest tests/test_api.py        # Run specific file
pytest -k "test_create"         # Run by name pattern
pytest -x                       # Stop on first failure
pytest --cov=src                # With coverage
pytest -v                       # Verbose output
pytest --tb=short               # Short tracebacks
```

## Guidelines

- Use fixtures for setup/teardown, not setUp/tearDown methods
- Put shared fixtures in `conftest.py`
- Name test files `test_*.py` and functions `test_*`
- Use `@pytest.mark.parametrize` for data-driven tests
- Use `@pytest.mark.asyncio` for async tests (requires pytest-asyncio)
- Prefer `assert` statements over unittest-style assertions
- Use `tmp_path` fixture for temporary files
