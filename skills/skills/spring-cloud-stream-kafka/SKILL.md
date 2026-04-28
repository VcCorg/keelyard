---
name: spring-cloud-stream-kafka
description: >-
  Using Spring Cloud Stream with Kafka binders for event-driven microservices.
  Use this skill when working with spring-cloud-stream-kafka technologies.
---

# Spring Cloud Stream with Kafka

## Key Concepts
*   **Producers and Consumers:** Applications interact with Kafka topics by producing messages (producers) or consuming messages (consumers).
*   **Bindings:** Spring Cloud Stream abstracts the underlying messaging system (Kafka) through bindings, which define the connection between application code and messaging channels.
*   **Channels:** Logical names representing a topic or a group of topics within Kafka.
*   **Binder Configuration:** Kafka-specific configurations for topics, partitions, consumer groups, serialization, etc., are managed through binder properties.
*   **Event-Driven Architecture:** Facilitates building loosely coupled, asynchronous microservices that communicate via events.

## Project Conventions
*   **`application.yml` / `application.properties`:** Kafka binder configurations, including broker addresses, consumer group IDs, topic names, and serialization settings, are typically defined here.
*   **Message Interfaces:** Define `@EnableBinding` interfaces (older style) or functional bean definitions (newer style) to declare producers and consumers.
*   **Message Payload:** Standard Java objects (POJOs) are commonly used as message payloads. Serialization/deserialization is handled by the binder.
*   **Error Handling:** Implement error channels (`.errors` suffix) for handling message processing failures.

## Common Patterns
*   **Sending Messages:**
    ```java
    @Configuration
    public class ProducerConfig {

        @Bean
        public NewTopic adviceTopic() {
            return new NewTopic("advice-topic", 3, 3);
        }

        @Bean
        public Supplier<String> adviceProducer() {
            return () -> "My awesome advice: " + Math.random();
        }
    }
    ```

*   **Receiving Messages:**
    ```java
    @Configuration
    public class ConsumerConfig {

        @Bean
        public Consumer<String> adviceConsumer() {
            return message -> {
                System.out.println("Received advice: " + message);
            };
        }
    }
    ```

*   **Using `StreamBridge` for dynamic sends:**
    ```java
    @Service
    public class DynamicProducerService {

        private final StreamBridge streamBridge;

        public DynamicProducerService(StreamBridge streamBridge) {
            this.streamBridge = streamBridge;
        }

        public void sendMessage(String message) {
            streamBridge.send("output-binding-name", message);
        }
    }
    ```

*   **Error Handling with Error Channel:**
    ```java
    @Configuration
    public class ErrorHandlingConfig {

        @Bean
        public Consumer<ErrorMessage> errorMessageConsumer() {
            return errorMessage -> {
                System.err.println("Error processing message: " + errorMessage.getPayload());
                // Log error, dead-letter queue, etc.
            };
        }
    }
    ```

## Guidelines
*   **Idempotency:** Design consumers to be idempotent, as Kafka guarantees at-least-once delivery, leading to potential duplicate messages.
*   **Schema Management:** Use a schema registry (like Confluent Schema Registry) for managing Avro or Protobuf schemas to ensure compatibility between producers and consumers.
*   **Consumer Groups:** Clearly define and manage consumer group IDs to control message distribution and parallel processing.
*   **Topic Partitioning:** Strategically choose the number of partitions for your topics to balance parallelism and throughput.
*   **Serialization:** Use efficient and compatible serialization formats (e.g., JSON, Avro, Protobuf) and configure them in the binder properties.
*   **Error Handling Strategy:** Implement robust error handling by leveraging Spring Cloud Stream's error channels and defining a clear strategy for failed messages (retry, dead-lettering).
*   **Configuration Properties:** Leverage Spring Boot's externalized configuration for Kafka binder settings to manage different environments easily.
*   **Health Checks:** Integrate Spring Boot Actuator for Kafka binder health indicators to monitor connectivity and status.