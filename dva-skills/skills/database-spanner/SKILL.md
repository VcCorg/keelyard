---
name: database-spanner
description: >-
  Cloud Spanner schema design, interleaved tables, query patterns, mutations.
  Use this skill when working with Google Cloud Spanner databases.
---

# Cloud Spanner Development

## Schema Design

- Primary keys are always explicitly defined (no auto-increment)
- Use UUIDs or composite keys
- Interleaved tables for parent-child relationships (co-located storage)
- Avoid hotspots: don't use monotonically increasing keys

```sql
CREATE TABLE Users (
    UserId STRING(36) NOT NULL,
    Email STRING(255) NOT NULL,
    Name STRING(255),
    CreatedAt TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
) PRIMARY KEY (UserId);

CREATE TABLE Orders (
    UserId STRING(36) NOT NULL,
    OrderId STRING(36) NOT NULL,
    Amount FLOAT64,
    Status STRING(20),
) PRIMARY KEY (UserId, OrderId),
  INTERLEAVE IN PARENT Users ON DELETE CASCADE;
```

## Query Patterns

```sql
-- Read with secondary index
SELECT * FROM Users@{FORCE_INDEX=UsersByEmail} WHERE Email = @email;

-- Stale reads (for read-heavy, latency-sensitive queries)
-- Use read-only transactions with staleness bounds

-- Partitioned DML for bulk updates
UPDATE Users SET Status = 'INACTIVE' WHERE LastLogin < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY);
```

## Java Client Patterns

```java
// Read
try (ResultSet rs = dbClient.singleUse()
    .executeQuery(Statement.of("SELECT * FROM Users WHERE UserId = @id"))) {
    while (rs.next()) {
        String name = rs.getString("Name");
    }
}

// Write (mutations)
dbClient.write(Arrays.asList(
    Mutation.newInsertOrUpdateBuilder("Users")
        .set("UserId").to(userId)
        .set("Name").to(name)
        .build()
));
```

## Guidelines

- Prefer interleaved tables over foreign keys for parent-child
- Use commit timestamps for audit trails
- Avoid large transactions (prefer smaller batches)
- Use read-only transactions for multi-read consistency
- Index carefully — secondary indexes are stored separately
- Use `INTERLEAVE IN PARENT` index for co-located index storage
- Partition large DML operations to avoid timeouts
