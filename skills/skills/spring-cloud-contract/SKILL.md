---
name: spring-cloud-contract
description: >-
  Spring Cloud Contract testing — consumer-driven contracts, stub generation,
  contract verifier, and stub runner for integration testing.
---

# Spring Cloud Contract Testing

## Overview

- **Producer side**: Defines contracts, generates tests and stubs
- **Consumer side**: Uses stub runner to test against generated stubs
- Contracts define expected request/response pairs between services

## Contract DSL (Groovy)

```groovy
// src/test/resources/contracts/patient/getPatient.groovy
Contract.make {
    description "should return patient by ID"
    request {
        method GET()
        url "/api/patients/12345"
        headers {
            contentType applicationJson()
        }
    }
    response {
        status 200
        headers {
            contentType applicationJson()
        }
        body([
            patientId: "12345",
            name: "John Doe",
            status: "ACTIVE"
        ])
    }
}
```

## Producer — Contract Verifier

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-contract-verifier</artifactId>
    <scope>test</scope>
</dependency>
```

```java
// Base test class for generated contract tests
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
public abstract class ContractVerifierBase {

    @Autowired
    private PatientController patientController;

    @BeforeEach
    void setup() {
        RestAssuredMockMvc.standaloneSetup(patientController);
    }
}
```

## Consumer — Stub Runner

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-contract-stub-runner</artifactId>
    <scope>test</scope>
</dependency>
```

```java
@SpringBootTest
@AutoConfigureStubRunner(
    ids = "com.example.cwow.patient:cwow-patient-command-spanner:+:stubs:8080",
    stubsMode = StubRunnerProperties.StubsMode.LOCAL
)
class PatientClientTest {

    @Test
    void shouldGetPatient() {
        // Stub server running on port 8080 with contract-defined responses
        ResponseEntity<PatientDto> response = restTemplate
            .getForEntity("http://localhost:8080/api/patients/12345", PatientDto.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().getName()).isEqualTo("John Doe");
    }
}
```

## Guidelines

- Place contracts in `src/test/resources/contracts/` on the producer side
- Use `stubsMode = CLASSPATH` for CI builds, `LOCAL` for development
- Contract base class name must match directory structure by convention
- Publish stubs to Artifactory: `mvn clean install -DskipTests=false`
- Consumer tests verify behavior against stubs, not live services
- Keep contracts in sync when API changes — update producer first
- Use `bodyMatchers` for flexible assertions (regex, type checking)
