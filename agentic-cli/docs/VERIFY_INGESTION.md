# How to Verify Ingested Data

## 📊 Quick Status Check

### Check All Jobs
```bash
`agent kg async list
```

### Check Specific Job
```bash
`agent kg async status <job-id>
```

### View Job Logs
```bash
# View last 50 lines
tail -50 ~/.keel-agentic/logs/job_<job-id>.log

# Follow in real-time
tail -f ~/.keel-agentic/logs/job_<job-id>.log
```

---

## 🔍 Verify Neo4j Data

### 1. Count Total Nodes
```bash
docker exec keel-neo4j cypher-shell -u neo4j -p password \
  "MATCH (n) RETURN count(n) as total_nodes"
```

### 2. Count by Label
```bash
docker exec keel-neo4j cypher-shell -u neo4j -p password \
  "MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC LIMIT 20"
```

### 3. View Sample Nodes
```bash
docker exec keel-neo4j cypher-shell -u neo4j -p password \
  "MATCH (n) RETURN n LIMIT 10"
```

### 4. Count Relationships
```bash
docker exec keel-neo4j cypher-shell -u neo4j -p password \
  "MATCH ()-[r]->() RETURN type(r) as relationship, count(r) as count ORDER BY count DESC"
```

### 5. Search for Specific Content
```bash
docker exec keel-neo4j cypher-shell -u neo4j -p password \
  "MATCH (n) WHERE n.name CONTAINS 'patient' RETURN n LIMIT 10"
```

### 6. Query via CLI
```bash
# Natural language query
`agent kg query "show me patient information"

# Direct Cypher query
`agent kg query "MATCH (n:Patient) RETURN n LIMIT 10" --format cypher
```

---

## 🔍 Verify LightRAG Data

### 1. Check Health
```bash
curl http://localhost:8001/health
```

Expected output:
```json
{
  "status": "healthy",
  "lightrag_initialized": true
}
```

### 2. Query via API
```bash
# Naive mode (fast)
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "patient information", "mode": "naive"}'

# Hybrid mode (comprehensive)
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "patient information", "mode": "hybrid"}'
```

### 3. Query via CLI
```bash
# Naive mode (fast, good for testing)
`agent kg query "patient information" --mode naive

# Local mode (entity-focused)
`agent kg query "patient information" --mode local

# Global mode (summary-focused)
`agent kg query "patient information" --mode global

# Hybrid mode (best results, slower)
`agent kg query "patient information" --mode hybrid
```

### 4. Check Storage
```bash
# LightRAG stores data in working directory
ls -lh ./dickens  # Default storage directory
```

---

## 📈 Monitor Ingestion Progress

### Watch Neo4j Node Count
```bash
# Create monitoring script
cat > /tmp/monitor_neo4j.sh << 'EOF'
#!/bin/bash
while true; do
  count=$(docker exec keel-neo4j cypher-shell -u neo4j -p password \
    "MATCH (n) RETURN count(n)" 2>/dev/null | tail -1)
  echo "$(date '+%H:%M:%S') - Nodes: $count"
  sleep 5
done
EOF

chmod +x /tmp/monitor_neo4j.sh
/tmp/monitor_neo4j.sh
```

### Watch Job Logs
```bash
# Follow specific job
tail -f ~/.keel-agentic/logs/job_<job-id>.log

# Follow all ingestion logs
tail -f ~/.keel-agentic/logs/async_ingestion.log
```

### Check Worker Process
```bash
# List all workers
ps aux | grep async_worker

# Check specific worker
ps aux | grep <worker-pid>
```

---

## 🎯 Complete Verification Workflow

### For Completed Jobs

```bash
# 1. Check job status
`agent kg async status <job-id>

# 2. View job results
`agent kg async status <job-id> --verbose

# 3. Verify data in target system
# For Neo4j:
docker exec keel-neo4j cypher-shell -u neo4j -p password \
  "MATCH (n) RETURN count(n)"

# For LightRAG:
`agent kg query "test query" --mode naive

