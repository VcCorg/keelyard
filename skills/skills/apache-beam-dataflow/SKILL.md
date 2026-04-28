---
name: apache-beam-dataflow
description: >-
  Apache Beam pipeline patterns on Google Cloud Dataflow — PCollections,
  transforms, IO connectors, and pipeline deployment.
---

# Apache Beam on GCP Dataflow

## Pipeline Structure

```java
Pipeline pipeline = Pipeline.create(options);

pipeline
    .apply("ReadFromSource", sourceTransform)
    .apply("Transform", ParDo.of(new ProcessFn()))
    .apply("WriteToSink", sinkTransform);

pipeline.run().waitUntilFinish();
```

## Core Concepts

- **PCollection**: Immutable distributed dataset
- **PTransform**: Operation on PCollections (ParDo, GroupByKey, Combine, etc.)
- **DoFn**: User-defined processing function
- **Pipeline Options**: Runtime configuration (runner, project, region, etc.)

## Common Transforms

```java
// ParDo — element-wise processing
.apply(ParDo.of(new DoFn<InputT, OutputT>() {
    @ProcessElement
    public void processElement(@Element InputT input, OutputReceiver<OutputT> out) {
        out.output(transform(input));
    }
}))

// Filter
.apply(Filter.by(element -> element.isActive()))

// GroupByKey
.apply(GroupByKey.create())

// Combine (aggregation)
.apply(Combine.globally(Sum.ofIntegers()))
```

## IO Connectors

```java
// Spanner Read
.apply(SpannerIO.read()
    .withInstanceId("my-instance")
    .withDatabaseId("my-database")
    .withQuery("SELECT * FROM Patients"))

// Spanner Write
.apply(SpannerIO.write()
    .withInstanceId("my-instance")
    .withDatabaseId("my-database"))

// BigQuery Write
.apply(BigQueryIO.writeTableRows()
    .to("project:dataset.table")
    .withSchema(tableSchema)
    .withWriteDisposition(WriteDisposition.WRITE_APPEND))

// Kafka Read
.apply(KafkaIO.<String, String>read()
    .withBootstrapServers("broker:9092")
    .withTopic("input-topic")
    .withKeyDeserializer(StringDeserializer.class)
    .withValueDeserializer(StringDeserializer.class))
```

## Pipeline Options

```java
public interface PatientBatchOptions extends DataflowPipelineOptions {
    @Description("Spanner instance ID")
    String getInstanceId();
    void setInstanceId(String value);

    @Description("Spanner database ID")
    String getDatabaseId();
    void setDatabaseId(String value);
}
```

## Running

```bash
# Local (DirectRunner)
mvn exec:java -Dexec.mainClass=com.example.Pipeline -Pdirect-runner

# GCP Dataflow
mvn exec:java -Dexec.mainClass=com.example.Pipeline -Pdataflow-runner \
  -Dexec.args="--project=my-project --region=us-central1 \
  --runner=DataflowRunner --tempLocation=gs://bucket/temp"
```

## Guidelines

- Use `@ProcessElement` in DoFn for element-wise transforms
- Prefer Beam built-in IO connectors over custom source/sink
- Use `maven-shade-plugin` for fat JAR packaging
- Keep DoFn stateless where possible; use `@StateId` for stateful processing
- Use `--maxNumWorkers` and `--autoscalingAlgorithm` for cost control
- Test pipelines with `TestPipeline` and `PAssert` in unit tests
- Use `Reshuffle.viaRandomKey()` to break fusion for parallelism
