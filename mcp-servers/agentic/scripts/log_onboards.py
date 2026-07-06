"""Log the 7 repo onboards to activity tracker and verify state."""
import json
from agentic_mcp.server import activity_log, activity_summary, repo_list, domain_get

repos_onboarded = [
    ("cwow-patient-query-spanner", 41),
    ("cwow-patient-batch", 16),
    ("cwow-patient-command-spanner", 35),
    ("cwow-patient-model-spanner", 21),
    ("cwow-patient-pillar-synchronizer-spanner", 29),
    ("cwow-patient-search-query-spanner", 24),
    ("cwow-patients-events-handler-spanner", 27),
]

print("=== Logging repo onboards ===")
for name, skills in repos_onboarded:
    activity_log(
        command="code",
        subcommand="onboard",
        status="success",
        repo_path=f"/Users/your-user/keel-workspace/{name}",
        details={"repo": name, "skills_installed": skills, "domain": "cwow-patient"},
    )
    print(f"  logged: {name} ({skills} skills)")

print("\n=== Repos in tracker ===")
repos = json.loads(repo_list())
for r in repos:
    si = r.get("skills_installed", "[]")
    skills = json.loads(si) if isinstance(si, str) else (si or [])
    print(f"  {r['name']}: {len(skills)} skills")

print(f"\n  Total repos onboarded: {len(repos)}")

print("\n=== cwow-facility domain ===")
fac = json.loads(domain_get("cwow-facility"))
print(f"  repos linked: {len(fac['repos'])}, docs tracked: {len(fac['docs'])}")

print("\n=== cwow-patient domain ===")
pat = json.loads(domain_get("cwow-patient"))
print(f"  repos linked: {len(pat['repos'])}, docs tracked: {len(pat['docs'])}")

print("\n=== Platform Summary ===")
summary = json.loads(activity_summary())
print(json.dumps(summary, indent=2))
