from typing import Dict, Any


def build_frailty_module(data: Dict[str, Any]) -> Dict[str, Any]:
    text = data.get("text", "").lower()

    drivers = []
    missing = []
    alerts = []
    monitoring = []

    score = 0

    # --- Age ---
    if any(x in text for x in ["80", "85", "90"]):
        score += 2
        drivers.append("Advanced age")

    elif any(x in text for x in ["70", "75"]):
        score += 1
        drivers.append("Older age")

    # --- Mobility ---
    if any(x in text for x in ["wheelchair", "bedbound"]):
        score += 3
        drivers.append("Severely limited mobility")
        alerts.append("High frailty risk — may affect recovery and disposition")

    elif any(x in text for x in ["walker", "cane", "limited ambulation"]):
        score += 2
        drivers.append("Impaired mobility")

    # --- Functional capacity ---
    if any(x in text for x in ["unable to climb stairs", "<4 mets", "poor exercise tolerance"]):
        score += 2
        drivers.append("Poor functional capacity")

    # --- Falls ---
    if "fall" in text:
        score += 2
        drivers.append("History of falls")
        alerts.append("Increased postop delirium and morbidity risk")

    # --- Cognitive ---
    if any(x in text for x in ["dementia", "confusion", "delirium"]):
        score += 3
        drivers.append("Cognitive impairment")
        alerts.append("High delirium risk")

    # --- Nutrition ---
    if any(x in text for x in ["weight loss", "malnutrition", "cachexia"]):
        score += 2
        drivers.append("Malnutrition / weight loss")

    # --- Dependency ---
    if any(x in text for x in ["assisted living", "dependent", "needs help with adls"]):
        score += 2
        drivers.append("Functional dependence")

    # --- Missing ---
    if "mets" not in text:
        missing.append("Functional capacity (METS) not documented")

    if "ambulation" not in text:
        missing.append("Baseline mobility not documented")

    # --- Score interpretation ---
    if score >= 6:
        frailty_level = "high"
    elif score >= 3:
        frailty_level = "moderate"
    else:
        frailty_level = "low"

    # --- Monitoring / implications ---
    if frailty_level in ["moderate", "high"]:
        monitoring.append("Higher risk of postoperative complications")
        monitoring.append("Consider extended recovery / higher level of care")

    if frailty_level == "high":
        alerts.append("Frailty may drive disposition and recovery trajectory")

    summary = (
        f"{frailty_level.upper()} frailty risk. "
        f"Drivers: {', '.join(drivers[:4]) if drivers else 'none documented'}."
    )

    return {
        "module": "Frailty / Functional Reserve",
        "frailty_level": frailty_level,
        "score": score,
        "drivers": list(set(drivers)),
        "plan_changing_alerts": list(set(alerts)),
        "monitoring_needs": list(set(monitoring)),
        "missing_data": list(set(missing)),
        "clinician_summary": summary,
        "confidence": "limited_by_text",
        "safety_statement": "Decision support only."
    }