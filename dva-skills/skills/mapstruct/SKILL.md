---
name: mapstruct
description: >-
  MapStruct compile-time DTO mapping — mapper interfaces, custom mappings,
  Spring integration, and annotation processor configuration.
---

# MapStruct DTO Mapping

## Basic Mapper

```java
@Mapper(componentModel = "spring")
public interface PatientMapper {

    PatientDto toDto(Patient entity);

    Patient toEntity(PatientDto dto);

    List<PatientDto> toDtoList(List<Patient> entities);
}
```

## Custom Field Mapping

```java
@Mapper(componentModel = "spring")
public interface PatientMapper {

    @Mapping(source = "firstName", target = "name")
    @Mapping(source = "dateOfBirth", target = "dob", dateFormat = "yyyy-MM-dd")
    @Mapping(target = "id", ignore = true)
    PatientDto toDto(Patient entity);

    @Mapping(source = "address.city", target = "city")   // nested source
    @Mapping(expression = "java(entity.getFullName())", target = "displayName")
    PatientSummaryDto toSummary(Patient entity);
}
```

## Using with Lombok

```java
// MapStruct + Lombok require correct annotation processor ordering
@Mapper(componentModel = "spring", builder = @Builder(disableBuilder = true))
public interface PatientMapper {
    PatientDto toDto(Patient entity);
}
```

## Maven Annotation Processor Config

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <configuration>
        <annotationProcessorPaths>
            <path>
                <groupId>org.projectlombok</groupId>
                <artifactId>lombok</artifactId>
            </path>
            <path>
                <groupId>org.projectlombok</groupId>
                <artifactId>lombok-mapstruct-binding</artifactId>
                <version>0.2.0</version>
            </path>
            <path>
                <groupId>org.mapstruct</groupId>
                <artifactId>mapstruct-processor</artifactId>
            </path>
        </annotationProcessorPaths>
        <compilerArgs>
            <arg>-Amapstruct.defaultComponentModel=spring</arg>
        </compilerArgs>
    </configuration>
</plugin>
```

## Merging / Update Mapping

```java
@Mapper(componentModel = "spring")
public interface PatientMapper {

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    void updateEntity(PatientUpdateDto dto, @MappingTarget Patient entity);
}
```

## Guidelines

- Always use `componentModel = "spring"` for Spring Boot projects
- Order annotation processors: Lombok → lombok-mapstruct-binding → MapStruct
- Use `@MappingTarget` for update/merge operations instead of creating new objects
- Prefer `@Mapping(target = "field", ignore = true)` over `unmappedTargetPolicy = IGNORE`
- Use `@AfterMapping` for complex post-processing logic
- Generated implementations are in `target/generated-sources/annotations/`
- Test mappers with `Mappers.getMapper(PatientMapper.class)` in unit tests
