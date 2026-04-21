---
name: resilience4j
description: >-
  Resilience4j circuit breaker, retry, rate limiter, and timeout patterns
  for fault-tolerant Spring Boot microservices.
---

# Resilience4j — Fault Tolerance

## Configuration

```yaml
resilience4j:
  circuitbreaker:
    instances:
      patientService:
        sliding-window-size: 10
        failure-rate-threshold: 50
        wait-duration-in-open-state: 10s
        permitted-number-of-calls-in-half-open-state: 3
        slow-call-rate-threshold: 80
        slow-call-duration-threshold: 2s
  retry:
    instances:
      patientService:
        max-attempts: 3
        wait-duration: 500ms
        exponential-backoff-multiplier: 2
        retry-exceptions:
          - java.io.IOException
          - java.net.SocketTimeoutException
  timelimiter:
    instances:
      patientService:
        timeout-duration: 5s
        cancel-running-future: true
```

## Circuit Breaker

```java
@Service
public class PatientService {

    @CircuitBreaker(name = "patientService", fallbackMethod = "fallback")
    public PatientDto getPatient(String id) {
        return restTemplate.getForObject(
            "http://patient-model-service/api/patients/{id}", PatientDto.class, id);
    }

    private PatientDto fallback(String id, Throwable t) {
        log.warn("Circuit breaker fallback for patient {}: {}", id, t.getMessage());
        return PatientDto.builder().patientId(id).name("Unavailable").build();
    }
}
```

## Retry

```java
@Retry(name = "patientService", fallbackMethod = "retryFallback")
public PatientDto getPatientWithRetry(String id) {
    return externalClient.fetchPatient(id);
}
```

## Rate Limiter

```yaml
resilience4j:
  ratelimiter:
    instances:
      externalApi:
        limit-for-period: 100
        limit-refresh-period: 1s
        timeout-duration: 0s
```

```java
@RateLimiter(name = "externalApi")
public ResponseEntity<Data> callExternalApi(String request) {
    return restTemplate.postForEntity(externalUrl, request, Data.class);
}
```

## Combining Patterns

```java
// Order matters: Retry → CircuitBreaker → RateLimiter → TimeLimiter
@CircuitBreaker(name = "patientService")
@Retry(name = "patientService")
@TimeLimiter(name = "patientService")
public CompletableFuture<PatientDto> getPatientResilent(String id) {
    return CompletableFuture.supplyAsync(() -> externalClient.fetchPatient(id));
}
```

## Monitoring

```yaml
# Expose circuit breaker health in Actuator
management:
  health:
    circuitbreakers:
      enabled: true
  endpoints:
    web:
      exposure:
        include: health, circuitbreakers, metrics
```

## Guidelines

- Define fallback methods with the same signature + `Throwable` parameter
- Use circuit breakers for external service calls (other microservices, APIs)
- Use retry for transient failures (network timeouts, connection resets)
- Set realistic timeout durations based on SLA requirements
- Monitor circuit breaker state via Actuator `/actuator/circuitbreakers`
- Annotation order determines execution order — outermost executes first
- Prefer `CompletableFuture` return type when using `@TimeLimiter`
