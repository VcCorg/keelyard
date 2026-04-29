---
name: docker
description: >-
  Dockerfile best practices, multi-stage builds, compose patterns.
  Use this skill when working with Docker containers and compose files.
---

# Docker Development

## Dockerfile Best Practices

```dockerfile
# Multi-stage build
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:20-slim
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 8080
CMD ["node", "dist/index.js"]
```

## Guidelines

- Use multi-stage builds to minimize image size
- Pin base image versions (not `latest`)
- Use `.dockerignore` to exclude unnecessary files
- Run as non-root user when possible
- Combine RUN commands to reduce layers
- Copy dependency files first, then source (leverages cache)
- Use `HEALTHCHECK` for production containers
- Prefer `COPY` over `ADD` unless extracting archives

## Docker Compose Patterns

```yaml
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgres://db:5432/mydb
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: mydb
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
      interval: 10s
      timeout: 5s
```
