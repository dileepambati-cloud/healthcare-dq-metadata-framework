"""
Generates small synthetic healthcare files for local testing.
No real patient data - everything here is random.

A few bad records are added on purpose so the DQ rules have
something to catch (null ids, duplicates, bad zip, negative amounts...).

Usage:
    python data/generate_sample_data.py
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT_DIR = Path(__file__).parent / "sample"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FIRST = ["James", "Mary", "John", "Linda", "Ravi", "Anita", "Carlos", "Mei", "Ahmed", "Sara"]
LAST = ["Smith", "Johnson", "Patel", "Garcia", "Lee", "Brown", "Khan", "Lopez", "Wilson", "Reddy"]


def random_dob():
    start = date(1940, 1, 1)
    return start + timedelta(days=random.randint(0, 30000))


def build_members(n=50):
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "member_id": f"M{i:05d}",
            "first_name": random.choice(FIRST),
            "last_name": random.choice(LAST),
            "gender": random.choice(["M", "F"]),
            "date_of_birth": random_dob().isoformat(),
            "zip_code": f"{random.randint(10000, 99999)}",
            "plan_code": random.choice(["PPO", "HMO", "EPO"]),
        })
    # bad records on purpose
    rows[3]["member_id"] = ""                        # null id
    rows[7]["member_id"] = rows[6]["member_id"]      # duplicate id
    rows[10]["gender"] = "X"                         # invalid gender
    rows[12]["zip_code"] = "6061"                    # bad zip
    rows[15]["date_of_birth"] = "2099-01-01"         # future dob
    return rows


def build_claims(members, n=120):
    valid_ids = [m["member_id"] for m in members if m["member_id"]]
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "claim_id": f"C{i:06d}",
            "member_id": random.choice(valid_ids),
            "service_date": (date(2026, 1, 1) + timedelta(days=random.randint(0, 300))).isoformat(),
            "claim_status": random.choice(["PAID", "PAID", "PAID", "DENIED", "PENDING"]),
            "paid_amount": round(random.uniform(20, 5000), 2),
        })
    rows[5]["claim_id"] = rows[4]["claim_id"]        # duplicate claim
    rows[9]["paid_amount"] = -150.00                 # negative amount
    rows[20]["member_id"] = "M99999"                 # orphan member
    rows[30]["claim_status"] = "VOID"                # invalid status
    rows[44]["claim_id"] = ""                        # null claim id
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows -> {path}")


if __name__ == "__main__":
    members = build_members()
    claims = build_claims(members)
    write_csv(OUT_DIR / "members.csv", members)
    write_csv(OUT_DIR / "claims.csv", claims)
