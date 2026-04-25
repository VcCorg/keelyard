"""Project detector — analyzes a repository to identify language, framework, dependencies, and structure."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


class ProjectAnalysis:
    """Results of project analysis."""

    def __init__(self):
        self.languages: list[str] = []
        self.frameworks: list[str] = []
        self.build_tools: list[str] = []
        self.test_frameworks: list[str] = []
        self.dependencies: list[str] = []
        self.ci_cd: list[str] = []
        self.databases: list[str] = []
        self.api_types: list[str] = []
        self.has_docker: bool = False
        self.project_files: dict[str, bool] = {}
        self.entry_points: list[str] = []
        self.module_structure: list[str] = []
        self.raw_dependencies: dict[str, str] = {}  # name -> version
        self.source_patterns: list[str] = []  # detected source code patterns

    def to_dict(self) -> dict[str, Any]:
        return {
            "languages": self.languages,
            "frameworks": self.frameworks,
            "build_tools": self.build_tools,
            "test_frameworks": self.test_frameworks,
            "dependencies": self.dependencies,
            "ci_cd": self.ci_cd,
            "databases": self.databases,
            "api_types": self.api_types,
            "has_docker": self.has_docker,
            "project_files": self.project_files,
            "entry_points": self.entry_points,
            "module_structure": self.module_structure,
            "raw_dependencies": self.raw_dependencies,
            "source_patterns": self.source_patterns,
        }


# --- File presence detectors ---

LANGUAGE_INDICATORS = {
    "java": ["*.java"],
    "python": ["*.py"],
    "typescript": ["*.ts", "*.tsx"],
    "javascript": ["*.js", "*.jsx"],
    "go": ["*.go"],
    "kotlin": ["*.kt", "*.kts"],
    "rust": ["*.rs"],
    "c#": ["*.cs"],
    "ruby": ["*.rb"],
}

BUILD_FILE_MAP = {
    "pom.xml": ("java", "maven"),
    "build.gradle": ("java", "gradle"),
    "build.gradle.kts": ("java", "gradle"),
    "settings.gradle": ("java", "gradle"),
    "settings.gradle.kts": ("java", "gradle"),
    "package.json": (None, "npm"),
    "yarn.lock": (None, "yarn"),
    "pnpm-lock.yaml": (None, "pnpm"),
    "requirements.txt": ("python", "pip"),
    "pyproject.toml": ("python", "pyproject"),
    "setup.py": ("python", "setuptools"),
    "setup.cfg": ("python", "setuptools"),
    "Pipfile": ("python", "pipenv"),
    "go.mod": ("go", "go-modules"),
    "Cargo.toml": ("rust", "cargo"),
    "Gemfile": ("ruby", "bundler"),
    "Makefile": (None, "make"),
}

CI_FILE_MAP = {
    "Jenkinsfile": "jenkins",
    ".github/workflows": "github-actions",
    "cloudbuild.yaml": "cloud-build",
    ".gitlab-ci.yml": "gitlab-ci",
    ".circleci/config.yml": "circleci",
    "azure-pipelines.yml": "azure-devops",
    ".travis.yml": "travis-ci",
}

DOCKER_FILES = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
DOCKER_SUBDIRS = ["docker", "deploy", ".docker"]


def analyze_project(project_path: Path) -> ProjectAnalysis:
    """Analyze a project directory and return structured results."""
    analysis = ProjectAnalysis()

    _detect_files(project_path, analysis)
    _detect_languages(project_path, analysis)
    _parse_dependencies(project_path, analysis)
    _detect_frameworks(analysis)
    _detect_test_frameworks(analysis)
    _detect_databases(analysis)
    _scan_source_patterns(project_path, analysis)
    _detect_api_types(project_path, analysis)
    _detect_ci_cd(project_path, analysis)
    _detect_docker(project_path, analysis)
    _detect_structure(project_path, analysis)

    # Deduplicate
    analysis.languages = sorted(set(analysis.languages))
    analysis.frameworks = sorted(set(analysis.frameworks))
    analysis.build_tools = sorted(set(analysis.build_tools))
    analysis.test_frameworks = sorted(set(analysis.test_frameworks))
    analysis.ci_cd = sorted(set(analysis.ci_cd))
    analysis.databases = sorted(set(analysis.databases))
    analysis.api_types = sorted(set(analysis.api_types))

    return analysis


def _detect_files(project_path: Path, analysis: ProjectAnalysis) -> None:
    """Record which key files exist."""
    for filename in list(BUILD_FILE_MAP.keys()) + DOCKER_FILES + list(CI_FILE_MAP.keys()):
        path = project_path / filename
        exists = path.exists() or path.is_dir()
        # Check common subdirectories for Docker files
        if not exists and filename in DOCKER_FILES:
            for subdir in DOCKER_SUBDIRS:
                if (project_path / subdir / filename).exists():
                    exists = True
                    break
        analysis.project_files[filename] = exists
        if exists and filename in BUILD_FILE_MAP:
            lang, tool = BUILD_FILE_MAP[filename]
            if lang and lang not in analysis.languages:
                analysis.languages.append(lang)
            if tool not in analysis.build_tools:
                analysis.build_tools.append(tool)


def _detect_languages(project_path: Path, analysis: ProjectAnalysis) -> None:
    """Detect languages by scanning file extensions (limited depth for speed)."""
    ext_counts: dict[str, int] = {}
    max_files = 500
    count = 0

    for p in project_path.rglob("*"):
        if count >= max_files:
            break
        if p.is_file() and not any(part.startswith(".") for part in p.parts[len(project_path.parts):]):
            # Skip hidden dirs, node_modules, .venv, etc.
            rel = str(p.relative_to(project_path))
            if any(skip in rel for skip in ["node_modules", ".venv", "__pycache__", "vendor", "target", "build/", ".git"]):
                continue
            ext = p.suffix.lower()
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
                count += 1

    for lang, patterns in LANGUAGE_INDICATORS.items():
        for pattern in patterns:
            ext = "." + pattern.lstrip("*.")
            if ext_counts.get(ext, 0) > 0:
                if lang not in analysis.languages:
                    analysis.languages.append(lang)


def _parse_dependencies(project_path: Path, analysis: ProjectAnalysis) -> None:
    """Parse dependency files to extract dependency names."""
    # Python: requirements.txt
    req_txt = project_path / "requirements.txt"
    if req_txt.exists():
        _parse_requirements_txt(req_txt, analysis)

    # Python: pyproject.toml
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        _parse_pyproject_toml(pyproject, analysis)

    # JavaScript/TypeScript: package.json
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        _parse_package_json(pkg_json, analysis)

    # Java: pom.xml
    pom = project_path / "pom.xml"
    if pom.exists():
        _parse_pom_xml(pom, analysis)

    # Java: build.gradle / build.gradle.kts
    for gradle_file in ["build.gradle", "build.gradle.kts"]:
        gradle = project_path / gradle_file
        if gradle.exists():
            _parse_gradle(gradle, analysis)

    # Go: go.mod
    gomod = project_path / "go.mod"
    if gomod.exists():
        _parse_go_mod(gomod, analysis)


def _parse_requirements_txt(path: Path, analysis: ProjectAnalysis) -> None:
    """Parse Python requirements.txt."""
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Extract package name (before ==, >=, ~=, etc.)
            match = re.match(r"^([a-zA-Z0-9_-]+)", line)
            if match:
                name = match.group(1).lower()
                analysis.dependencies.append(name)
                # Extract version if present
                ver_match = re.search(r"[=~>!<]+(.+)", line)
                analysis.raw_dependencies[name] = ver_match.group(1).strip() if ver_match else ""
    except OSError:
        pass


def _parse_pyproject_toml(path: Path, analysis: ProjectAnalysis) -> None:
    """Parse Python pyproject.toml for dependencies."""
    try:
        content = path.read_text()
        # Simple extraction — look for dependencies list
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("dependencies") and "=" in stripped:
                in_deps = True
                continue
            if in_deps:
                if stripped.startswith("]"):
                    in_deps = False
                    continue
                match = re.match(r'"([a-zA-Z0-9_-]+)', stripped)
                if match:
                    name = match.group(1).lower()
                    if name not in analysis.dependencies:
                        analysis.dependencies.append(name)
    except OSError:
        pass


def _parse_package_json(path: Path, analysis: ProjectAnalysis) -> None:
    """Parse Node.js package.json."""
    try:
        data = json.loads(path.read_text())
        for dep_key in ["dependencies", "devDependencies", "peerDependencies"]:
            deps = data.get(dep_key, {})
            for name, version in deps.items():
                if name not in analysis.dependencies:
                    analysis.dependencies.append(name)
                    analysis.raw_dependencies[name] = version
    except (OSError, json.JSONDecodeError):
        pass


def _parse_pom_xml(path: Path, analysis: ProjectAnalysis) -> None:
    """Parse Java pom.xml for dependencies."""
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        ns = ""
        # Handle Maven namespace
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        for dep in root.iter(f"{ns}dependency"):
            group = dep.find(f"{ns}groupId")
            artifact = dep.find(f"{ns}artifactId")
            version = dep.find(f"{ns}version")
            if group is not None and artifact is not None:
                dep_name = f"{group.text}:{artifact.text}"
                analysis.dependencies.append(dep_name)
                analysis.raw_dependencies[dep_name] = version.text if version is not None else ""
    except (OSError, ET.ParseError):
        pass


def _parse_gradle(path: Path, analysis: ProjectAnalysis) -> None:
    """Parse Gradle build file for dependencies."""
    try:
        content = path.read_text()
        # Match patterns like: implementation 'group:artifact:version'
        # or implementation("group:artifact:version")
        patterns = [
            r"(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\s*['\"]([^'\"]+)['\"]",
            r'(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\s*\(\s*["\']([^"\']+)["\']\s*\)',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                dep = match.group(1)
                if dep not in analysis.dependencies:
                    analysis.dependencies.append(dep)
                    parts = dep.split(":")
                    if len(parts) >= 2:
                        analysis.raw_dependencies[f"{parts[0]}:{parts[1]}"] = parts[2] if len(parts) > 2 else ""
    except OSError:
        pass


def _parse_go_mod(path: Path, analysis: ProjectAnalysis) -> None:
    """Parse Go go.mod for dependencies."""
    try:
        in_require = False
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("require ("):
                in_require = True
                continue
            if in_require:
                if stripped == ")":
                    in_require = False
                    continue
                parts = stripped.split()
                if len(parts) >= 2:
                    analysis.dependencies.append(parts[0])
                    analysis.raw_dependencies[parts[0]] = parts[1]
            elif stripped.startswith("require "):
                parts = stripped.split()
                if len(parts) >= 3:
                    analysis.dependencies.append(parts[1])
                    analysis.raw_dependencies[parts[1]] = parts[2]
    except OSError:
        pass


# --- Framework detection ---

FRAMEWORK_RULES = {
    "spring-boot": {
        "deps": ["org.springframework.boot:spring-boot-starter", "spring-boot-starter"],
        "skill": "java-spring-boot",
    },
    "fastapi": {
        "deps": ["fastapi"],
        "skill": "python-fastapi",
    },
    "django": {
        "deps": ["django", "Django"],
        "skill": "python-django",
    },
    "flask": {
        "deps": ["flask", "Flask"],
        "skill": "python-flask",
    },
    "react": {
        "deps": ["react", "react-dom"],
        "skill": "typescript-react",
    },
    "next.js": {
        "deps": ["next"],
        "skill": "typescript-nextjs",
    },
    "express": {
        "deps": ["express"],
        "skill": "typescript-node",
    },
    "gin": {
        "deps": ["github.com/gin-gonic/gin"],
        "skill": "go-standard",
    },
}


def _detect_frameworks(analysis: ProjectAnalysis) -> None:
    """Detect frameworks from dependencies."""
    dep_lower = [d.lower() for d in analysis.dependencies]
    for framework, rules in FRAMEWORK_RULES.items():
        for dep_pattern in rules["deps"]:
            if any(dep_pattern.lower() in d for d in dep_lower):
                analysis.frameworks.append(framework)
                break


# --- Test framework detection ---

TEST_FRAMEWORK_RULES = {
    "junit": ["org.junit.jupiter:junit-jupiter", "junit-jupiter", "junit", "spring-boot-starter-test"],
    "pytest": ["pytest"],
    "jest": ["jest", "@jest/core"],
    "mocha": ["mocha"],
    "testing-library": ["@testing-library/react", "@testing-library/jest-dom"],
    "mockito": ["org.mockito:mockito-core", "mockito-core"],
    "testng": ["org.testng:testng"],
}


def _detect_test_frameworks(analysis: ProjectAnalysis) -> None:
    """Detect test frameworks from dependencies."""
    dep_lower = [d.lower() for d in analysis.dependencies]
    for framework, patterns in TEST_FRAMEWORK_RULES.items():
        for pattern in patterns:
            if any(pattern.lower() in d for d in dep_lower):
                analysis.test_frameworks.append(framework)
                break


# --- Database detection ---

DATABASE_RULES = {
    "spanner": ["com.google.cloud:google-cloud-spanner", "google-cloud-spanner", "spring-cloud-gcp-starter-data-spanner", "spanner"],
    "bigquery": ["com.google.cloud:google-cloud-bigquery", "google-cloud-bigquery", "spring-cloud-gcp-starter-bigquery", "bigquery"],
    "postgresql": ["org.postgresql:postgresql", "psycopg2", "psycopg", "asyncpg", "pg"],
    "mysql": ["mysql-connector", "pymysql", "mysql2"],
    "mongodb": ["pymongo", "motor", "mongoose", "mongodb"],
    "redis": ["redis", "ioredis", "aioredis"],
    "sqlite": ["sqlite3", "better-sqlite3"],
    "elasticsearch": ["elasticsearch", "@elastic/elasticsearch"],
}


def _detect_databases(analysis: ProjectAnalysis) -> None:
    dep_lower = [d.lower() for d in analysis.dependencies]
    for db, patterns in DATABASE_RULES.items():
        for pattern in patterns:
            if any(pattern.lower() in d for d in dep_lower):
                analysis.databases.append(db)
                break


# --- API type detection ---

API_RULES = {
    "rest": ["spring-boot-starter-web", "fastapi", "express", "flask", "gin-gonic/gin", "@nestjs/core"],
    "grpc": ["grpcio", "io.grpc:grpc-core", "@grpc/grpc-js", "google.golang.org/grpc"],
    "graphql": ["graphql", "apollo-server", "ariadne", "strawberry-graphql"],
}


# Patterns to scan for in source files to verify API/framework usage
SOURCE_SCAN_PATTERNS = [
    "@RestController",
    "@Controller",
    "app.route",
    "router.get",
    "router.post",
    "@app.get",
    "@app.post",
]


def _scan_source_patterns(project_path: Path, analysis: ProjectAnalysis) -> None:
    """Scan source files for key patterns (annotations, decorators, etc.).

    This enables smarter skill matching — e.g., only classify a project as
    REST if it actually has controller annotations, not just a web dependency.
    """
    src_dirs = [project_path / "src" / "main" / "java",  # Java/Maven
                project_path / "src",                      # General
                project_path / "app",                      # Django/Rails
                project_path / "lib"]                      # Libraries

    skip_segments = {"node_modules", ".venv", "__pycache__", "target", "build", ".git", "test", "tests"}
    scan_exts = {".java", ".py", ".ts", ".js", ".go", ".kt"}
    max_files = 300
    count = 0

    for src_dir in src_dirs:
        if not src_dir.exists():
            continue
        for p in src_dir.rglob("*"):
            if count >= max_files:
                break
            if not p.is_file() or p.suffix.lower() not in scan_exts:
                continue
            if any(seg in p.parts for seg in skip_segments):
                continue
            try:
                content = p.read_text(errors="ignore")
                for pattern in SOURCE_SCAN_PATTERNS:
                    if pattern in content and pattern not in analysis.source_patterns:
                        analysis.source_patterns.append(pattern)
                count += 1
            except OSError:
                continue


def _detect_api_types(project_path: Path, analysis: ProjectAnalysis) -> None:
    """Detect API types from dependencies, refined by source pattern scanning.

    For Java projects with spring-boot-starter-web, we require actual
    @RestController or @Controller annotations to classify as REST.
    This avoids false positives on model/library projects that pull
    the web starter transitively.
    """
    dep_lower = [d.lower() for d in analysis.dependencies]
    rest_controller_annotations = {"@RestController", "@Controller"}
    python_route_patterns = {"app.route", "@app.get", "@app.post"}
    node_route_patterns = {"router.get", "router.post"}

    for api_type, patterns in API_RULES.items():
        for pattern in patterns:
            if any(pattern.lower() in d for d in dep_lower):
                # For Java web dependency: verify controllers exist in source
                if pattern == "spring-boot-starter-web":
                    if rest_controller_annotations & set(analysis.source_patterns):
                        analysis.api_types.append(api_type)
                    # else: skip — likely a model/library project
                else:
                    analysis.api_types.append(api_type)
                break


def _detect_ci_cd(project_path: Path, analysis: ProjectAnalysis) -> None:
    for filename, ci_name in CI_FILE_MAP.items():
        if (project_path / filename).exists() or (project_path / filename).is_dir():
            analysis.ci_cd.append(ci_name)


def _detect_docker(project_path: Path, analysis: ProjectAnalysis) -> None:
    for filename in DOCKER_FILES:
        if (project_path / filename).exists():
            analysis.has_docker = True
            return
    # Check common subdirectories (e.g., docker/, deploy/)
    for subdir in DOCKER_SUBDIRS:
        sub_path = project_path / subdir
        if sub_path.is_dir():
            for filename in DOCKER_FILES:
                if (sub_path / filename).exists():
                    analysis.has_docker = True
                    return


def _detect_structure(project_path: Path, analysis: ProjectAnalysis) -> None:
    """Detect top-level module structure and entry points."""
    # Top-level directories (exclude hidden, common non-source)
    skip = {".git", ".venv", "node_modules", "__pycache__", ".idea", ".vscode",
            ".gradle", ".mvn", "target", "build", "dist", "out", ".skills", ".opencode"}
    for item in sorted(project_path.iterdir()):
        if item.is_dir() and item.name not in skip and not item.name.startswith("."):
            analysis.module_structure.append(item.name + "/")

    # Entry points
    entry_candidates = [
        "src/main/java",
        "src/main.py",
        "src/app.py",
        "main.py",
        "app.py",
        "index.ts",
        "index.js",
        "src/index.ts",
        "src/index.js",
        "cmd/main.go",
        "main.go",
    ]
    for ep in entry_candidates:
        if (project_path / ep).exists():
            analysis.entry_points.append(ep)
