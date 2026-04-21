---
name: spring-cloud-gcp-observability
description: >-
  Leveraging Spring Cloud GCP for application observability on Google Cloud Platform.
  Use this skill when working with spring-cloud-gcp-observability technologies.
---

# Spring Cloud GCP Observability

## Key Concepts
*   **Metrics:** Collect and export application metrics to Google Cloud's operations suite (formerly Stackdriver) for monitoring and alerting.
*   **Tracing:** Integrate distributed tracing to track requests across microservices, enabling performance analysis and debugging.
*   **Logging:** Centralize and enrich application logs for easier analysis and troubleshooting within Google Cloud's operations suite.
*   **Spring Boot Auto-configuration:** Leverages Spring Boot's auto-configuration capabilities to simplify the setup of observability components.
*   **Google Cloud Native Integration:** Designed to seamlessly integrate with Google Cloud services like Cloud Monitoring and Cloud Trace.

## Project Conventions
*   **Dependency Management:** Typically managed via Spring Boot starters (e.g., `spring-cloud-gcp-starter-metrics`, `spring-cloud-gcp-starter-trace`).
*   **Configuration Properties:** Observability settings are primarily configured through `application.yml` or `application.properties` using prefixes like `spring.cloud.gcp.logging.*`, `spring.cloud.gcp.trace.*`, and `spring.cloud.gcp.metrics.*`.
*   **Annotation-based Configuration:** Certain aspects might be enabled or configured using Spring annotations, though property-based configuration is more common.
*   **Log Appenders:** Custom log appenders might be configured to direct logs to Google Cloud's operations suite logging.
*   **Metric Registries:** Leverages Micrometer for metric registration and export to Cloud Monitoring.

## Common Patterns
**Enabling Logging to Cloud Logging:**
```yaml
spring:
  cloud:
    gcp:
      logging:
        enabled: true
        log-to-println: false # Set to true for local testing or if Cloud Logging is not available
        enhance-with-trace-context: true # Enrich logs with trace and span IDs
        resource-type: k8s_container # Or 'gae_app', 'cloud_run_revision', etc.
```

**Enabling Tracing with Cloud Trace:**
```yaml
spring:
  cloud:
    gcp:
      trace:
        enabled: true
        project-id: ${GOOGLE_CLOUD_PROJECT} # Or explicitly set your GCP project ID
        sampling:
          probability: 1.0 # Sample all traces for development, adjust for production
```

**Configuring Metrics Export to Cloud Monitoring:**
```yaml
spring:
  cloud:
    gcp:
      metrics:
        enabled: true
        project-id: ${GOOGLE_CLOUD_PROJECT}
        # Optional: Specify a custom registry if not using the default
        # registry: myCustomMetricRegistry
```

**Adding Custom Log Attributes (if using a custom logging configuration):**
```java
import com.google.cloud.logging.LogEntry;
import com.google.cloud.logging.LoggingOptions;
import com.google.cloud.logging.Payload;
import com.google.cloud.logging.v2.LoggingClient;
import com.google.cloud.logging.v2.LoggingServiceSettings;
import com.google.cloud.logging.v2.WriteLogEntriesRequest;
import com.google.cloud.logging.v2.WriteLogEntriesResponse;
import com.google.common.collect.ImmutableMap;
import com.google.protobuf.Timestamp;
import com.google.rpc.Status;
import com.google.api.core.ApiFuture;
import com.google.cloud.logging.v2.MetricServiceSettings;
import com.google.cloud.logging.v2.LogMetric;
import com.google.cloud.logging.v2.ListLogMetricsRequest;
import com.google.cloud.logging.v2.ListLogMetricsResponse;

// ... within a Spring component or service ...

@Service
public class MyLoggingService {

    private final LoggingClient loggingClient;

    // Assume Spring Boot auto-configures this or you manually create it
    public MyLoggingService() throws IOException {
        LoggingServiceSettings settings = LoggingServiceSettings.newBuilder().build();
        this.loggingClient = LoggingClient.create(settings);
    }

    public void sendCustomLog(String message) {
        String logName = "projects/" + System.getenv("GOOGLE_CLOUD_PROJECT") + "/logs/my-application-log";
        LogEntry logEntry = LogEntry.newBuilder()
            .setPayload(Payload.forJson(ImmutableMap.of("message", message, "customField", "customValue")))
            .setSeverity(LogEntry.Severity.INFO)
            .setTimestamp(Timestamp.newBuilder().setSeconds(System.currentTimeMillis() / 1000).setNanos((int) (System.currentTimeMillis() % 1000 * 1000000)))
            .putLabels("component", "my-service")
            .build();

        WriteLogEntriesRequest request = WriteLogEntriesRequest.newBuilder()
            .setLogName(logName)
            .addEntries(logEntry)
            .build();

        ApiFuture<WriteLogEntriesResponse> futureResponse = loggingClient.writeLogEntriesCallable().futureCall(request);
        // Handle the future response asynchronously
    }
}
```

## Guidelines
*   **Resource Type Configuration:** Always configure `spring.cloud.gcp.logging.resource-type` accurately to ensure logs are correctly categorized in Google Cloud's operations suite. Common types include `k8s_container`, `gae_app`, `cloud_run_revision`, and `gce_instance`.
*   **Trace Context Enrichment:** For effective correlation between logs and traces, enable `spring.cloud.gcp.logging.enhance-with-trace-context=true`. This automatically adds trace and span IDs to log entries.
*   **Sampling Strategy:** For tracing, carefully consider your sampling strategy in production. Sampling all traces can be expensive and overwhelming. Start with a lower probability and increase if necessary for debugging specific issues.
*   **Error Handling:** Implement robust error handling for asynchronous API calls made by the observability clients, especially for logging and tracing.
*   **Local Development:** For local development, consider setting `spring.cloud.gcp.logging.log-to-println=true` to output logs to the console instead of attempting to send them to Cloud Logging, which might not be configured locally.
*   **Project ID Management:** Ensure your GCP project ID is correctly set, either via the `GOOGLE_CLOUD_PROJECT` environment variable or explicitly in the configuration properties.
*   **Authentication:** Ensure your application is properly authenticated to Google Cloud (e.g., via service accounts or workload identity). Spring Cloud GCP handles this automatically if the environment is set up correctly.
*   **Granularity of Metrics:** When using metrics, leverage Micrometer's capabilities to create granular and meaningful metrics that can be effectively queried and alerted on in Cloud Monitoring.