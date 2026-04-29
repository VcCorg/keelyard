# SQL/DDL/DML Data Model Support

## 🎯 Overview

The Git ingestion feature now includes comprehensive support for SQL database schema files (DDL) and data manipulation files (DML), enabling data model analysis and knowledge graph ingestion.

---

## ✅ What's Supported

### File Extensions
- `.sql` - General SQL files
- `.ddl` - Data Definition Language files
- `.dml` - Data Manipulation Language files

### Extracted Elements

#### **Tables** (CREATE TABLE)
- Table names
- Column definitions (name, type, constraints)
- Primary keys
- Nullable/NOT NULL constraints
- Default values
- Column count

#### **Views** (CREATE VIEW)
- View names
- View queries (SELECT statements)

#### **Stored Procedures & Functions**
- Procedure/function names
- Parameter definitions
- Procedure vs function distinction

#### **Indexes** (CREATE INDEX)
- Index names
- Target tables
- Indexed columns
- Unique vs regular indexes

#### **Constraints** (ALTER TABLE ADD CONSTRAINT)
- Constraint names
- Constraint types (FOREIGN KEY, PRIMARY KEY, UNIQUE, CHECK)
- Target tables
- Constraint definitions

---

## 🔍 SQLAnalyzer Implementation

### Architecture

```python
class SQLAnalyzer(CodeAnalyzer):
    """Analyzer for SQL DDL/DML files."""
    
    def analyze_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """
        Returns:
        {
            "file_path": str,
            "language": "sql",
            "file_type": "ddl" | "dml" | "mixed",
            "tables": List[Dict],
            "views": List[Dict],
            "procedures": List[Dict],
            "indexes": List[Dict],
            "constraints": List[Dict],
            "summary": str
        }
        """
```

### Extraction Methods

1. **`_extract_tables()`** - Parses CREATE TABLE statements
2. **`_extract_columns()`** - Extracts column definitions from tables
3. **`_extract_views()`** - Parses CREATE VIEW statements
4. **`_extract_procedures()`** - Parses CREATE PROCEDURE/FUNCTION
5. **`_extract_indexes()`** - Parses CREATE INDEX statements
6. **`_extract_constraints()`** - Parses ALTER TABLE ADD CONSTRAINT
7. **`_detect_file_type()`** - Determines if file is DDL, DML, or mixed

---

## 📊 Document Structure

### File Overview Document
```json
{
  "title": "repo-name/schema/patients.sql",
  "content": "SQL DDL file: patients.sql | Tables: patients, patient_history",
  "metadata": {
    "language": "sql",
    "file_type": "ddl",
    "tables": ["patients", "patient_history"],
    "views": [],
    "procedures": [],
    "persona": "developer"
  }
}
```

### Table Document
```json
{
  "title": "repo-name/schema/patients.sql::Table::patients",
  "content": "Table: patients\n\nColumns (5):\n  - patient_id: INT PRIMARY KEY NOT NULL\n  - first_name: VARCHAR\n  - last_name: VARCHAR\n  - dob: DATE\n  - email: VARCHAR",
  "metadata": {
    "doc_type": "table",
    "table_name": "patients",
    "column_count": 5,
    "columns": ["patient_id", "first_name", "last_name", "dob", "email"],
    "persona": "developer"
  }
}
```

### View Document
```json
{
  "title": "repo-name/schema/views.sql::View::patient_summary",
  "content": "View: patient_summary\n\nQuery:\nSELECT p.patient_id, p.first_name, p.last_name, COUNT(a.appointment_id) as appointment_count FROM patients p LEFT JOIN appointments a ON p.patient_id = a.patient_id GROUP BY p.patient_id",
  "metadata": {
    "doc_type": "view",
    "view_name": "patient_summary",
    "persona": "developer"
  }
}
```

### Procedure Document
```json
{
  "title": "repo-name/schema/procedures.sql::Procedure::get_patient_history",
  "content": "Procedure: get_patient_history\n\nParameters: patient_id INT",
  "metadata": {
    "doc_type": "procedure",
    "procedure_name": "get_patient_history",
    "persona": "developer"
  }
}
```

---

## 🎯 Use Cases

### 1. Database Schema Discovery
```bash
# Find all tables in the database
`agent kg query "show all database tables" --persona developer

# Find tables related to patients
`agent kg query "patient tables" --persona developer
```

### 2. Column Analysis
```bash
# Find tables with specific columns
`agent kg query "tables with email column" --persona developer

# Find primary key definitions
`agent kg query "primary key columns" --persona developer
```

### 3. Relationship Discovery
```bash
# Find foreign key relationships
`agent kg query "foreign key constraints" --persona developer

# Find tables related to a specific table
`agent kg query "tables referencing patients table" --persona developer
```

### 4. View and Procedure Discovery
```bash
# Find all views
`agent kg query "database views" --persona developer

# Find stored procedures
`agent kg query "stored procedures for patient data" --persona developer
```

### 5. Data Model Documentation
```bash
# Get complete schema overview
`agent kg query "database schema structure" --persona developer

