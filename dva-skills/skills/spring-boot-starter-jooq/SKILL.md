---
name: spring-boot-starter-jooq
description: >-
  Spring Boot Starter for JOOQ integration
  Use this skill when working with spring-boot-starter-jooq technologies.
---

# Spring Boot Starter JOOQ

## Key Concepts
* **Type-Safe SQL:** JOOQ generates Java classes from your database schema, allowing you to write SQL queries in a type-safe, object-oriented manner within Java.
* **Spring Boot Integration:** The `spring-boot-starter-jooq` dependency automatically configures JOOQ with your Spring Boot application, including datasource management, connection pooling, and transaction handling.
* **DSL Context:** The primary entry point for writing JOOQ queries is the `DSLContext` interface, which is typically auto-configured by Spring Boot.
* **Code Generation:** JOOQ generates Java classes (tables, columns, routines, etc.) based on your database schema. This process is usually configured via Maven or Gradle plugins.
* **Database Agnostic:** While JOOQ generates code for a specific database, the generated query DSL is largely database-agnostic, making it easier to switch databases.

## Project Conventions
* **Code Generation Directory:** Generated JOOQ classes are typically placed in a dedicated directory (e.g., `src/main/java` or `src/main/java-gen`) specified in the JOOQ Maven/Gradle plugin configuration.
* **Package Naming:** Generated classes often reside in a specific package (e.g., `org.jooq.generated` or a custom package defined in the JOOQ configuration).
* **Configuration Properties:** JOOQ specific properties are usually defined in `application.properties` or `application.yml` and prefixed with `spring.jooq.*`.
* **Repository/Service Layer Usage:** JOOQ queries are typically executed within Spring service or repository classes, often injected with the `DSLContext`.

## Common Patterns
* **Basic SELECT Query:**

```java
import org.jooq.DSLContext;
import org.jooq.generated.tables.Author;
import org.jooq.generated.tables.records.AuthorRecord;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class AuthorRepository {

    @Autowired
    private DSLContext dslContext;

    public List<AuthorRecord> findAllAuthors() {
        return dslContext.selectFrom(Author.AUTHOR)
                         .fetchInto(AuthorRecord.class);
    }
}
```

* **INSERT Statement:**

```java
import org.jooq.DSLContext;
import org.jooq.generated.tables.Author;
import org.jooq.generated.tables.records.AuthorRecord;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

@Repository
public class AuthorRepository {

    @Autowired
    private DSLContext dslContext;

    public void createAuthor(String firstName, String lastName) {
        dslContext.insertInto(Author.AUTHOR, Author.AUTHOR.FIRST_NAME, Author.AUTHOR.LAST_NAME)
                  .values(firstName, lastName)
                  .execute();
    }
}
```

* **JOIN Query:**

```java
import org.jooq.DSLContext;
import org.jooq.generated.tables.Author;
import org.jooq.generated.tables.Book;
import org.jooq.generated.tables.records.AuthorRecord;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class AuthorRepository {

    @Autowired
    private DSLContext dslContext;

    public List<AuthorRecord> findAuthorsWithBooks() {
        return dslContext.select(Author.AUTHOR.asterisk())
                         .from(Author.AUTHOR)
                         .join(Book.BOOK)
                         .on(Author.AUTHOR.ID.eq(Book.BOOK.AUTHOR_ID))
                         .fetchInto(AuthorRecord.class);
    }
}
```

* **Using Generated Values:**

```java
import org.jooq.DSLContext;
import org.jooq.generated.tables.pojos.Author;
import org.jooq.generated.tables.records.AuthorRecord;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class AuthorRepository {

    @Autowired
    private DSLContext dslContext;

    public List<Author> findAuthorsAsPOJOs() {
        return dslContext.selectFrom(Author.AUTHOR)
                         .fetchInto(Author.class); // Fetches into POJO
    }
}
```

## Guidelines
* **Leverage Code Generation:** Always use the generated JOOQ classes for table and column references to ensure type safety and reduce runtime errors.
* **Define Custom JOOQ Configuration:** For advanced configurations like custom converters, RenderListeners, or TransactionListeners, create a `@Configuration` class and define a `DSLContext` bean.
* **Use `DSLContext` Effectively:** Inject `DSLContext` into your repositories or services. Avoid direct `Connection` manipulation.
* **Handle Transactions Explicitly:** For complex operations, use Spring's `@Transactional` annotation or JOOQ's programmatic transaction management.
* **Optimize Queries:** Pay attention to the generated SQL. JOOQ's DSL can sometimes generate inefficient SQL if not used carefully. Analyze the generated SQL for performance bottlenecks.
* **Consider JOOQ's `ResultQuery` vs. `ExecuteUpdate`:** Use `fetch()` or `fetchInto()` for SELECT queries and `execute()` for INSERT, UPDATE, and DELETE statements.
* **Understand `fetch()` vs. `fetchInto()`:** `fetch()` returns `Record` objects, which provide access to columns by name or index. `fetchInto(Class)` maps results to POJOs or generated records.
* **Utilize JOOQ's `Settings`:** Configure JOOQ's behavior (e.g., query logging, case sensitivity) using `Settings` to tailor it to your application's needs.