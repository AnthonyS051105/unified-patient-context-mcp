class PatternSignature:
    """
    Extract GENERIC clinical conditions from FHIR data for Pattern Memory keys.

    CRITICAL RULE: Extract CATEGORIES, not specific numeric values.
    ALLOWED:   "creatinine_rising_trend", "news2_high_risk", "metformin_present"
    FORBIDDEN: "creatinine=1.8", "news2=7", "patient_eleanor"
    """

    _RULE_MAP = {
        "heart rate": "elevated_heart_rate",
        " hr ": "elevated_heart_rate",
        "hr ": "elevated_heart_rate",
        "tachycardia": "elevated_heart_rate",
        "bradycardia": "low_heart_rate",
        "respiratory": "elevated_respiratory_rate",
        "rr ": "elevated_respiratory_rate",
        "tachypnea": "elevated_respiratory_rate",
        "bradypnea": "low_respiratory_rate",
        "spo": "low_oxygen_saturation",
        "hypoxemia": "low_oxygen_saturation",
        "oxygen": "low_oxygen_saturation",
        "sbp": "abnormal_blood_pressure",
        "hypotension": "abnormal_blood_pressure",
        "hypertensive": "abnormal_blood_pressure",
        "blood pressure": "abnormal_blood_pressure",
        "temp": "abnormal_temperature",
        "fever": "abnormal_temperature",
        "hypothermia": "abnormal_temperature",
        "consciousness": "altered_consciousness",
        "mental status": "altered_consciousness",
        "avpu": "altered_consciousness",
        "news2": "news2_alert",
        "emergency": "news2_high_risk",
        "urgent": "news2_medium_risk",
    }

    def from_news2_result(self, score: int, triggered_rules: list[str]) -> list[str]:
        conditions: list[str] = []
        if score >= 7:
            conditions.append("news2_high_risk")
        elif score >= 5:
            conditions.append("news2_medium_risk")
        elif score >= 1:
            conditions.append("news2_low_medium_risk")
        else:
            conditions.append("news2_low_risk")

        for rule in triggered_rules:
            normalized = self._normalize_rule(rule)
            if normalized and normalized not in conditions:
                conditions.append(normalized)

        return conditions

    def from_synthesis_context(self, labs: list, meds: list, vitals_summary: dict) -> list[str]:
        conditions: list[str] = []

        for lab in labs:
            name = (getattr(lab, "display_name", None) or lab.get("display_name", "") if hasattr(lab, "get") else "").lower()
            trend_obj = getattr(lab, "trend", None) or (lab.get("trend") if hasattr(lab, "get") else None)
            trend = (trend_obj.get("direction") if isinstance(trend_obj, dict) else trend_obj) or ""

            if "creatinine" in name:
                if trend == "rising":
                    conditions.append("creatinine_rising_trend")
                elif trend == "falling":
                    conditions.append("creatinine_falling_trend")
                else:
                    conditions.append("creatinine_abnormal")
            if "hemoglobin" in name or "hgb" in name or "haemoglobin" in name:
                conditions.append("abnormal_hemoglobin")
            if "potassium" in name:
                conditions.append("abnormal_potassium")
            if "sodium" in name:
                conditions.append("abnormal_sodium")
            if "glucose" in name or "hba1c" in name:
                conditions.append("abnormal_glucose")
            if "wbc" in name or "white blood" in name:
                conditions.append("abnormal_wbc")

        for med in meds:
            name = (getattr(med, "display_name", None) or med.get("display_name", "") if hasattr(med, "get") else "").lower()
            flags = getattr(med, "interaction_flags", None) or (med.get("interaction_flags", []) if hasattr(med, "get") else [])

            if "metformin" in name:
                conditions.append("metformin_present")
            if "warfarin" in name or "coumadin" in name:
                conditions.append("anticoagulant_present")
            if "insulin" in name:
                conditions.append("insulin_present")
            if "ace" in name or "lisinopril" in name or "ramipril" in name:
                conditions.append("ace_inhibitor_present")
            if "nsaid" in name or "ibuprofen" in name or "naproxen" in name:
                conditions.append("nsaid_present")
            if flags:
                conditions.append("active_drug_interaction")

        risk = vitals_summary.get("deterioration_level") or vitals_summary.get("risk_level", "")
        if risk in ("high",):
            conditions.append("news2_high_risk")
        elif risk in ("medium",):
            conditions.append("news2_medium_risk")

        return list(dict.fromkeys(conditions))  # deduplicate, preserve order

    def _normalize_rule(self, rule: str) -> str | None:
        rule_lower = rule.lower()
        for keyword, label in self._RULE_MAP.items():
            if keyword in rule_lower:
                return label
        return None


# Singleton
pattern_signature = PatternSignature()
