---
name: spring-boot-configuration-processor
description: >-
  Spring Boot Configuration Processor for metadata generation
  Use this skill when working with spring-boot-configuration-processor technologies.
---

# Spring Boot Configuration Processor

This skill focuses on the `spring-boot-configuration-processor`, a tool that generates metadata for Spring Boot auto-configuration. This metadata enhances IDE support for configuration properties, providing autocompletion, type checking, and documentation directly within the editor.

## Key Concepts

*   **Configuration Metadata Generation:** The processor analyzes your Spring Boot application's configuration properties and generates a `spring-boot-configuration-metadata.json` file.
*   **IDE Integration:** The generated metadata file is consumed by IDEs (like IntelliJ IDEA, Eclipse) to provide intelligent assistance for `application.properties` and `application.yml` files.
*   **Auto-configuration Enhancement:** It helps document and describe auto-configuration properties, making them discoverable and easier to use for developers.
*   **Developer Experience Improvement:** Provides features like autocompletion, validation, and parameter information for configuration properties, reducing errors and development time.

## Project Conventions

*   **Dependency Inclusion:** The `spring-boot-configuration-processor` is typically added as a `annotationProcessor` or `kapt` (for Kotlin) dependency in your `pom.xml` or `build.gradle` file.
    ```xml
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-configuration-processor</artifactId>
        <optional>true</optional>
    </dependency>
    ```
    ```gradle
    dependencies {
        annotationProcessor 'org.springframework.boot:spring-boot-configuration-processor'
        // or for Kotlin:
        // kapt 'org.springframework.boot:spring-boot-configuration-processor'
    }
    ```
*   **Source Code Annotation:** Configuration properties are typically defined within `@ConfigurationProperties` annotated classes. The processor analyzes these classes.
*   **Metadata Output:** The generated `spring-boot-configuration-metadata.json` file is usually placed in the `META-INF` directory of your JAR artifact.

## Common Patterns

*   **Defining Configuration Properties:**
    ```java
    import org.springframework.boot.context.properties.ConfigurationProperties;
    import org.springframework.stereotype.Component;

    @Component
    @ConfigurationProperties(prefix = "app.messaging")
    public class MessagingProperties {
        private String brokerUrl;
        private int concurrentConsumers = 5;

        public String getBrokerUrl() {
            return brokerUrl;
        }

        public void setBrokerUrl(String brokerUrl) {
            this.brokerUrl = brokerUrl;
        }

        public int getConcurrentConsumers() {
            return concurrentConsumers;
        }

        public void setConcurrentConsumers(int concurrentConsumers) {
            this.concurrentConsumers = concurrentConsumers;
        }
    }
    ```
    This will generate metadata for `app.messaging.broker-url` and `app.messaging.concurrent-consumers`.

*   **Using Standard Java Beans Conventions:** The processor relies on standard Java Bean getter and setter methods (or Lombok annotations like `@Getter`, `@Setter`) for property detection.

*   **Adding Descriptions:** Use Javadoc comments on properties and their getters/setters to provide descriptions that will appear in IDE autocompletion.
    ```java
    /**
     * The URL of the message broker.
     */
    private String brokerUrl;

    /**
     * Gets the URL of the message broker.
     * @return the broker URL
     */
    public String getBrokerUrl() {
        return brokerUrl;
    }

    /**
     * Sets the URL of the message broker.
     * @param brokerUrl the message broker URL
     */
    public void setBrokerUrl(String brokerUrl) {
        this.brokerUrl = brokerUrl;
    }
    ```

*   **Handling Different Data Types:** The processor supports common data types like `String`, `int`, `boolean`, `List`, `Map`, `Duration`, etc.

## Guidelines

*   **Always Include as `optional`:** The `spring-boot-configuration-processor` should almost always be declared as an optional dependency. This ensures it's not included in the runtime classpath of your application, as it's only needed during the build process.
*   **Use `@ConfigurationProperties` for Externalized Configuration:** Leverage `@ConfigurationProperties` to define your application's external configuration rather than manually binding properties in `@Bean` methods.
*   **Provide Clear Descriptions:** Document your configuration properties using Javadoc. This significantly improves the developer experience for those consuming your library or application.
*   **Adhere to Naming Conventions:** Use kebab-case for configuration property names in `application.properties`/`yml` and let the processor map them to camelCase in your Java classes.
*   **Consider Default Values:** Provide sensible default values for your configuration properties to make them easier to use out-of-the-box.
*   **Keep Metadata Focused:** The processor is designed for configuration properties. Avoid using it for general code analysis or metadata generation unrelated to application settings.
*   **Verify Generated Metadata:** After a build, you can inspect the `spring-boot-configuration-metadata.json` file in your build output (e.g., `target/classes/META-INF`) to ensure the properties are correctly identified and described.
*   **Integrate with Build Tools:** Ensure the processor is correctly configured with your build tool (Maven or Gradle) to run during the compilation phase.