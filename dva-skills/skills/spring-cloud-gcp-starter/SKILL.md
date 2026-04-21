---
name: spring-cloud-gcp-starter
description: >-
  Spring Cloud GCP Starter for Google Cloud integration
  Use this skill when working with spring-cloud-gcp-starter technologies.
---

# Spring Cloud GCP Starter

## Key Concepts
*   **Auto-configuration:** Leverages Spring Boot's auto-configuration to automatically set up beans for various Google Cloud services based on presence and configuration.
*   **Service Integration:** Provides starters for integrating with core GCP services like Pub/Sub, Storage, Datastore, Spanner, Trace, Logging, and more.
*   **Spring Cloud Contracts:** Extends Spring Cloud patterns to GCP, allowing for familiar paradigms like distributed tracing and configuration management.
*   **Credentials Management:** Handles authentication and authorization to Google Cloud services, often via application default credentials or explicit service account key configurations.
*   **Environment Management:** Adapts Spring Boot application properties to map to GCP-specific configurations.

## Project Conventions
*   **Dependency Management:** Primarily declared via `com.google.cloud:spring-cloud-gcp-starter-[service]` in `pom.xml` (Maven) or `build.gradle` (Gradle).
*   **Configuration:** GCP-specific settings are typically defined in `application.properties` or `application.yml` using `spring.cloud.gcp.*` prefixes.
*   **Service Beans:** Auto-configured beans for GCP services are named following Spring conventions (e.g., `pubSubTemplate`, `storage`, `datastore`).
*   **Data Access:** For databases like Cloud Spanner and Datastore, integration with Spring Data is common (e.g., `spring-cloud-gcp-data-spanner`, `spring-cloud-gcp-data-datastore`).

## Common Patterns
### Publishing to Cloud Pub/Sub
```java
import com.google.cloud.spring.pubsub.core.PubSubTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class PubSubPublisher {

    private final PubSubTemplate pubSubTemplate;
    private static final String TOPIC_NAME = "my-topic";

    @Autowired
    public PubSubPublisher(PubSubTemplate pubSubTemplate) {
        this.pubSubTemplate = pubSubTemplate;
    }

    public void publishMessage(String message) {
        pubSubTemplate.publish(TOPIC_NAME, message.getBytes());
    }
}
```

### Storing Objects in Cloud Storage
```java
import com.google.cloud.spring.storage.GoogleStorageAccessor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.io.InputStream;

@Service
public class StorageService {

    private final GoogleStorageAccessor googleStorageAccessor;
    private static final String BUCKET_NAME = "my-bucket";

    @Autowired
    public StorageService(GoogleStorageAccessor googleStorageAccessor) {
        this.googleStorageAccessor = googleStorageAccessor;
    }

    public void uploadFile(String blobName, InputStream inputStream) {
        googleStorageAccessor.writeToBucket(BUCKET_NAME, blobName, inputStream);
    }

    public InputStream downloadFile(String blobName) {
        return googleStorageAccessor.readFromBucket(BUCKET_NAME, blobName);
    }
}
```

### Integrating with Cloud Trace
Spring Cloud GCP automatically configures Zipkin or other compatible tracing systems when the `spring-cloud-gcp-starter-trace` dependency is present. Requests to GCP services will be automatically instrumented.

## Guidelines
*   **Explicit Configuration:** While auto-configuration is convenient, explicitly define critical GCP configurations (like project ID, region, and credentials) in your `application.properties` or `application.yml` for clarity and maintainability.
*   **Service-Specific Starters:** Use the most granular starter for the specific GCP service you need (e.g., `spring-cloud-gcp-starter-pubsub`, `spring-cloud-gcp-starter-storage`). Avoid using a broad starter if a specific one suffices.
*   **Credentials Best Practices:** Prefer using Application Default Credentials (ADC) by setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable or running on GCP infrastructure. Avoid hardcoding service account keys in code or configuration files.
*   **Error Handling:** Implement robust error handling for interactions with GCP services, as network issues, service limits, or invalid requests can occur.
*   **Idempotency:** Design your application to handle retries and potential duplicate messages gracefully, especially when using asynchronous messaging services like Pub/Sub.
*   **Performance Tuning:** Be mindful of connection pooling, batching operations (where available), and appropriate resource allocation for high-throughput scenarios.
*   **Security:** Ensure your application's service account has the minimum necessary permissions required for its operations.
*   **Testing:** Utilize Spring Boot's testing capabilities and mock GCP services (e.g., using `spring-cloud-gcp-test` or local emulators) for effective unit and integration testing.