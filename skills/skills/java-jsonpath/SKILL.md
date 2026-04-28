---
name: java-jsonpath
description: >-
  Parsing and querying JSON data using JsonPath in Java.
  Use this skill when working with java-jsonpath technologies.
---

# Java JsonPath

## Key Concepts
*   **JsonPath Expression:** A string that defines a path to navigate and extract data from a JSON document, similar to XPath for XML.
*   **`JsonPath.read()`:** The primary method for parsing a JSON string or object and applying a JsonPath expression.
*   **JSON Structure Traversal:** Supports navigating arrays, objects, and nested structures using dot notation (`.`) and bracket notation (`[]`).
*   **Filter Expressions:** Allows for conditional selection of elements based on their values or properties.
*   **Deep Scanning Operator (`..`):** Enables searching for elements at any level of the JSON hierarchy.

## Project Conventions
*   **Dependency Management:** Typically managed via Maven (`com.jayway.jsonpath:json-path`) or Gradle.
*   **JSON Source:** JsonPath can parse `String` representations of JSON, `InputStream`, `File`, or existing `JSONObject`/`Map` structures.
*   **Configuration:** `JsonPath.using()` can be used to configure parsers (e.g., `JacksonJsonProvider`, `GsonJsonProvider`) and configuration options.
*   **Testing Integration:** Commonly used within unit and integration tests to validate JSON payloads from API responses or data files.

## Common Patterns
**Reading a specific field:**
```java
String json = "{\"name\": \"John Doe\", \"age\": 30}";
String name = JsonPath.read(json, "$.name"); // "John Doe"
```

**Accessing array elements:**
```java
String json = "{\"users\": [{\"name\": \"Alice\"}, {\"name\": \"Bob\"}]}";
String firstUserName = JsonPath.read(json, "$.users[0].name"); // "Alice"
```

**Filtering arrays:**
```java
String json = "{\"items\": [{\"id\": 1, \"active\": true}, {\"id\": 2, \"active\": false}]}";
List<Map<String, Object>> activeItems = JsonPath.read(json, "$.items[?(@.active == true)]");
```

**Using deep scanning:**
```java
String json = "{\"data\": {\"user\": {\"profile\": {\"email\": \"test@example.com\"}}}}";
String email = JsonPath.read(json, "$..email"); // "test@example.com"
```

**Reading into a specific Java type:**
```java
String json = "{\"name\": \"John Doe\", \"age\": 30}";
String name = JsonPath.read(json, "$.name", String.class);
Integer age = JsonPath.read(json, "$.age", Integer.class);
```

**Handling multiple matches:**
```java
String json = "{\"users\": [{\"id\": 1, \"name\": \"Alice\"}, {\"id\": 2, \"name\": \"Bob\"}]}";
List<String> userNames = JsonPath.read(json, "$.users[*].name"); // ["Alice", "Bob"]
```

## Guidelines
*   **Specificity is Key:** Write JsonPath expressions that are as specific as possible to avoid unintended matches in complex JSON structures.
*   **Handle `PathNotFoundException`:** Be prepared to catch `com.jayway.jsonpath.PathNotFoundException` when the specified path might not exist in the JSON.
*   **Use Appropriate Parser:** Configure `JsonPath` with the correct JSON provider (e.g., Jackson, Gson) that matches your project's JSON handling library.
*   **Escape Special Characters:** If your JSON values contain characters like quotes, be mindful of potential escaping issues within the JsonPath expression itself, although JsonPath generally handles this well.
*   **Consider Performance:** For very large JSON documents and frequent complex queries, consider alternative parsing strategies or libraries if performance becomes a bottleneck.
*   **Readability of Expressions:** While powerful, overly complex JsonPath expressions can become difficult to read and maintain. Consider breaking them down or using helper methods.
*   **`?(@.property)` for Filtering:** Leverage the `?(@.property)` syntax for filtering arrays based on element properties.
*   **`[*]`, `[*]`, `[?(...)]` for Collections:** Understand the different wildcard and filter syntaxes for navigating and selecting from JSON arrays.