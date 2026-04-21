# Git Repository Ingestion - End-to-End Test Guide

## 🎯 Overview

This guide walks you through testing the complete Git repository ingestion feature with developer persona support.

---

## 📋 Prerequisites

### 1. Install Dependencies

```bash
cd /Users/your-user/dva-agentic-project/dva-agentic-cli

# Install with KG dependencies (includes Git support)
uv pip install -e ".[kg]"

# Or with pip
pip install -e ".[kg]"
```

### 2. Verify Installation

```bash
# Check if gitingest is installed
python -c "import gitingest; print('✓ gitingest installed')"

# Check if GitPython is installed
python -c "import git; print('✓ GitPython installed')"

# Verify DVA CLI
dva --version
```

### 3. Start Knowledge Graph Infrastructure

**Option A: LightRAG (Recommended for testing)**
```bash
cd /Users/your-user/dva-agentic-project/lightrag-infrastructure
docker-compose up -d
docker logs -f dva-lightrag
```

**Option B: Neo4j**
```bash
docker run --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

---

## 🧪 Test Scenario 1: Small Public Repository (Python)

### Step 1: Configure KG Provider

```bash
# For LightRAG
dva kg init --provider lightrag --lightrag-url http://localhost:8001

# For Neo4j
dva kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password
```

### Step 2: Register Git Repository

```bash
dva data create \
  --name requests-lib \
  --source-type git \
  --source-location https://github.com/psf/requests.git \
  --git-branch main \
  --description "Python HTTP library for humans" \
  --tags "python,http,library,networking"
```

**Expected Output:**
```
✓ Data source created successfully
  Name: requests-lib
  Type: git
  Location: https://github.com/psf/requests.git
  Branch: main
  Tags: python, http, library, networking
```

### Step 3: Verify Data Source

```bash
dva data show requests-lib
```

**Expected Output:**
```
 Data Source: requests-lib 
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property    ┃ Value                                        ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Name        │ requests-lib                                 │
│ Type        │ git                                          │
│ Location    │ https://github.com/psf/requests.git          │
│ Description │ Python HTTP library for humans               │
│ Tags        │ python, http, library, networking            │
│ Branch      │ main                                         │
│ Created     │ 2025-11-22T22:15:00-06:00                    │
└─────────────┴──────────────────────────────────────────────┘
```

### Step 4: Ingest Repository

```bash
dva kg ingest --source requests-lib
```

**Expected Output:**
```
Resolving data source 'requests-lib'...
ℹ Git repository detected: requests-lib
  Branch: main
✓ Using source: https://github.com/psf/requests.git (type: git)
[INFO] Cloning repository: https://github.com/psf/requests.git
[INFO] Checking out branch: main
[INFO] Repository cloned: requests (a1b2c3d4)
[INFO] Generating repository digest with gitingest...
[INFO] Analyzing source files...
[INFO] Found 45 source files
[INFO] Parsed 156 documents from repository
✓ Successfully ingested Git repository
  Repository: requests-lib
  Documents: 156
  Total characters: 245678
```

### Step 5: Query Without Persona Filter

```bash
dva kg query "HTTP request methods"
```

**Expected Output:**
```
✓ Query executed (mode: hybrid)

The requests library provides several HTTP request methods through its main API...
[Detailed response with code examples and documentation]
```

### Step 6: Query with Developer Persona

```bash
dva kg query "HTTP request methods" --persona developer
```

**Expected Output:**
```
Persona filter: developer (filtering code/developer context)
✓ Query executed (mode: hybrid)

From the code perspective, the requests library implements HTTP methods in the `requests/api.py` module:

**Main Functions:**
- `get(url, params=None, **kwargs)` - Sends a GET request
- `post(url, data=None, json=None, **kwargs)` - Sends a POST request
- `put(url, data=None, **kwargs)` - Sends a PUT request
- `delete(url, **kwargs)` - Sends a DELETE request

[Code-focused response with function signatures and implementations]
```

### Step 7: Query with Business Persona

```bash
dva kg query "HTTP request documentation" --persona business
```

**Expected Output:**
```
Persona filter: business (filtering docs/business context)
✓ Query executed (mode: hybrid)

[Documentation-focused response, if README or docs were ingested]
```

---

## 🧪 Test Scenario 2: Java Repository

### Step 1: Register Java Repository

```bash
dva data create \
  --name spring-petclinic \
  --source-type git \
  --source-location https://github.com/spring-projects/spring-petclinic.git \
  --git-branch main \
  --description "Spring Framework sample application" \
  --tags "java,spring,mvc,sample"
```

### Step 2: Ingest Repository

```bash
dva kg ingest --source spring-petclinic
```

**Expected Output:**
```
[INFO] Cloning repository: https://github.com/spring-projects/spring-petclinic.git
[INFO] Found 78 source files
[INFO] Parsed 234 documents from repository
✓ Successfully ingested Git repository
  Repository: spring-petclinic
  Documents: 234
  Total characters: 456789
```

### Step 3: Query Java Code

```bash
dva kg query "Spring controller classes" --persona developer
```

**Expected Output:**
```
Persona filter: developer (filtering code/developer context)
✓ Query executed (mode: hybrid)

