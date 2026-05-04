from typing import Any, Dict, List


def _norm(value: Any) -> str:
    return "" if value is None else str(value).strip().lower()


def _med_list(data: Dict[str, Any]) -> List[str]:
    meds = data.get("medications", [])
    if isinstance(meds, str):
        meds = [meds]
    return [_norm(m) for m in meds]


def _contains(meds_str: str, terms: List[str]) -> bool:
    return any(term in meds_str for term in terms)


def build_med_safety_module(data: Dict[str, Any]) -> Dict[str, Any]:
    meds = _med_list(data)
    meds_str = " ".join(meds)

    items = []
    global_missing = []
    plan_changing_alerts = []
    interaction_alerts = []
    contraindication_cautions = []

    def add_item(
        medication_class: str,
        detected_terms: List[str],
        severity: str,
        confidence: str,
        why_it_matters: str,
        missing_data: List[str],
        suggested_next_steps: List[str],
        plan_changers: List[str] = None,
        interactions: List[str] = None,
        cautions: List[str] = None,
        do_not_assume: List[str] = None,
    ):
        plan_changers = plan_changers or []
        interactions = interactions or []
        cautions = cautions or []
        do_not_assume = do_not_assume or []

        items.append({
            "medication_class": medication_class,
            "detected_terms": detected_terms,
            "severity": severity,
            "confidence": confidence,
            "why_it_matters": why_it_matters,
            "missing_data": missing_data,
            "suggested_next_steps": suggested_next_steps,
            "plan_changing_alerts": plan_changers,
            "interaction_alerts": interactions,
            "contraindications_cautions": cautions,
            "do_not_assume": do_not_assume,
        })

        global_missing.extend(missing_data)
        plan_changing_alerts.extend(plan_changers)
        interaction_alerts.extend(interactions)
        contraindication_cautions.extend(cautions)

    def found(terms: List[str]) -> List[str]:
        return [t for t in terms if t in meds_str]

    # 1 GLP-1
    terms = ["semaglutide", "ozempic", "wegovy", "tirzepatide", "mounjaro", "zepbound", "liraglutide", "dulaglutide", "trulicity"]
    f = found(terms)
    if f:
        add_item(
            "GLP-1 receptor agonist",
            f,
            "high",
            "high",
            "May delay gastric emptying and increase aspiration concern, especially with escalation phase, high dose, weekly formulation, active GI symptoms, or other gastroparesis risks.",
            ["Last dose timing not documented", "Presence/absence of GI symptoms not documented", "Dose escalation phase not documented"],
            ["Clarify last dose, formulation, escalation phase, GI symptoms, and institutional GLP-1 policy.", "If high-risk features present, consider aspiration-risk mitigation such as liquid diet strategy, gastric ultrasound when available, or full-stomach precautions."],
            ["May change aspiration strategy or timing if high-risk GLP-1 features are present."],
            cautions=["Do not automatically cancel solely for GLP-1 presence; risk-stratify."],
            do_not_assume=["Do not assume stomach is empty based only on standard NPO time."]
        )

    # 2 SGLT2
    terms = ["empagliflozin", "jardiance", "dapagliflozin", "farxiga", "canagliflozin", "invokana", "ertugliflozin"]
    f = found(terms)
    if f:
        add_item(
            "SGLT2 inhibitor",
            f,
            "critical",
            "high",
            "Associated with perioperative euglycemic DKA risk, especially if not held, fasting, infection, dehydration, insulin deficiency, or major surgery.",
            ["Hold status not documented", "Ketone/acidosis assessment not documented", "Diabetes control not documented"],
            ["Confirm preoperative hold status.", "If not held or patient is ill, consider ketone/anion gap/bicarbonate assessment per institutional protocol."],
            ["May require metabolic workup, delay, or enhanced monitoring if not held or symptomatic."],
            cautions=["Euglycemic DKA can occur with normal or mildly elevated glucose."],
            do_not_assume=["Do not rule out DKA solely because glucose is not high."]
        )

    # 3 insulin
    terms = ["insulin", "glargine", "lantus", "basaglar", "detemir", "levemir", "degludec", "tresiba", "lispro", "humalog", "aspart", "novolog", "regular insulin"]
    f = found(terms)
    if f:
        add_item(
            "Insulin therapy",
            f,
            "high",
            "high",
            "Creates perioperative hypoglycemia/hyperglycemia risk and requires basal/bolus adjustment planning.",
            ["Perioperative insulin plan not documented", "Recent glucose/A1c not documented"],
            ["Clarify basal insulin plan, short-acting insulin plan, NPO status, and glucose monitoring schedule."],
            ["May require glucose management protocol."],
            do_not_assume=["Do not assume home insulin dosing is safe while NPO."]
        )

    # 4 metformin
    terms = ["metformin"]
    f = found(terms)
    if f:
        add_item(
            "Metformin",
            f,
            "moderate",
            "high",
            "Renal dysfunction, contrast exposure, or major illness may increase lactic acidosis concern.",
            ["Renal function not documented", "Hold plan not documented"],
            ["Assess renal function and institutional perioperative hold policy."],
            ["May change diabetes medication plan if renal dysfunction or contrast exposure present."]
        )

    # 5 ACE/ARB
    terms = ["lisinopril", "enalapril", "ramipril", "benazepril", "losartan", "valsartan", "olmesartan", "irbesartan", "candesartan"]
    f = found(terms)
    if f:
        add_item(
            "ACE inhibitor / ARB",
            f,
            "moderate",
            "high",
            "May contribute to intraoperative hypotension depending on patient/procedure context and local practice.",
            ["Day-of-surgery continuation/hold plan not documented"],
            ["Clarify institutional plan for morning-of-surgery ACE/ARB use."],
            ["May affect hemodynamic planning."]
        )

    # 6 beta blocker
    terms = ["metoprolol", "atenolol", "carvedilol", "bisoprolol", "propranolol", "labetalol", "nebivolol"]
    f = found(terms)
    if f:
        add_item(
            "Beta blocker",
            f,
            "moderate",
            "high",
            "Abrupt discontinuation may cause rebound tachycardia/hypertension; continuation is often important unless contraindicated.",
            ["Continuation plan not documented"],
            ["Confirm continuation plan and baseline heart rate/blood pressure."],
            interactions=["Additive bradycardia/hypotension risk with calcium channel blockers or anesthetic agents."]
        )

    # 7 calcium channel blocker
    terms = ["amlodipine", "diltiazem", "verapamil", "nifedipine"]
    f = found(terms)
    if f:
        add_item(
            "Calcium channel blocker",
            f,
            "moderate",
            "high",
            "Can contribute to hypotension or bradycardia, especially diltiazem/verapamil with beta blockers.",
            ["Continuation plan not documented"],
            ["Review hemodynamics, nodal agent combinations, and continuation plan."],
            interactions=["Additive bradycardia with beta blockers."]
        )

    # 8 diuretics
    terms = ["furosemide", "torsemide", "bumetanide", "hydrochlorothiazide", "chlorthalidone", "spironolactone", "eplerenone"]
    f = found(terms)
    if f:
        add_item(
            "Diuretic",
            f,
            "moderate",
            "high",
            "May affect volume status, potassium, renal function, and intraoperative hemodynamics.",
            ["Recent electrolytes not documented", "Renal function not documented", "Day-of-surgery plan not documented"],
            ["Check potassium, creatinine/eGFR, volume status, and day-of-surgery plan."],
            ["May change fluid/electrolyte plan."]
        )

    # 9 anticoagulants
    terms = ["apixaban", "eliquis", "rivaroxaban", "xarelto", "dabigatran", "pradaxa", "edoxaban", "warfarin", "coumadin", "enoxaparin", "lovenox", "heparin"]
    f = found(terms)
    if f:
        add_item(
            "Anticoagulant",
            f,
            "critical",
            "high",
            "Plan-changing bleeding, neuraxial/regional anesthesia, and surgical timing implications.",
            ["Last dose timing not documented", "Indication not documented", "Renal function not documented"],
            ["Confirm agent, dose, indication, renal function, last dose, and procedure/regional plan."],
            ["May change neuraxial/regional eligibility, surgical timing, or bleeding preparation."],
            cautions=["Coordinate with anticoagulation/regional anesthesia guidance."],
            do_not_assume=["Do not assume neuraxial safety without verified hold interval and relevant labs."]
        )

    # 10 antiplatelets
    terms = ["aspirin", "clopidogrel", "plavix", "prasugrel", "effient", "ticagrelor", "brilinta"]
    f = found(terms)
    if f:
        add_item(
            "Antiplatelet therapy",
            f,
            "high",
            "high",
            "Bleeding risk must be balanced against thrombotic risk, especially recent coronary stents.",
            ["Indication/stent history not documented", "Hold/continue plan not documented"],
            ["Clarify indication, stent timing, surgeon/cardiology plan, and regional anesthesia implications."],
            ["May change bleeding strategy and regional anesthesia eligibility."]
        )

    # 11 opioids
    terms = ["oxycodone", "hydrocodone", "morphine", "hydromorphone", "fentanyl patch", "methadone", "buprenorphine", "tramadol"]
    f = found(terms)
    if f:
        add_item(
            "Chronic opioid therapy",
            f,
            "high",
            "high",
            "Opioid tolerance, PONV, hyperalgesia, withdrawal risk, and respiratory depression risk.",
            ["Baseline daily opioid dose not documented", "Postoperative pain plan not documented"],
            ["Plan opioid-tolerant multimodal analgesia and respiratory monitoring."],
            ["May affect PACU/disposition and analgesic strategy."],
            interactions=["Additive respiratory depression with benzodiazepines, gabapentinoids, sedating antiemetics, and OSA."]
        )

    # 12 benzos/sedatives
    terms = ["lorazepam", "ativan", "alprazolam", "xanax", "diazepam", "valium", "clonazepam", "midazolam", "zolpidem", "ambien"]
    f = found(terms)
    if f:
        add_item(
            "Benzodiazepine / sedative hypnotic",
            f,
            "high",
            "high",
            "Increases sedation, delirium, falls, and respiratory depression risk when combined with opioids or OSA.",
            ["Sedation risk plan not documented"],
            ["Use caution with additional sedatives and assess OSA/respiratory risk."],
            ["May affect PACU monitoring and sedative strategy."],
            interactions=["Additive respiratory depression with opioids/gabapentinoids."]
        )

    # 13 gabapentinoids
    terms = ["gabapentin", "neurontin", "pregabalin", "lyrica"]
    f = found(terms)
    if f:
        add_item(
            "Gabapentinoid",
            f,
            "high",
            "high",
            "Can increase sedation and respiratory depression risk, especially with opioids, elderly patients, renal dysfunction, or OSA.",
            ["Renal function not documented", "Respiratory risk plan not documented"],
            ["Review renal function and additive sedation risk."],
            interactions=["Additive respiratory depression with opioids/benzodiazepines."]
        )

    # 14 serotonergic
    terms = ["sertraline", "zoloft", "fluoxetine", "prozac", "paroxetine", "paxil", "citalopram", "escitalopram", "venlafaxine", "duloxetine", "trazodone", "linezolid"]
    f = found(terms)
    if f:
        add_item(
            "Serotonergic medication",
            f,
            "moderate",
            "high",
            "Potential serotonergic interactions and possible bleeding tendency considerations with antiplatelet/NSAID context.",
            ["Interaction review not documented"],
            ["Review serotonergic analgesic/antiemetic combinations and bleeding context."],
            interactions=["Caution with serotonergic opioids such as tramadol/meperidine and linezolid/MAOI combinations."]
        )

    # 15 MAOI
    terms = ["phenelzine", "nardil", "tranylcypromine", "parnate", "isocarboxazid", "selegiline", "rasagiline"]
    f = found(terms)
    if f:
        add_item(
            "MAO inhibitor",
            f,
            "critical",
            "high",
            "Major interaction risk with vasopressors, serotonergic drugs, and some opioids.",
            ["MAOI perioperative plan not documented"],
            ["Create explicit anesthetic drug/vasopressor interaction plan."],
            ["May significantly change anesthetic and analgesic drug selection."],
            interactions=["Avoid high-risk interacting serotonergic/sympathomimetic combinations per institutional guidance."]
        )

    # 16 antiarrhythmics/QT
    terms = ["amiodarone", "sotalol", "dofetilide", "flecainide", "propafenone", "quinidine"]
    f = found(terms)
    if f:
        add_item(
            "Antiarrhythmic / QT-risk medication",
            f,
            "high",
            "high",
            "QT prolongation, bradycardia, conduction delay, and interaction risk.",
            ["Recent ECG/QT assessment not documented", "Electrolytes not documented"],
            ["Review ECG/QT, potassium/magnesium, and antiemetic/anesthetic interactions."],
            ["May affect antiemetic and anesthetic medication selection."],
            interactions=["Additive QT risk with ondansetron, droperidol, haloperidol, and other QT-prolonging agents."]
        )

    # 17 pulmonary HTN meds
    terms = ["sildenafil", "revatio", "tadalafil", "adcirca", "bosentan", "ambrisentan", "macitentan", "epoprostenol", "treprostinil", "iloprost", "riociguat"]
    f = found(terms)
    if f:
        add_item(
            "Pulmonary hypertension therapy",
            f,
            "critical",
            "high",
            "Abrupt interruption may worsen pulmonary hypertension or right heart failure.",
            ["Pulmonary vasodilator continuation plan not documented", "Pulmonary hypertension severity not documented"],
            ["Ensure perioperative continuation/availability and clarify pulmonary hypertension severity."],
            ["Major anesthetic and postoperative disposition implications."],
            do_not_assume=["Do not interrupt continuous prostacyclin therapy without expert plan."]
        )

    # 18 chronic steroids
    terms = ["prednisone", "prednisolone", "hydrocortisone", "methylprednisolone"]
    f = found(terms)
    if f:
        add_item(
            "Chronic steroid therapy",
            f,
            "high",
            "high",
            "Adrenal suppression, infection, wound, and glucose risk may be relevant.",
            ["Steroid dose/duration not documented", "Stress-dose plan not documented"],
            ["Clarify chronicity/dose and need for stress-dose steroids per protocol."],
            ["May affect hemodynamic and glucose management."]
        )

    # 19 immunosuppressants/transplant
    terms = ["tacrolimus", "prograf", "cyclosporine", "mycophenolate", "cellcept", "sirolimus", "everolimus", "azathioprine"]
    f = found(terms)
    if f:
        add_item(
            "Immunosuppressant / transplant medication",
            f,
            "high",
            "high",
            "Infection, renal toxicity, drug interactions, and continuation concerns.",
            ["Transplant organ/status not documented", "Continuation plan not documented", "Renal function not documented"],
            ["Coordinate continuation plan and check renal function/drug interactions."],
            ["May affect infection precautions, renal monitoring, and medication selection."]
        )

    # 20 Parkinson meds
    terms = ["levodopa", "carbidopa", "sinemet", "pramipexole", "ropinirole", "rotigotine", "amantadine"]
    f = found(terms)
    if f:
        add_item(
            "Parkinson / dopaminergic therapy",
            f,
            "high",
            "high",
            "Interruption may worsen rigidity, aspiration risk, neuroleptic sensitivity, and perioperative mobility.",
            ["Continuation timing not documented"],
            ["Continue dopaminergic therapy when feasible and avoid dopamine-antagonist antiemetics when appropriate."],
            ["May affect antiemetic selection and aspiration/airway risk."],
            interactions=["Avoid or use high caution with dopamine antagonist antiemetics such as metoclopramide, droperidol, haloperidol, prochlorperazine."]
        )

    overall_severity = "low"
    if any(i["severity"] == "critical" for i in items):
        overall_severity = "critical"
    elif any(i["severity"] == "high" for i in items):
        overall_severity = "high"
    elif any(i["severity"] == "moderate" for i in items):
        overall_severity = "moderate"

    if not items:
        clinician_summary = "No high-impact perioperative medication class detected from available text. Medication reconciliation still required."
    else:
        clinician_summary = (
            f"{overall_severity.upper()} medication safety relevance detected across {len(items)} high-impact medication class(es). "
            "Verify missing data, institutional hold/continue rules, interactions, and plan-changing alerts before final anesthetic planning."
        )

    return {
        "module": "Medication Safety",
        "overall_severity": overall_severity,
        "confidence": "limited_by_text_extraction",
        "items": items,
        "medications_detected": sorted({i["medication_class"] for i in items}),
        "critical_missing": sorted(set(global_missing)),
        "plan_changing_alerts": sorted(set(plan_changing_alerts)),
        "interaction_alerts": sorted(set(interaction_alerts)),
        "contraindications_cautions": sorted(set(contraindication_cautions)),
        "clinician_summary": clinician_summary,
        "do_not_assume_guardrails": [
            "Do not place medication orders automatically.",
            "Do not assume home medication list is reconciled.",
            "Do not assume last dose timing unless explicitly documented.",
            "Do not assume institutional hold/continue policy.",
            "Do not use this as final clearance."
        ],
        "safety_statement": (
            "Decision support only. Medication continuation, holding, dosing, and ordering require clinician review "
            "and institutional protocol."
        )
    }