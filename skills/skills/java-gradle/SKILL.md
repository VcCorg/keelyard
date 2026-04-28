---
name: java-gradle
description: >-
  Gradle build system patterns, task configuration, dependency management.
  Use this skill when working on a project that uses Gradle.
---

# Gradle Build System

## Key Files

- `build.gradle` or `build.gradle.kts` — Build script (Groovy or Kotlin DSL)
- `settings.gradle` or `settings.gradle.kts` — Multi-project settings
- `gradle.properties` — Build properties
- `gradle/wrapper/gradle-wrapper.properties` — Wrapper version

## Common Commands

```bash
./gradlew build              # Compile + test + assemble
./gradlew test               # Run tests only
./gradlew clean              # Clean build outputs
./gradlew bootRun            # Run Spring Boot app
./gradlew dependencies       # Show dependency tree
./gradlew tasks              # List all available tasks
./gradlew build -x test      # Build without tests
```

## Dependency Declaration (Kotlin DSL)

```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("com.google.cloud:google-cloud-spanner")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.junit.jupiter:junit-jupiter")
}
```

## Guidelines

- Use `./gradlew` (wrapper) instead of system `gradle`
- Prefer Kotlin DSL (`*.kts`) for type-safe build scripts
- Use `implementation` (not `compile`) for dependencies
- Use `api` only when exposing transitive dependencies to consumers
- Lock dependency versions with a version catalog (`libs.versions.toml`)
- Use `buildSrc/` or convention plugins for shared build logic
