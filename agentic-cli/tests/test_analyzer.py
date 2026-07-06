"""Tests for project analyzer — detector and matcher modules."""

import json
from pathlib import Path

from agentic_cli.analyzer.detector import ProjectAnalysis, analyze_project
from agentic_cli.analyzer.matcher import match_skills, load_registry


def _make_java_model_project(tmp_path: Path) -> Path:
    """Create a minimal Java model project (no REST controllers)."""
    # pom.xml with spring-boot-starter-web + liquibase-spanner
    pom = tmp_path / "pom.xml"
    pom.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>my-model</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>com.google.cloud</groupId>
            <artifactId>spring-cloud-gcp-starter-data-spanner</artifactId>
        </dependency>
        <dependency>
            <groupId>org.liquibase</groupId>
            <artifactId>liquibase-core</artifactId>
        </dependency>
        <dependency>
            <groupId>org.liquibase.ext</groupId>
            <artifactId>liquibase-spanner</artifactId>
        </dependency>
    </dependencies>
</project>
""")

    # Java entity file — NO @RestController
    java_dir = tmp_path / "src" / "main" / "java" / "com" / "example" / "model"
    java_dir.mkdir(parents=True)
    (java_dir / "Patient.java").write_text("""
package com.example.model;

import javax.persistence.Entity;
import javax.persistence.Id;

@Entity
public class Patient {
    @Id
    private String patientId;
    private String lastName;
}
""")
    return tmp_path


def _make_java_rest_project(tmp_path: Path) -> Path:
    """Create a minimal Java REST API project (with @RestController)."""
    pom = tmp_path / "pom.xml"
    pom.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>my-api</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
    </dependencies>
</project>
""")

    java_dir = tmp_path / "src" / "main" / "java" / "com" / "example" / "api"
    java_dir.mkdir(parents=True)
    (java_dir / "PatientController.java").write_text("""
package com.example.api;

import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;

@RestController
public class PatientController {
    @GetMapping("/patients")
    public String list() { return "[]"; }
}
""")
    return tmp_path


def _load_test_registry() -> dict:
    """Load the real registry.json from keel-skills."""
    registry_path = Path(__file__).parent.parent.parent / "keel-skills"
    if not (registry_path / "registry.json").exists():
        # Fallback: inline minimal registry for CI
        return {
            "skills": [
                {
                    "name": "liquibase-spanner",
                    "description": "Liquibase with Cloud Spanner",
                    "tags": ["database", "spanner", "liquibase"],
                    "auto_detect": {
                        "dependencies_all": ["org.liquibase:liquibase-core", "liquibase-spanner"]
                    }
                },
                {
                    "name": "api-rest",
                    "description": "RESTful API design",
                    "tags": ["api", "rest", "web"],
                    "auto_detect": {
                        "dependencies": ["spring-boot-starter-web", "fastapi", "express"],
                        "source_patterns": ["@RestController", "@Controller", "app.route"]
                    }
                },
                {
                    "name": "database-spanner",
                    "description": "Cloud Spanner",
                    "tags": ["database", "spanner"],
                    "auto_detect": {
                        "dependencies": ["spring-cloud-gcp-starter-data-spanner"]
                    }
                },
                {
                    "name": "java-maven",
                    "description": "Maven",
                    "tags": ["java", "maven"],
                    "auto_detect": {
                        "files": ["pom.xml"]
                    }
                },
            ]
        }
    return json.loads((registry_path / "registry.json").read_text())


# --- Tests ---


class TestDetectorApiTypes:
    """Test that _detect_api_types uses source patterns for Java projects."""

    def test_model_project_not_classified_as_rest(self, tmp_path):
        """A Java project with spring-boot-starter-web but NO controllers
        should NOT be classified as REST."""
        project = _make_java_model_project(tmp_path)
        analysis = analyze_project(project)

        assert "rest" not in analysis.api_types, (
            "Model project without controllers should not be classified as REST"
        )

    def test_rest_project_classified_as_rest(self, tmp_path):
        """A Java project with spring-boot-starter-web AND @RestController
        should be classified as REST."""
        project = _make_java_rest_project(tmp_path)
        analysis = analyze_project(project)

        assert "rest" in analysis.api_types, (
            "Project with @RestController should be classified as REST"
        )

    def test_source_patterns_detected(self, tmp_path):
        """Verify source patterns are populated for REST project."""
        project = _make_java_rest_project(tmp_path)
        analysis = analyze_project(project)

        assert "@RestController" in analysis.source_patterns


class TestDetectorSourcePatterns:
    """Test _scan_source_patterns."""

    def test_no_patterns_for_model_project(self, tmp_path):
        """Model project should have no REST-related source patterns."""
        project = _make_java_model_project(tmp_path)
        analysis = analyze_project(project)

        rest_patterns = {"@RestController", "@Controller"}
        assert not (rest_patterns & set(analysis.source_patterns))