The Spring PetClinic application contains several controller classes:

**VetController** (src/main/java/.../ VetController.java)
- Handles veterinarian-related requests
- Methods: showVetList(), showResourcesVetList()

**OwnerController** (src/main/java/.../OwnerController.java)
- Manages pet owner operations
- Methods: initCreationForm(), processCreationForm(), findOwners()

[Java-specific code details]
```

---

## 🧪 Test Scenario 3: Repository with SQL/DDL/DML Files

### Step 1: Register Repository with Database Schema

```bash
dva data create \
  --name patient-db-schema \
  --source-type git \
  --source-location https://github.com/your-org/patient-database.git \
  --git-branch main \
  --description "Patient database schema and migrations" \
  --tags "sql,database,schema,healthcare"
```

### Step 2: Ingest Repository

```bash
dva kg ingest --source patient-db-schema
```

**Expected Output:**
```
[INFO] Cloning repository: https://github.com/your-org/patient-database.git
[INFO] Found 25 source files (Python, Java, SQL/DDL/DML)
[INFO] Parsed 89 documents from repository
✓ Successfully ingested Git repository
  Repository: patient-db-schema
  Documents: 89
  Total characters: 123456
```

### Step 3: Query Database Schema

```bash
# Find all tables
dva kg query "show all database tables" --persona developer

# Find patient-related tables
dva kg query "patient tables and columns" --persona developer

# Find foreign key relationships
dva kg query "foreign key constraints" --persona developer
```

**Expected Output:**
```
Persona filter: developer (filtering code/developer context)
✓ Query executed (mode: hybrid)

**Database Tables:**

**patients** (schema/patients.sql)
- Columns: patient_id (INT PRIMARY KEY), first_name (VARCHAR), last_name (VARCHAR), dob (DATE)

**appointments** (schema/appointments.sql)
- Columns: appointment_id (INT PRIMARY KEY), patient_id (INT), appointment_date (DATETIME)
- Foreign Key: patient_id REFERENCES patients(patient_id)

**medical_records** (schema/medical_records.sql)
- Columns: record_id (INT PRIMARY KEY), patient_id (INT), diagnosis (TEXT)
- Foreign Key: patient_id REFERENCES patients(patient_id)

[Data model details with relationships]
```

### Step 4: Query Views and Procedures

```bash
# Find all views
dva kg query "database views" --persona developer

# Find stored procedures
dva kg query "stored procedures for patient data" --persona developer
```

**Expected Output:**
```
**Database Views:**

**patient_summary** (schema/views.sql)
- View combining patient data with appointment counts

**active_patients** (schema/views.sql)
- View showing patients with appointments in last 90 days

**Stored Procedures:**

**get_patient_history** (schema/procedures.sql)
- Parameters: patient_id INT
- Returns patient medical history

**schedule_appointment** (schema/procedures.sql)
- Parameters: patient_id INT, appointment_date DATETIME
- Creates new appointment record
```

---

## 🧪 Test Scenario 4: Private Repository (SSH)

### Step 1: Set Up SSH Keys

```bash
# Ensure SSH keys are configured
ssh -T git@github.com
```

### Step 2: Register Private Repository

```bash
dva data create \
  --name my-private-api \
  --source-type git \
  --source-location git@github.com:myorg/private-api.git \
  --git-branch develop \
  --description "Internal API service" \
  --tags "api,internal,python,fastapi"
```

### Step 3: Ingest with Specific Branch

```bash
dva kg ingest --source my-private-api
```

---

## 🧪 Test Scenario 4: Specific Tag/Release

### Step 1: Register with Tag

```bash
dva data create \
  --name requests-v2 \
  --source-type git \
  --source-location https://github.com/psf/requests.git \
  --git-tag v2.28.0 \
  --description "Requests library v2.28.0" \
  --tags "python,http,release"
```

### Step 2: Ingest Specific Version

```bash
dva kg ingest --source requests-v2
```

**Expected Output:**
```
ℹ Git repository detected: requests-v2
  Tag: v2.28.0
[INFO] Checking out tag: v2.28.0
[INFO] Repository cloned: requests (v2.28.0)
```

---

## 🧪 Test Scenario 5: Neo4j with Persona Filtering

### Step 1: Switch to Neo4j

```bash
dva kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password
```

### Step 2: Ingest Repository

```bash
dva kg ingest --source requests-lib
```

### Step 3: Query with Cypher and Persona

```bash
# Find all developer nodes
dva kg query "MATCH (n) WHERE n.persona = 'developer' RETURN n LIMIT 10" --format cypher

# Find Code::Function nodes
dva kg query "MATCH (n:Code:Function) RETURN n.name, n.file_path LIMIT 20" --format cypher
```

### Step 4: Natural Language Query with Persona

```bash
# Query only code
dva kg query "find all authentication functions" --persona developer

