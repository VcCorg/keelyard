---
name: spring-cloud-eureka-client
description: >-
  Integration with Spring Cloud Eureka for service discovery.
  Use this skill when working with spring-cloud-eureka-client technologies.
---

# Spring Cloud Eureka Client

## Key Concepts
*   **Service Registration:** The Eureka client registers itself with the Eureka server upon startup, providing its service name, IP address, port, and health check information.
*   **Service Discovery:** Other Eureka clients can query the Eureka server to discover the network locations (IP addresses and ports) of registered services.
*   **Health Checks:** The Eureka client periodically sends heartbeats to the Eureka server to indicate it's alive. If heartbeats stop, the server marks the instance as "out of service."
*   **Client-Side Load Balancing:** While Eureka primarily provides discovery, it often works in conjunction with client-side load balancing mechanisms (like Spring Cloud LoadBalancer) to distribute requests among multiple instances of a discovered service.
*   **Configuration:** Eureka client configuration is typically managed via `application.properties` or `application.yml`, specifying the Eureka server URL and other registration details.

## Project Conventions
*   **Dependency Inclusion:** The presence of `org.springframework.cloud:spring-cloud-starter-netflix-eureka-client` in `pom.xml` or `build.gradle` is the primary indicator.
*   **`@EnableEurekaClient` or `@EnableDiscoveryClient`:** These annotations on a Spring Boot application's main class are used to enable Eureka client functionality. `@EnableEurekaClient` is specific to Eureka, while `@EnableDiscoveryClient` is more general and can be used with other discovery services.
*   **Configuration File:** Eureka client settings are usually found in `src/main/resources/application.properties` or `src/main/resources/application.yml`.
*   **Service Naming:** Services are typically identified by a logical name (e.g., `spring.application.name=my-service`) which is used for registration and discovery.

## Common Patterns
**1. Basic Service Registration and Discovery**

```java
@SpringBootApplication
@EnableEurekaClient // or @EnableDiscoveryClient
public class MyServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyServiceApplication.class, args);
    }
}
```

```properties
# application.properties
spring.application.name=my-product-service
eureka.client.service-url.defaultZone=http://localhost:8761/eureka/
```

**2. Accessing a Discovered Service (using Spring Cloud LoadBalancer)**

```java
@Service
public class ProductService {

    private final RestTemplate restTemplate;
    private final LoadBalancerClient loadBalancer;

    public ProductService(RestTemplate restTemplate, LoadBalancerClient loadBalancer) {
        this.restTemplate = restTemplate;
        this.loadBalancer = loadBalancer;
    }

    public String getProductDetails(String productId) {
        // Using LoadBalancerClient to find and access the 'my-inventory-service'
        ServiceInstance instance = loadBalancer.choose("my-inventory-service");
        String baseUrl = instance.getUri().toString();

        // Construct the URL and make the request
        return restTemplate.getForObject(baseUrl + "/products/" + productId, String.class);
    }
}
```

```java
// Configuration for RestTemplate to be used with LoadBalancer
@Configuration
public class RestTemplateConfig {

    @Bean
    @LoadBalanced // Essential for client-side load balancing
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        return builder.build();
    }
}
```

**3. Customizing Registration Properties**

```properties
# application.properties
spring.application.name=my-user-service
eureka.client.service-url.defaultZone=http://eureka-server:8761/eureka/
eureka.instance.prefer-ip-address=true
eureka.instance.hostname=my-user-service-instance-1.my-domain.com
eureka.instance.instance-id=${spring.application.name}:${spring.application.instance_id:${random.value}}
```

## Guidelines
*   **Prefer `@EnableDiscoveryClient`:** While `@EnableEurekaClient` works, `@EnableDiscoveryClient` is more general and allows for easier migration to other discovery services if needed.
*   **Secure Eureka Server:** Always run your Eureka server with security enabled, especially in production environments.
*   **Multiple Eureka Servers:** Configure clients to connect to multiple Eureka servers for high availability. The `defaultZone` property can be a comma-separated list of URLs.
*   **Health Check Endpoint:** Ensure your microservices expose a `/health` endpoint that Eureka can ping to monitor their status. Spring Boot Actuator provides this out-of-the-box.
*   **IP Address vs. Hostname:** Decide whether to register using IP addresses (`prefer-ip-address=true`) or hostnames, and ensure your network can resolve them correctly.
*   **Instance ID Uniqueness:** Ensure each registered instance has a unique `instance-id`. The default format (`${spring.application.name}:${spring.application.instance_id:${random.value}}`) is generally sufficient.
*   **Lease Renewal Interval:** Configure `eureka.instance.lease-renewal-interval-in-seconds` and `eureka.instance.lease-expiration-duration-in-seconds` carefully to balance responsiveness to failures with network traffic.
*   **Use `spring-cloud-starter-loadbalancer` for Discovery Client:** When using Spring Cloud 2020.0.0 (Spring Boot 2.4) or later, `spring-cloud-starter-netflix-eureka-client` does not include client-side load balancing by default. You should explicitly add `spring-cloud-starter-loadbalancer` and use `@LoadBalanced` with `RestTemplate` or `WebClient` for effective service discovery and consumption.