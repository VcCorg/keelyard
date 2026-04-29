---
name: java-jaxb
description: >-
  Java Architecture for XML Binding (JAXB) for XML serialization/deserialization.
  Use this skill when working with java-jaxb technologies.
---

# Java JAXB (Java Architecture for XML Binding)

## Key Concepts
*   **Marshalling:** The process of converting Java objects into XML.
*   **Unmarshalling:** The process of converting XML into Java objects.
*   **Annotations:** JAXB uses annotations (e.g., `@XmlRootElement`, `@XmlElement`, `@XmlAttribute`) within Java classes to define the mapping between Java objects and XML.
*   **Context:** The `JAXBContext` class is central to JAXB operations, providing a factory for `Marshaller` and `Unmarshaller` instances.
*   **Package-Level Annotations:** Annotations like `@XmlSchema` can be applied at the package level to control XML structure and namespace.

## Project Conventions
*   **Model Classes:** Java classes intended for JAXB binding are typically located in a dedicated model or domain package.
*   **Annotation Placement:** Annotations are placed directly on fields, getter methods, setter methods, or the class itself.
*   **`pom.xml` / `build.gradle`:** JAXB runtime dependencies (e.g., `org.glassfish.jaxb:jaxb-runtime`) are declared in the build configuration.
*   **XML Schema (XSD) to Java:** While not strictly a convention, it's common to generate Java classes from an existing XSD using tools like `xjc`.

## Common Patterns
**Marshalling a Java Object to XML:**

```java
import javax.xml.bind.JAXBContext;
import javax.xml.bind.Marshaller;
import java.io.StringWriter;

// Assuming 'MyObject' is a JAXB-annotated class
MyObject myObject = new MyObject();
myObject.setId(123);
myObject.setName("Example");

try {
    JAXBContext context = JAXBContext.newInstance(MyObject.class);
    Marshaller marshaller = context.createMarshaller();
    marshaller.setProperty(Marshaller.JAXB_FORMATTED_OUTPUT, true); // Pretty print

    StringWriter writer = new StringWriter();
    marshaller.marshal(myObject, writer);
    String xmlString = writer.toString();
    System.out.println(xmlString);
} catch (Exception e) {
    e.printStackTrace();
}
```

**Unmarshalling XML to a Java Object:**

```java
import javax.xml.bind.JAXBContext;
import javax.xml.bind.Unmarshaller;
import java.io.StringReader;

String xmlString = "<myObject><id>123</id><name>Example</name></myObject>"; // Assume this is your XML

try {
    JAXBContext context = JAXBContext.newInstance(MyObject.class);
    Unmarshaller unmarshaller = context.createUnmarshaller();

    StringReader reader = new StringReader(xmlString);
    MyObject myObject = (MyObject) unmarshaller.unmarshal(reader);

    System.out.println("ID: " + myObject.getId());
    System.out.println("Name: " + myObject.getName());
} catch (Exception e) {
    e.printStackTrace();
}
```

**Basic JAXB Annotated Class:**

```java
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlElement;

@XmlRootElement(name = "myObject")
public class MyObject {
    private int id;
    private String name;

    @XmlElement(name = "id")
    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    @XmlElement(name = "name")
    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
```

## Guidelines
*   **Use Annotations Wisely:** Leverage JAXB annotations for clear and concise mapping. Avoid complex logic within your model classes solely for binding.
*   **Specify Root Element:** Always use `@XmlRootElement` on the top-level class to define the root element name in the XML.
*   **Control Element Names:** Use `@XmlElement` or `@XmlAttribute` to explicitly define XML element and attribute names, especially when they differ from Java field names.
*   **Handle Collections:** For collections (e.g., `List`), use `@XmlElementWrapper` and `@XmlElement` to control the wrapper element and the individual item elements.
*   **Namespace Management:** Utilize `@XmlSchema` at the package level for effective namespace management if required.
*   **Error Handling:** Always wrap JAXB operations (marshalling/unmarshalling) in try-catch blocks to handle potential `JAXBException` or other related errors.
*   **Dependency Management:** Ensure the correct JAXB runtime dependency is present in your project's build configuration.
*   **Consider Alternatives for Modern Java:** For newer Java versions (9+), JAXB is no longer included by default and might require explicit configuration or the use of alternative libraries like Jackson for XML.