---
name: api-rest
description: >-
  RESTful API design, HTTP methods, status codes, error handling, pagination.
  Use this skill when designing or implementing REST APIs.
---

# REST API Design

## HTTP Methods

| Method | Purpose | Idempotent | Request Body |
|--------|---------|-----------|-------------|
| GET | Retrieve resource(s) | Yes | No |
| POST | Create resource | No | Yes |
| PUT | Full update / replace | Yes | Yes |
| PATCH | Partial update | No | Yes |
| DELETE | Remove resource | Yes | No |

## URL Patterns

```
GET    /api/v1/resources              # List
GET    /api/v1/resources/{id}         # Get one
POST   /api/v1/resources              # Create
PUT    /api/v1/resources/{id}         # Full update
PATCH  /api/v1/resources/{id}         # Partial update
DELETE /api/v1/resources/{id}         # Delete
GET    /api/v1/resources/{id}/comments  # Nested resource
```

## Status Codes

| Code | When to Use |
|------|-------------|
| 200 | Successful GET, PUT, PATCH, DELETE |
| 201 | Successful POST (resource created) |
| 204 | Successful DELETE (no body) |
| 400 | Invalid request (validation error) |
| 401 | Unauthenticated |
| 403 | Unauthorized (forbidden) |
| 404 | Resource not found |
| 409 | Conflict (duplicate, version mismatch) |
| 422 | Unprocessable entity |
| 429 | Rate limited |
| 500 | Internal server error |

## Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Name is required",
    "details": [
      { "field": "name", "message": "must not be blank" }
    ]
  }
}
```

## Pagination

```json
GET /api/v1/resources?page=2&size=20

{
  "items": [...],
  "page": 2,
  "size": 20,
  "total": 156,
  "totalPages": 8
}
```

## Guidelines

- Use nouns for resources, not verbs (`/resources` not `/getResources`)
- Version your API (`/api/v1/`)
- Use consistent error response format across all endpoints
- Support filtering, sorting, pagination on list endpoints
- Use `Location` header for 201 Created responses
- Use `ETag` / `If-None-Match` for caching
- Document with OpenAPI/Swagger
- Return only what the client needs (avoid over-fetching)
