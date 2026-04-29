---
name: java-lombok
description: >-
  Lombok annotations for boilerplate code reduction in Java
  Use this skill when working with java-lombok technologies.
---

# Java Lombok

## Key Concepts
*   **Annotation-driven code generation:** Lombok processes annotations at compile time to generate boilerplate code (getters, setters, constructors, `toString`, `equals`, `hashCode`, etc.), reducing manual coding.
*   **Reduced verbosity:** Significantly decreases the amount of repetitive code required for common Java constructs.
*   **Compile-time processing:** Annotations are handled by an annotation processor during compilation, meaning no runtime overhead.
*   **External dependency:** Requires the `lombok` artifact to be added as a compile-time dependency (often `provided` scope in Maven/Gradle) and an IDE plugin for proper IDE support.

## Project Conventions
*   **Dependency Management:** The `lombok` dependency is typically declared in the build file (e.g., `pom.xml` or `build.gradle`). Its scope is often `provided` or `compileOnly` as the generated code is part of the compiled output.
*   **IDE Integration:** Crucial for IDEs (IntelliJ IDEA, Eclipse, VS Code) to recognize and process Lombok annotations, providing code completion, error checking, and refactoring support. Ensure the Lombok plugin is installed and enabled.
*   **Annotation Placement:** Annotations are generally placed at the class or field level, depending on the specific annotation's purpose.

## Common Patterns
**POJOs with Getters, Setters, and Constructors:**

```java
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class User {
    private String username;
    private int age;
}
```

**Immutability with `@Value`:**

```java
import lombok.Value;

@Value // Generates immutable fields, getters, equals(), hashCode(), toString()
public class ImmutablePoint {
    int x;
    int y;
}
```

**Builder Pattern with `@Builder`:**

```java
import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class Configuration {
    private String host;
    private int port;
    private boolean enabled;
}
```

**`toString()`, `equals()`, `hashCode()` generation:**

```java
import lombok.EqualsAndHashCode;
import lombok.ToString;

@ToString(of = {"id", "name"}) // Customize which fields to include in toString
@EqualsAndHashCode(callSuper = false, of = "id") // Customize fields for equals/hashCode
public class Product {
    private Long id;
    private String name;
    private double price;
}
```

**`@NonNull` for null checks:**

```java
import lombok.NonNull;

public class Validator {
    public void process(@NonNull String input) {
        // Lombok generates a null check at runtime if @NonNull is used without an IDE plugin or with specific configurations.
        // Typically used with @NonNull from Lombok, which can generate null checks for methods and constructor parameters.
        System.out.println(input.length());
    }
}
```

## Guidelines
*   **Use liberally for POJOs:** Lombok excels at reducing boilerplate for simple data-holding classes.
*   **Understand annotation scope:** Be aware of where each annotation can be applied (class, method, field) and its effect.
*   **Ensure IDE integration:** Always verify that Lombok is properly configured in your IDE to avoid compilation errors and for seamless development.
*   **Consider immutability:** Leverage `@Value` for immutable objects to promote safer code.
*   **Be mindful of debugging:** While Lombok reduces code, understanding how the generated code works is helpful for debugging complex scenarios.
*   **Avoid overusing `@Data`:** While convenient, `@Data` combines `@ToString`, `@EqualsAndHashCode`, `@Getter`, `@Setter`, and `@RequiredArgsConstructor`. For more control, use individual annotations.
*   **Test generated code implicitly:** Your tests should pass if Lombok generates the correct code for getters, setters, etc. Focus on business logic.
*   **Document non-obvious behaviors:** If you customize Lombok's output (e.g., using `exclude` in `@ToString`), document it.