---
name: spring-boot-actuator
description: >-
  Spring Boot Actuator for production-ready features
  Use this skill when working with spring-boot-actuator technologies.
---

# Spring Boot Actuator

## Key Concepts
*   **Production-Ready Features:** Actuator provides out-of-the-box endpoints for monitoring and managing your application in production.
*   **Info Endpoint:** Exposes arbitrary application information, typically including build details (version, git commit, etc.).
*   **Health Endpoint:** Reports the health of the application, which can be customized to include specific component health checks.
*   **Metrics Endpoint:** Exposes application metrics, which can be scraped by external monitoring systems (e.g., Prometheus).
*   **Dependency Management:** Requires `org.springframework.boot:spring-boot-starter-actuator` in the project's dependencies.

## Project Conventions
*   **`application.properties` / `application.yml` Configuration:** Actuator endpoints are typically configured in these files, controlling visibility, security, and custom endpoints.
*   **Endpoint Naming:** Standard endpoints follow a predictable naming convention (e.g., `/actuator/health`, `/actuator/info`, `/actuator/metrics`).
*   **Security Configuration:** Endpoints are often secured using Spring Security, with specific role-based access controls for sensitive endpoints.
*   **Custom Endpoints:** Developers can create custom endpoints by implementing `Endpoint` or `WebEndpoint` interfaces.

## Common Patterns
**Enabling and Configuring Endpoints:**

```java
// application.properties
management.endpoints.web.exposure.include=health,info,metrics,env,beans
management.endpoint.health.show-details=when_fully_healthy
management.info.build.location=classpath:META-INF/build-info.properties
```

**Creating a Custom Health Indicator:**

```java
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

@Component
public class CustomHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        // Perform health check logic
        boolean isHealthy = checkSomeExternalService();
        if (isHealthy) {
            return Health.up().withDetail("message", "External service is available").build();
        } else {
            return Health.down().withDetail("error", "External service is unavailable").build();
        }
    }

    private boolean checkSomeExternalService() {
        // ... implementation to check service health ...
        return true; // or false
    }
}
```

**Creating a Custom Info Contributor:**

```java
import org.springframework.boot.actuate.info.Info;
import org.springframework.boot.actuate.info.InfoContributor;
import org.springframework.stereotype.Component;

@Component
public class GitInfoContributor implements InfoContributor {

    @Override
    public void contribute(Info.Builder builder) {
        // Add Git commit hash, branch, etc. from build properties or environment variables
        builder.withDetail("git.commit", "abcdef123456");
        builder.withDetail("git.branch", "main");
    }
}
```

## Guidelines
*   **Secure Sensitive Endpoints:** Do not expose sensitive information (e.g., environment variables, beans) via unsecured endpoints in production.
*   **Configure `exposure` Wisely:** Explicitly define which endpoints are exposed via the web in `application.properties` or `application.yml` for better security.
*   **Use `when_fully_healthy` for Health Details:** Configure the health endpoint to show details only when the application is fully healthy to avoid revealing sensitive states during startup or partial failures.
*   **Leverage Built-in Metrics:** Utilize the standard metrics endpoints for integration with monitoring tools like Prometheus, Micrometer, or Grafana.
*   **Implement Custom Health Indicators:** For critical external dependencies or internal components, create custom `HealthIndicator` implementations to provide granular health status.
*   **Populate `info` Endpoint:** Regularly add build information (version, timestamp, git commit) to the `info` endpoint for easy visibility into deployed application versions.
*   **Consider Custom Endpoints for Application-Specific Operations:** Use custom endpoints for actions that need to be performed on a running application (e.g., cache clearing, triggering a re-scan) but are not standard monitoring concerns.
*   **Avoid Exposing `shutdown` Endpoint in Production:** Unless strictly necessary and heavily secured, the `shutdown` endpoint can be a security risk.