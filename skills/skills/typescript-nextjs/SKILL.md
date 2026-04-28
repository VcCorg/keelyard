---
name: typescript-nextjs
description: >-
  Next.js app router, server components, API routes, middleware.
  Use this skill when working on a Next.js project.
---

# Next.js Development

## Project Structure (App Router)

```
app/
├── layout.tsx                # Root layout
├── page.tsx                  # Home page
├── loading.tsx               # Loading UI
├── error.tsx                 # Error boundary
├── not-found.tsx             # 404 page
├── api/
│   └── resources/
│       └── route.ts          # API route handler
├── resources/
│   ├── page.tsx              # /resources page
│   └── [id]/
│       └── page.tsx          # /resources/:id page
components/                   # Shared components
lib/                          # Utility functions, API clients
```

## Key Patterns

### Server Component (default)

```tsx
// app/resources/page.tsx — runs on server, no "use client"
async function ResourcesPage() {
  const resources = await fetchResources(); // Direct DB/API call
  return <ResourceList items={resources} />;
}
```

### Client Component

```tsx
"use client";
import { useState } from "react";

export function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

### API Route Handler

```tsx
// app/api/resources/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const data = await fetchFromDB();
  return NextResponse.json(data);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const created = await createResource(body);
  return NextResponse.json(created, { status: 201 });
}
```

### Server Actions

```tsx
"use server";

export async function createResource(formData: FormData) {
  const name = formData.get("name") as string;
  await db.insert({ name });
  revalidatePath("/resources");
}
```

## Commands

```bash
npm run dev          # Development server (port 3000)
npm run build        # Production build
npm run start        # Start production server
npm run lint         # ESLint check
```

## Guidelines

- Default to Server Components; add `"use client"` only when needed (hooks, events, browser APIs)
- Use Server Actions for form handling and mutations
- Use `loading.tsx` and `error.tsx` for Suspense boundaries
- Use `revalidatePath()` or `revalidateTag()` for cache invalidation
- Prefer `fetch()` with Next.js caching over client-side data fetching
- Use Route Groups `(group)` for layout organization without URL impact
