---
name: java-maven
description: >-
  Maven build system, POM structure, plugin configuration.
  Use this skill when working on a project that uses Maven.
---

# Maven Build System

## Key Files

- `pom.xml` — Project Object Model (build config, dependencies, plugins)
- `.mvn/` — Maven wrapper config
- `settings.xml` — User/global Maven settings (~/.m2/settings.xml)

## Common Commands

```bash
./mvnw clean install          # Clean, compile, test, package, install
./mvnw test                   # Run tests only
./mvnw package -DskipTests    # Package without tests
./mvnw dependency:tree        # Show dependency tree
./mvnw spring-boot:run        # Run Spring Boot app
./mvnw versions:display-dependency-updates  # Check for updates
```

## POM Structure

```xml
<project>
  <groupId>com.example</groupId>
  <artifactId>my-service</artifactId>
  <version>1.0.0-SNAPSHOT</version>
  <packaging>jar</packaging>

  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.0</version>
  </parent>

  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
  </dependencies>
</project>
```

## Guidelines

- Use `./mvnw` (wrapper) instead of system `mvn`
- Manage versions in `<dependencyManagement>` or parent POM
- Use `<scope>test</scope>` for test-only dependencies
- Use profiles for environment-specific config (`-P production`)
- Check effective POM: `./mvnw help:effective-pom`
