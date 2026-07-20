"""Tests for the structured doctor report that powers the setup wizard."""

from src.services import setup_service as svc


def test_doctor_report_has_sections_and_summary():
    report = svc.get_doctor_report(probe=False)
    # Always returns a runtime section (Python version) and a summary.
    assert report.sections, "expected at least one diagnostic section"
    names = {s.name for s in report.sections}
    assert "Runtime" in names
    total = report.summary.ok + report.summary.warn + report.summary.fail + report.summary.skip
    assert total == report.summary.total
    assert report.summary.total > 0


def test_doctor_runtime_check_passes_on_supported_python():
    report = svc.get_doctor_report()
    runtime = next(s for s in report.sections if s.name == "Runtime")
    py = next(r for r in runtime.results if r.name == "Python version")
    # This test runs on the project's 3.10+ interpreter.
    assert py.status == "ok"


def test_doctor_never_raises_and_is_serializable():
    report = svc.get_doctor_report()
    # Pydantic round-trip mirrors what the API returns.
    dumped = report.model_dump()
    assert "healthy" in dumped and "sections" in dumped and "summary" in dumped
    assert isinstance(dumped["healthy"], bool)


def test_collect_sections_matches_report_shape():
    from agentic_cli.doctor import collect_sections, sections_to_dict

    data = sections_to_dict(collect_sections(probe=False))
    assert set(data.keys()) == {"sections", "summary", "healthy"}
    assert data["summary"]["total"] == sum(
        len(s["results"]) for s in data["sections"]
    )