# Query without filter
dva kg query "find all authentication related items"
```

---

## 🔍 Verification Checklist

### ✅ Git Parser
- [ ] Repository clones successfully
- [ ] Branch/tag checkout works
- [ ] Python files are analyzed (AST parsing)
- [ ] Java files are analyzed (regex parsing)
- [ ] Functions and classes are extracted
- [ ] Imports/dependencies are captured
- [ ] Temp directory is cleaned up

### ✅ Persona Support
- [ ] Documents have `persona: "developer"` metadata
- [ ] Neo4j nodes have `Code::` namespace
- [ ] Neo4j nodes have `persona` property
- [ ] LightRAG documents include persona in metadata

### ✅ Query Filtering
- [ ] `--persona developer` filters to code
- [ ] `--persona business` filters to docs
- [ ] No persona flag shows all results
- [ ] Neo4j Cypher queries include persona filter
- [ ] LightRAG queries include persona context

### ✅ Smart Chunking
- [ ] Repository overview document created
- [ ] File-level documents created
- [ ] Class-level documents created
- [ ] Function-level documents created
- [ ] Each chunk has proper metadata

---

## 🐛 Troubleshooting

### Issue: Git Clone Fails

**Error:** `Authentication failed`

**Solution:**
```bash
# For HTTPS, use personal access token
git config --global credential.helper store

# For SSH, verify keys
ssh-add -l
ssh-add ~/.ssh/id_rsa
```

### Issue: gitingest Not Found

**Error:** `ModuleNotFoundError: No module named 'gitingest'`

**Solution:**
```bash
pip install gitingest
# or
uv pip install gitingest
```

### Issue: Large Repository Timeout

**Error:** `Cloning takes too long`

**Solution:**
```bash
# Use shallow clone (modify parser.py)
git.Repo.clone_from(repo_url, temp_dir, depth=1)
```

### Issue: Parse Errors

**Error:** `Syntax error in Python file`

**Solution:**
Files with syntax errors are automatically skipped with warnings. Check logs for details.

### Issue: No Results from Query

**Possible Causes:**
1. Documents still processing (check `dva kg stats`)
2. Persona filter too restrictive
3. Query doesn't match content

**Solution:**
```bash
# Check ingestion status
dva kg stats

# Try without persona filter
dva kg query "your query"

# Try broader query
dva kg query "all nodes" --persona developer
```

---

## 📊 Expected Performance

| Repository Size | Files | Clone Time | Parse Time | Total Docs | Total Time |
|----------------|-------|------------|------------|------------|------------|
| Small (<50 files) | 45 | 5-10s | 10-15s | 100-200 | 15-25s |
| Medium (50-200 files) | 150 | 15-30s | 30-60s | 400-800 | 45-90s |
| Large (200-500 files) | 400 | 30-60s | 60-120s | 1000-2000 | 90-180s |
| Very Large (>500 files) | 1000+ | 60-120s | 120-300s | 2500+ | 180-420s |

---

## 🎉 Success Criteria

Your implementation is working correctly if:

1. ✅ Git repositories clone successfully
2. ✅ Python and Java files are parsed
3. ✅ Functions and classes are extracted
4. ✅ Documents have `persona: "developer"` metadata
5. ✅ Neo4j nodes have `Code::` namespace
6. ✅ Queries with `--persona developer` return code-focused results
7. ✅ Queries with `--persona business` return doc-focused results
8. ✅ Queries without persona return all results
9. ✅ Smart chunking creates multiple document types
10. ✅ Temp directories are cleaned up after ingestion

---

## 📝 Test Report Template

```markdown
# Git Ingestion Test Report

**Date:** 2025-11-22
**Tester:** [Your Name]
**Provider:** LightRAG / Neo4j

## Test Results

### Test 1: Small Python Repository
- Repository: https://github.com/psf/requests.git
- Status: ✅ Pass / ❌ Fail
- Documents Created: 156
- Query Results: ✅ Relevant / ❌ Not Relevant
- Persona Filter: ✅ Working / ❌ Not Working
- Notes: [Any observations]

### Test 2: Java Repository
- Repository: https://github.com/spring-projects/spring-petclinic.git
- Status: ✅ Pass / ❌ Fail
- Documents Created: 234
- Query Results: ✅ Relevant / ❌ Not Relevant
- Persona Filter: ✅ Working / ❌ Not Working
- Notes: [Any observations]

## Issues Found
1. [Issue description]
2. [Issue description]

## Recommendations
1. [Recommendation]
2. [Recommendation]
```

---

## 🚀 Next Steps

After successful testing:

1. **Performance Optimization**
   - Add caching for repeated clones
   - Implement incremental updates
   - Optimize AST parsing

2. **Feature Enhancements**
   - Add more language support (JavaScript, Go, Rust)
   - Extract function call relationships
   - Build dependency graphs
   - Add code metrics (complexity, LOC)

3. **Documentation**
   - Add more query examples
   - Create developer guide
   - Document best practices

4. **Testing**
   - Add unit tests for parsers
   - Add integration tests
   - Performance benchmarks

---

## 📞 Support

If you encounter issues:

1. Check logs: `docker logs dva-lightrag`
2. Verify configuration: `dva kg config show`
3. Check data sources: `dva data list`
4. Review documentation: `docs/GIT_INGESTION.md`

Happy Testing! 🎉
