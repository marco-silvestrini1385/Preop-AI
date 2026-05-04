from typing import Dict, Any


def build_cancellation_module(result: Dict[str, Any]) -> Dict[str, Any]:

    blockers = []
    warnings = []
    missing = []
    immediate_actions = []

    proceed = "likely safe to proceed"
    risk_level = "low"

    # --- Pull modules ---
    pulmonary = result.get("pulmonary", {})
    med = result.get("med_safety", {})
    anticoag = result.get("anticoag", {})
    renal = result.get("renal", {})
    dispo = result.get("disposition", {})
    airway = result.get("airway_risk_module", {})

    # -----------------------------
    # HARD STOP CONDITIONS
    # -----------------------------

    # Hyperkalemia risk
    if "hyperkalemia" in str(renal.get("drivers", "")).lower():
        blockers.append("Possible hyperkalemia")
        immediate_actions.append("Verify potassium before proceeding")
        risk_level = "critical"

    # Anticoag unknown timing
    if any("not documented" in x.lower() for x in anticoag.get("critical_missing", [])):
        blockers.append("Anticoagulation timing unknown")
        immediate_actions.append("Confirm last anticoagulation dose")
        risk_level = "critical"

    # SGLT2 not held
    if "SGLT2 inhibitor" in str(med.get("medications_detected", "")):
        blockers.append("SGLT2 status unclear")
        immediate_actions.append("Confirm SGLT2 hold status / consider metabolic check")
        risk_level = "critical"

    # Pulmonary severe instability
    if pulmonary.get("severity") == "high":
        warnings.append("High pulmonary risk")
        risk_level = "high"

    # Airway unknown
    if airway.get("missing_airway_data"):
        blockers.append("Airway exam not documented")
        immediate_actions.append("Perform airway assessment before anesthesia")
        risk_level = "high"

    # -----------------------------
    # MODERATE RISKS
    # -----------------------------

    if dispo.get("disposition_risk") in ["high", "critical"]:
        warnings.append("High postoperative risk")
        risk_level = "high"

    if renal.get("severity") in ["high", "critical"]:
        warnings.append("Renal/electrolyte concern")

    if med.get("overall_severity") in ["high", "critical"]:
        warnings.append("Medication safety complexity")

    # -----------------------------
    # MISSING CRITICAL DATA
    # -----------------------------

    missing.extend(med.get("critical_missing", []))
    missing.extend(renal.get("missing_data", []))
    missing.extend(pulmonary.get("missing", []))

    if len(missing) > 5:
        blockers.append("Excessive critical missing data")
        immediate_actions.append("Clarify missing high-impact clinical data")
        risk_level = "high"

    # -----------------------------
    # FINAL DECISION
    # -----------------------------

    if risk_level == "critical":
        proceed = "do NOT proceed — requires optimization"
    elif risk_level == "high":
        proceed = "proceed with caution — optimization required"
    elif warnings:
        proceed = "proceed with awareness of elevated risk"

    summary = (
        f"{risk_level.upper()} proceed risk. "
        f"Recommendation: {proceed}. "
        f"Blockers: {', '.join(blockers[:3]) if blockers else 'none'}."
    )

    return {
        "module": "Case Cancellation / Proceed Risk",
        "proceed_recommendation": proceed,
        "risk_level": risk_level,
        "blockers": list(set(blockers)),
        "warnings": list(set(warnings)),
        "immediate_actions": list(set(immediate_actions)),
        "missing_data": list(set(missing)),
        "clinician_summary": summary,
        "safety_statement": "Decision support only. Does not determine case cancellation."
    }