# 4. Check job logs for any errors
tail -100 ~/.keel-agentic/logs/job_<job-id>.log | grep -i error
```

### For Running Jobs

```bash
# 1. Check status
`agent kg async status <job-id>

# 2. Follow logs
tail -f ~/.keel-agentic/logs/job_<job-id>.log

# 3. Monitor progress (in separate terminal)
# For Neo4j:
watch -n 5 'docker exec keel-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n)" 2>/dev/null'

# 4. Check worker is running
ps aux | grep <worker-pid>
```

---

## 🚨 Troubleshooting

### Job Stuck in "Running"

```bash
# 1. Check if worker process exists
ps aux | grep <worker-pid>

# 2. Check logs for errors
tail -100 ~/.keel-agentic/logs/job_<job-id>.log

# 3. Check target system health
# Neo4j:
docker ps | grep neo4j
docker logs keel-neo4j --tail 50

# LightRAG:
curl http://localhost:8001/health
```

### No Data Appearing

```bash
# 1. Verify job completed successfully
`agent kg async status <job-id>

# 2. Check for errors in logs
grep -i error ~/.keel-agentic/logs/job_<job-id>.log

# 3. Verify source path exists
ls -la <source-path>

# 4. Check target system connectivity
# Neo4j:
docker exec keel-neo4j cypher-shell -u neo4j -p password "RETURN 1"

# LightRAG:
curl http://localhost:8001/health
```

### Query Timeout

```bash
# LightRAG queries can be slow on first run
# Try with faster mode:
`agent kg query "your query" --mode naive

# Or increase timeout in config:
# Edit ~/.keel-agentic/kg-config.json
# Set "lightrag_timeout": 120
```

---

## 📊 Example Verification Session

```bash
# 1. List all jobs
`agent kg async list

# Output:
# Job ID      | Source              | Provider | Status      | Duration
# bdd4a450... | .../patient/docs    | lightrag | ✓ Completed | 35.8s
# 011ae616... | .../patient/docs    | neo4j    | 🔄 Running  | 265.6s

# 2. Check completed LightRAG job
`agent kg async status bdd4a450-4cb1-4ef7-86b1-182098a65443 --verbose

# 3. Query LightRAG
`agent kg query "patient care" --mode naive

# 4. Check running Neo4j job
tail -20 ~/.keel-agentic/logs/job_011ae616-1ddc-48bc-ba0e-2dcca4265270.log

# 5. Count Neo4j nodes
docker exec keel-neo4j cypher-shell -u neo4j -p password \
  "MATCH (n) RETURN count(n)"

# Output: 6759 nodes

# 6. Wait for Neo4j job to complete
`agent kg async status 011ae616-1ddc-48bc-ba0e-2dcca4265270

# 7. Query Neo4j
`agent kg query "MATCH (n:Patient) RETURN n LIMIT 5" --format cypher
```

---

## ✅ Success Indicators

### Job Completed Successfully
- ✅ Status: `completed`
- ✅ No errors in logs
- ✅ Result shows document/node counts
- ✅ Data queryable in target system

### Neo4j Ingestion Success
- ✅ Node count increased
- ✅ Multiple entity types present
- ✅ Relationships created (if enabled)
- ✅ Queries return results

### LightRAG Ingestion Success
- ✅ Health check returns `healthy`
- ✅ Queries return relevant results
- ✅ Storage directory has data files
- ✅ No timeout errors

---

## 🎯 Quick Commands Reference

```bash
# Status
`agent kg async list
`agent kg async status <job-id>

# Logs
tail -f ~/.keel-agentic/logs/job_<job-id>.log

# Neo4j
docker exec keel-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n)"

# LightRAG
curl http://localhost:8001/health
`agent kg query "test" --mode naive

# Workers
ps aux | grep async_worker
```

---

## 📚 Related Documentation

- **Async Ingestion Guide**: `docs/ASYNC_INGESTION.md`
- **Knowledge Graph Guide**: `docs/KNOWLEDGE_GRAPH.md`
- **CLI Reference**: `README.md`
