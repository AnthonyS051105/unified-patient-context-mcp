"""
Upload Synthea FHIR R4 bundles to HAPI FHIR public server.

Usage:
    python scripts/seed_synthea.py --dir path/to/synthea_fhir_r4/ --count 5

Download Synthea data from: https://synthea.mitre.org/downloads
Select: "100 Sample Synthetic Patient Records, FHIR R4"
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4")
OUTPUT_FILE = Path(__file__).parent.parent / "tests" / "fixtures" / "test_patients.json"
TIMEOUT = 30.0


async def upload_bundle(client: httpx.AsyncClient, bundle_path: Path) -> dict | None:
    print(f"Uploading {bundle_path.name}...")
    with open(bundle_path) as f:
        bundle = json.load(f)

    if bundle.get("resourceType") != "Bundle":
        print(f"  SKIP — not a Bundle")
        return None

    try:
        response = await client.post(
            FHIR_BASE_URL,
            json=bundle,
            headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"},
        )
        response.raise_for_status()
        result = response.json()

        patient_id = None
        for entry in result.get("entry", []):
            location = entry.get("response", {}).get("location", "")
            if location.startswith("Patient/"):
                patient_id = location.split("/")[1].split("/_history")[0]
                break

        if patient_id:
            patient_entry = next(
                (e for e in bundle.get("entry", []) if e.get("resource", {}).get("resourceType") == "Patient"),
                None,
            )
            name = "Unknown"
            if patient_entry:
                names = patient_entry["resource"].get("name", [])
                if names:
                    given = " ".join(names[0].get("given", []))
                    family = names[0].get("family", "")
                    name = f"{given} {family}".strip()

            print(f"  OK — patient ID: {patient_id} ({name})")
            return {"patient_id": patient_id, "name": name, "source_file": bundle_path.name}
        else:
            print(f"  WARNING — could not extract patient ID from response")
            return None

    except httpx.HTTPStatusError as e:
        print(f"  ERROR HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser(description="Seed Synthea patients to HAPI FHIR")
    parser.add_argument("--dir", required=True, help="Directory with Synthea FHIR R4 JSON bundles")
    parser.add_argument("--count", type=int, default=5, help="Number of patients to upload (default 5)")
    args = parser.parse_args()

    bundle_dir = Path(args.dir)
    if not bundle_dir.is_dir():
        print(f"ERROR: {bundle_dir} is not a directory")
        sys.exit(1)

    bundle_files = list(bundle_dir.glob("*.json"))[:args.count]
    if not bundle_files:
        print(f"ERROR: No JSON files found in {bundle_dir}")
        sys.exit(1)

    print(f"Uploading {len(bundle_files)} bundles to {FHIR_BASE_URL}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        results = []
        for bundle_path in bundle_files:
            result = await upload_bundle(client, bundle_path)
            if result:
                results.append(result)
            await asyncio.sleep(0.5)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nSeeded {len(results)} patients.")
    print(f"Patient IDs saved to: {OUTPUT_FILE}")
    for r in results:
        print(f"  {r['patient_id']} — {r['name']}")


if __name__ == "__main__":
    asyncio.run(main())
