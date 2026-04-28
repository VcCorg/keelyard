---
name: java-jackson
description: >-
  Jackson library for JSON processing in Java
  Use this skill when working with java-jackson technologies.
---

# Jackson for Java JSON Processing

## Key Concepts
*   **`ObjectMapper`**: The central class for performing JSON serialization and deserialization. It's thread-safe and can be reused.
*   **Serialization**: Converting Java objects to JSON strings.
*   **Deserialization**: Converting JSON strings to Java objects.
*   **Annotations**: Jackson uses annotations (e.g., `@JsonProperty`, `@JsonIgnore`, `@JsonInclude`) to control the serialization/deserialization process.
*   **Modules**: Extensible components that add support for custom types or features (e.g., `jackson-datatype-jsr310` for Java 8 Date and Time API).

## Project Conventions
*   **Dependency Management**: Typically managed via Maven (`pom.xml`) or Gradle (`build.gradle`). Common dependencies include `jackson-core`, `jackson-databind`, and `jackson-annotations`.
*   **POJOs/Beans**: JSON is usually mapped to Plain Old Java Objects (POJOs) or Java Beans with getters and setters.
*   **Configuration**: `ObjectMapper` instances are often configured once and reused across the application for efficiency and consistency. Common configurations involve setting date formats, ignoring nulls, or enabling specific features.

## Common Patterns
**Serialization of a Java Object to JSON:**

```java
import com.fasterxml.jackson.databind.ObjectMapper;

public class User {
    private String name;
    private int age;

    // Getters and Setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public int getAge() { return age; }
    public void setAge(int age) { this.age = age; }
}

// In another class:
ObjectMapper objectMapper = new ObjectMapper();
User user = new User();
user.setName("Alice");
user.setAge(30);

try {
    String jsonString = objectMapper.writeValueAsString(user);
    System.out.println(jsonString); // {"name":"Alice","age":30}
} catch (Exception e) {
    e.printStackTrace();
}
```

**Deserialization of JSON to a Java Object:**

```java
import com.fasterxml.jackson.databind.ObjectMapper;

// Assuming User class from above

// In another class:
ObjectMapper objectMapper = new ObjectMapper();
String jsonString = "{\"name\":\"Bob\",\"age\":25}";

try {
    User user = objectMapper.readValue(jsonString, User.class);
    System.out.println("Name: " + user.getName() + ", Age: " + user.getAge()); // Name: Bob, Age: 25
} catch (Exception e) {
    e.printStackTrace();
}
```

**Handling Collections:**

```java
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import java.util.List;
import java.util.Arrays;
import java.util.ArrayList;

// In another class:
ObjectMapper objectMapper = new ObjectMapper();

// Serialization of a List
List<String> names = Arrays.asList("Charlie", "David");
String jsonList = objectMapper.writeValueAsString(names);
System.out.println(jsonList); // ["Charlie","David"]

// Deserialization of a List
String jsonStringList = "[\"Eve\",\"Frank\"]";
List<String> deserializedNames = objectMapper.readValue(jsonStringList, new TypeReference<List<String>>() {});
System.out.println(deserializedNames); // [Eve, Frank]
```

**Customizing Serialization with Annotations:**

```java
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;

@JsonInclude(JsonInclude.Include.NON_NULL) // Don't include null fields
public class Product {
    @JsonProperty("product_name") // Rename field in JSON
    private String name;

    private double price;

    @JsonIgnore // Ignore this field during serialization/deserialization
    private String internalSku;

    // Getters and Setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public double getPrice() { return price; }
    public void setPrice(double price) { this.price = price; }
    public String getInternalSku() { return internalSku; }
    public void setInternalSku(String internalSku) { this.internalSku = internalSku; }
}

// In another class:
ObjectMapper objectMapper = new ObjectMapper();
Product product = new Product();
product.setName("Widget");
product.setPrice(19.99);
// product.setInternalSku("XYZ123"); // This will be ignored

String jsonProduct = objectMapper.writeValueAsString(product);
System.out.println(jsonProduct); // {"product_name":"Widget","price":19.99}
```

## Guidelines
*   **Reuse `ObjectMapper`**: Instantiate `ObjectMapper` once and reuse it throughout your application. Creating new instances frequently can be inefficient.
*   **Use `TypeReference` for Generic Types**: When deserializing generic types (like `List<MyObject>` or `Map<String, MyObject>`), use `TypeReference` to preserve generic type information.
*   **Configure `ObjectMapper` Appropriately**: For specific needs (e.g., date formatting, handling unknown properties, ignoring nulls), configure the `ObjectMapper` instance.
*   **Handle Exceptions**: Always wrap `writeValueAsString` and `readValue` calls in `try-catch` blocks to handle potential `JsonProcessingException` or `IOException`.
*   **Use Annotations for Clarity**: Leverage annotations like `@JsonProperty`, `@JsonIgnore`, `@JsonInclude`, and `@JsonFormat` to make your POJOs clearly define their JSON representation and behavior.
*   **Consider Performance**: For very high-throughput scenarios, explore performance tuning options of Jackson, but start with the default configurations.
*   **Register Modules for Specific Types**: For Java 8 Date/Time API or other custom types, ensure the relevant Jackson module (e.g., `jackson-datatype-jsr310`) is registered with the `ObjectMapper`.
*   **Handle Unknown Properties**: Decide on a strategy for unknown properties in incoming JSON. You can configure `ObjectMapper` to ignore them (`FAIL_ON_UNKNOWN_PROPERTIES` to `false`) or throw an exception.