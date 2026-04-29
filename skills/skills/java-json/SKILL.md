---
name: java-json
description: >-
  Using the `org.json` library for JSON manipulation in Java.
  Use this skill when working with java-json technologies.
---

# Java JSON Manipulation (`org.json`)

## Key Concepts
*   **`JSONObject`**: Represents a JSON object, a collection of key-value pairs. Keys are strings, and values can be strings, numbers, booleans, `JSONObject`s, `JSONArray`s, or null.
*   **`JSONArray`**: Represents a JSON array, an ordered list of values. Values can be any valid JSON type.
*   **Parsing**: Converting a JSON string into a `JSONObject` or `JSONArray` object for programmatic access.
*   **Serialization**: Converting `JSONObject` or `JSONArray` objects back into a JSON string.
*   **Navigation and Manipulation**: Accessing, modifying, and adding key-value pairs to `JSONObject`s and elements to `JSONArray`s.

## Project Conventions
*   **Package Structure**: Typically resides within utility or model packages, such as `com.example.util.json` or `com.example.model.dto`.
*   **File Layout**: JSON data is often read from or written to files or network streams. The `org.json` library is used within Java classes that handle these I/O operations.
*   **Naming Conventions**: Variable names for `JSONObject` and `JSONArray` instances usually follow standard Java camelCase conventions (e.g., `userData`, `configArray`). Key names within JSON objects are often preserved as-is from the source or follow camelCase/snake_case as dictated by the API contract.

## Common Patterns
**Parsing JSON from a String:**
```java
import org.json.JSONObject;
import org.json.JSONArray;
import org.json.JSONException;

public class JsonParserExample {
    public static void main(String[] args) {
        String jsonString = "{\"name\":\"Alice\", \"age\":30, \"isStudent\":false, \"courses\":[\"Math\",\"Science\"]}";

        try {
            JSONObject jsonObject = new JSONObject(jsonString);

            String name = jsonObject.getString("name");
            int age = jsonObject.getInt("age");
            boolean isStudent = jsonObject.getBoolean("isStudent");
            JSONArray coursesArray = jsonObject.getJSONArray("courses");

            System.out.println("Name: " + name);
            System.out.println("Age: " + age);
            System.out.println("Is Student: " + isStudent);

            System.out.println("Courses:");
            for (int i = 0; i < coursesArray.length(); i++) {
                System.out.println("- " + coursesArray.getString(i));
            }

        } catch (JSONException e) {
            e.printStackTrace();
        }
    }
}
```

**Building a JSON Object:**
```java
import org.json.JSONObject;
import org.json.JSONArray;

public class JsonBuilderExample {
    public static void main(String[] args) {
        JSONObject userProfile = new JSONObject();
        userProfile.put("userId", "user123");
        userProfile.put("username", "bob_smith");
        userProfile.put("active", true);

        JSONArray roles = new JSONArray();
        roles.put("admin");
        roles.put("editor");
        userProfile.put("roles", roles);

        JSONObject preferences = new JSONObject();
        preferences.put("theme", "dark");
        preferences.put("notifications", true);
        userProfile.put("preferences", preferences);

        System.out.println(userProfile.toString(2)); // Pretty print with indent of 2 spaces
    }
}
```

**Handling Null Values and Optional Fields:**
```java
import org.json.JSONObject;
import org.json.JSONObject;

public class SafeJsonAccess {
    public static void processUserData(JSONObject userData) {
        String email = userData.optString("email", "N/A"); // optString returns default if key missing or null
        String phone = userData.has("phone") ? userData.getString("phone") : null; // Explicit check

        System.out.println("Email: " + email);
        System.out.println("Phone: " + phone);
    }
}
```

## Guidelines
*   **Error Handling**: Always wrap JSON parsing and access operations within `try-catch` blocks to handle `JSONException` for malformed JSON or missing keys.
*   **Use `opt` methods**: Prefer `optString()`, `optInt()`, `optBoolean()`, `optJSONObject()`, `optJSONArray()` over their non-`opt` counterparts when a field might be missing or null. This avoids `JSONException` and allows for providing default values.
*   **`has()` for existence**: Use `jsonObject.has("key")` to explicitly check for the existence of a key before attempting to retrieve its value if you need to distinguish between a missing key and a key with a null value.
*   **Pretty Printing**: Use `jsonObject.toString(indentFactor)` for human-readable output during debugging or logging.
*   **Immutability**: The `org.json` library's objects are mutable. Be mindful of this if passing `JSONObject` or `JSONArray` instances between threads or to external methods where unexpected modifications could occur. Consider creating copies if necessary.
*   **Nested Structures**: Recursively access nested `JSONObject`s and `JSONArray`s using the same `get`/`opt` methods.
*   **Type Safety**: Be explicit with `getString()`, `getInt()`, `getBoolean()`, etc., as attempting to retrieve a value with the wrong type will result in a `JSONException`.
*   **Empty JSON**: Understand how the library handles empty JSON objects (`{}`) and arrays (`[]`).
*   **Null Handling**: `jsonObject.isNull("key")` can be used to check if a key maps to `null`. When serializing, `put(key, JSONObject.NULL)` explicitly adds a null value.