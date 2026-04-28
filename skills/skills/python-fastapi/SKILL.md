---
name: python-fastapi
description: >-
  FastAPI patterns, Pydantic models, async endpoints, dependency injection.
  Use this skill when working on a FastAPI project.
---

# FastAPI Development

## Project Structure

```
src/
├── main.py               # FastAPI app creation, router includes
├── config.py             # Settings via pydantic-settings
├── routers/              # API route modules
│   ├── __init__.py
│   └── resources.py      # @router.get, @router.post
├── models/               # Pydantic models (request/response)
├── services/             # Business logic
├── repositories/         # Data access layer
├── dependencies/         # FastAPI Depends() functions
├── middleware/            # Custom middleware
└── exceptions/           # Custom exception handlers
```

## Key Patterns

### Endpoint Definition

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])

class CreateRequest(BaseModel):
    name: str
    description: str | None = None

class ResourceResponse(BaseModel):
    id: str
    name: str

@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: str, service: ResourceService = Depends(get_service)):
    result = await service.find_by_id(resource_id)
    if not result:
        raise HTTPException(status_code=404, detail="Resource not found")
    return result

@router.post("/", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(request: CreateRequest, service: ResourceService = Depends(get_service)):
    return await service.create(request)
```

### Configuration with pydantic-settings

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_key: str
    debug: bool = False

    class Config:
        env_file = ".env"
```

### Dependency Injection

```python
from fastapi import Depends

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_service(db: Session = Depends(get_db)):
    return ResourceService(db)
```

## Guidelines

- Use `async def` for I/O-bound endpoints
- Define request/response models with Pydantic — never return raw dicts
- Use `Depends()` for dependency injection (database sessions, services, auth)
- Validate with Pydantic models, not manual checks
- Use `HTTPException` for error responses with appropriate status codes
- Group routes with `APIRouter` and include in main app
- Use `response_model` to control serialization and generate OpenAPI docs
- Keep business logic in services, not in route handlers
- Use `BackgroundTasks` for fire-and-forget operations
