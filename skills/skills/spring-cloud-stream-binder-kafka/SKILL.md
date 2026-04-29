---
name: spring-cloud-stream-binder-kafka
description: >-
  Spring Cloud Stream Kafka Binder for Kafka integration
  Use this skill when working with spring-cloud-stream-binder-kafka technologies.
---

# Spring Cloud Stream Kafka Binder

## Key Concepts
*   **Producers and Consumers:** Applications interact with Kafka through `Source` (producer) and `Sink` (consumer) interfaces, abstracting away direct Kafka producer/consumer API details.
*   **Message Channels:** Spring Cloud Stream utilizes `MessageChannel` interfaces (e.g., `FluxMessageChannel`, `Queue`) to represent streams of data, enabling loose coupling between application logic and the underlying messaging system.
*   **Binder Abstraction:** The Kafka binder translates Spring Cloud Stream's abstractions into Kafka-specific operations, managing connections, topics, partitions, and serialization.
*   **Binding Configuration:** Properties defined in `application.yml` (or `.properties`) are used to configure binder behavior, including broker addresses, topic names, group IDs, serialization, and error handling.
*   **Event-Driven Microservices:** Facilitates building event-driven microservices by providing a standardized way to produce and consume messages from Kafka.

## Project Conventions
*   **Dependency Management:** Typically included via `spring-cloud-starter-stream-kafka`.
*   **Configuration Properties:** Binder settings are managed under `spring.cloud.stream.kafka.*` and `spring.cloud.stream.bindings.<channelName>.*` prefixes.
*   **Channel Naming:** Logical channel names (e.g., `order-events`, `user-updates`) are used in application code and mapped to Kafka topics via configuration.
*   **Consumer Group IDs:** Explicitly defined or derived from application properties to manage Kafka consumer group behavior.
*   **Serialization:** Default to `java.serialization` or configure explicit serializers/deserializers (e.g., JSON, Avro) using `spring.cloud.stream.kafka.binder.deserialization.key/value` and `serialization.key/value`.

## Common Patterns
**Producing Messages:**

```java
import org.springframework.cloud.stream.function.StreamBridge;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Component;

@Component
public class MyProducer {

    private final StreamBridge streamBridge;

    public MyProducer(StreamBridge streamBridge) {
        this.streamBridge = streamBridge;
    }

    public void sendOrderCreatedEvent(OrderCreatedEvent event) {
        streamBridge.send("order-created-out", MessageBuilder.withPayload(event).build());
    }
}
```

**Consuming Messages:**

```java
import org.springframework.context.annotation.Bean;
import org.springframework.stereotype.Component;
import java.util.function.Consumer;

@Component
public class OrderConsumer {

    @Bean
    public Consumer<OrderPlacedEvent> orderPlacedListener() {
        return event -> {
            System.out.println("Received order placed event: " + event.getOrderId());
            // Process the event
        };
    }
}
```

**Configuring Bindings:**

```yaml
spring:
  cloud:
    stream:
      bindings:
        order-created-out:
          destination: orders
          content-type: application/json
        orderPlacedListener-in-0: # Default name derived from function name
          destination: orders
          group: order-processor-group
          concurrency: 3
          partitioned: true
      kafka:
        binder:
          brokers:
            - kafka-broker1:9092
            - kafka-broker2:9092
          deserialization:
            key: org.apache.kafka.common.serialization.StringDeserializer
            value: com.example.MyCustomDeserializer
          configuration:
            auto-offset-reset: earliest
```

## Guidelines
*   Use `StreamBridge` for imperative outbound message sending when not using functional programming model directly.
*   Leverage Spring Cloud Stream's functional programming model (`Supplier`, `Consumer`, `Function`) for declarative message processing.
*   Explicitly configure `content-type` for bindings to ensure correct serialization and deserialization.
*   Define explicit `group` IDs for consumers to ensure proper Kafka consumer group management and scalability.
*   Set `concurrency` for consumer bindings to control the number of parallel message processing instances.
*   Utilize `partitioned: true` when the downstream Kafka topic is partitioned and you want the binder to respect partition keys.
*   Implement robust error handling strategies (e.g., dead-letter queues, retry mechanisms) at the binder or application level.
*   Choose appropriate serialization formats (JSON, Avro, Protobuf) based on performance, schema evolution, and interoperability needs.