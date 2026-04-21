"""Code analysis utilities for extracting structure from source code.

Supports Python and Java code parsing to extract:
- Functions/Methods
- Classes
- Imports/Dependencies
- Docstrings/Comments
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class CodeAnalyzer:
    """Base class for code analysis."""
    
    def __init__(self, language: str):
        self.language = language
    
    def analyze_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """
        Analyze a source code file.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Dictionary with extracted code structure
        """
        raise NotImplementedError


class PythonAnalyzer(CodeAnalyzer):
    """Analyzer for Python code."""
    
    def __init__(self):
        super().__init__("python")
    
    def analyze_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """
        Analyze Python file using AST.
        
        Returns:
            {
                "file_path": str,
                "language": "python",
                "imports": List[str],
                "classes": List[Dict],
                "functions": List[Dict],
                "summary": str
            }
        """
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {
                "file_path": str(file_path),
                "language": "python",
                "error": f"Syntax error: {e}",
                "imports": [],
                "classes": [],
                "functions": [],
                "summary": f"Failed to parse {file_path.name}"
            }
        
        imports = []
        classes = []
        functions = []
        
        for node in ast.walk(tree):
            # Extract imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
            
            # Extract classes
            elif isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "type": "class",
                    "line_start": node.lineno,
                    "line_end": node.end_lineno,
                    "docstring": ast.get_docstring(node),
                    "methods": [],
                    "bases": [self._get_name(base) for base in node.bases]
                }
                
                # Extract methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = {
                            "name": item.name,
                            "type": "method",
                            "line_start": item.lineno,
                            "line_end": item.end_lineno,
                            "docstring": ast.get_docstring(item),
                            "args": [arg.arg for arg in item.args.args],
                            "is_async": isinstance(item, ast.AsyncFunctionDef)
                        }
                        class_info["methods"].append(method_info)
                
                classes.append(class_info)
            
            # Extract top-level functions
            elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                function_info = {
                    "name": node.name,
                    "type": "function",
                    "line_start": node.lineno,
                    "line_end": node.end_lineno,
                    "docstring": ast.get_docstring(node),
                    "args": [arg.arg for arg in node.args.args],
                    "is_async": isinstance(node, ast.AsyncFunctionDef)
                }
                functions.append(function_info)
        
        # Generate summary
        summary = self._generate_summary(file_path, imports, classes, functions)
        
        return {
            "file_path": str(file_path),
            "language": "python",
            "imports": list(set(imports)),  # Deduplicate
            "classes": classes,
            "functions": functions,
            "summary": summary
        }
    
    def _get_name(self, node) -> str:
        """Extract name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)
    
    def _generate_summary(
        self,
        file_path: Path,
        imports: List[str],
        classes: List[Dict],
        functions: List[Dict]
    ) -> str:
        """Generate a quick summary of the file."""
        parts = [f"Python module: {file_path.name}"]
        
        if imports:
            parts.append(f"Imports: {len(set(imports))} modules")
        
        if classes:
            class_names = [c["name"] for c in classes]
            parts.append(f"Classes: {', '.join(class_names)}")
        
        if functions:
            func_names = [f["name"] for f in functions]
            parts.append(f"Functions: {', '.join(func_names)}")
        
        return " | ".join(parts)


