from typing import Dict, Any


def build_pulmonary_module(data: Dict[str, Any]):

    text = data.get("text", "").lower()

    findings = []
    missing = []
    plan = []
    alerts = []
    interactions = []
    guardrails = []

    severity = "low"

    # --- OSA ---
    if "osa" in text or "sleep apnea" in text:
        findings.append("Obstructive sleep apnea")

        severity = "high"

        if "cpap" not in text:
            missing.append("CPAP use/compliance not documented")

        plan.append("Consider postoperative CPAP and respiratory monitoring")
        alerts.append("OSA increases risk of opioid-induced respiratory depression")

    # --- COPD / Asthma ---
    if "copd" in text or "asthma" in text:
        findings.append("Chronic lung disease")

        severity = "moderate" if severity != "high" else severity

        if "exacerbation" in text or "recent" in text:
            alerts.append("Recent pulmonary exacerbation increases perioperative risk")

        plan.append("Assess current control and bronchodilator use")

    # --- Smoking ---
    if "smoker" in text:
        findings.append("Active smoker")
        plan.append("Smoking increases pulmonary complications")

    # --- Obesity hypoventilation ---
    if "bmi" in text or "obesity" in text:
        findings.append("Possible obesity-related hypoventilation risk")
        interactions.append("Obesity + opioids → respiratory depression risk")

    # --- Pulmonary hypertension ---
    if "pulmonary hypertension" in text:
        findings.append("Pulmonary hypertension")

        severity = "high"

        alerts.append("Pulmonary hypertension → risk of RV failure and hypoxia")
        plan.append("Avoid hypoxia, hypercarbia, acidosis")

    # --- Home oxygen ---
    if "home oxygen" in text:
        findings.append("Home oxygen dependence")

        severity = "high"

        plan.append("High risk for postoperative respiratory support")

    # --- Opioids ---
    if "opioid" in text or "oxycodone" in text:
        interactions.append("Opioids increase respiratory depression risk")

    # --- Benzodiazepines ---
    if "benzodiazepine" in text or "lorazepam" in text:
        interactions.append("Benzodiazepines increase sedation risk")

    # --- Gabapentin ---
    if "gabapentin" in text:
        interactions.append("Gabapentin increases respiratory depression risk")

    # --- Missing critical data ---
    if "spo2" not in text:
        missing.append("Baseline oxygen saturation not documented")

    if "co2" not in text:
        missing.append("CO2/bicarbonate not documented")

    # --- Plan summary ---
    summary = "Low respiratory risk."

    if severity == "moderate":
        summary = "Moderate respiratory risk. Optimize pulmonary status and monitor closely."

    if severity == "high":
        summary = "High respiratory risk. Requires careful intraoperative management and postoperative monitoring."

    guardrails = [
        "Do not assume normal oxygenation without documented SpO2",
        "Do not assume CPAP compliance in OSA patients",
        "Do not assume safe opioid use without considering OSA/sedatives",
    ]

    return {
        "severity": severity,
        "findings": findings,
        "alerts": alerts,
        "interactions": interactions,
        "missing": missing,
        "plan": plan,
        "summary": summary,
        "guardrails": guardrails
    }