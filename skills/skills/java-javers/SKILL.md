---
name: java-javers
description: >-
  Auditing and versioning object changes using Javers in Java.
  Use this skill when working with java-javers technologies.
---

# Javers for Java Auditing and Versioning

## Key Concepts
*   **Object Graph Auditing:** Javers tracks changes to object graphs, not just individual entities. It understands relationships between objects.
*   **Change Tracking:** Automatically records changes (creation, update, deletion) to Java objects.
*   **Snapshots:** Creates point-in-time snapshots of object states, allowing for historical querying and restoration.
*   **Value Objects vs. Entities:** Javers distinguishes between value objects (immutable, defined by their state) and entities (identified by a unique ID).
*   **Commit API:** Provides a fluent API to manually control commits or leverage automatic commit mechanisms.

## Project Conventions
*   **`Javers` Instance:** Typically, a single `Javers` instance is configured and injected (e.g., via Spring, Guice) throughout the application.
*   **Annotated Domain Objects:** Domain objects intended for auditing are often annotated with `@Id`, `@ShallowReference`, `@DeepReference`, and `@Transient` where appropriate.
*   **Repository Integration:** Javers often integrates with existing persistence layers (JPA, Hibernate, etc.) to store snapshots and changes. Custom `SnapshotRepository` and `CommitMetadata` implementations might be needed.
*   **Auditing Annotations:** Use `@DiffIgnore` to exclude specific fields from being audited if necessary.

## Common Patterns
**Basic Auditing with Automatic Commits:**
```java
import org.javers.core.Javers;
import org.javers.core.JaversBuilder;
import org.javers.core.commit.Commit;

public class AuditService {

    private final Javers javers;

    public AuditService() {
        // Configure Javers, potentially with custom repositories and serializers
        this.javers = JaversBuilder.javers()
            .registerValue("<YourCustomValueObjectSerializer>") // Example if needed
            .build();
    }

    public void processDomainObject(MyDomainObject object) {
        // Assuming object is managed by a service that automatically detects changes
        // Javers will automatically commit changes if configured for automatic detection
        // or you can manually commit:
        Commit commit = javers.commit("user-123", object, new MyCustomCommitMetadata());
        System.out.println("Committed changes: " + commit.getChanges().size());
    }
}
```

**Manually Committing Changes:**
```java
import org.javers.core.Javers;
import org.javers.core.JaversBuilder;
import org.javers.core.commit.Commit;
import org.javers.repository.api.JaversRepository;
import org.javers.repository.inmemory.InMemoryJaversRepository;

public class ManualAuditService {

    private final Javers javers;
    private final JaversRepository repository;

    public ManualAuditService(JaversRepository repository) {
        this.repository = repository;
        this.javers = JaversBuilder.javers()
            .registerJaversRepository(repository)
            .build();
    }

    public void updateAndAudit(MyDomainObject oldObject, MyDomainObject newObject) {
        Commit commit = javers.commit("admin", newObject, "updated object");
        // You can also compare specific objects
        // Diff diff = javers.compare(oldObject, newObject);
        // Commit commit = javers.commit("admin", diff, "updated object");
    }
}
```

**Querying Object History:**
```java
import org.javers.core.Javers;
import org.javers.core.commit.Commit;
import org.javers.repository.api.JaversRepository;
import org.javers.repository.inmemory.InMemoryJaversRepository;
import org.javers.snapshots.Snapshot;

public class HistoryQueryService {

    private final Javers javers;
    private final JaversRepository repository;

    public HistoryQueryService(JaversRepository repository) {
        this.repository = repository;
        this.javers = JaversBuilder.javers()
            .registerJaversRepository(repository)
            .build();
    }

    public void printHistory(MyDomainObject object) {
        // Get all snapshots for a specific object
        List<Snapshot> snapshots = javers.findObjectSnapshots(object.getId(), MyDomainObject.class);
        snapshots.forEach(snapshot -> System.out.println("Snapshot at: " + snapshot.getCommitMetadata().getAuthor() + " - " + snapshot.getCommitMetadata().getCommitDate()));

        // Get all commits
        List<Commit> commits = javers.getCommits();
        commits.forEach(commit -> System.out.println("Commit: " + commit.getId() + " by " + commit.getAuthor()));
    }
}
```

## Guidelines
*   **Configure `JaversRepository` Appropriately:** Choose and configure a repository that suits your persistence needs (e.g., `InMemoryJaversRepository` for testing, or custom implementations for databases).
*   **Define Commit Metadata:** Use meaningful commit metadata (author, comment) to provide context for changes. Consider custom `CommitMetadataFactory`.
*   **Handle Large Object Graphs Carefully:** For very large or deeply nested object graphs, consider strategies like partial commits or filtering to avoid performance issues.
*   **Use `DiffIgnore` Judiciously:** Exclude fields from auditing only when they are truly non-essential for historical tracking or pose performance risks.
*   **Leverage `ValueObject` and `Entity` Distinction:** Properly model your domain objects to ensure Javers correctly interprets changes.
*   **Integrate with Application Lifecycle:** Ensure the `Javers` instance is properly initialized and available where needed, often through dependency injection.
*   **Test Auditing Logic:** Write tests that specifically verify that changes are being audited and that historical data can be retrieved and interpreted correctly.
*   **Consider Serialization:** If dealing with complex custom types, ensure appropriate serializers are registered with `JaversBuilder`.