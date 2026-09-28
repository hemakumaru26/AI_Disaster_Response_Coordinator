"""Seed volunteer master data across all 38 Tamil Nadu districts.

This script populates a realistic, balanced volunteer database for the AI
Disaster Response Coordinator. It is deterministic, idempotent, and safe to run
multiple times.

Usage:
    python scripts/seed_volunteers.py [--db PATH] [--dry-run]
"""

import argparse
import os
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.models.volunteer_model import (
    add_volunteer,
    initialize_volunteer_storage,
)

TAMIL_NADU_DISTRICTS = [
    "Ariyalur",
    "Chengalpattu",
    "Chennai",
    "Coimbatore",
    "Cuddalore",
    "Dharmapuri",
    "Dindigul",
    "Erode",
    "Kallakurichi",
    "Kancheepuram",
    "Karur",
    "Krishnagiri",
    "Madurai",
    "Mayiladuthurai",
    "Nagapattinam",
    "Kanniyakumari",
    "Namakkal",
    "Perambalur",
    "Pudukkottai",
    "Ramanathapuram",
    "Ranipet",
    "Salem",
    "Sivaganga",
    "Tenkasi",
    "Thanjavur",
    "Theni",
    "Thoothukudi",
    "Tiruchirappalli",
    "Tirunelveli",
    "Tirupathur",
    "Tiruppur",
    "Tiruvallur",
    "Tiruvarur",
    "Tiruvannamalai",
    "The Nilgiris",
    "Vellore",
    "Viluppuram",
    "Virudhunagar",
]

FIRST_NAMES = [
    "Karthik",
    "Ananya",
    "Vignesh",
    "Priya",
    "Dinesh",
    "Kavitha",
    "Arvind",
    "Meena",
]

LAST_NAMES = [
    "Raman",
    "Sundaram",
    "Natarajan",
    "Selvam",
    "Krishnan",
    "Murugan",
    "Balaji",
    "Chandran",
    "Venkatesh",
    "Saravanan",
    "Pillai",
    "Iyer",
    "Rajan",
    "Mani",
    "Babu",
    "Perumal",
    "Subramanian",
    "Ganesan",
    "Velu",
]

# 8 balanced role templates per district
PROFILE_TEMPLATES = [
    {
        "role": "Water / Flood Specialist",
        "skills": "Flood Rescue, Boat Operations, Water Rescue",
        "notes_tmpl": "Certified swift-water rescue operator and inflatable boat handler in {district}.",
    },
    {
        "role": "Medical / Paramedic Specialist",
        "skills": "First Aid, Medical Assistance, Disaster Relief",
        "notes_tmpl": "Trained emergency medical responder with triage and trauma care experience in {district}.",
    },
    {
        "role": "Search, Rescue & Fire Specialist",
        "skills": "Search & Rescue, Evacuation, Fire & Emergency",
        "notes_tmpl": "Urban search and rescue trained; collapsed structure extraction specialist in {district}.",
    },
    {
        "role": "Relief Camp & Logistics Lead",
        "skills": "Shelter Management, Logistics, Food Distribution",
        "notes_tmpl": "Disaster relief camp coordinator and mass-feeding logistics manager in {district}.",
    },
    {
        "role": "Emergency Comms Coordinator",
        "skills": "Emergency Communication, Logistics, Disaster Relief",
        "notes_tmpl": "HAM radio operator and incident command communication specialist in {district}.",
    },
    {
        "role": "Cyclone & Evacuation Lead",
        "skills": "Cyclone Response, Evacuation, Water Distribution",
        "notes_tmpl": "Coastal cyclone preparedness coordinator and community evacuation lead in {district}.",
    },
    {
        "role": "Rapid Response First Aider",
        "skills": "First Aid, Search & Rescue, Evacuation",
        "notes_tmpl": "Community emergency response team leader; rapid deployment first responder in {district}.",
    },
    {
        "role": "Relief & Shelter Support",
        "skills": "Flood Rescue, Food Distribution, Shelter Management",
        "notes_tmpl": "Inundation zone relief volunteer and temporary relief shelter administrator in {district}.",
    },
]


def _slug(text: str) -> str:
    """Create a URL/email-safe lowercase identifier from a string."""
    clean = re.sub(r"[^a-zA-Z0-9]+", ".", text.strip().lower())
    return clean.strip(".")


