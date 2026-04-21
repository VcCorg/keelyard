---
name: spring-boot-jooq
description: >-
  Integration with JOOQ for type-safe SQL querying within Spring Boot applications.
  Use this skill when working with spring-boot-jooq technologies.
---

# Spring Boot JOOQ Integration

## Key Concepts
*   **Type-Safe SQL:** JOOQ generates Java classes from your database schema, enabling compile-time checking of SQL queries.
*   **DSL Context:** The `DSLContext` is the central entry point for constructing and executing JOOQ queries within your application.
*   **Generated Code:** JOOQ generates classes for tables, columns, data types, and constants based on your database schema.
*   **Spring Boot Starter:** The `spring-boot-starter-jooq` dependency simplifies configuration and integrates JOOQ with Spring's transaction management.
*   **Data Access Object (DAO) Pattern:** JOOQ queries are typically encapsulated within DAOs for clean separation of concerns.

## Project Conventions
*   **Generated Code Location:** JOOQ-generated code is conventionally placed in a dedicated package, often named `org.jooq.generated` or similar, to separate it from application code.
*   **Configuration Properties:** JOOQ-specific properties, such as schema generation settings and database connection details (often managed by Spring Boot's data source), are typically configured in `application.properties` or `application.yml`.
*   **DAO Implementation:** Repository or DAO classes that utilize JOOQ will often be Spring `@Repository` or `@Component` beans.
*   **DSLContext Injection:** The `DSLContext` is typically injected into DAOs or service classes using `@Autowired`.

## Common Patterns
*   **Selecting Data:**
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
        private DSLContext dsl;

        private final Author AUTHOR = Author.AUTHOR;

        public List<AuthorRecord> findAll() {
            return dsl.selectFrom(AUTHOR)
                      .fetch();
        }

        public AuthorRecord findById(int id) {
            return dsl.selectFrom(AUTHOR)
                      .where(AUTHOR.ID.eq(id))
                      .fetchOne();
        }
    }
    ```

*   **Inserting Data:**
    ```java
    import org.jooq.DSLContext;
    import org.jooq.generated.tables.Author;
    import org.jooq.generated.tables.records.AuthorRecord;
    import org.springframework.beans.factory.annotation.Autowired;
    import org.springframework.stereotype.Repository;

    @Repository
    public class AuthorRepository {

        @Autowired
        private DSLContext dsl;

        private final Author AUTHOR = Author.AUTHOR;

        public void insertAuthor(String firstName, String lastName) {
            dsl.insertInto(AUTHOR, AUTHOR.FIRST_NAME, AUTHOR.LAST_NAME)
               .values(firstName, lastName)
               .execute();
        }
    }
    ```

*   **Updating Data:**
    ```java
    import org.jooq.DSLContext;
    import org.jooq.generated.tables.Author;
    import org.springframework.beans.factory.annotation.Autowired;
    import org.springframework.stereotype.Repository;

    @Repository
    public class AuthorRepository {

        @Autowired
        private DSLContext dsl;

        private final Author AUTHOR = Author.AUTHOR;

        public int updateAuthorLastName(int id, String newLastName) {
            return dsl.update(AUTHOR)
                      .set(AUTHOR.LAST_NAME, newLastName)
                      .where(AUTHOR.ID.eq(id))
                      .execute();
        }
    }
    ```

*   **Deleting Data:**
    ```java
    import org.jooq.DSLContext;
    import org.jooq.generated.tables.Author;
    import org.springframework.beans.factory.annotation.Autowired;
    import org.springframework.stereotype.Repository;

    @Repository
    public class AuthorRepository {

        @Autowired
        private DSLContext dsl;

        private final Author AUTHOR = Author.AUTHOR;

        public int deleteAuthor(int id) {
            return dsl.deleteFrom(AUTHOR)
                      .where(AUTHOR.ID.eq(id))
                      .execute();
        }
    }
    ```

*   **Joining Tables:**
    ```java
    import org.jooq.DSLContext;
    import org.jooq.Record;
    import org.jooq.generated.tables.Author;
    import org.jooq.generated.tables.Book;
    import org.jooq.impl.DSL;
    import org.springframework.beans.factory.annotation.Autowired;
    import org.springframework.stereotype.Repository;

    import java.util.List;

    @Repository
    public class BookAuthorRepository {

        @Autowired
        private DSLContext dsl;

        private final Author AUTHOR = Author.AUTHOR;
        private final Book BOOK = Book.BOOK;

        public List<Record> findBooksByAuthorFirstName(String firstName) {
            return dsl.select(BOOK.TITLE, AUTHOR.FIRST_NAME, AUTHOR.LAST_NAME)
                      .from(BOOK)
                      .join(AUTHOR)
                      .on(BOOK.AUTHOR_ID.eq(AUTHOR.ID))
                      .where(AUTHOR.FIRST_NAME.eq(firstName))
                      .fetch();
        }
    }
    ```

## Guidelines
*   **Keep Generated Code Separate:** Avoid modifying JOOQ-generated code directly. If schema changes, regenerate the code.
*   **Use `DSLContext`:** Always use `DSLContext` for constructing and executing queries for type safety and consistency.
*   **Inject `DSLContext`:** Inject `DSLContext` into your repository or DAO classes.
*   **Leverage Table and Column References:** Utilize the generated table and column objects (e.g., `Author.AUTHOR`, `AUTHOR.ID`) for compile-time safety.
*   **Handle Nulls Explicitly:** Be mindful of nullable columns and handle potential `null` values returned by `fetchOne()` or other fetching methods.
*   **Use Transactions:** Integrate JOOQ queries with Spring's transaction management (`@Transactional` annotation) for reliable data operations.
*   **Consider `fetch()` vs. `fetchOne()` vs. `fetchInto()`:** Choose the appropriate fetching method based on whether you expect multiple records, a single record, or to map directly to a POJO.
*   **Optimize Queries:** While JOOQ provides type safety, it's still important to write efficient SQL. Use JOOQ's query building capabilities to express complex logic when needed, but review generated SQL if performance is critical.