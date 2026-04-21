---
name: database-mongodb
description: >-
  MongoDB document design, aggregation pipeline, indexing patterns.
  Use this skill when working with MongoDB databases.
---

# MongoDB Development

## Document Design

```javascript
// Embed related data when read together
{
  _id: ObjectId("..."),
  name: "Resource A",
  status: "active",
  tags: ["web", "api"],
  metadata: {
    createdBy: "user-123",
    version: 2
  },
  comments: [                    // Embedded array (bounded)
    { author: "user-456", text: "Looks good", createdAt: ISODate("...") }
  ]
}

// Reference when data is large, shared, or unbounded
{
  _id: ObjectId("..."),
  resourceId: ObjectId("..."),   // Reference to resources collection
  content: "...",
}
```

## Query Patterns

```javascript
// Find with filter and projection
db.resources.find({ status: "active" }, { name: 1, status: 1 });

// Aggregation pipeline
db.resources.aggregate([
  { $match: { status: "active" } },
  { $group: { _id: "$category", count: { $sum: 1 } } },
  { $sort: { count: -1 } },
  { $limit: 10 }
]);

// Update with operators
db.resources.updateOne(
  { _id: ObjectId("...") },
  { $set: { status: "archived" }, $inc: { version: 1 }, $currentDate: { updatedAt: true } }
);
```

## Indexing

```javascript
db.resources.createIndex({ status: 1 });                    // Single field
db.resources.createIndex({ status: 1, createdAt: -1 });     // Compound
db.resources.createIndex({ name: "text" });                  // Text search
db.resources.createIndex({ location: "2dsphere" });          // Geospatial
db.resources.createIndex({ status: 1 }, { partialFilterExpression: { status: "active" } }); // Partial
```

## Guidelines

- Embed when data is read together and bounded in size
- Reference when data is large, shared across documents, or frequently updated independently
- Design schema for your query patterns (not for normalization)
- Use compound indexes — field order matters (equality → sort → range)
- Use `explain()` to verify query plans
- Avoid unbounded array growth in embedded documents
- Use `$lookup` sparingly (it's a left outer join, can be slow)