def generate_volunteer_records():
    """Generate the full deterministic volunteer roster for all 38 districts."""
    records = []
    total_last_names = len(LAST_NAMES)

    for d_idx, district in enumerate(TAMIL_NADU_DISTRICTS):
        for p_idx, template in enumerate(PROFILE_TEMPLATES):
            first_name = FIRST_NAMES[p_idx]
            # Deterministic surname variation across districts and profiles
            last_name = LAST_NAMES[(d_idx * len(PROFILE_TEMPLATES) + p_idx) % total_last_names]
            full_name = f"{first_name} {last_name}"

            # Valid-looking email format for notifications
            contact_email = f"{_slug(first_name)}.{_slug(last_name)}.{_slug(district)}@tn-volunteers.org"
            notes = template["notes_tmpl"].format(district=district)

            records.append(
                {
                    "name": full_name,
                    "contact": contact_email,
                    "district": district,
                    "skills": template["skills"],
                    "availability_status": "available",
                    "availability_details": notes,
                    "role": template["role"],
                }
            )

    return records


def seed_volunteers(db_path: str, dry_run: bool = False) -> dict:
    """Seed volunteers into the target SQLite database with idempotency checks."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")

    records = generate_volunteer_records()
    total_target = len(records)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        initialize_volunteer_storage(conn)

        # Check existing records
        cur = conn.cursor()
        existing_contacts = {
            row["contact"]
            for row in cur.execute("SELECT contact FROM volunteers").fetchall()
        }
        existing_name_districts = {
            (row["name"], row["district"])
            for row in cur.execute("SELECT name, district FROM volunteers").fetchall()
        }

        added = 0
        already_existing = 0
        skills_counter = Counter()
        district_counter = Counter()

        for rec in records:
            contact = rec["contact"]
            name_dist = (rec["name"], rec["district"])

            for skill in [s.strip() for s in rec["skills"].split(",")]:
                skills_counter[skill] += 1
            district_counter[rec["district"]] += 1

            if contact in existing_contacts or name_dist in existing_name_districts:
                already_existing += 1
                continue

            if not dry_run:
                add_volunteer(
                    name=rec["name"],
                    contact=rec["contact"],
                    district=rec["district"],
                    skills=rec["skills"],
                    availability_status=rec["availability_status"],
                    availability_details=rec["availability_details"],
                    connection=conn,
                )
            added += 1

        # Query final counts from DB
        cur.execute("SELECT count(*) FROM volunteers")
        final_count = cur.fetchone()[0]

        summary = {
            "total_target": total_target,
            "districts_count": len(TAMIL_NADU_DISTRICTS),
            "added": added,
            "already_existing": already_existing,
            "dry_run": dry_run,
            "db_final_total": final_count,
            "skills_distribution": dict(skills_counter.most_common()),
            "district_distribution": dict(district_counter),
        }

        return summary

    finally:
        conn.close()


def print_summary(summary: dict):
    """Format and print the seeding summary to stdout."""
    print("=" * 60)
    print("      VOLUNTEER MASTER DATABASE SEEDING SUMMARY")
    print("=" * 60)
    print(f"Target Volunteers:        {summary['total_target']}")
    print(f"Districts Covered:        {summary['districts_count']}")
    print(f"Mode:                     {'DRY-RUN (Simulated)' if summary['dry_run'] else 'APPLIED'}")
    print(f"Volunteers Added:         {summary['added']}")
    print(f"Already Existing:         {summary['already_existing']}")
    print(f"Total in Database:        {summary['db_final_total']}")
    print("-" * 60)
    print("Skill Categories & Frequency:")
    for skill, count in summary["skills_distribution"].items():
        print(f"  - {skill:<26}: {count}")
    print("-" * 60)
    print(f"All {summary['districts_count']} districts have {summary['total_target'] // summary['districts_count']} volunteers each.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Seed Tamil Nadu district volunteers.")
    parser.add_argument(
        "--db",
        type=str,
        default=str(PROJECT_ROOT / "database" / "disaster.db"),
        help="Path to SQLite database (default: database/disaster.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate insertions without writing to database",
    )

    args = parser.parse_args()

    print(f"Database target: {args.db}")
    print(f"Dry-run mode:    {args.dry_run}")

    summary = seed_volunteers(args.db, dry_run=args.dry_run)
    print_summary(summary)


if __name__ == "__main__":
    main()

