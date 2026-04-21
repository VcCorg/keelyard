---
name: java-commons-io
description: >-
  Utilizing Apache Commons IO for common I/O utility operations.
  Use this skill when working with java-commons-io technologies.
---

# Apache Commons IO

## Key Concepts
*   **File and Directory Manipulation:** Simplifies operations like copying, moving, deleting, and creating files and directories.
*   **Stream Handling:** Provides utilities for reading from and writing to various input and output streams, including line-by-line reading and byte-to-character conversion.
*   **Content Comparison:** Offers methods for comparing file content and detecting changes.
*   **IO Utilities:** Encapsulates common I/O tasks, reducing boilerplate code and improving readability.
*   **Buffering and Wrapping:** Facilitates efficient I/O through buffering and wrapping of standard Java I/O classes.

## Project Conventions
*   **Package Structure:** Typically resides within standard Java package structures, often in utility or helper classes.
*   **Naming Conventions:** Utility classes and methods often follow the naming conventions of the Apache Commons family, with clear and descriptive names (e.g., `FileUtils.copyFile`, `IOUtils.closeQuietly`).
*   **Static Usage:** Many `commons-io` utility methods are static, designed for direct invocation without object instantiation.

## Common Patterns

**Reading a File Line by Line:**

```java
import org.apache.commons.io.FileUtils;
import org.apache.commons.io.LineIterator;

import java.io.File;
import java.io.IOException;

public class FileReaderExample {
    public void processFile(File file) {
        LineIterator it = null;
        try {
            it = FileUtils.lineIterator(file, "UTF-8");
            while (it.hasNext()) {
                String line = it.nextLine();
                // Process the line
                System.out.println(line);
            }
        } catch (IOException e) {
            // Handle exception
            e.printStackTrace();
        } finally {
            LineIterator.closeQuietly(it);
        }
    }
}
```

**Copying a File:**

```java
import org.apache.commons.io.FileUtils;

import java.io.File;
import java.io.IOException;

public class FileCopier {
    public void copyFile(File source, File destination) throws IOException {
        FileUtils.copyFile(source, destination);
    }
}
```

**Deleting a Directory Recursively:**

```java
import org.apache.commons.io.FileUtils;

import java.io.File;
import java.io.IOException;

public class DirectoryCleaner {
    public void deleteDirectory(File directory) throws IOException {
        if (directory.exists()) {
            FileUtils.deleteDirectory(directory);
        }
    }
}
```

**Reading Entire File Content to String:**

```java
import org.apache.commons.io.FileUtils;

import java.io.File;
import java.io.IOException;

public class FileContentReader {
    public String readFileContent(File file) throws IOException {
        return FileUtils.readFileToString(file, "UTF-8");
    }
}
```

## Guidelines
*   **Prefer `commons-io` over raw Java I/O:** For common tasks, `commons-io` provides more concise and robust solutions.
*   **Use `IOUtils.closeQuietly()`:** Always ensure streams and readers are closed, and `IOUtils.closeQuietly()` is the safest way to do so without risking `IOException` during closing.
*   **Specify Encoding:** When reading or writing text files, explicitly define the character encoding (e.g., "UTF-8") to avoid platform-dependent issues.
*   **Handle `IOException`:** I/O operations are prone to errors. Always wrap I/O calls in `try-catch` blocks to handle `IOException`.
*   **Leverage `FileUtils` for File Operations:** Use `FileUtils` for file and directory manipulation tasks like copying, moving, deleting, and checking existence.
*   **Utilize `IOUtils` for Stream Operations:** `IOUtils` offers methods for reading from and writing to streams, converting between byte and character streams, and closing resources.
*   **Consider Performance:** For very large files or high-throughput scenarios, be mindful of using buffered readers/writers or specific stream implementations provided by `commons-io`.
*   **Be Aware of Overwriting:** When copying or moving files, be aware of the behavior when the destination already exists. `FileUtils.copyFile` by default will overwrite.