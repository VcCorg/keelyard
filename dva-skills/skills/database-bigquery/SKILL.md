---
name: database-bigquery
description: >-
  Google BigQuery table design, query patterns, Java client usage,
  and Spring Cloud GCP BigQuery integration.
---

# Google BigQuery Development

## Table Design

- Use **partitioned tables** (by date/timestamp) for cost and performance
- Use **clustered columns** for frequently filtered fields
- Prefer **denormalized schemas** — BigQuery is optimized for wide, flat tables
- Use `STRUCT` and `ARRAY` for nested/repeated data

```sql
CREATE TABLE `project.dataset.patient_events` (
    event_id STRING NOT NULL,
    patient_id STRING NOT NULL,
    event_type STRING NOT NULL,
    event_data JSON,
    created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY patient_id, event_type;
```

## Query Patterns

```sql
-- Partition pruning (always filter on partition column)
SELECT * FROM `project.dataset.patient_events`
WHERE DATE(created_at) BETWEEN '2024-01-01' AND '2024-01-31'
  AND patient_id = @patientId;

-- Aggregation
SELECT event_type, COUNT(*) as cnt
FROM `project.dataset.patient_events`
WHERE DATE(created_at) = CURRENT_DATE()
GROUP BY event_type;

-- MERGE (upsert)
MERGE `project.dataset.patients` T
USING `project.dataset.staging_patients` S
ON T.patient_id = S.patient_id
WHEN MATCHED THEN UPDATE SET T.name = S.name
WHEN NOT MATCHED THEN INSERT VALUES (S.patient_id, S.name);
```

## Spring Cloud GCP Integration

```yaml
spring:
  cloud:
    gcp:
      bigquery:
        dataset-name: patient_dataset
        project-id: ${GCP_PROJECT_ID}
```

```java
@Service
@RequiredArgsConstructor
public class BigQueryService {

    private final BigQuery bigQuery;

    public TableResult query(String sql) {
        QueryJobConfiguration config = QueryJobConfiguration.newBuilder(sql)
            .setUseLegacySql(false)
            .build();
        return bigQuery.query(config);
    }

    public void insertRows(String table, List<Map<String, Object>> rows) {
        TableId tableId = TableId.of("dataset", table);
        InsertAllRequest.Builder builder = InsertAllRequest.newBuilder(tableId);
        rows.forEach(row -> builder.addRow(row));
        bigQuery.insertAll(builder.build());
    }
}
```

## Guidelines

- Always filter on partition columns to avoid full table scans
- Use parameterized queries (`@param`) to prevent SQL injection
- Prefer streaming inserts for real-time data; batch loads for bulk
- Use `INFORMATION_SCHEMA` views for metadata queries
- Set query cost limits with `maximum_bytes_billed`
- Use materialized views for frequently computed aggregations
- Avoid `SELECT *` — specify only needed columns to reduce cost
