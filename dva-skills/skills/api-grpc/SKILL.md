---
name: api-grpc
description: >-
  gRPC service definitions, protobuf, streaming patterns, interceptors.
  Use this skill when working with gRPC APIs.
---

# gRPC Development

## Proto File Structure

```protobuf
syntax = "proto3";

package myservice.v1;

option java_package = "com.example.myservice.v1";
option go_package = "github.com/example/myservice/v1";

service ResourceService {
  rpc GetResource(GetResourceRequest) returns (ResourceResponse);
  rpc ListResources(ListResourcesRequest) returns (ListResourcesResponse);
  rpc CreateResource(CreateResourceRequest) returns (ResourceResponse);
  rpc WatchResources(WatchRequest) returns (stream ResourceEvent);  // Server streaming
}

message ResourceResponse {
  string id = 1;
  string name = 2;
  google.protobuf.Timestamp created_at = 3;
}

message GetResourceRequest {
  string id = 1;
}

message ListResourcesRequest {
  int32 page_size = 1;
  string page_token = 2;
}

message ListResourcesResponse {
  repeated ResourceResponse resources = 1;
  string next_page_token = 2;
}
```

## Streaming Patterns

| Pattern | Use Case |
|---------|----------|
| Unary | Simple request/response |
| Server streaming | Watch for updates, large result sets |
| Client streaming | Upload chunks, batch operations |
| Bidirectional streaming | Chat, real-time sync |

## Error Handling

```
gRPC Status Codes:
OK (0)              — Success
CANCELLED (1)       — Client cancelled
INVALID_ARGUMENT (3) — Bad request (like 400)
NOT_FOUND (5)       — Resource not found (like 404)
ALREADY_EXISTS (6)  — Conflict (like 409)
PERMISSION_DENIED (7) — Forbidden (like 403)
UNAUTHENTICATED (16) — Auth required (like 401)
INTERNAL (13)       — Server error (like 500)
UNAVAILABLE (14)    — Service down (retry)
DEADLINE_EXCEEDED (4) — Timeout
```

## Code Generation

```bash
# Python
python -m grpc_tools.protoc -I protos --python_out=. --grpc_python_out=. protos/service.proto

# Java (Gradle)
# Uses protobuf-gradle-plugin — generates from src/main/proto/

# Go
protoc --go_out=. --go-grpc_out=. protos/service.proto
```

## Guidelines

- Design proto files as API contracts — version them carefully
- Use `google.protobuf.FieldMask` for partial updates
- Use deadline/timeout on every RPC call
- Use interceptors for auth, logging, metrics (like HTTP middleware)
- Use `oneof` for polymorphic fields
- Avoid breaking changes: never reuse field numbers, only add fields
- Use `buf` for proto linting and breaking change detection
