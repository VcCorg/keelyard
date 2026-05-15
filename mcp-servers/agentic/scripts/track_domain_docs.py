"""Generic domain doc tracker — track Confluence pages for any domain.

Usage:
    python track_domain_docs.py --domain cwow-facility
    python track_domain_docs.py --domain cwow-patient
    python track_domain_docs.py --domain cwow-facility --list
    python track_domain_docs.py --domain cwow-facility --dry-run

Docs are defined in DOMAIN_DOCS dict below. Add new domains as needed.
Each entry: (page_id, space_key, title, tags)
"""
import argparse
import json
import sys
from agentic_mcp.server import domain_add_doc, domain_list_docs, activity_log

# ── Domain doc registry ────────────────────────────────────────────────────────
# Format: { "domain-slug": [ (page_id, space_key, title, tags), ... ] }
# tags: list of labels e.g. ["release-30", "facility-management", "oneview"]

DOMAIN_DOCS = {
    "cwow-facility": [
        # CWOV release index pages
        ("63215138",   "CWOV", "CWOW OneViews - Requirements Index",                    ["index"]),
        ("847844496",  "CWOV", "Release 30 - Facility",                                 ["release-30"]),
        ("847844475",  "CWOV", "Release 29 - Facility",                                 ["release-29"]),
        ("847844414",  "CWOV", "Release 28 - Facility",                                 ["release-28"]),
        # Release 30: Facility Management (container — no OVs yet)
        ("847844502",  "CWOV", "Release 30: Facility Management",                       ["release-30", "facility-management"]),
        # Release 29: Facility Management OneViews
        ("847844481",  "CWOV", "Release 29: Facility Management",                       ["release-29", "facility-management"]),
        ("1170473595", "CWOV", "CWOW-278922 Manage HDF Treatment Standards 01",         ["release-29", "oneview", "hdf"]),
        # Release 28: Facility Management OneViews
        ("847844420",  "CWOV", "Release 28: Facility Management",                       ["release-28", "facility-management"]),
        ("1052115253", "CWOV", "CWOW-245773 Manage MBD Protocols in Governing Body 01", ["release-28", "oneview", "protocols"]),
        ("1043957623", "CWOV", "CWOW-262245 Manage Medication Standards 06",            ["release-28", "oneview", "medication"]),
        ("1170488862", "CWOV", "CWOW-277399 Manage Medication Standards 6.1 (PCR)",     ["release-28", "oneview", "medication"]),
    ],
    "cwow-patient": [
        # Patient domain page
        ("1206618985", "~your-user", "CWOW - Patient Domain",                             ["index"]),
        # CWOV shared requirements
        ("63215138",   "CWOV",     "CWOW OneViews - Requirements Index",                ["index"]),
    ],
}


def track_docs(domain: str, dry_run: bool = False) -> int:
    docs = DOMAIN_DOCS.get(domain)
    if not docs:
        print(f"No docs defined for domain '{domain}'. Add them to DOMAIN_DOCS in this script.")
        sys.exit(1)

    print(f"{'[DRY RUN] ' if dry_run else ''}Tracking {len(docs)} docs for '{domain}'...")
    added = skipped = errors = 0

    for page_id, space, title, tags in docs:
        if dry_run:
            print(f"  [would add] [{space}] {title} ({page_id}) tags={tags}")
            continue
        result = json.loads(domain_add_doc(
            domain_slug=domain,
            page_id=page_id,
            space_key=space,
            title=title,
        ))
        status = result.get("status", result.get("error", "?"))
        if status == "added":
            added += 1
        elif status == "exists":
            skipped += 1
        else:
            errors += 1
        print(f"  [{status}] [{space}] {title} ({page_id})")

    if not dry_run:
        activity_log(
            command="onboard",
            subcommand="domain_add_docs",
            status="success",
            details={"domain": domain, "added": added, "skipped": skipped, "errors": errors},
        )
        print(f"\nResult: {added} added, {skipped} already tracked, {errors} errors")
    return added


def list_docs(domain: str):
    tracked = json.loads(domain_list_docs(domain_slug=domain))
    print(f"\nCurrently tracked docs for '{domain}' ({len(tracked)} total):")
    for d in tracked:
        print(f"  [{d['source_space_key']}] {d['title']} (page {d['source_page_id']})")
    return tracked


def main():
    parser = argparse.ArgumentParser(description="Track Confluence docs for a domain")
    parser.add_argument("--domain", required=True, help="Domain slug e.g. cwow-facility")
    parser.add_argument("--list", action="store_true", help="List currently tracked docs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    if args.list:
        list_docs(args.domain)
        return

    track_docs(args.domain, dry_run=args.dry_run)
    list_docs(args.domain)


if __name__ == "__main__":
    main()
