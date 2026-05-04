from typing import Any, Dict, List, Optional


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _med_list(patient_data: Dict[str, Any]) -> List[str]:
    meds = patient_data.get("medications", [])
    if isinstance(meds, str):
        meds = [meds]
    return [_norm(m) for m in meds]


def _has_any_med(patient_meds: List[str], keywords: List[str]) -> List[str]:
    matches = []
    for med in patient_meds:
        for keyword in keywords:
            if keyword in med:
                matches.append(med)
    return sorted(set(matches))


def build_ponv_module(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    PONV Module v4
    Includes:
    - Apfel-style risk scoring
    - Missing-data detection
    - Prophylaxis timing
    - Drug-level options with common adult reference doses
    - Contraindication filtering
    - Medication interaction flags
    - Rescue strategy

    Important:
    This is clinician decision support, not an automatic medication order.
    """

    patient_meds = _med_list(patient_data)

    ponv = {
    "module": "PONV",
    "safety_statement": (
        "Medication options and common adult reference doses are for clinician decision support only. "
        "Final drug choice, dose, route, and timing must follow local protocols, patient-specific factors, "
        "and clinician judgment."
    ),

    # Core risk output
    "risk_level": "not assessable",
    "risk_score_estimate": 0,
    "risk_factors_present": [],
    "missing_data": [],
    "why_it_matters": "",

    # Enterprise fields
    "severity": "not documented",
    "confidence": "limited_by_text_extraction",
    "clinician_summary": "",
    "drivers": [],
    "plan_changing_alerts": [],
    "contraindications_cautions": [],
    "do_not_assume_guardrails": [
        "Do not assume prophylaxis was given unless documented.",
        "Do not repeat the same antiemetic class too soon after failed prophylaxis.",
        "Do not ignore QT risk, Parkinson disease, sedation risk, glaucoma, urinary retention, or medication interactions.",
        "Do not treat suggested doses as automatic orders."
    ],

    # Drug-level intelligence
    "drug_options": [],
    "recommended_strategy": {
        "overall_approach": "",
        "preoperative": [],
        "induction": [],
        "end_of_case": [],
        "anesthetic_modifiers": [],
    },
    "rescue_plan": {
        "early_pacu": [],
        "delayed": [],
        "principles": [],
    },
    "contraindication_flags": [],
    "medication_interaction_flags": [],
    "plan_summary": "",
}

    sex = _norm(patient_data.get("sex"))
    smoking_status = _norm(patient_data.get("smoking_status"))

    prior_ponv = patient_data.get("prior_ponv")
    motion_sickness = patient_data.get("motion_sickness")
    postop_opioids_expected = patient_data.get("postop_opioids_expected")

    qt_prolongation = patient_data.get("qt_prolongation")
    parkinson_disease = patient_data.get("parkinson_disease")
    high_sedation_risk = patient_data.get("high_sedation_risk")
    elderly_delirium_risk = patient_data.get("elderly_delirium_risk")
    glaucoma = patient_data.get("glaucoma")
    urinary_retention = patient_data.get("urinary_retention")
    osa = patient_data.get("osa")
    chronic_opioid_use = patient_data.get("chronic_opioid_use")
    diabetes_poor_control = patient_data.get("diabetes_poor_control")
    bowel_obstruction = patient_data.get("bowel_obstruction")

    # -----------------------------
    # Missing data
    # -----------------------------
    if not sex:
        ponv["missing_data"].append("sex not documented")
    if not smoking_status:
        ponv["missing_data"].append("smoking status not documented")
    if prior_ponv is None:
        ponv["missing_data"].append("prior PONV history not documented")
    if motion_sickness is None:
        ponv["missing_data"].append("motion sickness history not documented")
    if postop_opioids_expected is None:
        ponv["missing_data"].append("postoperative opioid plan not documented")

    # -----------------------------
    # Risk scoring
    # -----------------------------
    score = 0

    if sex == "female":
        score += 1
        ponv["risk_factors_present"].append("female sex")

    if smoking_status in ["nonsmoker", "non-smoker", "never smoker"]:
        score += 1
        ponv["risk_factors_present"].append("nonsmoker")

    if prior_ponv is True:
        score += 1
        ponv["risk_factors_present"].append("history of prior PONV")

    if motion_sickness is True:
        score += 1
        ponv["risk_factors_present"].append("history of motion sickness")

    if postop_opioids_expected is True:
        score += 1
        ponv["risk_factors_present"].append("postoperative opioids expected")

    ponv["risk_score_estimate"] = score

    if score <= 1:
        ponv["risk_level"] = "low"
    elif score == 2:
        ponv["risk_level"] = "moderate"
    elif score == 3:
        ponv["risk_level"] = "high"
    else:
        ponv["risk_level"] = "very high"

    # -----------------------------
    # Drug options
    # -----------------------------
    drug_options = [
        {
            "drug": "ondansetron",
            "class": "5-HT3 antagonist",
            "typical_adult_reference_dose": "4 mg IV",
            "typical_timing": "near end of case or rescue if 5-HT3 antagonist not already used",
            "avoid_or_caution_if": ["QT prolongation", "concurrent QT-prolonging medications"],
            "status": "available_option",
            "flags": [],
        },
        {
            "drug": "dexamethasone",
            "class": "corticosteroid",
            "typical_adult_reference_dose": "4–8 mg IV",
            "typical_timing": "after induction",
            "avoid_or_caution_if": ["poor glycemic control", "active infection concern"],
            "status": "available_option",
            "flags": [],
        },
        {
            "drug": "droperidol",
            "class": "butyrophenone / dopamine antagonist",
            "typical_adult_reference_dose": "0.625–1.25 mg IV",
            "typical_timing": "near end of case or rescue from alternate class",
            "avoid_or_caution_if": ["QT prolongation", "Parkinson disease", "EPS risk", "concurrent dopamine blockers"],
            "status": "available_option",
            "flags": [],
        },
        {
            "drug": "haloperidol",
            "class": "dopamine antagonist",
            "typical_adult_reference_dose": "0.5–1 mg IV",
            "typical_timing": "rescue or prophylaxis depending on local practice",
            "avoid_or_caution_if": ["QT prolongation", "Parkinson disease", "EPS risk", "concurrent dopamine blockers"],
            "status": "available_option",
            "flags": [],
        },
        {
            "drug": "metoclopramide",
            "class": "dopamine antagonist / prokinetic",
            "typical_adult_reference_dose": "10 mg IV",
            "typical_timing": "rescue",
            "avoid_or_caution_if": ["Parkinson disease", "bowel obstruction", "EPS risk", "concurrent dopamine blockers"],
            "status": "available_option",
            "flags": [],
        },
        {
            "drug": "promethazine",
            "class": "phenothiazine / antihistamine",
            "typical_adult_reference_dose": "6.25–12.5 mg IV/IM",
            "typical_timing": "rescue",
            "avoid_or_caution_if": ["OSA", "high sedation risk", "respiratory depression risk", "concurrent CNS depressants"],
            "status": "available_option",
            "flags": [],
        },
        {
            "drug": "scopolamine",
            "class": "anticholinergic",
            "typical_adult_reference_dose": "1.5 mg transdermal patch",
            "typical_timing": "preoperative, ideally several hours before surgery",
            "avoid_or_caution_if": ["glaucoma", "urinary retention", "elderly delirium risk"],
            "status": "available_option",
            "flags": [],
        },
        {
            "drug": "aprepitant",
            "class": "NK1 antagonist",
            "typical_adult_reference_dose": "40 mg PO",
            "typical_timing": "preoperative",
            "avoid_or_caution_if": ["major CYP3A4 drug interactions", "formulary limitation"],
            "status": "available_option",
            "flags": [],
        },
        {
            "drug": "fosaprepitant",
            "class": "NK1 antagonist",
            "typical_adult_reference_dose": "150 mg IV",
            "typical_timing": "preoperative",
            "avoid_or_caution_if": ["major CYP3A4 drug interactions", "infusion reaction risk", "formulary limitation"],
            "status": "available_option",
            "flags": [],
        },
        {
            "drug": "amisulpride",
            "class": "D2/D3 antagonist",
            "typical_adult_reference_dose": "5 mg IV prophylaxis; 10 mg IV rescue",
            "typical_timing": "prophylaxis or rescue depending on prior agents",
            "avoid_or_caution_if": ["QT prolongation", "Parkinson disease", "concurrent dopamine blockers"],
            "status": "available_option",
            "flags": [],
        },
    ]

    def flag_drug(drug_name: str, reason: str, severity: str = "caution") -> None:
        for drug in drug_options:
            if drug["drug"] == drug_name:
                drug["status"] = "caution" if severity == "caution" else "avoid_or_high_caution"
                drug["flags"].append(reason)

    def add_contra_flag(reason: str, affected: List[str]) -> None:
        ponv["contraindication_flags"].append({
            "reason": reason,
            "affected_antiemetics": affected,
        })

    def add_interaction_flag(kind: str, trigger_meds: List[str], affected: List[str], message: str) -> None:
        ponv["medication_interaction_flags"].append({
            "interaction_type": kind,
            "trigger_medications_found": trigger_meds,
            "affected_antiemetics": affected,
            "message": message,
        })

    # -----------------------------
    # Contraindication logic
    # -----------------------------
    if qt_prolongation is True:
        affected = ["ondansetron", "droperidol", "haloperidol", "amisulpride"]
        for d in affected:
            flag_drug(d, "QT prolongation documented", "high")
        add_contra_flag("QT prolongation documented", affected)

    if parkinson_disease is True:
        affected = ["droperidol", "haloperidol", "metoclopramide", "amisulpride"]
        for d in affected:
            flag_drug(d, "Parkinson disease documented; dopamine antagonism may worsen symptoms", "high")
        add_contra_flag("Parkinson disease documented", affected)

    if high_sedation_risk is True or osa is True:
        affected = ["promethazine"]
        flag_drug("promethazine", "OSA/high sedation risk documented", "high")
        add_contra_flag("OSA or high sedation risk documented", affected)

    if elderly_delirium_risk is True:
        affected = ["scopolamine"]
        flag_drug("scopolamine", "elderly/delirium risk documented", "caution")
        add_contra_flag("elderly or delirium risk documented", affected)

    if glaucoma is True:
        affected = ["scopolamine"]
        flag_drug("scopolamine", "glaucoma documented", "high")
        add_contra_flag("glaucoma documented", affected)

    if urinary_retention is True:
        affected = ["scopolamine"]
        flag_drug("scopolamine", "urinary retention documented", "high")
        add_contra_flag("urinary retention documented", affected)

    if diabetes_poor_control is True:
        affected = ["dexamethasone"]
        flag_drug("dexamethasone", "poor glycemic control documented", "caution")
        add_contra_flag("poor glycemic control documented", affected)

    if bowel_obstruction is True:
        affected = ["metoclopramide"]
        flag_drug("metoclopramide", "bowel obstruction concern documented", "high")
        add_contra_flag("bowel obstruction concern documented", affected)

    # -----------------------------
    # Medication interaction logic
    # -----------------------------
    QT_PROLONGING = [
        "amiodarone", "sotalol", "dofetilide", "ibutilide", "methadone",
        "azithromycin", "clarithromycin", "erythromycin",
        "ciprofloxacin", "levofloxacin", "moxifloxacin",
        "quetiapine", "ziprasidone", "risperidone", "olanzapine",
        "citalopram", "escitalopram", "tacrolimus"
    ]

    CNS_DEPRESSANTS = [
        "morphine", "hydromorphone", "oxycodone", "hydrocodone", "fentanyl",
        "methadone", "tramadol", "lorazepam", "alprazolam", "diazepam",
        "clonazepam", "midazolam", "zolpidem", "eszopiclone",
        "gabapentin", "pregabalin", "baclofen", "tizanidine"
    ]

    SEROTONERGIC = [
        "sertraline", "fluoxetine", "paroxetine", "citalopram", "escitalopram",
        "venlafaxine", "duloxetine", "desvenlafaxine", "trazodone",
        "mirtazapine", "linezolid", "tramadol", "meperidine", "maoi",
        "phenelzine", "tranylcypromine"
    ]

    DOPAMINE_BLOCKERS = [
        "haloperidol", "droperidol", "metoclopramide", "prochlorperazine",
        "chlorpromazine", "quetiapine", "risperidone", "olanzapine",
        "ziprasidone", "aripiprazole"
    ]

    CYP3A4_INTERACTORS = [
        "clarithromycin", "erythromycin", "ketoconazole", "itraconazole",
        "voriconazole", "posaconazole", "ritonavir", "cobicistat",
        "rifampin", "rifabutin", "carbamazepine", "phenytoin",
        "phenobarbital", "st john"
    ]

    qt_meds = _has_any_med(patient_meds, QT_PROLONGING)
    if qt_meds:
        affected = ["ondansetron", "droperidol", "haloperidol", "amisulpride"]
        for d in affected:
            flag_drug(d, f"additive QT risk with current medication(s): {', '.join(qt_meds)}", "caution")
        add_interaction_flag(
            "QT prolongation",
            qt_meds,
            affected,
            "Patient is taking medication(s) associated with QT prolongation; additive QT risk may affect antiemetic selection."
        )

    cns_meds = _has_any_med(patient_meds, CNS_DEPRESSANTS)
    if cns_meds:
        affected = ["promethazine"]
        flag_drug("promethazine", f"additive sedation/respiratory depression risk with: {', '.join(cns_meds)}", "caution")
        add_interaction_flag(
            "CNS/respiratory depression",
            cns_meds,
            affected,
            "Concurrent CNS depressants increase sedation and respiratory depression risk with sedating antiemetics."
        )

    serotonin_meds = _has_any_med(patient_meds, SEROTONERGIC)
    if serotonin_meds:
        affected = ["ondansetron", "metoclopramide"]
        for d in affected:
            flag_drug(d, f"serotonergic medication(s) present: {', '.join(serotonin_meds)}", "caution")
        add_interaction_flag(
            "Serotonergic burden",
            serotonin_meds,
            affected,
            "Serotonergic medications present; consider theoretical serotonin-toxicity risk with serotonergic antiemetic strategies."
        )

    dopamine_meds = _has_any_med(patient_meds, DOPAMINE_BLOCKERS)
    if dopamine_meds:
        affected = ["droperidol", "haloperidol", "metoclopramide", "amisulpride"]
        for d in affected:
            flag_drug(d, f"concurrent dopamine-blocking medication(s): {', '.join(dopamine_meds)}", "caution")
        add_interaction_flag(
            "Dopamine blockade stacking",
            dopamine_meds,
            affected,
            "Concurrent dopamine-blocking medications may increase EPS risk and may also add QT risk."
        )

    cyp_meds = _has_any_med(patient_meds, CYP3A4_INTERACTORS)
    if cyp_meds:
        affected = ["aprepitant", "fosaprepitant"]
        for d in affected:
            flag_drug(d, f"possible CYP3A4 interaction with: {', '.join(cyp_meds)}", "caution")
        add_interaction_flag(
            "CYP3A4 interaction",
            cyp_meds,
            affected,
            "Potential CYP3A4 interaction may alter NK1 antagonist exposure or interacting medication levels."
        )

    ponv["drug_options"] = drug_options

    # -----------------------------
    # Strategy by risk level
    # -----------------------------
    if ponv["risk_level"] == "low":
        ponv["recommended_strategy"]["overall_approach"] = (
            "Low documented PONV risk. Minimal prophylaxis may be reasonable unless additional undocumented risk factors are identified."
        )
    elif ponv["risk_level"] == "moderate":
        ponv["recommended_strategy"]["overall_approach"] = (
            "Moderate PONV risk. Consider 1–2 antiemetic classes with staged timing."
        )
        ponv["recommended_strategy"]["induction"].append("Consider dexamethasone after induction if appropriate.")
        ponv["recommended_strategy"]["end_of_case"].append("Consider ondansetron near end of case if appropriate.")
    elif ponv["risk_level"] == "high":
        ponv["recommended_strategy"]["overall_approach"] = (
            "High PONV risk. Consider multimodal prophylaxis with at least 2 antiemetic classes."
        )
        ponv["recommended_strategy"]["preoperative"].append("Consider scopolamine patch preoperatively if appropriate and not contraindicated.")
        ponv["recommended_strategy"]["induction"].append("Consider dexamethasone after induction if appropriate.")
        ponv["recommended_strategy"]["end_of_case"].append("Consider ondansetron near end of case and/or another non-overlapping class if appropriate.")
    else:
        ponv["recommended_strategy"]["overall_approach"] = (
            "Very high PONV risk. Consider 3 or more antiemetic classes plus anesthetic technique modification."
        )
        ponv["recommended_strategy"]["preoperative"].extend([
            "Consider scopolamine patch preoperatively if appropriate and not contraindicated.",
            "Consider NK1 antagonist such as aprepitant/fosaprepitant if available, appropriate, and no major interaction concerns."
        ])
        ponv["recommended_strategy"]["induction"].append("Consider dexamethasone after induction if appropriate.")
        ponv["recommended_strategy"]["end_of_case"].append("Consider ondansetron and/or dopamine-antagonist class depending on contraindications and local protocol.")

    ponv["recommended_strategy"]["anesthetic_modifiers"] = [
        "Consider propofol-based TIVA when clinically appropriate.",
        "Avoid nitrous oxide when clinically appropriate.",
        "Minimize volatile anesthetic exposure when feasible.",
        "Use opioid-sparing multimodal analgesia when clinically appropriate.",
        "Consider regional, neuraxial, or local analgesic techniques when appropriate."
    ]

    # -----------------------------
    # Rescue plan
    # -----------------------------
    ponv["rescue_plan"]["early_pacu"] = [
        "If PONV occurs despite prophylaxis, choose rescue therapy from a different pharmacologic class than agents already given.",
        "If no 5-HT3 antagonist was used prophylactically, ondansetron may be considered as rescue if not contraindicated.",
        "If a 5-HT3 antagonist was already used, consider alternate class options such as dopamine antagonist, antihistamine/phenothiazine, anticholinergic, or NK1 antagonist depending on contraindications and local formulary."
    ]

    ponv["rescue_plan"]["delayed"] = [
        "For delayed PONV, consider an alternative class not previously used.",
        "Avoid repeating the same class too soon unless sufficient time has elapsed and local guidance supports redosing.",
        "Reassess for non-PONV causes if symptoms are persistent or severe."
    ]

    ponv["rescue_plan"]["principles"] = [
        "Rescue antiemetic should generally be from a different class than prophylaxis.",
        "Repeating the same class early after failure usually provides limited benefit.",
        "Match rescue choice to QT risk, sedation risk, Parkinson disease, delirium risk, glaucoma, urinary retention, bowel obstruction concern, and current medications."
    ]

    # -----------------------------
    # Why it matters + summary
    # -----------------------------
    if ponv["risk_level"] in ["high", "very high"]:
        ponv["why_it_matters"] = (
            "Elevated PONV risk may delay PACU recovery, worsen patient experience, increase aspiration risk, "
            "and contribute to delayed discharge or unplanned admission."
        )
    elif ponv["risk_level"] == "moderate":
        ponv["why_it_matters"] = "Moderate PONV risk may affect recovery quality and discharge readiness."
    else:
        ponv["why_it_matters"] = (
            "Low documented PONV risk based on available data, but missing risk-factor data may limit confidence."
        )

    ponv["plan_summary"] = (
        f"{ponv['risk_level'].capitalize()} PONV risk with score estimate {score}. "
        f"{ponv['recommended_strategy']['overall_approach']} "
        "Use drug options after reviewing contraindication and medication-interaction flags. "
        "Plan rescue from a different antiemetic class if PONV occurs."
    )

# -----------------------------
# Enterprise fields
# -----------------------------

    ponv["drivers"] = ponv.get("risk_factors_present", [])

    if ponv["risk_level"] == "very high":
        ponv["severity"] = "high"
    elif ponv["risk_level"] == "high":
        ponv["severity"] = "moderate"
    elif ponv["risk_level"] == "moderate":
        ponv["severity"] = "moderate"
    else:
        ponv["severity"] = "low"

    if ponv.get("missing_data"):
        ponv["confidence"] = "limited_by_missing_data"
    else:
        ponv["confidence"] = "moderate"

    if ponv["risk_level"] in ["high", "very high"]:
        ponv["plan_changing_alerts"].append(
            "High PONV risk may require multimodal prophylaxis, anesthetic technique modification, and rescue planning."
       )

    if ponv.get("contraindication_flags"):
        ponv["plan_changing_alerts"].append(
        "PONV medication selection affected by contraindications or patient-specific cautions."
       )

    if ponv.get("medication_interaction_flags"):
        ponv["plan_changing_alerts"].append(
        "PONV medication selection affected by current medication interactions."
       )

    ponv["contraindications_cautions"] = [
        c.get("reason", str(c)) for c in ponv.get("contraindication_flags", [])
    ]

    ponv["clinician_summary"] = (
        f"{ponv['risk_level'].upper()} PONV risk with score estimate {score}. "
        f"{ponv['why_it_matters']} "
        f"{ponv['recommended_strategy']['overall_approach']}"
    )

    return ponv