---
name: spanner-change-streams
description: >-
  Integration with Spanner Change Streams for real-time data event processing.
  Use this skill when working with spanner-change-streams technologies.
tags: database, gcp, streaming
---

# Spanner Change Streams

## Key Concepts
*   **Change Streams:** A GCP Spanner feature that captures and delivers committed data changes (inserts, updates, deletes) from Spanner tables in near real-time.
*   **Change Record:** A unit of data representing a committed transaction's data modifications, containing metadata and changed data.
*   **Change Stream APIs:** Mechanisms (e.g., Pub/Sub, Dataflow) to consume and process change records.
*   **Dataflow Integration:** A common pattern for large-scale, robust processing of Spanner Change Streams, enabling transformations, aggregations, and sinks to other systems.
*   **Event-Driven Architecture:** Spanner Change Streams facilitate building event-driven systems where downstream services react to data modifications in Spanner.

## Project Conventions
*   **Dataflow Pipelines:** Structure Dataflow jobs logically, separating input (Spanner Change Streams) from transformation and output (sinks).
*   **Schema Definition:** Maintain clear schema definitions for your Spanner tables and how they map to change records.
*   **Error Handling:** Implement robust error handling within Dataflow pipelines, including dead-letter queues for unprocessable records.
*   **Idempotency:** Design downstream consumers to be idempotent to handle potential duplicate change records.
*   **Configuration Management:** Use environment variables or configuration files for Spanner instance, database, change stream name, and Pub/Sub topic details.

## Common Patterns
*   **Streaming to Pub/Sub:**
    ```python
    from apache_beam import Pipeline
    from apache_beam.options.pipeline_options import PipelineOptions
    from apache_beam.transforms.io.gcp.spanner import SpannerIO

    # ... (PipelineOptions setup)

    with Pipeline(options=pipeline_options) as pipeline:
        (
            pipeline
            | 'Read Spanner Change Streams' >> SpannerIO.change_streams_read(
                project='your-gcp-project',
                instance='your-spanner-instance',
                database='your-spanner-database',
                change_stream_name='your-change-stream-name'
            )
            # Further processing or writing to Pub/Sub
            # | 'Write to Pub/Sub' >> PubSubIO.write(...)
        )
    ```
*   **Transforming and Sinking with Dataflow:**
    ```python
    # Assuming 'change_records' is a PCollection of change records from Spanner
    def process_change_record(record):
        # Logic to parse and transform change record
        # ...
        return transformed_data

    def write_to_bigquery(data):
        # Logic to write to BigQuery
        # ...
        pass

    (
        change_records
        | 'Process Change Records' >> beam.Map(process_change_record)
        | 'Write to BigQuery' >> beam.ParDo(write_to_bigquery())
    )
    ```
*   **Filtering Specific Table Changes:**
    ```python
    def is_from_users_table(record):
        return record.table_name == 'Users'

    (
        pipeline
        | 'Read Spanner Change Streams' >> SpannerIO.change_streams_read(...)
        | 'Filter Users Table' >> beam.Filter(is_from_users_table)
        # ... further processing
    )
    ```

## Guidelines
*   **Enable Change Streams:** Ensure Change Streams are enabled for the relevant Spanner tables.
*   **Grant Permissions:** Provide necessary IAM permissions for the service account running the Dataflow job to access Spanner and Pub/Sub.
*   **Monitor Pipeline Health:** Actively monitor Dataflow job health, metrics, and logs for any processing issues.
*   **Choose Appropriate Sink:** Select a sink (e.g., BigQuery, Pub/Sub, Cloud Storage) that aligns with your downstream use case.
*   **Handle Schema Evolution:** Plan for and handle schema changes in your Spanner tables to avoid breaking downstream consumers.
*   **Consider Watermarks:** For complex event-time aggregations, understand and manage watermarks in your Dataflow pipeline.
*   **Optimize Dataflow Resources:** Tune Dataflow worker types, number of workers, and autoscaling to balance cost and performance.
*   **Batching vs. Real-time:** Decide if batch processing or near real-time processing is sufficient for your use case, influencing Dataflow windowing strategies.