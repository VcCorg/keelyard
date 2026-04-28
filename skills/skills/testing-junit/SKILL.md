---
name: testing-junit
description: >-
  JUnit 5 patterns, Mockito mocking, Spring Boot test slices, assertions.
  Use this skill when writing or modifying tests in a Java project.
---

# JUnit 5 Testing

## Test Structure

```
src/test/java/com/example/
├── controller/           # @WebMvcTest controller tests
├── service/              # Unit tests with Mockito
├── repository/           # @DataJpaTest / @DataSpannerTest
└── integration/          # @SpringBootTest full integration tests
```

## Key Patterns

### Unit Test with Mockito

```java
@ExtendWith(MockitoExtension.class)
class ResourceServiceTest {
    @Mock private ResourceRepository repository;
    @InjectMocks private ResourceService service;

    @Test
    void shouldReturnResource_whenExists() {
        when(repository.findById("id-1")).thenReturn(Optional.of(new Resource("id-1", "name")));
        ResourceDto result = service.findById("id-1");
        assertThat(result.getName()).isEqualTo("name");
        verify(repository).findById("id-1");
    }

    @Test
    void shouldThrow_whenNotFound() {
        when(repository.findById("missing")).thenReturn(Optional.empty());
        assertThrows(ResourceNotFoundException.class, () -> service.findById("missing"));
    }
}
```

### Controller Test

```java
@WebMvcTest(ResourceController.class)
class ResourceControllerTest {
    @Autowired private MockMvc mockMvc;
    @MockBean private ResourceService service;

    @Test
    void shouldReturnOk() throws Exception {
        when(service.findById("id-1")).thenReturn(new ResourceDto("id-1", "name"));
        mockMvc.perform(get("/api/v1/resources/id-1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.name").value("name"));
    }
}
```

### Integration Test

```java
@SpringBootTest
@AutoConfigureMockMvc
class ResourceIntegrationTest {
    @Autowired private MockMvc mockMvc;

    @Test
    void shouldCreateAndRetrieve() throws Exception {
        // POST create
        mockMvc.perform(post("/api/v1/resources")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"name\":\"test\"}"))
            .andExpect(status().isCreated());
    }
}
```

## Guidelines

- Name tests descriptively: `should<Expected>_when<Condition>`
- Use `@ExtendWith(MockitoExtension.class)` for unit tests
- Use `@WebMvcTest` for controller-only tests (no full context)
- Use `@SpringBootTest` sparingly (slow, loads full context)
- Prefer AssertJ (`assertThat`) over JUnit assertions
- Verify mock interactions with `verify()`
- Use `@ParameterizedTest` for data-driven tests
