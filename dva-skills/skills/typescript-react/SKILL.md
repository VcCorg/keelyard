---
name: typescript-react
description: >-
  React component patterns, hooks, state management, TypeScript types.
  Use this skill when working on a React + TypeScript project.
---

# React + TypeScript Development

## Project Structure

```
src/
├── App.tsx                   # Root component
├── index.tsx                 # Entry point
├── components/               # Reusable UI components
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.test.tsx
│   │   └── index.ts
├── pages/                    # Page-level components
├── hooks/                    # Custom hooks
├── services/                 # API calls
├── types/                    # TypeScript type definitions
├── utils/                    # Utility functions
└── context/                  # React context providers
```

## Key Patterns

### Functional Component

```tsx
interface ResourceCardProps {
  id: string;
  name: string;
  onSelect: (id: string) => void;
}

export function ResourceCard({ id, name, onSelect }: ResourceCardProps) {
  return (
    <div onClick={() => onSelect(id)}>
      <h3>{name}</h3>
    </div>
  );
}
```

### Custom Hook

```tsx
function useResource(id: string) {
  const [data, setData] = useState<Resource | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    fetchResource(id)
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [id]);

  return { data, loading, error };
}
```

### Context Pattern

```tsx
const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  return (
    <AuthContext.Provider value={{ user, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
```

## Guidelines

- Use TypeScript interfaces for all props and state
- Prefer functional components with hooks over class components
- Extract reusable logic into custom hooks (`use*` prefix)
- Use `React.memo()` for expensive renders
- Avoid inline object/function creation in JSX (causes re-renders)
- Use `useCallback` and `useMemo` only when profiling shows need
- Co-locate tests with components (`Component.test.tsx`)
- Use barrel exports (`index.ts`) for clean imports
