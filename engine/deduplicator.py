"""
Semantic deduplication for medications — merges brand/generic duplicates.
Uses a hardcoded mapping for common drugs + normalized string matching.
"""

BRAND_TO_GENERIC: dict[str, str] = {
    # Analgesics / antipyretics
    "tylenol": "acetaminophen",
    "panadol": "acetaminophen",
    "advil": "ibuprofen",
    "motrin": "ibuprofen",
    "aleve": "naproxen",
    # Statins
    "lipitor": "atorvastatin",
    "crestor": "rosuvastatin",
    "zocor": "simvastatin",
    "pravachol": "pravastatin",
    "mevacor": "lovastatin",
    # Antihypertensives
    "norvasc": "amlodipine",
    "zestril": "lisinopril",
    "prinivil": "lisinopril",
    "diovan": "valsartan",
    "cozaar": "losartan",
    "altace": "ramipril",
    "toprol": "metoprolol",
    "lopressor": "metoprolol",
    "tenormin": "atenolol",
    "coreg": "carvedilol",
    # Diabetes
    "glucophage": "metformin",
    "januvia": "sitagliptin",
    "lantus": "insulin glargine",
    "novolog": "insulin aspart",
    "humalog": "insulin lispro",
    # Anticoagulants
    "coumadin": "warfarin",
    "jantoven": "warfarin",
    "xarelto": "rivaroxaban",
    "eliquis": "apixaban",
    "pradaxa": "dabigatran",
    # Antibiotics
    "augmentin": "amoxicillin-clavulanate",
    "zithromax": "azithromycin",
    "cipro": "ciprofloxacin",
    "levaquin": "levofloxacin",
    "keflex": "cephalexin",
    # GI
    "prilosec": "omeprazole",
    "nexium": "esomeprazole",
    "prevacid": "lansoprazole",
    "pepcid": "famotidine",
    "zantac": "ranitidine",
    # Psychiatric / neuro
    "prozac": "fluoxetine",
    "zoloft": "sertraline",
    "lexapro": "escitalopram",
    "effexor": "venlafaxine",
    "wellbutrin": "bupropion",
    "abilify": "aripiprazole",
    "seroquel": "quetiapine",
    "ambien": "zolpidem",
    # Respiratory
    "ventolin": "albuterol",
    "proventil": "albuterol",
    "symbicort": "budesonide-formoterol",
    "advair": "fluticasone-salmeterol",
    "spiriva": "tiotropium",
    # Thyroid
    "synthroid": "levothyroxine",
    "levoxyl": "levothyroxine",
}


def _normalize(name: str) -> str:
    return name.lower().strip().split()[0]


def _canonical(name: str) -> str:
    normalized = _normalize(name)
    return BRAND_TO_GENERIC.get(normalized, normalized)


def deduplicate_medications(med_list: list[dict]) -> list[dict]:
    """
    Merge medications with same canonical (generic) name.
    Returns deduplicated list with is_duplicate_merged=True on merged entries.
    Each dict must have a 'display_name' key.
    """
    seen: dict[str, dict] = {}
    result: list[dict] = []

    for med in med_list:
        display = med.get("display_name", "")
        canonical = _canonical(display)

        if canonical in seen:
            existing = seen[canonical]
            merged_from = existing.get("merged_from", [existing.get("display_name", "")])
            if display not in merged_from:
                merged_from.append(display)
            existing["merged_from"] = merged_from
            existing["is_duplicate_merged"] = True
            if not existing.get("generic_name"):
                existing["generic_name"] = canonical
        else:
            entry = dict(med)
            entry["merged_from"] = []
            entry["is_duplicate_merged"] = False
            if not entry.get("generic_name"):
                entry["generic_name"] = canonical
            seen[canonical] = entry
            result.append(entry)

    return result
