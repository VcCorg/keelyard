---
name: java-mapstruct
description: >-
  MapStruct for efficient bean mapping in Java
  Use this skill when working with java-mapstruct technologies.
---

# Java MapStruct

## Key Concepts
* **Annotation Processor:** MapStruct is an annotation processor that generates type-safe, performant mapping code at compile time, eliminating the need for manual mapping implementations.
* **Mapper Interfaces:** Developers define abstract interfaces with mapping methods annotated with `@Mapper`. MapStruct generates concrete implementations for these interfaces.
* **Source and Target Types:** Mapping methods specify source and target object types, and MapStruct infers mapping rules based on property names and types.
* **Custom Mappings:** Developers can define custom mapping logic for complex transformations, conditional mappings, or when property names/types don't align directly.
* **Dependency Injection:** MapStruct integrates seamlessly with dependency injection frameworks like Spring, allowing generated mappers to be injected where needed.

## Project Conventions
* **Mapper Interface Location:** Typically placed in a dedicated `mapper` or `mapping` package within the project (e.g., `com.example.myapp.mapper`).
* **Mapper Interface Naming:** Conventionally named with a suffix like `Mapper`, `Converter`, or `Transformer` (e.g., `UserMapper.java`, `OrderConverter.java`).
* **Generated Implementation Location:** MapStruct generates implementations in a package derived from the mapper interface's package, usually suffixed with `.impl` (e.g., `com.example.myapp.mapper.impl.UserMapperImpl`). This package is generally not managed directly by developers.
* **Annotation Usage:** `@Mapper` annotation on the interface, with configuration options like `componentModel = "spring"` for Spring integration.
* **Mapping Method Naming:** Common patterns include `toDto(Source source)`, `toEntity(Target target)`, `map(Source source, Target target)`.

## Common Patterns
* **Simple Property Mapping:**
```java
@Mapper
public interface UserMapper {
    UserDto toDto(User user);
    User toEntity(UserDto userDto);
}
```

* **Mapping with Custom Fields:**
```java
@Mapper
public interface ProductMapper {
    @Mapping(source = "productName", target = "name")
    @Mapping(target = "createdAt", ignore = true) // Ignore a field
    ProductDto toDto(Product product);
}
```

* **Nested Object Mapping:**
```java
@Mapper
public interface OrderMapper {
    OrderDto toDto(Order order);
}
```
(Assuming `OrderDto` and `Order` have nested `AddressDto` and `Address` respectively, MapStruct handles it automatically if property names align).

* **Collection Mapping:**
```java
@Mapper
public interface ItemMapper {
    List<ItemDto> toDtoList(List<Item> items);
    Set<ItemDto> toDtoSet(Set<Item> items);
}
```

* **Mapping with Instance-Specific Methods:**
```java
@Mapper
public interface PriceMapper {
    @AfterMapping
    default void setDefaultCurrency(Price price, @MappingTarget PriceDto priceDto) {
        if (priceDto.getCurrency() == null) {
            priceDto.setCurrency("USD");
        }
    }
    PriceDto toDto(Price price);
}
```

* **Spring Component Model:**
```java
@Mapper(componentModel = "spring")
public interface ProductMapper {
    ProductDto toDto(Product product);
}
```

## Guidelines
* **Favor `@Mapping` over manual implementation:** Use `@Mapping` for simple field renames or ignored fields. Only resort to custom mapping methods for complex logic.
* **Configure `componentModel` appropriately:** Use `"spring"` or `"cdi"` for integration with relevant frameworks. If no framework is used, `"default"` is sufficient.
* **Use `@MappingTarget` for updating existing objects:** This allows for efficient updates without creating new instances.
* **Keep mapper interfaces focused:** Avoid creating monolithic mappers. Group related mappings into separate interfaces.
* **Leverage MapStruct's built-in type conversions:** It supports common conversions between primitive types, wrappers, and standard Java types.
* **Annotate for clarity and maintainability:** Use `@Mapping` to document explicit mapping rules, especially when property names or types differ significantly.
* **Test your mappers:** Although MapStruct generates code, it's crucial to test your mapping logic to ensure correctness, especially for complex scenarios.
* **Consider performance:** While MapStruct is highly performant, be mindful of overly complex mapping methods that might degrade performance.