# Find indexes for performance optimization
`agent kg query "database indexes" --persona developer
```

---

## 📝 Example SQL File

```sql
-- patients.sql

CREATE TABLE patients (
    patient_id INT PRIMARY KEY NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    dob DATE,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE appointments (
    appointment_id INT PRIMARY KEY NOT NULL,
    patient_id INT NOT NULL,
    appointment_date DATETIME NOT NULL,
    status VARCHAR(50),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

CREATE VIEW patient_summary AS
SELECT 
    p.patient_id,
    p.first_name,
    p.last_name,
    COUNT(a.appointment_id) as appointment_count
FROM patients p
LEFT JOIN appointments a ON p.patient_id = a.patient_id
GROUP BY p.patient_id;

CREATE INDEX idx_patient_email ON patients(email);

CREATE PROCEDURE get_patient_history(IN patient_id INT)
BEGIN
    SELECT * FROM appointments WHERE patient_id = patient_id;
END;
```

### Extracted Information

**Tables:**
- `patients` (6 columns: patient_id, first_name, last_name, dob, email, created_at)
- `appointments` (4 columns: appointment_id, patient_id, appointment_date, status)

**Views:**
- `patient_summary` (aggregates patient data with appointment counts)

**Indexes:**
- `idx_patient_email` on `patients(email)`

**Procedures:**
- `get_patient_history(patient_id INT)` - retrieves appointment history

**Constraints:**
- Foreign key: `appointments.patient_id` → `patients.patient_id`

---

## 🔧 Neo4j Schema

### Node Labels

```cypher
// Tables
(:Code:Table {
    name: "patients",
    column_count: 6,
    columns: ["patient_id", "first_name", ...],
    persona: "developer"
})

// Views
(:Code:View {
    name: "patient_summary",
    query: "SELECT ...",
    persona: "developer"
})

// Procedures
(:Code:Procedure {
    name: "get_patient_history",
    parameters: "patient_id INT",
    persona: "developer"
})
```

### Potential Relationships

```cypher
// Table to column relationships
(:Code:Table)-[:HAS_COLUMN]->(:Code:Column)

// Foreign key relationships
(:Code:Table)-[:REFERENCES {constraint: "fk_name"}]->(:Code:Table)

// View dependencies
(:Code:View)-[:DEPENDS_ON]->(:Code:Table)

// Procedure dependencies
(:Code:Procedure)-[:ACCESSES]->(:Code:Table)
```

---

## 🎓 Query Examples

### Find All Tables
```bash
`agent kg query "MATCH (t:Code:Table) RETURN t.name, t.column_count" --format cypher --persona developer
```

### Find Tables with Foreign Keys
```bash
`agent kg query "tables with foreign key constraints" --persona developer
```

### Find Views Using Specific Table
```bash
`agent kg query "views that use patients table" --persona developer
```

### Get Complete Schema for a Domain
```bash
`agent kg query "patient database schema including tables, views, and procedures" --persona developer
```

---

## 🚀 Benefits

### 1. **Automated Data Model Documentation**
- Automatically extract and document database schemas
- Keep documentation in sync with code
- Query-able data model knowledge base

### 2. **Impact Analysis**
- Find all tables affected by a change
- Identify dependent views and procedures
- Understand foreign key relationships

### 3. **Schema Evolution Tracking**
- Track schema changes across Git commits
- Compare schemas between branches/tags
- Understand migration history

### 4. **Developer Onboarding**
- New developers can query the data model
- Understand table relationships quickly
- Find relevant stored procedures

### 5. **Data Governance**
- Identify sensitive columns (email, SSN, etc.)
- Track data lineage through views
- Audit database access patterns

---

## 🔍 Supported SQL Dialects

The SQLAnalyzer uses regex patterns that work with most SQL dialects:

- ✅ **MySQL**
- ✅ **PostgreSQL**
- ✅ **SQL Server** (T-SQL)
- ✅ **Oracle** (PL/SQL)
- ✅ **SQLite**
- ✅ **MariaDB**

### Dialect-Specific Notes

- **Backticks** (MySQL): `` `table_name` ``
- **Double Quotes** (PostgreSQL): `"table_name"`
- **Square Brackets** (SQL Server): `[table_name]`

All are supported and normalized during parsing.

---

## 📊 Statistics

For a typical database schema repository:

| Metric | Example Value |
|--------|---------------|
| SQL Files | 15-50 files |
| Tables Extracted | 20-100 tables |
| Views Extracted | 5-20 views |
| Procedures Extracted | 10-50 procedures |
| Total Documents Created | 100-500 documents |
| Ingestion Time | 10-30 seconds |

---

## 🎉 Summary

The SQL/DDL/DML support enables:
- ✅ **Comprehensive data model analysis**
- ✅ **Automatic schema documentation**
- ✅ **Query-able database knowledge**
- ✅ **Developer persona integration**
- ✅ **Multi-dialect support**
- ✅ **Smart chunking by database objects**

This makes the knowledge graph a powerful tool for understanding and querying database schemas alongside application code!
