---
name: spring-cloud-config
description: >-
  Spring Cloud Config Server, Eureka service discovery, and Bootstrap context
  for centralized configuration and microservice registration.
---

# Spring Cloud Config & Service Discovery

## Config Client Setup

```yaml
# bootstrap.yml (loaded before application.yml)
spring:
  application:
    name: cwow-patient-query-spanner
  cloud:
    config:
      uri: ${CONFIG_SERVER_URI:http://localhost:8888}
      fail-fast: true
      retry:
        max-attempts: 6
        initial-interval: 1000
```

## Eureka Client Setup

```yaml
eureka:
  client:
    service-url:
      defaultZone: ${EUREKA_URI:http://localhost:8761/eureka}
    fetch-registry: true
    register-with-eureka: true
  instance:
    prefer-ip-address: true
    instance-id: ${spring.application.name}:${random.value}
```

## Key Dependencies

```xml
<!-- Config Client -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-config</artifactId>
</dependency>

<!-- Bootstrap context (required for bootstrap.yml) -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-bootstrap</artifactId>
</dependency>

<!-- Eureka Discovery -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-client</artifactId>
</dependency>
```

## Service-to-Service Calls

```java
// Using service discovery name instead of hardcoded URL
@FeignClient(name = "cwow-patient-model-spanner")
public interface PatientModelClient {
    @GetMapping("/api/patients/{id}")
    PatientDto getPatient(@PathVariable String id);
}

// Or with RestTemplate + @LoadBalanced
@Bean
@LoadBalanced
public RestTemplate restTemplate() {
    return new RestTemplate();
}
// Usage: restTemplate.getForObject("http://cwow-patient-model-spanner/api/patients/{id}", ...)
```

## Configuration Profiles

- Config Server stores properties per app + profile: `/{application}/{profile}`
- Common pattern: `application.yml` (shared) + `cwow-patient-query-spanner.yml` (app-specific)
- Profiles: `default`, `dev`, `staging`, `prod`

## Refresh Configuration

```java
// Annotate beans that need config refresh
@RefreshScope
@Component
public class FeatureFlags {
    @Value("${feature.new-search:false}")
    private boolean newSearchEnabled;
}
```

## Guidelines

- Always include `spring-cloud-starter-bootstrap` for `bootstrap.yml` support
- Use `fail-fast: true` in production to prevent startup with stale config
- Prefer Eureka instance names for inter-service communication
- Use `@RefreshScope` for beans that need dynamic config updates
- Keep secrets in Config Server encrypted or use GCP Secret Manager
- Set `prefer-ip-address: true` in containerized deployments
- Use health checks to deregister unhealthy instances from Eureka
