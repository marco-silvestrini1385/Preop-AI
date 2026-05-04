from typing import Dict, Any


def build_renal_module(data: Dict[str, Any]) -> Dict[str, Any]:
    text = data.get("text", "").lower()

    drivers = []
    monitoring = []
    missing = []
    alerts = []

    severity = "low"

    # --- CKD / renal dysfunction ---
    if any(x in text for x in ["ckd", "chronic kidney", "renal failure", "esrd"]):
        severity = "high"
        drivers.append("Chronic kidney disease / renal dysfunction")
        monitoring.append("Monitor renal function, fluid status, drug dosing")
        alerts.append("Renal dysfunction may affect anesthetic drug selection and clearance")

    # --- Dialysis ---
    if any(x in text for x in ["hemodialysis", "dialysis"]):
        severity = "critical"
        drivers.append("Dialysis-dependent patient")
        monitoring.append("Confirm last dialysis session and volume status")
        alerts.append("Dialysis timing and electrolytes may change case timing")

        if "last dialysis" not in text:
            missing.append("Last dialysis timing not documented")

    # --- Hyperkalemia risk ---
    if "potassium" in text or "k " in text:
        drivers.append("Potassium referenced — verify level")

    if any(x in text for x in ["hyperkalemia", "k 6", "k 5.5"]):
        severity = "critical"
        drivers.append("Possible hyperkalemia")
        alerts.append("Hyperkalemia may require urgent optimization before anesthesia")

    else:
        missing.append("Recent potassium level not documented")

    # --- Creatinine / renal labs ---
    if "creatinine" not in text:
        missing.append("Recent creatinine not documented")

    # --- Medication interactions ---
    if any(x in text for x in ["metformin"]):
        drivers.append("Metformin present — renal clearance relevant")
        alerts.append("Renal dysfunction may affect metformin safety")

    if any(x in text for x in ["apixaban", "rivaroxaban", "dabigatran"]):
        drivers.append("DOAC present — renal clearance relevant")
        alerts.append("Renal function affects anticoagulation clearance")

    if any(x in text for x in ["furosemide", "diuretic"]):
        drivers.append("Diuretic use — electrolyte risk")

    # --- Final severity adjustment ---
    if severity != "critical":
        if len(drivers) >= 3:
            severity = "high"
        elif len(drivers) >= 1:
            severity = "moderate"

    # --- Summary ---
    summary = (
        f"{severity.upper()} renal/electrolyte relevance. "
        f"Drivers: {', '.join(drivers[:4]) if drivers else 'none documented'}."
    )

    return {
        "module": "Renal / Electrolyte",
        "severity": severity,
        "drivers": list(set(drivers)),
        "monitoring_needs": list(set(monitoring)),
        "plan_changing_alerts": list(set(alerts)),
        "missing_data": list(set(missing)),
        "clinician_summary": summary,
        "confidence": "limited_by_text",
        "safety_statement": "Decision support only. Requires clinician verification."
    }