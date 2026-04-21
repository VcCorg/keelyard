---
name: spring-boot-cache
description: >-
  Implementing caching strategies within Spring Boot applications.
  Use this skill when working with spring-boot-cache technologies.
---

# Spring Boot Cache

## Key Concepts
*   **Caching Abstraction:** Spring Boot's cache abstraction provides a unified API to interact with various caching providers, decoupling application logic from specific implementations.
*   **Cache Annotations:** Annotations like `@Cacheable`, `@CachePut`, `@CacheEvict`, and `@Caching` are used to declaratively manage cache operations on methods.
*   **Cache Manager:** An implementation of `CacheManager` (e.g., `ConcurrentMapCacheManager`, `CaffeineCacheManager`) is responsible for creating and managing `Cache` instances.
*   **Cache Providers:** Integration with popular caching solutions like Caffeine, Ehcache, Redis, etc., through their respective Spring Cache implementations.
*   **Cache Keys:** Strategies for generating effective cache keys to ensure correct data retrieval and avoid cache misses.

## Project Conventions
*   **Configuration Class:** Cache configuration is typically done in a dedicated `@Configuration` class, often annotated with `@EnableCaching`.
*   **Cache Manager Bean:** Define a `CacheManager` bean to specify which caching provider to use.
*   **Cache Names:** Use descriptive and consistent names for caches (e.g., `users`, `products`, `orders`) often defined in `application.properties` or `application.yml`.
*   **Cacheable Methods:** Annotate service or repository methods that perform expensive operations and whose results can be cached.
*   **Dependency Management:** Include `spring-boot-starter-cache` and the specific cache provider dependency (e.g., `caffeine`).

## Common Patterns
**1. Basic Caching with `@Cacheable`**

```java
@Service
public class UserService {

    @Cacheable(value = "users", key = "#userId")
    public User getUserById(Long userId) {
        // Simulate a time-consuming operation
        System.out.println("Fetching user from database for ID: " + userId);
        return userRepository.findById(userId);
    }
}
```

**2. Updating Cache with `@CachePut`**

```java
@Service
public class ProductService {

    @CachePut(value = "products", key = "#product.id")
    public Product updateProduct(Product product) {
        // Simulate updating product in database
        System.out.println("Updating product in database: " + product.getName());
        return productRepository.save(product);
    }
}
```

**3. Evicting Cache with `@CacheEvict`**

```java
@Service
public class OrderService {

    @CacheEvict(value = "orders", key = "#orderId")
    public void deleteOrder(Long orderId) {
        // Simulate deleting order from database
        System.out.println("Deleting order from database: " + orderId);
        orderRepository.deleteById(orderId);
    }
}
```

**4. Conditional Caching with `condition` and `unless`**

```java
@Service
public class AnalyticsService {

    @Cacheable(value = "analyticsCache", key = "#reportId",
               condition = "#reportId != null && #reportId > 0",
               unless = "#result == null || #result.isEmpty()")
    public Report generateReport(Long reportId) {
        // ... generate report
        return report;
    }
}
```

**5. Using `Caching` for Multiple Operations**

```java
@Service
public class CacheService {

    @Caching(
        cacheable = @Cacheable(value = "items", key = "#itemId"),
        evict = {
            @CacheEvict(value = "allItems", allEntries = true),
            @CacheEvict(value = "itemDetails", key = "#itemId")
        }
    )
    public Item getItemById(String itemId) {
        // ... fetch item
        return item;
    }
}
```

## Guidelines
*   **Choose the Right Cache Provider:** Select a cache provider that aligns with your application's needs for performance, scalability, and persistence (e.g., Caffeine for in-memory, Redis for distributed).
*   **Effective Cache Key Generation:** Design robust `key` expressions for annotations. Use unique identifiers and consider compound keys for complex objects.
*   **Cache Invalidation Strategy:** Implement appropriate cache eviction strategies (`@CacheEvict`) to ensure data consistency, especially when data is modified.
*   **Avoid Caching for Volatile Data:** Do not cache data that changes frequently or requires real-time accuracy.
*   **Consider Cache Serialization:** If using distributed caches like Redis, ensure objects are serializable or use appropriate serialization mechanisms.
*   **Monitor Cache Performance:** Track cache hit/miss ratios and latency to identify performance bottlenecks and tune cache configurations.
*   **Use `allEntries=true` Sparingly:** While convenient, `allEntries=true` can be inefficient for large caches. Prefer targeted evictions when possible.
*   **Handle Null Results:** Be mindful of how your cache provider handles null results. `@Cacheable` might cache nulls, which could be undesirable. Use `unless` or custom logic to control this.