---
name: spring-cloud-gcp-logging
description: >-
  Utilizing Spring Cloud GCP for centralized logging to Google Cloud Logging.
  Use this skill when working with spring-cloud-gcp-logging technologies.
---

# Spring Cloud GCP Logging

## Key Concepts
* **Centralized Logging:** Aggregates logs from multiple Spring Boot applications into a single, searchable location in Google Cloud Logging.
* **Structured Logging:** Emits logs in a structured format (JSON) compatible with Google Cloud Logging, enabling richer querying and analysis.
* **Automatic Metadata Enrichment:** Automatically includes GCP-specific metadata like trace IDs and span IDs (if distributed tracing is enabled) with log entries.
* **Spring Boot Integration:** Seamlessly integrates with Spring Boot's logging framework (Logback, Log4j2) by providing an appender that directs output to Cloud Logging.
* **Configuration Driven:** Relies on Spring Boot's `application.properties` or `application.yml` for configuration of GCP project, log level, etc.

## Project Conventions
* **Dependency Management:** Typically declared in `pom.xml` (Maven) or `build.gradle` (Gradle) using `com.google.cloud:spring-cloud-gcp-logging`. Customizations or internal wrapper libraries (like `com.example.common:example-spring-cloud-gcp-logging`) may also be present.
* **Configuration:** Logging configuration is managed within `src/main/resources/application.properties` or `src/main/resources/application.yml`. Key properties often include `spring.cloud.gcp.logging.enabled`, `spring.cloud.gcp.project-id`, and potentially `logging.level.<package>`.
* **Logging Framework:** Assumes usage of standard Java logging frameworks like Logback or Log4j2, with the Spring Cloud GCP appender configured to capture their output.

## Common Patterns
**Basic Configuration:**

```yaml
spring:
  cloud:
    gcp:
      project-id: <your-gcp-project-id>
      logging:
        enabled: true
        log-stackdriver-format: true # For structured logging to Stackdriver/Cloud Logging
        # Optional: if using a custom service account key file
        # credentials:
        #   location: file:/path/to/your/keyfile.json
```

**Configuring Log Levels:**

```properties
logging.level.org.springframework.web=DEBUG
logging.level.com.example.myapp=INFO
```

**Disabling Spring Cloud GCP Logging:**

```yaml
spring:
  cloud:
    gcp:
      logging:
        enabled: false
```

**Customizing Log Appenders (Logback Example):**

```xml
<configuration>
    <appender name="CLOUD_LOGGING" class="com.google.cloud.logging.LogAppender">
        <projectId>${CLOUD_PROJECT_ID}</projectId>
        <logName>my-application-logs</logName>
        <autoPopulateMetadata>true</autoPopulateMetadata>
    </appender>

    <root level="INFO">
        <appender-ref ref="CLOUD_LOGGING" />
    </root>
</configuration>
```

## Guidelines
* **Enable Structured Logging:** Always set `spring.cloud.gcp.logging.log-stackdriver-format=true` for richer querying and analysis in Google Cloud Logging.
* **Use Specific Project IDs:** Explicitly configure `spring.cloud.gcp.project-id` in your application properties to ensure logs go to the correct project.
* **Manage Credentials Securely:** For production environments, leverage application default credentials or properly configured service account keys via GKE's Workload Identity or other secure methods. Avoid hardcoding credentials.
* **Configure Log Levels Appropriately:** Set appropriate logging levels for different packages to avoid excessive log volume. Use `INFO` for general application flow and `DEBUG` for troubleshooting.
* **Monitor Log Volume and Costs:** Be mindful of the volume of logs generated, as high volumes can impact performance and incur costs in Google Cloud Logging.
* **Integrate with Distributed Tracing:** If using Spring Cloud Sleuth or similar for distributed tracing, ensure it's enabled alongside Spring Cloud GCP Logging to automatically correlate logs with traces.
* **Consider Log Rotation and Retention:** Configure retention policies within Google Cloud Logging to manage historical data and comply with any regulatory requirements.
* **Use Custom Log Names:** For better organization, consider defining custom log names using `log-name` in the configuration.