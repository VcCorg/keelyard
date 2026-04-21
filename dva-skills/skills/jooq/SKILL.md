---
name: jooq
description: >-
  jOOQ type-safe SQL — DSL query building, code generation,
  Spring Boot integration, and Spanner dialect usage.
---

# jOOQ — Type-Safe SQL

## Overview

- jOOQ generates Java classes from database schema
- Provides a fluent DSL for writing type-safe SQL queries
- Catches SQL errors at compile time instead of runtime

## Spring Boot Configuration

```yaml
spring:
  jooq:
    sql-dialect: CLOUD_SPANNER   # or POSTGRES, MYSQL, etc.
```

```java
@Configuration
public class JooqConfig {

    @Bean
    public DSLContext dslContext(DataSource dataSource) {
        return DSL.using(dataSource, SQLDialect.CLOUD_SPANNER);
    }
}
```

## Query Patterns

```java
@Repository
@RequiredArgsConstructor
public class PatientRepository {

    private final DSLContext dsl;

    // Select
    public List<PatientRecord> findByStatus(String status) {
        return dsl.selectFrom(PATIENT)
            .where(PATIENT.STATUS.eq(status))
            .orderBy(PATIENT.LAST_NAME.asc())
            .fetchInto(PatientRecord.class);
    }

    // Select with join
    public List<PatientWithAddress> findWithAddress(String patientId) {
        return dsl.select(PATIENT.fields())
            .select(ADDRESS.CITY, ADDRESS.STATE)
            .from(PATIENT)
            .join(ADDRESS).on(PATIENT.PATIENT_ID.eq(ADDRESS.PATIENT_ID))
            .where(PATIENT.PATIENT_ID.eq(patientId))
            .fetchInto(PatientWithAddress.class);
    }

    // Insert
    public void insert(Patient patient) {
        dsl.insertInto(PATIENT)
            .set(PATIENT.PATIENT_ID, patient.getId())
            .set(PATIENT.FIRST_NAME, patient.getFirstName())
            .set(PATIENT.LAST_NAME, patient.getLastName())
            .execute();
    }

    // Update
    public int updateStatus(String patientId, String status) {
        return dsl.update(PATIENT)
            .set(PATIENT.STATUS, status)
            .set(PATIENT.UPDATED_AT, LocalDateTime.now())
            .where(PATIENT.PATIENT_ID.eq(patientId))
            .execute();
    }

    // Conditional / dynamic queries
    public List<PatientRecord> search(PatientSearchCriteria criteria) {
        var query = dsl.selectFrom(PATIENT).where(DSL.trueCondition());
        if (criteria.getName() != null) {
            query = query.and(PATIENT.LAST_NAME.likeIgnoreCase("%" + criteria.getName() + "%"));
        }
        if (criteria.getStatus() != null) {
            query = query.and(PATIENT.STATUS.eq(criteria.getStatus()));
        }
        return query.fetchInto(PatientRecord.class);
    }
}
```

## Pagination

```java
public Page<PatientRecord> findPaged(int page, int size) {
    int offset = page * size;
    List<PatientRecord> records = dsl.selectFrom(PATIENT)
        .orderBy(PATIENT.CREATED_AT.desc())
        .limit(size)
        .offset(offset)
        .fetchInto(PatientRecord.class);

    int total = dsl.fetchCount(PATIENT);
    return new PageImpl<>(records, PageRequest.of(page, size), total);
}
```

## Guidelines

- Use `DSLContext` injection (not static `DSL.using()`) in Spring Boot
- Prefer `fetchInto(DTO.class)` for mapping results to POJOs
- Build dynamic queries with conditional `.and()` / `.or()` clauses
- Use jOOQ's `CLOUD_SPANNER` dialect for Spanner-specific SQL
- Keep generated classes in a separate `jooq` package
- Use `fetchOptional()` for single-result queries to avoid NPE
- Combine with Spring `@Transactional` for write operations
