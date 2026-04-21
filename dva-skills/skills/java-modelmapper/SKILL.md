---
name: java-modelmapper
description: >-
  Using ModelMapper for object-to-object mapping in Java applications.
  Use this skill when working with java-modelmapper technologies.
---

# ModelMapper

## Key Concepts
*   **Object-to-Object Mapping:** Automating the process of copying properties from a source object to a destination object, especially between different class types like entities and DTOs.
*   **Convention Over Configuration:** ModelMapper attempts to map properties based on naming conventions (e.g., `userId` to `userId`).
*   **Type Mapping:** Explicitly defining how properties of a specific type should be mapped between source and destination.
*   **Property Mapping:** Specifying how individual properties should be mapped, including renaming, conditional mapping, and skipping.
*   **Custom Converters/Providers:** Extending ModelMapper to handle complex or custom mapping logic not covered by default conventions.

## Project Conventions
*   **ModelMapper Instance:** Typically, a single `ModelMapper` instance is configured and reused throughout the application, often as a Spring Bean.
*   **Mapping Configuration:** Configuration logic is often placed within a dedicated configuration class, annotated with `@Configuration`, and the `ModelMapper` bean is defined there.
*   **DTO Packages:** Data Transfer Objects (DTOs) are usually located in separate packages (e.g., `com.example.dto`) distinct from entity classes.
*   **Mapper Classes:** While not strictly necessary, some projects might have dedicated "Mapper" classes (e.g., `UserMapper.java`) that encapsulate `ModelMapper` operations for specific entities.

## Common Patterns
**Basic Mapping:**

```java
// Source Object (e.g., Entity)
class UserEntity {
    private Long id;
    private String firstName;
    private String lastName;
    // getters and setters
}

// Destination Object (e.g., DTO)
class UserDto {
    private Long userId;
    private String fullName;
    // getters and setters
}

// Configuration
@Configuration
public class MapperConfig {
    @Bean
    public ModelMapper modelMapper() {
        ModelMapper modelMapper = new ModelMapper();
        // Add custom mappings here if needed
        return modelMapper;
    }
}

// Usage (e.g., in a Service)
@Service
public class UserService {
    private final ModelMapper modelMapper;

    public UserService(ModelMapper modelMapper) {
        this.modelMapper = modelMapper;
    }

    public UserDto mapToDto(UserEntity userEntity) {
        return modelMapper.map(userEntity, UserDto.class);
    }
}
```

**Custom Property Mapping:**

```java
// In ModelMapper configuration
modelMapper.createTypeMap(UserEntity.class, UserDto.class)
           .addMapping(UserEntity::getFirstName, UserDto::setFirstName) // Explicitly map firstName
           .addMapping(UserEntity::getLastName, UserDto::setLastName)   // Explicitly map lastName
           .addMapping(UserEntity::getId, UserDto::setUserId);          // Rename userId
```

**Custom Type Mapping (e.g., Date to String):**

```java
// In ModelMapper configuration
modelMapper.addConverter(new Converter<Date, String>() {
    public String convert(MappingContext<Date, String> context) {
        return context.getSource() == null ? null : new SimpleDateFormat("yyyy-MM-dd").format(context.getSource());
    }
});
```

**Skipping Properties:**

```java
// In ModelMapper configuration
modelMapper.createTypeMap(SourceObject.class, DestinationObject.class)
           .addMappings(mapper -> mapper.skip(DestinationObject::setUnwantedProperty));
```

## Guidelines
*   **Instantiate Once:** Configure and reuse a single `ModelMapper` instance to avoid performance overhead.
*   **Prefer Conventions:** Leverage ModelMapper's convention-based mapping as much as possible. Explicit mappings add boilerplate and can be harder to maintain.
*   **Use TypeMap for Complexities:** For property renaming, conditional mapping, or complex transformations, use `createTypeMap`.
*   **Consider `addMappings`:** Use `addMappings` for defining multiple property mappings or skips for a given type map.
*   **Custom Converters for Specific Types:** For mapping complex data types or custom formatting (like dates), implement `Converter` or `Provider`.
*   **Avoid Deep Nesting:** Be cautious with deeply nested objects, as mapping can become complex and error-prone. Consider flattening or breaking down mappings.
*   **Test Mappings:** Thoroughly test your mappings, especially custom ones, to ensure data integrity.
*   **Keep Mappings Focused:** Define mappings relevant to the specific object transformations you need. Avoid over-configuring a single `ModelMapper` instance with mappings for every possible class.