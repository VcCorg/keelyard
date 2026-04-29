---
name: testing-jest
description: >-
  Jest test patterns, mocking, snapshot testing, React Testing Library.
  Use this skill when writing or modifying tests in a JavaScript/TypeScript project.
---

# Jest Testing

## Test Structure

```
src/
├── components/
│   ├── Button.tsx
│   └── Button.test.tsx       # Co-located test
├── services/
│   ├── api.ts
│   └── __tests__/
│       └── api.test.ts       # __tests__ directory
```

## Key Patterns

### Basic Test

```typescript
describe("ResourceService", () => {
  it("should create a resource", async () => {
    const result = await service.create({ name: "test" });
    expect(result.id).toBeDefined();
    expect(result.name).toBe("test");
  });

  it("should throw when not found", async () => {
    await expect(service.findById("missing")).rejects.toThrow("Not found");
  });
});
```

### Mocking

```typescript
// Mock a module
jest.mock("../services/api");
import { fetchData } from "../services/api";
const mockFetchData = fetchData as jest.MockedFunction<typeof fetchData>;

mockFetchData.mockResolvedValue({ id: "1", name: "test" });

// Mock a function
const mockCallback = jest.fn();
mockCallback.mockReturnValue(42);

// Verify calls
expect(mockCallback).toHaveBeenCalledWith("arg1");
expect(mockCallback).toHaveBeenCalledTimes(1);
```

### React Testing Library

```tsx
import { render, screen, fireEvent } from "@testing-library/react";

test("renders and handles click", () => {
  const onSelect = jest.fn();
  render(<ResourceCard id="1" name="Test" onSelect={onSelect} />);

  expect(screen.getByText("Test")).toBeInTheDocument();
  fireEvent.click(screen.getByText("Test"));
  expect(onSelect).toHaveBeenCalledWith("1");
});
```

## Commands

```bash
npx jest                     # Run all tests
npx jest --watch             # Watch mode
npx jest --coverage          # With coverage
npx jest path/to/test        # Run specific file
npx jest -t "pattern"        # Run by test name
```

## Guidelines

- Use `describe` blocks to group related tests
- Name tests clearly: `it("should <expected> when <condition>")`
- Use `beforeEach` for common setup, `afterEach` for cleanup
- Prefer `screen.getByRole` over `getByTestId` for accessibility
- Use `waitFor` for async assertions
- Use snapshot testing sparingly (mostly for UI components)
- Mock external dependencies, not internal implementation
