"""Fresh onboard: register product, domains, link repos, track docs.

Logs every action to the activity_log for full traceability.
"""

import json
import time

from agentic_mcp.server import (
    product_create,
    product_list,
    domain_create,
    domain_list,
    domain_link_repo,
    domain_add_doc,
    activity_log,
    activity_summary,
)


def log_action(command, subcommand, details):
    """Log + print an onboarding action."""
    activity_log(command=command, subcommand=subcommand, status="success", details=details)
    print(f"  [logged] {command}.{subcommand}")


# === Step 1: Register Product ===
print("=== Step 1: Register Product CWOW ===")
result = json.loads(product_create(name="CWOW", description="Clinical & Workforce Operations for the Web"))
print(f"  Created: {result}")
log_action("onboard", "product_create", {"product": "CWOW"})

# === Step 2: Create Facility Domain ===
print("\n=== Step 2: Create Facility Domain ===")
result = json.loads(
    domain_create(
        domain="Facility",
        product="CWOW",
        jira="CWOW",
        bb="CGF",
        confluence="MTT",
        description="Facility management - scheduling, billing, watercheck, product recall",
    )
)
print(f"  Created: {result}")
log_action("onboard", "domain_create", {"domain": "cwow-facility", "bb": "CGF", "jira": "CWOW", "confluence": "MTT"})

# === Step 3: Create Patient Domain ===
print("\n=== Step 3: Create Patient Domain ===")
result = json.loads(
    domain_create(
        domain="Patient",
        product="CWOW",
        jira="CWOW",
        bb="CGP",
        confluence="CWOV",
        description="Patient management - commands, queries, events, batch, dataflows",
    )
)
print(f"  Created: {result}")
log_action("onboard", "domain_create", {"domain": "cwow-patient", "bb": "CGP", "jira": "CWOW", "confluence": "CWOV"})

# === Step 4a: Link Facility Repos (14 active, DEPRECATED filtered) ===
print("\n=== Step 4a: Link 14 Facility Repos (CGF) ===")
facility_repos = [
    "cwow-facility-batch-state-transition-scheduler-spanner",
    "cwow-facility-billing-exception-command-spanner",
    "cwow-facility-command-spanner",
    "cwow-facility-datafix",
    "cwow-facility-data-migration",
    "cwow-facility-model-spanner",
    "cwow-facility-pillar-synchronizer-spanner",
    "cwow-facility-product-recall-command-spanner",
    "cwow-facility-product-recall-model-spanner",
    "cwow-facility-query-spanner",
    "cwow-facility-watercheck",
    "cwow-facility-watercheck-migration",
    "cwow-facility-watercheck-scheduler",
    "cwow-facility-watercheck-trigger",
]
for repo in facility_repos:
    url = f"https://bitbucket.example.com/projects/CGF/repos/{repo}"
    domain_link_repo(domain_slug="cwow-facility", repo_slug=repo, clone_url=url)
    print(f"  linked: {repo}")
log_action("onboard", "domain_link_repos", {"domain": "cwow-facility", "count": len(facility_repos)})

# === Step 4b: Link Patient Repos (18 active, DEPRECATED + pipeline filtered) ===
print("\n=== Step 4b: Link 18 Patient Repos (CGP) ===")
patient_repos = [
    "cwow-patient-annuric-status-migration",
    "cwow-patient-batch",
    "cwow-patient-batch-scheduler",
    "cwow-patient-command-spanner",
    "cwow-patient-data-migration-spanner",
    "cwow-patient-graph-query",
    "cwow-patient-hospital-master-dataflow",
    "cwow-patient-modality-dataflow",
    "cwow-patient-model-spanner",
    "cwow-patient-pillar-synchronizer-spanner",
    "cwow-patient-query-spanner",
    "cwow-patients-common-util",
    "cwow-patients-csv-storage",
    "cwow-patients-datafix",
    "cwow-patient-search-query-spanner",
    "cwow-patients-events-handler-spanner",
    "cwow-patient-status-dataflow",
    "cwow-patient-user-facility-migration",
]
for repo in patient_repos:
    url = f"https://bitbucket.example.com/projects/CGP/repos/{repo}"
    domain_link_repo(domain_slug="cwow-patient", repo_slug=repo, clone_url=url)
    print(f"  linked: {repo}")
log_action("onboard", "domain_link_repos", {"domain": "cwow-patient", "count": len(patient_repos)})

# === Step 5: Track Confluence Docs ===
print("\n=== Step 5: Track Confluence Docs ===")
domain_add_doc(domain_slug="cwow-patient", page_id="1206618985", space_key="~your-user", title="CWOW - Patient Domain")
print("  tracked: CWOW - Patient Domain (page 1206618985, space ~your-user) -> cwow-patient")

domain_add_doc(domain_slug="cwow-facility", page_id="63215138", space_key="CWOV", title="CWOW OneViews - Requirements")
print("  tracked: CWOW OneViews (page 63215138, space CWOV) -> cwow-facility")

domain_add_doc(domain_slug="cwow-patient", page_id="63215138", space_key="CWOV", title="CWOW OneViews - Requirements")
print("  tracked: CWOW OneViews (page 63215138, space CWOV) -> cwow-patient")

log_action("onboard", "domain_add_docs", {"docs_tracked": 3, "pages": ["1206618985", "63215138"]})

# === Summary ===
print("\n=== Platform Summary ===")
summary = json.loads(activity_summary())
print(json.dumps(summary, indent=2))
print(f"\nDone: {summary['products']} products, {summary['domains']} domains, {summary['total_activities']} activities logged")
