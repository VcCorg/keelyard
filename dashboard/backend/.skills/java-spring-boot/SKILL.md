---
name: java-spring-boot
description: >-
  Spring Boot 3.x conventions, annotations, dependency injection, REST patterns.
  Use this skill when working on a Spring Boot project.
---

# Spring Boot Development

## Project Conventions

- Entry point: `@SpringBootApplication` annotated class with `main()` method
- Configuration: `application.yml` or `application.properties` in `src/main/resources/`
- Profiles: `application-{profile}.yml` activated via `spring.profiles.active`

## Package Structure

```
src/main/java/com/example/
├── Application.java          # @SpringBootApplication
├── config/                   # @Configuration classes
├── controller/               # @RestController endpoints
├── service/                  # @Service business logic
├── repository/               # @Repository data access
├── model/                    # Entity / DTO classes
├── dto/                      # Request/Response DTOs
├── exception/                # Custom exceptions + @ControllerAdvice
└── util/                     # Utility classes
```

## Key Annotations

| Annotation | Purpose |
|------------|---------|
| `@RestController` | REST endpoint class |
| `@Service` | Business logic bean |
| `@Repository` | Data access bean |
| `@Configuration` | Config class |
| `@Autowired` / constructor injection | Dependency injection (prefer constructor) |
| `@Value("${prop}")` | Inject config property |
| `@Transactional` | Transaction boundary |
| `@Valid` / `@Validated` | Request validation |

## REST Endpoint Pattern

```java
@RestController
@RequestMapping("/api/v1/resources")
public class ResourceController {
    private final ResourceService service;

    public ResourceController(ResourceService service) {
        this.service = service;
    }

    @GetMapping("/{id}")
    public ResponseEntity<ResourceDto> getById(@PathVariable String id) {
        return ResponseEntity.ok(service.findById(id));
    }

    @PostMapping
    public ResponseEntity<ResourceDto> create(@Valid @RequestBody CreateRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(service.create(request));
    }
}
```

## Error Handling

```java
@ControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(ResourceNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(new ErrorResponse(ex.getMessage()));
    }
}
```

## Guidelines

- Prefer constructor injection over field `@Autowired`
- Use `ResponseEntity<>` for explicit HTTP status control
- Validate request DTOs with `@Valid` + Jakarta Bean Validation annotations
- Use `@Transactional` at service layer, not controller
- Keep controllers thin — delegate to services
- Use `@ConfigurationProperties` for complex config binding
- Write integration tests with `@SpringBootTest` and test slices (`@WebMvcTest`, `@DataJpaTest`)
