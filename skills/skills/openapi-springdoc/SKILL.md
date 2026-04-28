---
name: openapi-springdoc
description: >-
  Springdoc OpenAPI 3 documentation — Swagger UI, API annotations,
  schema customization, and Spring Boot auto-configuration.
---

# OpenAPI with Springdoc

## Auto-Configuration

Springdoc auto-generates OpenAPI 3.0 docs from Spring MVC controllers.

```yaml
springdoc:
  api-docs:
    path: /v3/api-docs
  swagger-ui:
    path: /swagger-ui.html
    tags-sorter: alpha
    operations-sorter: alpha
  show-actuator: false
  packages-to-scan: com.example.cwow.patient
```

- **Swagger UI**: `http://localhost:8080/swagger-ui.html`
- **OpenAPI JSON**: `http://localhost:8080/v3/api-docs`

## Controller Annotations

```java
@RestController
@RequestMapping("/api/patients")
@Tag(name = "Patients", description = "Patient management operations")
public class PatientController {

    @Operation(
        summary = "Get patient by ID",
        description = "Returns a single patient record"
    )
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "Patient found"),
        @ApiResponse(responseCode = "404", description = "Patient not found")
    })
    @GetMapping("/{id}")
    public PatientDto getPatient(
        @Parameter(description = "Patient ID", example = "12345")
        @PathVariable String id) {
        return patientService.findById(id);
    }

    @Operation(summary = "Search patients")
    @GetMapping
    public Page<PatientDto> search(
        @Parameter(description = "Patient name filter")
        @RequestParam(required = false) String name,
        @Parameter(description = "Page number") @RequestParam(defaultValue = "0") int page,
        @Parameter(description = "Page size") @RequestParam(defaultValue = "20") int size) {
        return patientService.search(name, page, size);
    }
}
```

## Schema Annotations

```java
@Schema(description = "Patient data transfer object")
public class PatientDto {
    @Schema(description = "Unique patient ID", example = "12345")
    private String patientId;

    @Schema(description = "Patient full name", example = "John Doe")
    private String name;

    @Schema(description = "Patient status", allowableValues = {"ACTIVE", "INACTIVE"})
    private String status;
}
```

## Security in Docs

```java
@Configuration
public class OpenApiConfig {
    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
            .info(new Info()
                .title("CWOW Patient API")
                .version("1.0")
                .description("Patient domain REST API"))
            .addSecurityItem(new SecurityRequirement().addList("bearer-jwt"))
            .components(new Components()
                .addSecuritySchemes("bearer-jwt",
                    new SecurityScheme()
                        .type(SecurityScheme.Type.HTTP)
                        .scheme("bearer")
                        .bearerFormat("JWT")));
    }
}
```

## Guidelines

- Springdoc auto-discovers `@RestController` endpoints — minimal config needed
- Use `@Tag` on controllers and `@Operation` on methods for documentation
- Use `@Schema` on DTOs for field descriptions and examples
- Group APIs with `springdoc.group-configs` for multi-module projects
- Hide internal endpoints with `@Hidden` annotation
- Use `@Parameter(hidden = true)` for injected parameters (e.g., auth)
- Customize via `OpenApiCustomizer` beans for global modifications
