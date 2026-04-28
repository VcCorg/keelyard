---
name: spring-boot-devtools
description: >-
  Spring Boot DevTools for development-time features
  Use this skill when working with spring-boot-devtools technologies.
---

# Spring Boot DevTools

## Key Concepts
*   **Automatic Restart:** DevTools automatically restarts the application context when classpath changes are detected, speeding up the development feedback loop.
*   **LiveReload:** DevTools integrates with LiveReload to automatically trigger browser refreshes when application changes are made.
*   **Remote Application Restart:** DevTools can be configured to restart remote applications when changes are pushed to a remote repository.
*   **Property Defaults:** DevTools provides sensible defaults for development-time configurations, such as disabling template caching.
*   **Customizable Triggering:** Developers can fine-tune which file changes trigger restarts or LiveReload events.

## Project Conventions
*   The `spring-boot-devtools` dependency is typically included in the `dependencies` section of a Maven `pom.xml` or Gradle `build.gradle` file.
*   DevTools features are automatically enabled when the dependency is present and the application is run in a development environment.
*   Configuration for DevTools, such as remote restart properties, often resides in `application.properties` or `application.yml`.
*   For LiveReload, a compatible browser extension is usually required.

## Common Patterns
**Dependency Inclusion (Maven):**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-devtools</artifactId>
    <scope>runtime</scope>
    <optional>true</optional>
</dependency>
```

**Dependency Inclusion (Gradle):**
```gradle
developmentOnly 'org.springframework.boot:spring-boot-devtools'
```

**Disabling Cache (Example - often handled by DevTools defaults):**
```yaml
spring:
  thymeleaf:
    cache: false
```

**Configuring Remote Restart (Example):**
```properties
spring.devtools.remote.restart.enabled=true
spring.devtools.remote.secret=my-secret-key
```

## Guidelines
*   Always ensure `spring-boot-devtools` is marked with `<scope>runtime</scope>` and `<optional>true</optional>` in Maven (or `developmentOnly` in Gradle) to prevent it from being included in production builds.
*   Understand that DevTools adds overhead; disable it for performance-sensitive testing or production deployments.
*   Leverage automatic restarts for rapid iteration on code changes.
*   Familiarize yourself with the LiveReload integration for front-end development workflows.
*   Configure remote restart carefully, especially in shared development environments, to avoid unintended application restarts on other developers' machines.
*   Be aware of potential issues with certain IDE configurations or build tools that might interfere with DevTools' classpath scanning.
*   Use DevTools to experiment with property defaults and understand how they differ from production settings.
*   For advanced scenarios, explore DevTools' properties for fine-grained control over restart behavior and remote execution.