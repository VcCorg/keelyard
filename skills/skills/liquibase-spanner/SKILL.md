---
name: liquibase-spanner
description: >-
  Liquibase with Cloud Spanner extensions for DDL, DML, ref data, and change streams.
  Use this skill when creating or modifying database changelogs, schema migrations,
  or reference data loads targeting Google Cloud Spanner.
---

# Liquibase + Cloud Spanner

This skill covers Liquibase usage with the `liquibase-spanner` extension for managing DDL, DML, reference data, and change streams against Google Cloud Spanner.

## Project Structure

```
src/main/resources/db/
├── liquibase.properties              # JDBC driver + Spanner connection URL
├── changelog-master.xml              # Top-level includes per-release aggregators
└── changelog/
    ├── changelog_000_ddl.xml         # Initial DDL
    ├── changelog_000_dml.xml         # Initial DML / seed data
    ├── rXX.xml                       # Release aggregator (includes DDL, DML, change streams)
    ├── changelog_rXX_ddl.xml         # Per-release DDL changelog
    ├── changelog_rXX_dml.xml         # Per-release DML changelog
    ├── rXX/                          # SQL files for release XX
    │   ├── 1_rXX_table_name_ddl.sql
    │   └── 1_rXX_table_name_ddl_rollback.sql
    └── csv/rXX/                      # CSV files for bulk ref-data loads
```

## Release Aggregator Pattern

Each release has an aggregator XML that includes DDL, DML, and optionally change stream files:

```xml
<databaseChangeLog
    xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
        http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-3.8.xsd"
    logicalFilePath="db/changelog-master.xml">

    <property name="batchSize" value="50" />

    <include file="changelog_rXX_ddl.xml" relativeToChangelogFile="true"/>
    <include file="changelog_rXX_dml.xml" relativeToChangelogFile="true"/>
    <include file="changelog_rXX_change_stream_ddl.xml" relativeToChangelogFile="true"/>
</databaseChangeLog>
```

Then register it in `changelog-master.xml`:
```xml
<include file="changelog/rXX.xml" relativeToChangelogFile="true"/>
```

## Contexts

| Context | Purpose |
|---------|---------|
| `ddl` | Schema changes (CREATE, ALTER, DROP TABLE/INDEX) |
| `refdata` | Reference / seed data inserts/updates via inline SQL |
| `ref` | Reference data via CSV bulk loads (`gcp:spannerLoadData`) |
| `change_stream` | Spanner change stream DDL |

## DDL ChangeSet Template

DDL changesets reference external `.sql` files with matching `_rollback.sql`:

```xml
<changeSet author="yourname" context="ddl" id="1_rXX_table_name_ddl" runInTransaction="false">
    <validCheckSum>ANY</validCheckSum>
    <comment>RXX Schema - TABLE_NAME</comment>
    <sqlFile path="rXX/1_rXX_table_name_ddl.sql" relativeToChangelogFile="true" />
    <rollback>
        <sqlFile path="rXX/1_rXX_table_name_ddl_rollback.sql" relativeToChangelogFile="true" />
    </rollback>
</changeSet>
```

## DML ChangeSet Templates

### Inline SQL (inserts / updates)

```xml
<changeSet author="yourname" context="refdata" id="rXX_description" runInTransaction="false">
    <validCheckSum>ANY</validCheckSum>
    <comment>Description of the data change</comment>
    <gcp:sql>
        INSERT INTO TABLE_NAME (COL1, COL2, UPDATE_DATE_TIME_GMT)
        VALUES ('val1', 'val2', CURRENT_TIMESTAMP());
    </gcp:sql>
    <rollback>
        <gcp:partitionedDml>
            DELETE FROM TABLE_NAME WHERE COL1 = 'val1';
        </gcp:partitionedDml>
    </rollback>
</changeSet>
```

### CSV Bulk Load

```xml
<changeSet author="yourname" id="REF_DATA_NAME_RXX.csv" context="ref" runInTransaction="false">
    <validCheckSum>ANY</validCheckSum>
    <comment>Import CSV into TABLE_NAME</comment>
    <gcp:partitionedDml>
        DELETE TABLE_NAME WHERE CATEGORY_NAME IN ("CAT1", "CAT2")
    </gcp:partitionedDml>
    <gcp:spannerLoadData tableName="TABLE_NAME"
            file="csv/rXX/REF_DATA_NAME_RXX.csv" batchSize="${batchSize}">
        <gcp:column header="code_id" name="CODE_ID" type="STRING" primaryKey="true" />
        <gcp:column header="category_name" name="CATEGORY_NAME" type="STRING" />
        <gcp:column name="UPDATE_DATE_TIME_GMT" type="TIMESTAMP"
                    value="2024-01-01" remarks="yyyy-MM-dd" />
    </gcp:spannerLoadData>
    <gcp:partitionedDml>
        UPDATE TABLE_NAME SET UPDATE_DATE_TIME_GMT = PENDING_COMMIT_TIMESTAMP()
        WHERE CATEGORY_NAME IN ("CAT1", "CAT2")
    </gcp:partitionedDml>
    <rollback>
        <gcp:partitionedDml>
            DELETE TABLE_NAME WHERE CATEGORY_NAME IN ("CAT1", "CAT2")
        </gcp:partitionedDml>
    </rollback>
</changeSet>
```

## Spanner-Specific GCP XML Namespace

All DML changelogs must declare the Spanner GCP namespace:

```xml
<databaseChangeLog
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:gcp="http://www.liquibase.org/xml/ns/changelog-spanner"
    xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
    xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
        http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-3.1.xsd">
```

## Key Rules

- **Always** set `runInTransaction="false"` — Spanner does not support DDL inside transactions
- **Always** include `<validCheckSum>ANY</validCheckSum>` to avoid checksum failures on re-runs
- **Always** provide a `<rollback>` block for every changeset
- Use `gcp:partitionedDml` for large deletes/updates (avoids transaction size limits)
- Use `gcp:sql` for small inline DML (inserts, single-row updates)
- Use `PENDING_COMMIT_TIMESTAMP()` for commit-timestamp columns after bulk loads
- SQL file naming: `{seq}_r{XX}_{description}.sql` and `{seq}_r{XX}_{description}_rollback.sql`
- CSV files go in `csv/r{XX}/`
- ChangeSet IDs must be unique across the entire changelog history

## Adding a New Release

1. Create directory `src/main/resources/db/changelog/r{XX}/` for SQL files
2. Create directory `src/main/resources/db/changelog/csv/r{XX}/` if CSV loads are needed
3. Create `changelog_r{XX}_ddl.xml`, `changelog_r{XX}_dml.xml` (and optionally `_change_stream_ddl.xml`)
4. Create aggregator `r{XX}.xml` that includes the above files
5. Add `<include file="changelog/r{XX}.xml" relativeToChangelogFile="true"/>` to `changelog-master.xml`