class JavaAnalyzer(CodeAnalyzer):
    """Analyzer for Java code using regex patterns."""
    
    def __init__(self):
        super().__init__("java")
    
    def analyze_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """
        Analyze Java file using regex patterns.
        
        Returns:
            {
                "file_path": str,
                "language": "java",
                "package": str,
                "imports": List[str],
                "classes": List[Dict],
                "interfaces": List[Dict],
                "summary": str
            }
        """
        # Extract package
        package_match = re.search(r'package\s+([\w.]+);', content)
        package = package_match.group(1) if package_match else ""
        
        # Extract imports
        imports = re.findall(r'import\s+([\w.]+);', content)
        
        # Extract classes
        classes = self._extract_java_classes(content)
        
        # Extract interfaces
        interfaces = self._extract_java_interfaces(content)
        
        # Generate summary
        summary = self._generate_summary(file_path, package, imports, classes, interfaces)
        
        return {
            "file_path": str(file_path),
            "language": "java",
            "package": package,
            "imports": imports,
            "classes": classes,
            "interfaces": interfaces,
            "summary": summary
        }
    
    def _extract_java_classes(self, content: str) -> List[Dict]:
        """Extract Java class definitions."""
        classes = []
        
        # Pattern for class declaration
        class_pattern = r'(public|private|protected)?\s*(abstract|final)?\s*class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?'
        
        for match in re.finditer(class_pattern, content):
            visibility = match.group(1) or "package-private"
            modifier = match.group(2) or ""
            name = match.group(3)
            extends = match.group(4)
            implements = match.group(5)
            
            class_info = {
                "name": name,
                "type": "class",
                "visibility": visibility,
                "modifier": modifier,
                "extends": extends,
                "implements": [i.strip() for i in implements.split(",")] if implements else [],
                "methods": self._extract_java_methods(content, name)
            }
            classes.append(class_info)
        
        return classes
    
    def _extract_java_interfaces(self, content: str) -> List[Dict]:
        """Extract Java interface definitions."""
        interfaces = []
        
        # Pattern for interface declaration
        interface_pattern = r'(public|private|protected)?\s*interface\s+(\w+)(?:\s+extends\s+([\w,\s]+))?'
        
        for match in re.finditer(interface_pattern, content):
            visibility = match.group(1) or "package-private"
            name = match.group(2)
            extends = match.group(3)
            
            interface_info = {
                "name": name,
                "type": "interface",
                "visibility": visibility,
                "extends": [e.strip() for e in extends.split(",")] if extends else []
            }
            interfaces.append(interface_info)
        
        return interfaces
    
    def _extract_java_methods(self, content: str, class_name: str) -> List[Dict]:
        """Extract methods from a Java class."""
        methods = []
        
        # Simple method pattern (not perfect but good enough)
        method_pattern = r'(public|private|protected)\s+(static\s+)?([\w<>[\]]+)\s+(\w+)\s*\((.*?)\)'
        
        for match in re.finditer(method_pattern, content):
            visibility = match.group(1)
            is_static = bool(match.group(2))
            return_type = match.group(3)
            name = match.group(4)
            params = match.group(5)
            
            method_info = {
                "name": name,
                "type": "method",
                "visibility": visibility,
                "is_static": is_static,
                "return_type": return_type,
                "parameters": params.strip() if params else ""
            }
            methods.append(method_info)
        
        return methods
    
    def _generate_summary(
        self,
        file_path: Path,
        package: str,
        imports: List[str],
        classes: List[Dict],
        interfaces: List[Dict]
    ) -> str:
        """Generate a quick summary of the Java file."""
        parts = [f"Java file: {file_path.name}"]
        
        if package:
            parts.append(f"Package: {package}")
        
        if imports:
            parts.append(f"Imports: {len(imports)} modules")
        
        if classes:
            class_names = [c["name"] for c in classes]
            parts.append(f"Classes: {', '.join(class_names)}")
        
        if interfaces:
            interface_names = [i["name"] for i in interfaces]
            parts.append(f"Interfaces: {', '.join(interface_names)}")
        
        return " | ".join(parts)


def get_analyzer(language: str) -> Optional[CodeAnalyzer]:
    """
    Get appropriate code analyzer for the language.
    
    Args:
        language: Programming language (python, java, sql)
        
    Returns:
        CodeAnalyzer instance or None if unsupported
    """
    analyzers = {
        "python": PythonAnalyzer,
        "java": JavaAnalyzer,
        "sql": SQLAnalyzer,
    }
    
    analyzer_class = analyzers.get(language.lower())
    return analyzer_class() if analyzer_class else None


