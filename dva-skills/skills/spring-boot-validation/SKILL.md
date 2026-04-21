---
name: spring-boot-validation
description: >-
  Utilizing Spring Boot's built-in validation mechanisms.
  Use this skill when working with spring-boot-validation technologies.
---

# Spring Boot Validation

## Key Concepts
*   **Bean Validation API (JSR 380):** Spring Boot leverages the Bean Validation API for defining and applying validation constraints.
*   **Annotations:** Validation rules are expressed using annotations like `@NotNull`, `@NotBlank`, `@Size`, `@Email`, `@Pattern`, `@Valid`, etc., directly on model classes (DTOs, Entities).
*   **`Validator` Interface:** Spring provides a `Validator` interface and an auto-configured `ValidatorFactoryBean` that can be injected to perform manual validation.
*   **Automatic Validation in Controllers:** Spring MVC automatically validates request bodies (e.g., `@RequestBody`) annotated with `@Valid` before invoking the controller method.
*   **Custom Validators:** The ability to create custom validation constraints using `@Constraint` annotation and custom validator implementations.

## Project Conventions
*   **DTOs for Request/Response:** Validation is typically applied to Data Transfer Objects (DTOs) used for API requests and responses, not directly to JPA entities.
*   **Package Structure:** Validation annotations are usually placed directly within the model/DTO classes. Custom validator implementations might reside in a `validation` or `constraints` sub-package.
*   **Naming Conventions:** Validation annotations are applied directly to fields or getters of DTOs. Custom validator class names often end with `Validator` (e.g., `UniqueEmailValidator`).

## Common Patterns
*   **Validating Request Body:**

    ```java
    @RestController
    @RequestMapping("/api/users")
    public class UserController {

        @PostMapping
        public ResponseEntity<UserResponse> createUser(@Valid @RequestBody CreateUserRequest request) {
            // ... user creation logic
            return ResponseEntity.ok(new UserResponse(/* ... */));
        }
    }
    ```

*   **Defining Validation Constraints on DTOs:**

    ```java
    public class CreateUserRequest {

        @NotBlank(message = "Username cannot be blank")
        @Size(min = 3, max = 50, message = "Username must be between 3 and 50 characters")
        private String username;

        @Email(message = "Invalid email format")
        private String email;

        // getters and setters
    }
    ```

*   **Manual Validation:**

    ```java
    @Service
    public class UserService {

        private final Validator validator;

        public UserService(Validator validator) {
            this.validator = validator;
        }

        public void processUserData(UserData data) {
            Set<ConstraintViolation<UserData>> violations = validator.validate(data);
            if (!violations.isEmpty()) {
                throw new ValidationException(violations.iterator().next().getMessage());
            }
            // ... process valid data
        }
    }
    ```

*   **Custom Constraint Annotation:**

    ```java
    @Target({FIELD, METHOD, PARAMETER})
    @Retention(RUNTIME)
    @Constraint(validatedBy = CustomConstraintValidator.class)
    public @interface CustomConstraint {
        String message() default "Custom validation failed";
        Class<?>[] groups() default {};
        Class<? extends Payload>[] payload() default {};
    }
    ```

*   **Custom Validator Implementation:**

    ```java
    public class CustomConstraintValidator implements ConstraintValidator<CustomConstraint, String> {
        @Override
        public void initialize(CustomConstraint constraintAnnotation) {
            // initialization logic if needed
        }

        @Override
        public boolean isValid(String value, ConstraintValidatorContext context) {
            // validation logic
            return value != null && value.startsWith("prefix_");
        }
    }
    ```

## Guidelines
*   **Validate Early, Validate Often:** Implement validation at the earliest possible point, typically on incoming API requests.
*   **Use DTOs for Validation:** Apply validation constraints on DTOs that represent API request and response payloads. Avoid validating JPA entities directly at the API layer.
*   **Provide Meaningful Error Messages:** Use the `message` attribute in validation annotations or `ConstraintValidatorContext` to provide clear and helpful error messages to API consumers.
*   **Leverage `@Valid` and `@Validated`:** Use `@Valid` for validating nested objects and `@Validated` for specifying validation groups on controller methods or beans.
*   **Handle Validation Errors Gracefully:** Implement a global exception handler (`@ControllerAdvice`) to catch `MethodArgumentNotValidException` (for `@RequestBody` validation) or `ConstraintViolationException` (for manual validation) and return appropriate HTTP error responses (e.g., 400 Bad Request).
*   **Keep Validation Logic within Models/DTOs:** For simple validation, keep annotations directly on the model classes. For complex or reusable validation, consider custom constraints.
*   **Don't Re-implement Standard Logic:** Utilize the rich set of built-in validation annotations provided by the Bean Validation API before resorting to custom validators.
*   **Consider Validation Groups:** Use validation groups (`groups` attribute) to differentiate validation rules for different scenarios (e.g., creation vs. update).