class TestMatcherDependenciesAll:
    """Test that dependencies_all requires ALL listed deps to match."""

    def test_liquibase_spanner_matched_when_both_deps_present(self, tmp_path):
        """liquibase-spanner skill should match when both liquibase-core
        AND liquibase-spanner dependencies are present."""
        project = _make_java_model_project(tmp_path)
        analysis = analyze_project(project)
        registry = _load_test_registry()

        matches = match_skills(analysis, registry)
        matched_names = [m.name for m in matches]

        assert "liquibase-spanner" in matched_names, (
            "liquibase-spanner skill should be auto-detected"
        )

    def test_liquibase_spanner_not_matched_when_partial(self, tmp_path):
        """liquibase-spanner should NOT match with only liquibase-core."""
        pom = tmp_path / "pom.xml"
        pom.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>my-project</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>org.liquibase</groupId>
            <artifactId>liquibase-core</artifactId>
        </dependency>
    </dependencies>
</project>
""")
        analysis = analyze_project(tmp_path)
        registry = _load_test_registry()

        matches = match_skills(analysis, registry)
        matched_names = [m.name for m in matches]

        assert "liquibase-spanner" not in matched_names, (
            "liquibase-spanner should not match with only liquibase-core"
        )


class TestMatcherSourcePatterns:
    """Test that source_patterns gate controls skill matching."""

    def test_api_rest_not_matched_for_model_project(self, tmp_path):
        """api-rest should NOT match for a model project without controllers."""
        project = _make_java_model_project(tmp_path)
        analysis = analyze_project(project)
        registry = _load_test_registry()

        matches = match_skills(analysis, registry)
        matched_names = [m.name for m in matches]

        assert "api-rest" not in matched_names, (
            "api-rest should not match model project without controllers"
        )

    def test_api_rest_matched_for_rest_project(self, tmp_path):
        """api-rest SHOULD match for a project with @RestController."""
        project = _make_java_rest_project(tmp_path)
        analysis = analyze_project(project)
        registry = _load_test_registry()

        matches = match_skills(analysis, registry)
        matched_names = [m.name for m in matches]

        assert "api-rest" in matched_names, (
            "api-rest should match project with @RestController"
        )


class TestDetectorDocker:
    """Test Docker detection including subdirectories."""

    def test_docker_detected_in_root(self, tmp_path):
        """Docker should be detected when Dockerfile is in root."""
        (tmp_path / "Dockerfile").write_text("FROM openjdk:21\n")
        analysis = analyze_project(tmp_path)
        assert analysis.has_docker is True

    def test_docker_detected_in_subdirectory(self, tmp_path):
        """Docker should be detected when Dockerfile is in docker/ subdirectory."""
        docker_dir = tmp_path / "docker"
        docker_dir.mkdir()
        (docker_dir / "Dockerfile").write_text("FROM openjdk:21\n")
        analysis = analyze_project(tmp_path)
        assert analysis.has_docker is True, (
            "Docker should be detected in docker/ subdirectory"
        )

    def test_docker_compose_detected_in_subdirectory(self, tmp_path):
        """docker-compose.yml in docker/ should be detected."""
        docker_dir = tmp_path / "docker"
        docker_dir.mkdir()
        (docker_dir / "docker-compose.yml").write_text("version: '3'\n")
        analysis = analyze_project(tmp_path)
        assert analysis.has_docker is True

    def test_docker_project_files_reflect_subdirectory(self, tmp_path):
        """project_files['Dockerfile'] should be True even if in docker/ subdir."""
        docker_dir = tmp_path / "docker"
        docker_dir.mkdir()
        (docker_dir / "Dockerfile").write_text("FROM openjdk:21\n")
        analysis = analyze_project(tmp_path)
        assert analysis.project_files.get("Dockerfile") is True

    def test_docker_not_detected_when_absent(self, tmp_path):
        """Docker should not be detected when no Docker files exist."""
        (tmp_path / "pom.xml").write_text("<project></project>")
        analysis = analyze_project(tmp_path)
        assert analysis.has_docker is False


class TestDetectorDatabases:
    """Test database detection patterns."""

    def test_spanner_detected_via_model_dependency(self, tmp_path):
        """Spanner should be detected from dependencies containing 'spanner'."""
        pom = tmp_path / "pom.xml"
        pom.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>my-service</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>com.example.cwow.model</groupId>
            <artifactId>model-base-spanner</artifactId>
        </dependency>
    </dependencies>
</project>
""")
        analysis = analyze_project(tmp_path)
        assert "spanner" in analysis.databases, (
            "Spanner should be detected from model-base-spanner dependency"
        )

    def test_bigquery_detected(self, tmp_path):
        """BigQuery should be detected from GCP BigQuery dependencies."""
        pom = tmp_path / "pom.xml"
        pom.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>my-service</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>com.google.cloud</groupId>
            <artifactId>spring-cloud-gcp-starter-bigquery</artifactId>
        </dependency>
    </dependencies>
</project>
""")
        analysis = analyze_project(tmp_path)
        assert "bigquery" in analysis.databases, (
            "BigQuery should be detected from spring-cloud-gcp-starter-bigquery"
        )

    def test_spanner_detected_via_direct_gcp_dep(self, tmp_path):
        """Spanner detected via the standard GCP Spanner dependency."""
        project = _make_java_model_project(tmp_path)
        analysis = analyze_project(project)
        assert "spanner" in analysis.databases
