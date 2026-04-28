---
name: java-jsoup
description: >-
  Web scraping and parsing HTML content using Jsoup in Java.
  Use this skill when working with java-jsoup technologies.
---

# Java Jsoup: Web Scraping and HTML Parsing

Jsoup is a Java library for working with real-world HTML. It provides a very convenient API for extracting and manipulating data, parsing HTML, and dealing with messy HTML.

## Key Concepts

*   **Document Parsing:** Jsoup can parse HTML from strings, files, or URLs into a navigable `Document` object.
*   **Selectors:** Uses CSS-like selectors (e.g., `"#id"`, `".class"`, `"tag"`, `"[attribute]"`) to efficiently locate elements within the HTML.
*   **Element Traversal:** Provides methods for navigating the DOM tree (e.g., `parent()`, `children()`, `nextElementSibling()`).
*   **Data Extraction:** Allows easy extraction of text content, attribute values, and HTML content from elements.
*   **HTML Manipulation:** Supports modifying the DOM by adding, removing, or changing elements and attributes.

## Project Conventions

*   **Dependency Management:** The `org.jsoup:jsoup` artifact is typically managed via build tools like Maven or Gradle.
*   **Source Code:** Jsoup usage is often found within service classes, utility classes, or specific web scraping modules.
*   **Error Handling:** Consider using `try-catch` blocks for network operations (fetching HTML) and potential parsing errors.
*   **User Agent:** When making HTTP requests, setting a meaningful `User-Agent` header is crucial for mimicking browser behavior and avoiding blocks.

## Common Patterns

**Fetching and Parsing HTML from a URL:**

```java
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import java.io.IOException;

public class HtmlFetcher {
    public Document fetch(String url) throws IOException {
        return Jsoup.connect(url)
                    .userAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                    .timeout(5000) // 5 seconds timeout
                    .get();
    }
}
```

**Extracting Text from Elements using Selectors:**

```java
import org.jsoup.nodes.Document;
import org.jsoup.select.Elements;
import java.util.List;
import java.util.stream.Collectors;

public class TextExtractor {
    public List<String> extractTitles(Document document) {
        Elements titleElements = document.select("h1.article-title");
        return titleElements.stream()
                            .map(element -> element.text().trim())
                            .collect(Collectors.toList());
    }
}
```

**Extracting Attribute Values:**

```java
import org.jsoup.nodes.Document;
import org.jsoup.select.Elements;
import java.util.List;
import java.util.stream.Collectors;

public class AttributeExtractor {
    public List<String> extractImageUrls(Document document) {
        Elements imgElements = document.select("img[src]");
        return imgElements.stream()
                          .map(element -> element.attr("src"))
                          .filter(url -> !url.isEmpty())
                          .collect(Collectors.toList());
    }
}
```

**Iterating Through Elements and Accessing Data:**

```java
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

public class DataScraper {
    public void scrapeProductDetails(Document document) {
        Elements productItems = document.select("div.product-item");
        for (Element item : productItems) {
            String name = item.selectFirst("h3.product-name").text().trim();
            String price = item.selectFirst("span.product-price").text().trim();
            System.out.println("Product: " + name + ", Price: " + price);
        }
    }
}
```

## Guidelines

*   **Be Respectful:** Always check `robots.txt` and avoid excessive requests to prevent overwhelming servers.
*   **Handle Network Errors:** Network requests can fail. Implement robust error handling for `IOException`.
*   **Handle Malformed HTML:** Jsoup is designed to handle imperfect HTML, but be prepared for unexpected structures.
*   **Use Specific Selectors:** Prefer more specific CSS selectors to avoid brittle parsing that breaks with minor HTML changes.
*   **Avoid Deep DOM Traversal:** While possible, deeply nested traversals can become complex and less performant.
*   **Set a User-Agent:** Always set a custom `User-Agent` to identify your scraper and mimic a browser.
*   **Manage Timeouts:** Configure appropriate connection and read timeouts to prevent long-running requests.
*   **Extract What You Need:** Avoid parsing or storing unnecessary HTML elements to improve efficiency.
*   **Consider Dynamic Content:** Jsoup is best for static HTML. For JavaScript-rendered content, consider using tools like Selenium.
*   **Check for Element Existence:** Before calling `.text()` or `.attr()` on a selected element, ensure the element was found (e.g., `selectFirst()` returns non-null).