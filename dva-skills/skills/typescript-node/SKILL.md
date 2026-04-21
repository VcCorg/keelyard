---
name: typescript-node
description: >-
  Node.js patterns, Express/Fastify, async patterns, module system.
  Use this skill when working on a Node.js backend project.
---

# Node.js Backend Development

## Project Structure

```
src/
├── index.ts                  # Entry point
├── app.ts                    # Express/Fastify app setup
├── routes/                   # Route handlers
├── controllers/              # Request/response logic
├── services/                 # Business logic
├── middleware/                # Custom middleware
├── models/                   # Data models / types
├── utils/                    # Helpers
└── config/                   # Environment config
```

## Express Patterns

```typescript
import express, { Request, Response, NextFunction } from "express";

const app = express();
app.use(express.json());

app.get("/api/resources/:id", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const resource = await service.findById(req.params.id);
    if (!resource) return res.status(404).json({ error: "Not found" });
    res.json(resource);
  } catch (err) {
    next(err);
  }
});

// Error middleware (must have 4 params)
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: "Internal server error" });
});
```

## Async Patterns

```typescript
// Promise.all for parallel operations
const [users, orders] = await Promise.all([
  fetchUsers(),
  fetchOrders(),
]);

// Error handling wrapper
function asyncHandler(fn: Function) {
  return (req: Request, res: Response, next: NextFunction) =>
    Promise.resolve(fn(req, res, next)).catch(next);
}
```

## Commands

```bash
npm run dev           # Development with ts-node or tsx
npm run build         # Compile TypeScript
npm run start         # Run compiled JS
npm test              # Run tests
```

## Guidelines

- Use `async/await` over raw Promise chains
- Always wrap async route handlers in try/catch or use an error wrapper
- Use environment variables for config (never hardcode secrets)
- Use `zod` or `joi` for request validation
- Prefer ESM imports (`import/export`) over CommonJS (`require`)
- Use TypeScript strict mode (`"strict": true` in tsconfig)
