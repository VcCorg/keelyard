---
name: spring-cloud-starter-config
description: >-
  Spring Cloud Config for externalized configuration
  Use this skill when working with spring-cloud-starter-config technologies.
---

# Spring Cloud Config Starter

## Key Concepts
*   **Externalized Configuration:** Centralizes application configuration outside of the application's codebase, enabling dynamic updates and environment-specific settings.
*   **Configuration Server:** A dedicated service (often built using Spring Cloud Config Server) that hosts and serves configuration properties.
*   **Configuration Client:** Applications that depend on `spring-cloud-starter-config` to fetch configuration from the server.
*   **Configuration Sources:** Supports various backend repositories like Git, Apache Subversion (SVN), and file systems for storing configuration files.
*   **Profile-Based Configuration:** Allows different configuration profiles (e.g., `dev`, `prod`, `test`) to be applied based on the environment.

## Project Conventions
*   **Configuration Files:** Typically stored in a dedicated Git repository, organized by application name and profile (e.g., `my-app-dev.properties`, `my-app-prod.yml`).
*   **Application Naming:** Configuration server uses the `spring.application.name` property to locate the correct configuration files for a client.
*   **Profile Naming:** Configuration files can be suffixed with profile names (e.g., `application-dev.properties`) which are activated via `spring.profiles.active` environment property or bootstrap properties.
*   **Bootstrap Context:** Clients typically use a `bootstrap.yml` or `bootstrap.properties` file to define the configuration server location (`spring.cloud.config.uri`) and application details.

## Common Patterns
**Client Configuration:**

```yaml
# bootstrap.yml (or bootstrap.properties) on the client application
spring:
  application:
    name: my-client-app
  cloud:
    config:
      uri: http://localhost:8888 # URL of the Spring Cloud Config Server
      # Optional: Specify a label (branch) in Git
      # label: main
      # Optional: Enable/disable config server discovery via service registry
      # discovery:
      #   enabled: true
      #   service-id: config-server
```

**Server Configuration:**

```yaml
# application.yml (or application.properties) for the Config Server
spring:
  application:
    name: spring-cloud-config-server
  cloud:
    config:
      server:
        git:
          uri: https://github.com/your-username/your-config-repo.git
          # Optional: Specify username and password for private repositories
          # username: your-git-username
          # password: your-git-password
          # Optional: Specify a search path within the Git repository
          # search-paths: config/{application}/{profile}
```

**Accessing Properties in Client:**

```java
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class MyConfiguredService {

    private final String customProperty;

    public MyConfiguredService(@Value("${my.custom.property:default_value}") String customProperty) {
        this.customProperty = customProperty;
    }

    public void displayProperty() {
        System.out.println("My custom property value: " + customProperty);
    }
}
```

**Dynamic Property Refresh (using Spring Cloud Bus or Actuator):**

If `spring-boot-starter-actuator` is included and `/actuate/refresh` endpoint is exposed:
Send a POST request to `/actuate/refresh` on the client application.

For bus-enabled refresh:
Send a POST request to the `/actuate/bus/refresh` endpoint on the *config server* or a *client* configured with Spring Cloud Bus.

## Guidelines
*   **Secure Configuration:** Use appropriate security measures for your configuration server, especially when dealing with sensitive properties. Consider encrypted properties or authentication.
*   **Version Control Configuration:** Treat your configuration repository like application code. Use branches, commits, and pull requests for managing changes.
*   **Environment-Specific Properties:** Leverage profiles to manage different configurations for development, testing, staging, and production environments.
*   **Health Checks:** Ensure your configuration server is highly available and has proper health checks.
*   **Client Startup:** Be aware that configuration is fetched during the bootstrap phase. Any issues with the config server can prevent the client from starting.
*   **Property Resolution Order:** Understand how Spring Cloud Config resolves properties, especially when multiple sources or profiles are involved.
*   **Decouple Configuration:** Aim to keep application code independent of specific configuration sources, allowing flexibility in choosing backend repositories.
*   **Avoid Over-Configuration:** Don't store sensitive credentials directly in plain text configuration files. Use external secrets management or encryption.