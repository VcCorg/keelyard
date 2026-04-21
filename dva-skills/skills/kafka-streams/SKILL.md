---
name: kafka-streams
description: >-
  Spring Cloud Stream with Kafka binder — event-driven messaging patterns,
  consumer/producer configuration, and stream processing.
---

# Kafka & Spring Cloud Stream

## Architecture

- **Spring Cloud Stream** abstracts messaging middleware behind Binder API
- **Kafka Binder** connects Spring Cloud Stream to Apache Kafka
- Functions (`java.util.function.Consumer`, `Supplier`, `Function`) replace legacy `@StreamListener`

## Configuration

```yaml
spring:
  cloud:
    stream:
      bindings:
        input-in-0:
          destination: patient-events
          group: ${spring.application.name}
          content-type: application/json
        output-out-0:
          destination: patient-notifications
          content-type: application/json
      kafka:
        binder:
          brokers: ${KAFKA_BROKERS:localhost:9092}
          auto-create-topics: false
        bindings:
          input-in-0:
            consumer:
              auto-offset-reset: earliest
              enable-dlq: true
              dlq-name: patient-events.dlq
```

## Consumer Pattern

```java
@Configuration
public class EventConsumerConfig {

    @Bean
    public Consumer<Message<PatientEvent>> input() {
        return message -> {
            PatientEvent event = message.getPayload();
            log.info("Received event: type={}, id={}", event.getType(), event.getId());
            // Process event
        };
    }
}
```

## Producer Pattern

```java
@Component
@RequiredArgsConstructor
public class EventPublisher {

    private final StreamBridge streamBridge;

    public void publish(PatientEvent event) {
        streamBridge.send("output-out-0", MessageBuilder
            .withPayload(event)
            .setHeader("eventType", event.getType())
            .build());
    }
}
```

## Functional Processor (transform)

```java
@Bean
public Function<PatientEvent, PatientNotification> process() {
    return event -> new PatientNotification(event.getPatientId(), event.getType());
}
```

## Error Handling

- Enable DLQ (Dead Letter Queue) for failed messages
- Use `@ServiceActivator(inputChannel = "error")` for global error handling
- Configure retry via `spring.cloud.stream.bindings.<name>.consumer.max-attempts`

## Guidelines

- Use functional programming model (`Consumer`, `Supplier`, `Function`) over `@StreamListener`
- Always define consumer groups to prevent duplicate processing
- Enable DLQ for production consumers
- Use `content-type: application/json` and let Spring handle serialization
- Avoid blocking operations in consumers — offload to async threads if needed
- Use message headers for routing and metadata (event type, correlation ID)
- Test with `spring-cloud-stream-test-binder` for unit tests