class SQLAnalyzer(CodeAnalyzer):
    """Analyzer for SQL DDL/DML files."""
    
    def __init__(self):
        super().__init__("sql")
    
    def analyze_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """
        Analyze SQL file for DDL and DML statements.
        
        Returns:
            {
                "file_path": str,
                "language": "sql",
                "tables": List[Dict],
                "views": List[Dict],
                "procedures": List[Dict],
                "indexes": List[Dict],
                "constraints": List[Dict],
                "summary": str
            }
        """
        content_upper = content.upper()
        
        # Extract tables
        tables = self._extract_tables(content)
        
        # Extract views
        views = self._extract_views(content)
        
        # Extract stored procedures/functions
        procedures = self._extract_procedures(content)
        
        # Extract indexes
        indexes = self._extract_indexes(content)
        
        # Extract constraints
        constraints = self._extract_constraints(content)
        
        # Detect file type (DDL vs DML)
        file_type = self._detect_file_type(content_upper)
        
        # Generate summary
        summary = self._generate_summary(file_path, file_type, tables, views, procedures)
        
        return {
            "file_path": str(file_path),
            "language": "sql",
            "file_type": file_type,
            "tables": tables,
            "views": views,
            "procedures": procedures,
            "indexes": indexes,
            "constraints": constraints,
            "summary": summary
        }
    
    def _detect_file_type(self, content_upper: str) -> str:
        """Detect if file is DDL, DML, or mixed."""
        has_ddl = any(keyword in content_upper for keyword in ["CREATE TABLE", "ALTER TABLE", "CREATE VIEW"])
        has_dml = any(keyword in content_upper for keyword in ["INSERT INTO", "UPDATE ", "DELETE FROM"])
        
        if has_ddl and has_dml:
            return "mixed"
        elif has_ddl:
            return "ddl"
        elif has_dml:
            return "dml"
        return "unknown"
    
    def _extract_tables(self, content: str) -> List[Dict]:
        """Extract CREATE TABLE statements."""
        tables = []
        
        # Pattern for CREATE TABLE
        table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"\[]?\w+[`"\]]?\.?[`"\[]?\w+[`"\]]?)\s*\((.*?)\);'
        
        for match in re.finditer(table_pattern, content, re.IGNORECASE | re.DOTALL):
            table_name = match.group(1).strip('`"[]')
            columns_def = match.group(2)
            
            # Extract columns
            columns = self._extract_columns(columns_def)
            
            tables.append({
                "name": table_name,
                "type": "table",
                "columns": columns,
                "column_count": len(columns)
            })
        
        return tables
    
    def _extract_columns(self, columns_def: str) -> List[Dict]:
        """Extract column definitions from CREATE TABLE."""
        columns = []
        
        # Split by comma (simple approach)
        lines = columns_def.split(',')
        
        for line in lines:
            line = line.strip()
            if not line or line.upper().startswith(('PRIMARY KEY', 'FOREIGN KEY', 'CONSTRAINT', 'UNIQUE', 'CHECK', 'INDEX')):
                continue
            
            # Extract column name and type
            parts = line.split()
            if len(parts) >= 2:
                col_name = parts[0].strip('`"[]')
                col_type = parts[1].upper()
                
                # Check for constraints
                is_primary = 'PRIMARY KEY' in line.upper()
                is_nullable = 'NOT NULL' not in line.upper()
                has_default = 'DEFAULT' in line.upper()
                
                columns.append({
                    "name": col_name,
                    "type": col_type,
                    "primary_key": is_primary,
                    "nullable": is_nullable,
                    "has_default": has_default
                })
        
        return columns
    
    def _extract_views(self, content: str) -> List[Dict]:
        """Extract CREATE VIEW statements."""
        views = []
        
        # Pattern for CREATE VIEW
        view_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([`"\[]?\w+[`"\]]?\.?[`"\[]?\w+[`"\]]?)\s+AS\s+(.*?);'
        
        for match in re.finditer(view_pattern, content, re.IGNORECASE | re.DOTALL):
            view_name = match.group(1).strip('`"[]')
            view_query = match.group(2).strip()
            
            views.append({
                "name": view_name,
                "type": "view",
                "query": view_query[:200] + "..." if len(view_query) > 200 else view_query
            })
        
        return views
    
    def _extract_procedures(self, content: str) -> List[Dict]:
        """Extract stored procedures and functions."""
        procedures = []
        
        # Pattern for CREATE PROCEDURE/FUNCTION
        proc_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?(PROCEDURE|FUNCTION)\s+([`"\[]?\w+[`"\]]?\.?[`"\[]?\w+[`"\]]?)\s*\((.*?)\)'
        
        for match in re.finditer(proc_pattern, content, re.IGNORECASE | re.DOTALL):
            proc_type = match.group(1).lower()
            proc_name = match.group(2).strip('`"[]')
            parameters = match.group(3).strip()
            
            procedures.append({
                "name": proc_name,
                "type": proc_type,
                "parameters": parameters[:100] + "..." if len(parameters) > 100 else parameters
            })
        
        return procedures
    
    def _extract_indexes(self, content: str) -> List[Dict]:
        """Extract CREATE INDEX statements."""
        indexes = []
        
        # Pattern for CREATE INDEX
        index_pattern = r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+([`"\[]?\w+[`"\]]?)\s+ON\s+([`"\[]?\w+[`"\]]?\.?[`"\[]?\w+[`"\]]?)\s*\((.*?)\)'
        
        for match in re.finditer(index_pattern, content, re.IGNORECASE):
            index_name = match.group(1).strip('`"[]')
            table_name = match.group(2).strip('`"[]')
            columns = match.group(3).strip()
            
            indexes.append({
                "name": index_name,
                "type": "index",
                "table": table_name,
                "columns": columns
            })
        
        return indexes
    
    def _extract_constraints(self, content: str) -> List[Dict]:
        """Extract constraint definitions."""
        constraints = []
        
        # Pattern for ALTER TABLE ADD CONSTRAINT
        constraint_pattern = r'ALTER\s+TABLE\s+([`"\[]?\w+[`"\]]?\.?[`"\[]?\w+[`"\]]?)\s+ADD\s+CONSTRAINT\s+([`"\[]?\w+[`"\]]?)\s+(.*?);'
        
        for match in re.finditer(constraint_pattern, content, re.IGNORECASE | re.DOTALL):
            table_name = match.group(1).strip('`"[]')
            constraint_name = match.group(2).strip('`"[]')
            constraint_def = match.group(3).strip()
            
            # Determine constraint type
            constraint_type = "unknown"
            if "FOREIGN KEY" in constraint_def.upper():
                constraint_type = "foreign_key"
            elif "PRIMARY KEY" in constraint_def.upper():
                constraint_type = "primary_key"
            elif "UNIQUE" in constraint_def.upper():
                constraint_type = "unique"
            elif "CHECK" in constraint_def.upper():
                constraint_type = "check"
            
            constraints.append({
                "name": constraint_name,
                "type": constraint_type,
                "table": table_name,
                "definition": constraint_def[:100] + "..." if len(constraint_def) > 100 else constraint_def
            })
        
        return constraints
    
    def _generate_summary(
        self,
        file_path: Path,
        file_type: str,
        tables: List[Dict],
        views: List[Dict],
        procedures: List[Dict]
    ) -> str:
        """Generate a quick summary of the SQL file."""
        parts = [f"SQL {file_type.upper()} file: {file_path.name}"]
        
        if tables:
            table_names = [t["name"] for t in tables]
            parts.append(f"Tables: {', '.join(table_names)}")
        
        if views:
            view_names = [v["name"] for v in views]
            parts.append(f"Views: {', '.join(view_names)}")
        
        if procedures:
            proc_names = [p["name"] for p in procedures]
            parts.append(f"Procedures/Functions: {', '.join(proc_names)}")
        
        return " | ".join(parts)


def detect_language(file_path: Path) -> Optional[str]:
    """
    Detect programming language from file extension.
    
    Args:
        file_path: Path to source file
        
    Returns:
        Language name or None if unknown
    """
    extension_map = {
        ".py": "python",
        ".java": "java",
        ".sql": "sql",
        ".ddl": "sql",
        ".dml": "sql",
    }
    
    return extension_map.get(file_path.suffix.lower())
