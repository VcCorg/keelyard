---
name: spring-cloud-bootstrap
description: >-
  Spring Cloud Bootstrap for externalized configuration in distributed systems.
  Use this skill when working with spring-cloud-bootstrap technologies.
---

# Spring Cloud Bootstrap

## Key Concepts
*   **Externalized Configuration:** Centralizes and externalizes application configuration, making it accessible from a central location (e.g., Spring Cloud Config Server, HashiCorp Vault, AWS Parameter Store).
*   **Bootstrap Context:** A special, lightweight Spring `ApplicationContext` that is bootstrapped *before* the main application context. It is responsible for discovering and loading external configuration properties.
*   **`spring.cloud.bootstrap.enabled`:** A critical property, typically set to `true` in `bootstrap.properties` or `bootstrap.yml`, to enable the bootstrap context.
*   **Configuration Sources:** Supports various external configuration sources, including Git repositories, Consul, ZooKeeper, Vault, and custom sources.
*   **Property Hierarchy:** Defines a specific order of precedence for loading properties, allowing for default values and overrides.

## Project Conventions
*   **Configuration Files:** External configuration properties are typically stored in `bootstrap.properties` or `bootstrap.yml` files placed in the `src/main/resources` directory of the application. These files are processed by the bootstrap context.
*   **Naming Conventions:** Configuration property names follow Spring Boot's standard naming conventions, with dot notation. When using Spring Cloud Config Server, property files are often named after the application ID and profile (e.g., `my-app.properties`, `my-app-dev.yml`).
*   **Application Identification:** Applications are identified by an `spring.application.name` property, which is crucial for fetching configurations from a central server.

## Common Patterns
*   **Enabling Bootstrap Context:**
    ```yaml
    # bootstrap.yml
    spring:
      cloud:
        bootstrap:
          enabled: true
    ```
*   **Configuring Spring Cloud Config Server:**
    ```yaml
    # bootstrap.yml
    spring:
      cloud:
        config:
          uri: http://localhost:8888
          name: my-app # Name of the configuration file on the server (e.g., my-app.yml)
          profile: dev # Profile to fetch (e.g., my-app-dev.yml)
          label: main # Git branch/label
    ```
*   **Accessing Bootstrap Properties in the Application:**
    Properties loaded via bootstrap are available directly as Spring `Environment` properties in the main application context.
    ```java
    @Service
    public class MyService {

        @Value("${my.custom.setting}")
        private String customSetting;

        public void doSomething() {
            System.out.println("Custom setting: " + customSetting);
        }
    }
    ```
*   **Using `spring.cloud.bootstrap.loader.enabled` for Custom Loaders:**
    Allows disabling default bootstrap loaders if you're implementing a custom bootstrapping process.
    ```properties
    # bootstrap.properties
    spring.cloud.bootstrap.loader.enabled=false
    ```

## Guidelines
*   Always use `bootstrap.properties` or `bootstrap.yml` for bootstrapping-related configurations, not `application.properties` or `application.yml`.
*   Ensure `spring.application.name` is correctly set to uniquely identify your application for configuration retrieval.
*   Prioritize using a dedicated configuration server (like Spring Cloud Config Server) for managing configurations in a distributed environment.
*   Be mindful of property precedence. Properties defined in `bootstrap.properties`/`yml` generally override those in `application.properties`/`yml` loaded later.
*   For sensitive information, consider integrating with secure secret management systems like HashiCorp Vault or AWS Secrets Manager.
*   Avoid hardcoding configuration values that should be externalized.
*   When using multiple configuration sources, understand their defined order of precedence to prevent unexpected overrides.
*   If migrating from older Spring Cloud versions, be aware of potential changes in bootstrap behavior or configuration loading mechanisms.