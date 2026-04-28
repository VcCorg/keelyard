---
name: go-standard
description: >-
  Go project layout, error handling, interfaces, concurrency patterns.
  Use this skill when working on a Go project.
---

# Go Development

## Project Layout

```
cmd/
├── server/
│   └── main.go            # Entry point
internal/                   # Private packages (not importable)
├── handler/                # HTTP handlers
├── service/                # Business logic
├── repository/             # Data access
└── model/                  # Domain types
pkg/                        # Public reusable packages
go.mod
go.sum
```

## Key Patterns

### Error Handling

```go
func FindByID(id string) (*Resource, error) {
    result, err := repo.Get(id)
    if err != nil {
        return nil, fmt.Errorf("finding resource %s: %w", id, err)
    }
    return result, nil
}
```

- Always check errors immediately
- Wrap errors with context using `fmt.Errorf("context: %w", err)`
- Use `errors.Is()` and `errors.As()` for error inspection
- Define sentinel errors: `var ErrNotFound = errors.New("not found")`

### Interfaces

```go
type Repository interface {
    Get(id string) (*Resource, error)
    Create(r *Resource) error
}
```

- Define interfaces where they're used, not where they're implemented
- Keep interfaces small (1-3 methods)
- Accept interfaces, return structs

### Concurrency

```go
func processItems(items []Item) []Result {
    results := make([]Result, len(items))
    var wg sync.WaitGroup
    for i, item := range items {
        wg.Add(1)
        go func(i int, item Item) {
            defer wg.Done()
            results[i] = process(item)
        }(i, item)
    }
    wg.Wait()
    return results
}
```

## Commands

```bash
go build ./...              # Build all
go test ./...               # Test all
go test -race ./...         # Test with race detector
go vet ./...                # Static analysis
go mod tidy                 # Clean dependencies
```

## Guidelines

- Use `context.Context` as first parameter for cancelable operations
- Prefer composition over inheritance (embed structs)
- Use table-driven tests
- Run `go vet` and `golangci-lint` before committing
- Keep functions short and focused
