from typing import Any, Dict, List


def _get(result: Dict[str, Any], path: List[str], default=None):
    cur = result
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key, default)
    return cur


def build_disposition_module(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enterprise Postoperative Disposition Module.
    Uses outputs from other modules.
    Decision support only — does not create admission/ICU orders.
    """

    drivers = []
    monitoring_needs = []
    missing_data = []
    plan_changing_alerts = []
    guardrails = []
    confidence_limitations = []

    recommended_level = "routine PACU / standard recovery"
    severity_score = 0

    # -----------------------------
    # Pull module outputs
    # -----------------------------
    pulmonary = result.get("pulmonary", {})
    med_safety = result.get("med_safety", {})
    anticoag = result.get("anticoag", {})
    ponv = result.get("ponv", {})
    airway = result.get("airway_risk_module", {})
    scores = result.get("risk_scores", {})
    cardiac = result.get("cardiac_function_module", {})
    rcri = result.get("cardiac_risk_index", {})
    blood = result.get("blood_management_module", {})

    # -----------------------------
    # Pulmonary drivers
    # -----------------------------
    pulm_severity = pulmonary.get("severity")

    if pulm_severity == "high":
        severity_score += 3
        drivers.append("High pulmonary/respiratory risk")
        monitoring_needs.append("Continuous pulse oximetry")
        monitoring_needs.append("Low threshold for extended PACU or higher-acuity monitoring")
        plan_changing_alerts.append("Pulmonary risk may drive postoperative disposition.")

    elif pulm_severity == "moderate":
        severity_score += 2
        drivers.append("Moderate pulmonary/respiratory risk")
        monitoring_needs.append("Postoperative oxygenation monitoring")

    for finding in pulmonary.get("findings", []):
        finding_l = str(finding).lower()

        if "home oxygen" in finding_l:
            severity_score += 3
            drivers.append("Home oxygen dependence")
            monitoring_needs.append("Postoperative respiratory support readiness")

        if "pulmonary hypertension" in finding_l:
            severity_score += 4
            drivers.append("Pulmonary hypertension / RV-risk physiology")
            monitoring_needs.append("Telemetry or higher-acuity monitoring consideration")
            monitoring_needs.append("Avoid hypoxia, hypercarbia, acidosis")
            plan_changing_alerts.append("Pulmonary hypertension may require ICU/stepdown-level monitoring depending on severity.")

        if "osa" in finding_l or "sleep apnea" in finding_l:
            severity_score += 2
            drivers.append("OSA")
            monitoring_needs.append("Postoperative CPAP/BiPAP availability if used at home")

        if "copd" in finding_l or "chronic lung disease" in finding_l:
            severity_score += 2
            drivers.append("Chronic lung disease")

    for interaction in pulmonary.get("interactions", []):
        interaction_l = str(interaction).lower()
        if "opioid" in interaction_l or "benzodiazepine" in interaction_l or "gabapentin" in interaction_l:
            severity_score += 2
            drivers.append("Medication-related respiratory depression risk")
            monitoring_needs.append("Enhanced respiratory monitoring if opioids/sedatives required")

    if pulmonary.get("missing"):
        missing_data.extend(pulmonary.get("missing", []))
        confidence_limitations.append("Pulmonary risk confidence limited by missing respiratory baseline data.")

    # -----------------------------
    # Medication safety drivers
    # -----------------------------
    med_sev = med_safety.get("overall_severity")

    if med_sev == "critical":
        severity_score += 3
        drivers.append("Critical medication safety relevance")
        plan_changing_alerts.extend(med_safety.get("plan_changing_alerts", []))

    elif med_sev == "high":
        severity_score += 2
        drivers.append("High medication safety relevance")
        plan_changing_alerts.extend(med_safety.get("plan_changing_alerts", []))

    med_classes = [str(x).lower() for x in med_safety.get("medications_detected", [])]

    if any("opioid" in x for x in med_classes):
        severity_score += 1
        drivers.append("Chronic opioid therapy")
        monitoring_needs.append("Opioid-tolerant pain plan with respiratory-risk awareness")

    if any("benzodiazepine" in x or "sedative" in x for x in med_classes):
        severity_score += 1
        drivers.append("Sedative medication exposure")

    if any("gabapentinoid" in x for x in med_classes):
        severity_score += 1
        drivers.append("Gabapentinoid exposure")

    if any("pulmonary hypertension" in x for x in med_classes):
        severity_score += 3
        drivers.append("Pulmonary hypertension therapy present — continuation/availability matters")
        monitoring_needs.append("Ensure pulmonary vasodilator continuation plan")

    if any("sglt2" in x for x in med_classes):
        severity_score += 2
        drivers.append("SGLT2 inhibitor metabolic risk")
        monitoring_needs.append("Consider postoperative metabolic monitoring if hold status unclear or patient ill")

    if med_safety.get("critical_missing"):
        missing_data.extend(med_safety.get("critical_missing", []))
        confidence_limitations.append("Medication safety confidence limited by missing medication-management data.")

    # -----------------------------
    # Anticoagulation / bleeding drivers
    # -----------------------------
    if anticoag.get("bleeding_risk_level") == "high":
        severity_score += 2
        drivers.append("High bleeding / anticoagulation relevance")
        plan_changing_alerts.append("Anticoagulation may affect regional technique, bleeding preparation, and postoperative monitoring.")

    if anticoag.get("neuraxial_block_safe") is False:
        severity_score += 1
        drivers.append("Neuraxial/deep regional technique not safe without further review")

    if anticoag.get("red_flags"):
        plan_changing_alerts.extend(anticoag.get("red_flags", []))

    if anticoag.get("critical_missing"):
        missing_data.extend(anticoag.get("critical_missing", []))
        confidence_limitations.append("Bleeding/neuraxial confidence limited by missing anticoagulation data.")

    # -----------------------------
    # PONV / recovery drivers
    # -----------------------------
    if ponv.get("risk_level") in ["high", "very high"]:
        severity_score += 1
        drivers.append(f"{ponv.get('risk_level', '').upper()} PONV risk")
        monitoring_needs.append("PACU rescue antiemetic plan")
        plan_changing_alerts.append("High PONV risk may delay discharge readiness.")

    # -----------------------------
    # Airway drivers
    # -----------------------------
    difficult_mask = str(airway.get("difficult_mask_risk", "")).lower()
    difficult_intubation = str(airway.get("difficult_intubation_risk", "")).lower()
    aspiration = str(airway.get("aspiration_risk", "")).lower()

    if "high" in difficult_mask or "high" in difficult_intubation:
        severity_score += 2
        drivers.append("High airway risk documented")
        monitoring_needs.append("Post-extubation airway vigilance")

    if "high" in aspiration:
        severity_score += 1
        drivers.append("High aspiration risk")
        monitoring_needs.append("Monitor for aspiration/respiratory complications")

    if airway.get("missing_airway_data"):
        missing_data.extend(airway.get("missing_airway_data", []))
        confidence_limitations.append("Airway-related disposition confidence limited by missing airway exam data.")

    # -----------------------------
    # Cardiac / complexity drivers
    # -----------------------------
    global_score = scores.get("global_complexity_score")
    tier = str(scores.get("action_priority_tier", "")).lower()

    try:
        if int(global_score) >= 12:
            severity_score += 3
            drivers.append("High global complexity score")
    except Exception:
        pass

    if "high" in tier or "critical" in tier:
        severity_score += 2
        drivers.append(f"Action priority tier: {scores.get('action_priority_tier')}")

    nyha = str(cardiac.get("nyha_class", "")).lower()
    if "iii" in nyha or "iv" in nyha:
        severity_score += 3
        drivers.append(f"Reduced functional/cardiac reserve: NYHA {cardiac.get('nyha_class')}")
        monitoring_needs.append("Consider telemetry or higher-acuity postop monitoring")

    rcri_score = rcri.get("rcri_score")
    try:
        if int(rcri_score) >= 2:
            severity_score += 2
            drivers.append(f"Elevated cardiac risk index: RCRI {rcri_score}")
            monitoring_needs.append("Consider postoperative cardiac monitoring depending on procedure and symptoms")
    except Exception:
        pass

    # -----------------------------
    # Blood / anemia drivers
    # -----------------------------
    if str(blood.get("bleeding_risk_level", "")).lower() == "high":
        severity_score += 2
        drivers.append("High surgical/clinical bleeding risk")

    if str(blood.get("anemia_flag", "")).lower() in ["yes", "true", "present", "high"]:
        severity_score += 1
        drivers.append("Anemia documented")
        monitoring_needs.append("Postoperative hemoglobin/bleeding monitoring as appropriate")

    # -----------------------------
    # Recommendation logic
    # -----------------------------
    if severity_score >= 10:
        recommended_level = "ICU / high-acuity monitored setting should be considered"
        disposition_risk = "critical"
    elif severity_score >= 6:
        recommended_level = "stepdown / extended PACU / monitored bed should be considered"
        disposition_risk = "high"
    elif severity_score >= 3:
        recommended_level = "standard PACU with targeted monitoring considerations"
        disposition_risk = "moderate"
    else:
        recommended_level = "routine PACU / standard recovery"
        disposition_risk = "low"

    # Confidence
    confidence = "high"
    if missing_data:
        confidence = "moderate"
    if len(missing_data) >= 6:
        confidence = "limited"

    guardrails = [
        "Do not treat this as a final admission or ICU order.",
        "Do not assume outpatient eligibility when respiratory, bleeding, cardiac, or medication-risk data are missing.",
        "Do not assume CPAP adherence unless documented.",
        "Do not assume anticoagulation safety without last-dose timing and guideline-based review.",
        "Final disposition requires clinician judgment, surgical context, institutional resources, and real-time postoperative course."
    ]

    clinician_summary = (
        f"{disposition_risk.upper()} postoperative disposition concern. "
        f"Suggested level: {recommended_level}. "
        f"Primary drivers: {', '.join(sorted(set(drivers))[:6]) if drivers else 'none documented'}."
    )

    return {
        "module": "Postoperative Disposition",
        "recommended_level": recommended_level,
        "disposition_risk": disposition_risk,
        "severity_score": severity_score,
        "confidence": confidence,
        "drivers": sorted(set(drivers)),
        "monitoring_needs": sorted(set(monitoring_needs)),
        "missing_data": sorted(set(missing_data)),
        "plan_changing_alerts": sorted(set(plan_changing_alerts)),
        "confidence_limitations": sorted(set(confidence_limitations)),
        "do_not_assume_guardrails": guardrails,
        "clinician_summary": clinician_summary,
        "safety_statement": (
            "Decision support only. Does not determine final admission status, discharge eligibility, ICU need, "
            "or postoperative orders."
        )
    }