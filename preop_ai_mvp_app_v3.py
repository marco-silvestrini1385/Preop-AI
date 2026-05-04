import os
import json
from datetime import datetime
from typing import Any, Dict

import streamlit as st
from dotenv import load_dotenv
from ponv_module import build_ponv_module
from anticoag_module import build_anticoag_module
from med_safety_module import build_med_safety_module
from pulmonary_module import build_pulmonary_module
from disposition_module import build_disposition_module
from renal_module import build_renal_module
from frailty_module import build_frailty_module 
from cancellation_module import build_cancellation_module 
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0


TAB_MAP = {
    "Proceed Risk": 1,
    "Disposition": 2,
    "Frailty": 3,
    "Cardiac": 4,
    "METS": 5,
    "Renal": 6,
    "Procedure / Technique": 7,
    "ERAS Meds": 8,
    "Med Safety": 9,
    "PONV": 10,
    "Pulmonary": 11,
    "Airway": 12,
    "Blood": 13,
    "Plan-Changing": 14
}

def extract_ponv_fields(text):

    text = text.lower()

    return {

        "sex": "female" if "female" in text else "male" if "male" in text else None,

        "smoking_status": "nonsmoker" if "nonsmoker" in text else None,

        "prior_ponv": True if "ponv" in text else None,

        "motion_sickness": True if "motion sickness" in text else None,

        "postop_opioids_expected": True if "opioid" in text else None,

        "qt_prolongation": True if "qt prolongation" in text else False,

        "parkinson_disease": True if "parkinson" in text else False,

        "osa": True if "osa" in text or "sleep apnea" in text else False,

        "high_sedation_risk": True if "opioid" in text or "benzodiazepine" in text else False,

        "elderly_delirium_risk": True if "dementia" in text or "delirium" in text else False,

        "glaucoma": True if "glaucoma" in text else False,

        "urinary_retention": True if "urinary retention" in text else False,

        "diabetes_poor_control": True if "a1c" in text or "hyperglycemia" in text else False,

        "bowel_obstruction": True if "obstruction" in text else False,

        "medications": [word.strip(",.") for word in text.split()]

    }

def extract_anticoag_fields(text):
    t = text.lower()

    return {
        "medications": [word.strip(",.;:()[]") for word in t.split()],
        "planned_neuraxial": any(x in t for x in ["spinal", "epidural", "neuraxial"]),
        "planned_deep_block": any(x in t for x in ["lumbar plexus", "paravertebral", "deep plexus", "deep peripheral block"]),
        "renal_function": "abnormal" if any(x in t for x in ["ckd", "renal failure", "esrd", "egfr", "creatinine"]) else "not documented",
        "platelet_count": "documented" if any(x in t for x in ["platelet", "plt"]) else "not documented",
        "inr": "documented" if "inr" in t else "not documented",
        "last_dose": "documented" if "last dose" in t or "held" in t else "not documented",
        "procedure_bleeding_risk": "high" if any(x in t for x in ["spine", "craniotomy", "major vascular", "liver resection"]) else "not documented",
        "thrombotic_risk": "high" if any(x in t for x in ["mechanical valve", "recent stroke", "recent pe", "recent dvt", "recent stent"]) else "not documented",
    }

def extract_med_safety_fields(text):

    text_lower = text.lower()

    return {
        "text": text_lower,  # 👈 ADD THIS
        "medications": [word.strip(",.;:()[]") for word in text_lower.split()]
        
    }
def extract_pulmonary_fields(text):
    return {
        "text": text.lower()
    }

def extract_renal_fields(text):
    return {
        "text": text.lower()
    }
def extract_frailty_fields(text):
    return {"text": text.lower()}

load_dotenv("/Users/Marco/.env", override=True)
api_key = os.getenv("OPENAI_API_KEY")

try:
    from openai import OpenAI
except Exception:
    OpenAI = None
# =========================================================
# PREOP AI MVP v1.2
# Data Validity Brain + Clinical Risk Brain + Dashboard + Note
# =========================================================

APP_TITLE = "Preop AI Clinical Intelligence"
APP_SUBTITLE = "Procedure-aware pre-anesthesia risk extraction, safety gating, and clinician decision support"

MODEL_NAME = "gpt-4.1-mini"  # Change if your account uses a different OpenAI model.

MASTER_SYSTEM_PROMPT = """
You are Preop AI: a preoperative anesthesia intelligence engine.

MISSION:
Analyze provided EMR/patient data and produce anesthesia-relevant preoperative risk intelligence.

ABSOLUTE RULES:
1. Use ONLY the patient data provided by the user.
2. Do NOT assume, infer, or invent missing information.
3. If data is absent, say "not documented".
4. Do NOT provide surgical clearance, medical clearance, or final proceed/cancel decisions.
5. Focus only on anesthesia-relevant risk, missing data, and plan-changing concerns.
6. Every finding, score, concern, or recommendation must be traceable to provided patient data.
7. Do not treat "not documented" as normal.
8. Output valid JSON only. No markdown. No commentary outside JSON.

CORE OBJECTIVE:
Separate two questions:
A. DATA VALIDITY BRAIN: Can we trust the chart enough to risk-stratify?
B. CLINICAL RISK BRAIN: If yes, what are the anesthesia-relevant risks?

DATA VALIDITY BRAIN:
Assess whether provided data are complete, current, internally consistent, and usable.
Flag:
- Missing critical information
- Outdated labs, imaging, or tests when dates are provided
- Conflicting information
- Unclear medication status
- Unclear anticoagulant/antiplatelet status
- Missing prior anesthesia history
- Missing airway data
- Missing cardiopulmonary status
- Missing functional capacity
- Missing surgical/procedure details
- Missing implantable cardiac device details when applicable
- Missing pregnancy status when clinically applicable and provided context supports relevance

CLINICAL RISK BRAIN:
Extract and prioritize anesthesia-relevant information only.
Evaluate domains:
- Cardiac
- Pulmonary
- Airway
- Renal
- Endocrine/metabolic
- Neurologic
- Hematologic/bleeding/anticoagulation
- Hepatic/GI/aspiration
- Prior anesthesia history
- Surgical/procedural impact
- Medications with anesthesia implications
- Labs/imaging/diagnostics relevant to anesthesia

CARDIAC FUNCTION / NYHA MODULE:

Assess NYHA functional class using ONLY documented symptoms and functional limitation.

Output:
- nyha_class: I | II | III | IV | not documented
- nyha_rationale

Do NOT infer NYHA class if symptoms or exertional tolerance are not documented.
If functional capacity is documented, use it cautiously and explain limitation.

RCRI MODULE:

Calculate Revised Cardiac Risk Index using ONLY documented data.

Components:
- high-risk surgery
- history of ischemic heart disease
- history of heart failure
- history of cerebrovascular disease
- insulin-dependent diabetes
- creatinine > 2.0 mg/dL

Output:
- rcri_score
- estimated_risk
- components_present
- missing_components
- interpretation

Do NOT assume missing components.

METS / FUNCTIONAL CAPACITY MODULE:

Assess functional capacity using ONLY documented patient data.

Classify:
- excellent: >10 METs
- good: 7–10 METs
- moderate: 4–6 METs
- poor: <4 METs
- unknown: not documented

Use common functional markers when documented:
- can climb 1–2 flights of stairs
- can walk uphill
- can perform moderate housework
- can perform strenuous sports/exercise
- cannot climb one flight of stairs
- dyspnea with minimal exertion

Output:
- mets_category
- estimated_mets_range
- documented_functional_evidence
- limitations
- anesthesia_relevance

STRICT RULES:
- Do NOT invent METs.
- Do NOT convert vague statements into exact METs.
- If functional capacity is not documented, output unknown.
- If poor functional capacity is documented, flag as anesthesia-relevant.

DOMAIN SCORING:
Score each domain 0-4 using only documented information:
0 = no documented risk
1 = mild risk
2 = moderate risk
3 = major risk, likely anesthesia-relevant
4 = critical or plan-altering risk

GLOBAL COMPLEXITY SCORE:
Use this method:
- Sum the top 5 domain scores.
- Add modifiers, max 4 total:
  +1 active instability documented
  +1 recent deterioration documented
  +1 critical missing data
  +1 interacting moderate risks
- Cap global score at 16.

ACTION PRIORITY TIER:
Assign one:
- Tier 1: Low complexity / routine review likely adequate
- Tier 2: Moderate complexity / focused anesthesia review
- Tier 3: High complexity / early anesthesiologist review recommended
- Tier 4: Very high complexity / plan-altering issue or critical missing data

IMPORTANT:
The tier is not clearance. It is only workflow priority.

PROCEDURE-DRIVEN ANESTHESIA INTELLIGENCE LAYER:

For every case:

STEP 1 — IDENTIFY:
- Surgical specialty
- Exact procedure (if documented)
- If not documented → state "procedure not documented"

STEP 2 — PROCEDURE RISK STRATIFICATION:
Classify:
- low risk
- intermediate risk
- high risk

Based ONLY on procedure type (if documented).

STEP 3 — ANESTHESIA TECHNIQUE CONSIDERATIONS:

Generate CONDITIONAL considerations (NOT a final plan):

1. GENERAL ANESTHESIA
- When it may be appropriate
- When it may be preferred

2. REGIONAL / NEURAXIAL
- When it may be appropriate
- Procedure-specific options

3. MAC / SEDATION
- When feasible
- When unsafe

4. AIRWAY STRATEGY
- Natural airway vs LMA vs ETT
- Based on:
  - procedure type
  - positioning
  - aspiration risk
  - duration
  - surgical access

STRICT:
- Do NOT choose one technique
- Present as conditional options only

STEP 4 — PROCEDURE-SPECIFIC RISKS:
Identify:
- bleeding risk
- positioning risk
- airway interference
- hemodynamic impact
- pulmonary impact
- neurologic considerations

STEP 5 — REGIONAL ANESTHESIA MODULE:
If applicable:

- List procedure-specific blocks
- Indications
- Contraindications

MUST CHECK:
- anticoagulation status
- infection
- neurologic deficits
- ability to assess postop

If missing → state:
"regional anesthesia eligibility cannot be confirmed"

PROCEDURE-SPECIFIC REGIONAL MATCHING:

For abdominal surgery:
- Laparoscopic/robotic colectomy: consider TAP block or QL block for abdominal wall analgesia if not contraindicated.
- Open colectomy/open abdominal surgery: consider thoracic epidural, TAP block, QL block, or rectus sheath block depending incision and anticoagulation status.
- Hernia repair: consider TAP, ilioinguinal/iliohypogastric, rectus sheath, or local infiltration depending location.
- Cesarean/hysterectomy/open pelvic surgery: consider TAP or QL if neuraxial opioid is not used or if additional analgesia is needed.

For every regional recommendation:
- Match block to procedure and incision.
- Do not give generic regional options.
- If procedure is robotic/laparoscopic abdominal surgery, TAP/QL must be considered unless contraindicated or insufficient data.
- If anticoagulation status is unknown, output:
"TAP/QL may be procedure-relevant, but regional safety cannot be confirmed because anticoagulation status is not documented."

ASRA ANTICOAGULATION SAFETY GATE:

For any neuraxial, deep plexus, or deep peripheral block:

Identify:
- anticoagulant or antiplatelet medications
- last dose timing
- renal function if relevant
- platelet/coagulation status if available

Then evaluate approximate ASRA-based timing considerations:

Examples (DO NOT assume safety, use as reference only):

- Apixaban / Rivaroxaban:
  → typical hold ~72 hours for neuraxial (longer if renal dysfunction)

- Dabigatran:
  → 72–120 hours depending on renal function

- Enoxaparin (LMWH):
  → prophylactic dose: ~12 hours
  → therapeutic dose: ~24 hours

- Unfractionated heparin:
  → IV infusion: ~4–6 hours
  → SQ prophylactic: ~4–6 hours

- Clopidogrel (Plavix):
  → ~5–7 days

- Aspirin:
  → generally acceptable for neuraxial alone (context-dependent)

STRICT RULES:
- These are reference ranges ONLY, not decisions
- Adjust interpretation based on renal function and dose
- If timing, dose, or renal function is unknown → classify as "insufficient_data"
- If outside safe window → classify as "blocked"
- Do NOT assume last dose timing

OUTPUT:
- safety_classification: eligible | caution | blocked | insufficient_data
- reason
- relevant timing consideration (if applicable)
- missing data that limits decision

Example:
"Apixaban in use; last dose not documented → neuraxial safety cannot be confirmed. Typical hold ~72h."

ADDITIONAL SPECIALTY MODULES:

GI / ENDOSCOPY:
For EGD, colonoscopy, ERCP, EUS, PEG, advanced endoscopy:
- evaluate aspiration risk, GI bleed, obstruction/full stomach, anticoagulation, biopsy/polypectomy bleeding risk
- evaluate sedation vs GA
- evaluate airway strategy: natural airway vs LMA vs ETT
- for ERCP/EUS, consider prone or semi-prone positioning and limited airway access
- flag OSA/COPD/home oxygen as sedation risk modifiers

EP / CARDIAC ELECTROPHYSIOLOGY:
For ablation, cardioversion, pacemaker/ICD procedures, lead extraction:
- evaluate arrhythmia type, EF/HF status, anticoagulation, device status, magnet/reprogramming needs
- evaluate vascular access bleeding risk
- evaluate MAC vs GA depending procedure duration, immobility, arrhythmia instability, and institutional practice
- flag lead extraction as higher risk than routine device work

INTERVENTIONAL RADIOLOGY:
For biopsy, drain, embolization, TIPS, nephrostomy, tumor ablation, central access:
- evaluate remote-site anesthesia risk, positioning, airway access after positioning, bleeding risk, anticoagulation, sepsis, renal/contrast risk
- evaluate MAC/local vs GA
- flag prone or difficult-access cases as airway-risk modifiers

NEURO-INTERVENTIONAL RADIOLOGY:
For thrombectomy, aneurysm coiling, AVM embolization, carotid/intracranial stenting:
- evaluate neurologic baseline, emergent status, aspiration risk, BP goals, anticoagulation/antiplatelet status, immobility, and postop neuro-monitoring needs
- evaluate MAC vs GA conditionally
- do not make final stroke/anesthesia pathway decisions

STEP 6 — ERAS + MEDICATION STRATEGY:

For this procedure, generate:

- preoperative medications
- intraoperative medications
- postoperative medications

Include:
- dosing ranges (not prescriptions)
- opioid-sparing approach
- PONV prophylaxis

For every medication recommendation, include:
- medication name
- typical adult dose range when applicable
- timing
- status: eligible | caution | blocked | insufficient_data
- reason for status

STEP 7 — MEDICATION SAFETY ENGINE:

MEDICATION DOSE + BLOCKER ENGINE:

PONV RISK + MANAGEMENT MODULE:

Calculate adult simplified Apfel PONV risk score using ONLY documented data.

Apfel risk factors:
1. Female sex
2. Non-smoker
3. History of PONV and/or motion sickness
4. Expected postoperative opioid use

Score:
0 = low risk, approximately 10%
1 = mild risk, approximately 20%
2 = moderate risk, approximately 40%
3 = high risk, approximately 60%
4 = very high risk, approximately 80%

If a factor is not documented, do NOT assume it. Mark it as "not documented" and list it under missing_data.

Also identify procedure/anesthetic PONV modifiers when documented:
- laparoscopic/robotic surgery
- gynecologic surgery
- volatile anesthetic exposure
- nitrous oxide exposure
- opioid-heavy plan
- prior severe PONV
- younger age
- pregnancy/non-obstetric surgery if relevant

Management recommendations must be risk-based and medication-level.

Baseline risk reduction options:
- consider propofol-based TIVA when appropriate
- minimize volatile anesthetic and nitrous oxide when appropriate
- opioid-sparing analgesia
- adequate hydration when appropriate

Antiemetic options with typical adult doses:
- Dexamethasone: 4–8 mg IV after induction; caution with uncontrolled diabetes or infection concern.
- Ondansetron: 4 mg IV near end of case; caution with QT prolongation.
- Droperidol: 0.625–1.25 mg IV near end of case; caution with QT prolongation or institutional restrictions.
- Haloperidol: 0.5–1 mg IV; caution with QT prolongation.
- Scopolamine patch: apply preop; caution/block with narrow-angle glaucoma, urinary retention, elderly/delirium risk.
- Aprepitant: 40 mg PO preop for high-risk patients; check formulary/institutional protocol.

Risk-based prophylaxis:
- Low risk: consider no prophylaxis or single agent depending context.
- Moderate risk: consider 2 antiemetic interventions from different classes.
- High/very high risk: consider 3 or more interventions from different classes plus baseline risk reduction.

Rescue rule:
If PONV occurs despite prophylaxis, recommend rescue from a DIFFERENT medication class than already used when documented.

STRICT RULES:
- Do not recommend antiemetics as active orders.
- Use "consider" and "requires clinician confirmation."
- If QT status is not documented, flag QT-sensitive medications as caution or insufficient_data.
- If diabetes is documented, dexamethasone requires glucose-risk caution.

For every ERAS medication recommendation, output medication-level items only.

Do NOT write vague phrases such as:
- "multimodal analgesia"
- "PONV prophylaxis"
- "opioid-sparing strategy"

Instead convert them into structured medication options.

Each medication item MUST include:
- medication
- typical_adult_dose_range
- timing
- purpose
- status: eligible | caution | blocked | insufficient_data
- blocker_or_caution_reason
- missing_data_if_any

POSTOPERATIVE DISPOSITION MODULE:

Based ONLY on documented patient data and procedure type, generate conditional postoperative monitoring considerations.

Evaluate:
- cardiopulmonary risk
- OSA/OHS or respiratory risk
- home oxygen or CPAP/BiPAP use
- difficult airway or airway edema risk
- hemodynamic instability risk
- HFrEF, CAD, pulmonary hypertension, arrhythmia
- renal/metabolic abnormalities
- anemia or bleeding risk
- anticoagulation concerns
- surgical magnitude and expected pain/opioid needs
- procedure positioning or robotic/laparoscopic physiologic stress

Output conditional disposition categories:
- routine PACU
- extended PACU monitoring
- telemetry consideration
- step-down consideration
- ICU-level care consideration

STRICT RULES:
- Do NOT assign a bed.
- Do NOT create admission orders.
- Do NOT say the patient “requires ICU.”
- Use conditional language: “consider,” “may require,” “higher risk for.”
- If data is insufficient, say what is missing.
- Every recommendation must include rationale tied to documented data.

For each recommendation include:
- recommended_level
- rationale
- risk_factors
- monitoring_needs
- uncertainty_or_missing_data

PLAN-CHANGING EXPLAINER MODULE:

For every item listed in "could_change_anesthetic_plan", explain why it matters.

Each item must include:
- finding
- affected_domain: airway | hemodynamics | monitoring | regional_eligibility | medication_choice | postop_disposition | blood_management | surgical_coordination
- why_it_matters
- possible_anesthesia_implication
- missing_data_if_any

STRICT RULES:
- Use only documented patient data.
- Do not create a final anesthetic plan.
- Do not overstate certainty.
- Use conditional language.

AIRWAY RISK MODULE:

Based ONLY on documented patient data, assess airway-related perioperative risk.

Evaluate:
- documented airway exam: Mallampati, mouth opening, thyromental distance, neck mobility, dentition
- prior difficult mask ventilation or difficult intubation
- OSA/OHS
- obesity or BMI if documented
- GERD/aspiration risk
- cervical spine disease or limited mobility
- facial/neck mass, airway tumor, ENT pathology
- pulmonary disease requiring careful ventilation
- procedure position and surgical access
- robotic/laparoscopic cases with Trendelenburg or limited access after docking

Output:
- difficult_mask_risk: low | moderate | high | unknown
- difficult_intubation_risk: low | moderate | high | unknown
- aspiration_risk: low | moderate | high | unknown
- airway_access_risk: low | moderate | high | unknown
- key_risk_factors
- missing_airway_data
- technique_implications

STRICT RULES:
- Do NOT declare airway safe if key data are missing.
- If airway exam is missing, classify difficult airway risk as "unknown."
- Use conditional language only.
- Do NOT create a final airway plan.

BLOOD MANAGEMENT MODULE:

Based ONLY on documented data and procedure type, assess bleeding and transfusion-related considerations.

Evaluate:
- hemoglobin/hematocrit and trends (if dates provided)
- anticoagulation/antiplatelet use and timing (if documented)
- coagulopathy, liver disease, thrombocytopenia
- renal disease impacting bleeding risk
- procedure bleeding risk (low / intermediate / high based on type if documented)
- expected surgical magnitude (open vs laparoscopic/robotic)
- history of bleeding or transfusion (if documented)

Output:
- bleeding_risk_level: low | moderate | high | unknown
- transfusion_risk: low | moderate | high | unknown
- anemia_flag: none | mild | moderate | severe | unknown
- anticoagulation_impact: summary of relevance to bleeding/regional eligibility
- recommendations (conditional, NOT orders)
- monitoring_needs
- missing_data

Recommendations may include (conditional language only):
- type and screen vs type and cross consideration
- availability of blood products
- cell saver consideration (if appropriate to procedure)
- TXA consideration (if appropriate and not contraindicated)
- correction of anemia or coagulopathy prior to surgery

STRICT RULES:
- Do NOT order blood.
- Do NOT recommend transfusion thresholds as directives.
- Do NOT assume anticoagulation timing if not documented.
- If data is missing, explicitly state uncertainty.

COMMON ERAS MEDICATION OPTIONS TO CONSIDER WHEN PROCEDURE-APPROPRIATE:

Analgesia:
- Acetaminophen: 650–1000 mg PO/IV preop or q6h postop; caution/limit in hepatic disease.
- Celecoxib: 200–400 mg PO preop; block/caution with NSAID allergy, renal dysfunction, high bleeding risk, anticoagulation concern, CABG-related surgery.
- Ketorolac: 15–30 mg IV intraop/postop; block/caution with renal dysfunction, bleeding risk, anticoagulation, elderly/frail patients.
- Gabapentin: 100–300 mg PO preop; caution/block with OSA/OHS, respiratory risk, renal dysfunction, elderly/fall/delirium risk.
- Ketamine: low-dose bolus/infusion may be considered for opioid-sparing analgesia; caution with severe CAD, uncontrolled HTN, psychosis.
- Lidocaine infusion: 1–1.5 mg/kg bolus then 1–2 mg/kg/hr; caution/block with conduction disease, severe hepatic disease, local anesthetic toxicity risk.

PONV:
- Dexamethasone: 4–8 mg IV after induction; caution with uncontrolled diabetes or infection concern.
- Ondansetron: 4 mg IV near end of case; caution with QT prolongation.
- Scopolamine patch: apply preop; caution/block with narrow-angle glaucoma, urinary retention, elderly/delirium risk.

Blood conservation:
- Tranexamic acid: 1 g IV or weight-based institutional dosing; consider for ortho/high blood loss cases; caution/block with active thrombosis, recent thromboembolism, seizure risk, renal dysfunction.

Respiratory/OSA risk:
- Avoid opioid-heavy plans.
- Flag sedating adjuncts when OSA/OHS, COPD on home oxygen, or respiratory depression risk is documented.

STRICT SAFETY RULES:
- If allergy status is not documented, classify relevant meds as insufficient_data or caution.
- If renal function is abnormal or missing, NSAIDs, gabapentinoids, TXA, and renally cleared meds require caution or block.
- If hepatic disease is documented or liver status is missing, acetaminophen requires caution.
- If anticoagulation status/timing is unknown, NSAIDs and regional adjunct recommendations require caution or block.
- Do NOT recommend a medication as eligible unless required safety data are documented.
- Do NOT generate active orders.
- Output is "Suggested only — clinician must verify local protocol, dose, timing, and contraindications."

STEP 8 — UNSAFE RECOMMENDATION BLOCKER:

If:
- contraindication present
- allergy present
- safety data missing

Then:
- DO NOT recommend
- Output: "blocked" or "cannot confirm safety"

STEP 9 — PREOP TESTING / OPTIMIZATION GATE:

Recommend additional evaluation ONLY if it could change anesthesia management.

STRICT RULES:
- Do NOT recommend routine or blanket testing
- Do NOT suggest tests without a clear anesthesia-related purpose
- Tie every recommendation to documented patient data

For each suggested test or optimization, include:
- test or intervention
- reason
- what decision it could change
- urgency: routine | before day of surgery | urgent review

Examples:
- Echocardiogram → if cardiac function unclear and impacts induction or fluid strategy
- Labs → if abnormal values could change management
- Pulmonary optimization → if COPD/OSA impacts ventilation or postop risk

If no testing is needed:
Output: "no additional testing recommended based on available data"

ANESTHESIA SNAPSHOT MODULE:

Create a concise 1–2 sentence anesthesia-facing summary.

Include:
- patient/procedure
- highest anesthesia-relevant risks
- major plan-changing blockers
- highest-yield next steps

STRICT:
- Do not provide clearance.
- Do not create a final anesthetic plan.
- Use only documented data.
- If key data are missing, explicitly mention them as planning blockers.

OUTPUT JSON SCHEMA:
{
  "data_validity": {
    "chart_trust_level": "high | moderate | low",
    "can_risk_stratify": true,
    "critical_missing_information": [],
    "data_conflicts": [],
    "outdated_or_unclear_data": [],
    "validity_summary": ""
  },
  "dashboard": {
    "top_10_second_view": [],
    "red_flags": [],
    "yellow_flags": [],
    "green_flags": [],
    "could_change_anesthetic_plan": [],
    "needs_human_review": true
  },
  "risk_scores": {
    "cardiac": {"score": 0, "rationale": ""},
    "pulmonary": {"score": 0, "rationale": ""},
    "airway": {"score": 0, "rationale": ""},
    "renal": {"score": 0, "rationale": ""},
    "endocrine_metabolic": {"score": 0, "rationale": ""},
    "neurologic": {"score": 0, "rationale": ""},
    "hematologic_bleeding_anticoagulation": {"score": 0, "rationale": ""},
    "hepatic_gi_aspiration": {"score": 0, "rationale": ""},
    "prior_anesthesia_history": {"score": 0, "rationale": ""},
    "surgical_procedural_impact": {"score": 0, "rationale": ""},
    "global_complexity_score": 0,
    "modifiers_applied": [],
    "action_priority_tier": ""

 "cardiac_function_module": {
    "nyha_class": "",
    "nyha_rationale": ""
 },
 "cardiac_risk_index": {
    "rcri_score": 0,
    "estimated_risk": "",
    "components_present": [],
    "missing_components": [],
    "interpretation": ""
 },
  
 "functional_capacity_module": {
    "mets_category": "",
    "estimated_mets_range": "",
    "documented_functional_evidence": [],
    "limitations": [],
    "anesthesia_relevance": ""
},
  "clinical_extraction": {
    "key_concerns_prioritized": [],
    "relevant_medical_history": [],
    "prior_anesthesia_history": "",
    "airway_assessment": "",
    "medications_anesthesia_implications": [],
    "labs_relevant_abnormal_or_missing": [],
    "imaging_diagnostics_relevant": [],
    "system_based_risks": {
      "cardiac": [],
      "pulmonary": [],
      "neurologic": [],
      "renal": [],
      "hematologic_oncology": [],
      "gi_hepatic_aspiration": [],
      "endocrine_metabolic": []
    }
  },
  "draft_preop_note": {
    "key_concerns": [],
    "relevant_history": "",
    "prior_anesthesia": "",
    "airway": "",
    "medications": "",
    "labs_diagnostics": "",
    "missing_information": [],
    "assessment": ""
  },

  "postoperative_disposition": {
    "recommended_level": "",
    "rationale": [],
    "risk_factors": [],
    "monitoring_needs": [],
    "uncertainty_or_missing_data": []
{
  "ponv": {
    "risk_level": "high",
    "risk_factors_present": [
      "female sex",
      "history of PONV",
      "postoperative opioids expected"
    ],
    "missing_data": [
      "smoking status not documented",
      "motion sickness history not documented"
    ],
    "prophylaxis_suggestions": [
      "Consider multimodal prophylaxis using agents from different classes",
      "Consider minimizing volatile anesthetic and postoperative opioids when clinically appropriate",
      "Consider regional/neuraxial/local analgesic strategies if applicable"
    ],
    "potential_agent_classes": [
      "5-HT3 antagonist",
      "corticosteroid",
      "dopamine antagonist",
      "anticholinergic",
      "NK1 antagonist"
    ],
    "rescue_options_if_ponv_occurs": [
      "If ondansetron was already used prophylactically, consider rescue from a different class such as droperidol/haloperidol, promethazine/prochlorperazine, metoclopramide, scopolamine, or NK1 antagonist depending on patient factors and local formulary",
      "If no 5-HT3 antagonist was given, ondansetron may be considered as rescue",
      "Avoid repeating the same class too soon unless guideline timing criteria are met"
    ],
    "cautions": [
      "Check QT prolongation risk before dopamine antagonists or 5-HT3 agents",
      "Avoid sedating rescue choices when respiratory depression risk is high",
      "Use caution with anticholinergics in glaucoma, urinary retention, or elderly delirium risk"
    ]
  }

  "procedure_module": {
    "specialty": "",
    "procedure": "",
    "procedure_risk": "",
    "procedure_specific_risks": []
  },

  "specialty_module": {
    "specialty_considerations": [],
    "positioning_access": [],
    "environment_risks": [],
    "red_flags": []
}
  "airway_risk_module": {
    "difficult_mask_risk": "",
    "difficult_intubation_risk": "",
    "aspiration_risk": "",
    "airway_access_risk": "",
    "key_risk_factors": [],
    "missing_airway_data": [],
    "technique_implications": []
}
  "anesthesia_technique": {
    "general_anesthesia": [],
    "regional_neuraxial": [],
    "mac_sedation": [],
    "airway_strategy": []
  },

  "blood_management_module": {
    "bleeding_risk_level": "",
    "transfusion_risk": "",
    "anemia_flag": "",
    "anticoagulation_impact": "",
    "recommendations": [],
    "monitoring_needs": [],
    "missing_data": []
}
  "procedure_matched_regional": {
    "procedure": "",
    "approach": "",
    "matched_blocks": [],
    "not_recommended_blocks": [],
    "safety_limitations": [],
    "safety_classification": "",
    "rationale": ""
},
  "plan_changing_explainer": [
  {
    "finding": "",
    "affected_domain": "",
    "why_it_matters": "",
    "possible_anesthesia_implication": "",
    "missing_data_if_any": []
  }
],
  },
"medication_module": {
  "preoperative": [
    {
      "medication": "",
      "typical_adult_dose_range": "",
      "timing": "",
      "purpose": "",
      "status": "eligible | caution | blocked | insufficient_data",
      "blocker_or_caution_reason": "",
      "missing_data_if_any": []
    }
  ],
  "intraoperative": [
    {
      "medication": "",
      "typical_adult_dose_range": "",
      "timing": "",
      "purpose": "",
      "status": "eligible | caution | blocked | insufficient_data",
      "blocker_or_caution_reason": "",
      "missing_data_if_any": []
    }
  ],
  "postoperative": [
    {
      "medication": "",
      "typical_adult_dose_range": "",
      "timing": "",
      "purpose": "",
      "status": "eligible | caution | blocked | insufficient_data",
      "blocker_or_caution_reason": "",
      "missing_data_if_any": []
    }
  ],
  "eligible": [],
  "caution": [],
  "blocked": [],
  "insufficient_data": []
}
  "preop_set_recommendation": {
    "summary": "",
    "items": [],
    "note": "Suggested only. Requires clinician confirmation."
},
  "preop_testing_optimization": {
    "recommendations": [],
    "not_recommended": [],
    "missing_data_that_limits_testing_decisions": []
},

"anesthesia_snapshot": {
  "one_liner": "",
  "priority_reason": "",
  "planning_blockers": [],
  "highest_yield_next_steps": []
},

"safety_footer": "This output is decision support only. It does not provide clearance or replace clinician judgment."
  },
 
"""
SAMPLE_CASE = """
72-year-old male scheduled for robotic colectomy.
PMH: CAD with PCI/stent in 2021, HFrEF EF 32% on echo from 14 months ago, COPD on home oxygen 2 L at night, CKD stage 3, type 2 diabetes on insulin, atrial fibrillation on apixaban.
Meds: metoprolol, lisinopril, furosemide, insulin glargine, apixaban. Last apixaban dose not documented.
Labs: Hgb 9.1, Cr 1.9, K 5.4, A1c 8.8. Lab date 2 weeks ago.
Airway: Mallampati not documented. Prior anesthesia history not documented.
Functional capacity: cannot climb one flight of stairs due to dyspnea.
Imaging: CXR with hyperinflation. ECG: atrial fibrillation.
"""


def empty_result(error_message: str = "") -> Dict[str, Any]:
    return {
        "data_validity": {
            "chart_trust_level": "low",
            "can_risk_stratify": False,
            "critical_missing_information": ["Unable to generate structured output"],
            "data_conflicts": [],
            "outdated_or_unclear_data": [],
            "validity_summary": error_message or "Model output could not be parsed."
        },
        "dashboard": {
            "top_10_second_view": ["Output parsing failed"],
            "red_flags": [error_message or "Invalid model output"],
            "yellow_flags": [],
            "green_flags": [],
            "could_change_anesthetic_plan": [],
            "needs_human_review": True
        },
        "risk_scores": {},
        "clinical_extraction": {},
        "draft_preop_note": {},
        "safety_footer": "This output is decision support only. It does not provide clearance or replace clinician judgment."
    }


def call_openai(patient_text: str, api_key: str) -> Dict[str, Any]:
    if OpenAI is None:
        return empty_result("OpenAI package is not installed. Run: pip install openai")

    if not api_key:
        raise ValueError("API key not found. Check your .env file.")

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": MASTER_SYSTEM_PROMPT},
                {"role": "user", "content": patient_text}
            ]
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as exc:
        return empty_result(str(exc))


def score_color(score: int) -> str:
    if score >= 4:
        return "🔴"
    if score == 3:
        return "🟠"
    if score == 2:
        return "🟡"
    if score == 1:
        return "🟢"
    return "⚪"


def tier_color(tier: str) -> str:
    tier_lower = str(tier).lower()
    if "tier 4" in tier_lower:
        return "🔴"
    if "tier 3" in tier_lower:
        return "🟠"
    if "tier 2" in tier_lower:
        return "🟡"
    return "🟢"


def list_block(title: str, items: Any):
    st.subheader(title)
    if not items:
        st.write("None documented")
        return
    if isinstance(items, str):
        st.write(items)
        return
    for item in items:
        st.write(f"- {item}")


def render_dashboard(result: Dict[str, Any]):
    epic_header(result)

    # --- Case Complexity Badge ---
    tier = result.get("risk_scores", {}).get("action_priority_tier", "not documented")

    st.markdown(
        f"""
        <div style="padding:10px; border-radius:6px; background-color:#edf2f7; margin-bottom:10px;">
            <b>Case Complexity:</b> {tier}
        </div>
        """,
        unsafe_allow_html=True
    )
    validity = result.get("data_validity", {})
    dashboard = result.get("dashboard", {})
    scores = result.get("risk_scores", {})

    rcri = result.get("cardiac_risk_index", {})
    nyha = result.get("cardiac_function_module", {})

    chart_trust = validity.get("chart_trust_level", "not documented")
    can_risk = validity.get("can_risk_stratify", False)
    global_score = scores.get("global_complexity_score", "not documented")
    tier = scores.get("action_priority_tier", "not documented")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Chart Trust", str(chart_trust).upper())
    col2.metric("Risk Stratify?", "YES" if can_risk else "NO")
    col3.metric("Global Score", global_score)
    col4.metric("Priority Tier", f"{tier_color(tier)} {tier}")

    col5, col6 = st.columns(2)
    col5.metric("RCRI", rcri.get("rcri_score", "N/A"))
    col6.metric("NYHA", result.get("cardiac_function_module", {}).get("nyha_class", "N/A"))

    snapshot = result.get("anesthesia_snapshot", {})

    st.info(snapshot.get("one_liner", "Anesthesia snapshot not documented."))

    if snapshot.get("priority_reason"):
       st.write(f"**Priority reason:** {snapshot.get('priority_reason')}")

    clinical_card("Red Flags", dashboard.get("red_flags", []), "red")
    clinical_card("Planning Blockers", snapshot.get("planning_blockers", []), "red")
    clinical_card("Highest-Yield Next Steps", snapshot.get("highest_yield_next_steps", []), "yellow")
    clinical_card("10-Second View", dashboard.get("top_10_second_view", []), "green")

    st.info(
        "Anesthesia Snapshot: Review chart validity, plan-changing risks, procedure-specific technique considerations, "
        "regional eligibility, ERAS medication safety, airway risk, PONV risk, and blood management."
    )

    st.divider()

    left, right = st.columns([1, 1])
    with left:
        list_block("10-Second View", dashboard.get("top_10_second_view", []))
        list_block("Could Change Anesthetic Plan", dashboard.get("could_change_anesthetic_plan", []))
    with right:
        list_block("Red Flags", dashboard.get("red_flags", []))
        list_block("Critical Missing Information", validity.get("critical_missing_information", []))

    st.divider()
    st.subheader("Domain Scores")
    domain_keys = [
        "cardiac", "pulmonary", "airway", "renal", "endocrine_metabolic",
        "neurologic", "hematologic_bleeding_anticoagulation",
        "hepatic_gi_aspiration", "prior_anesthesia_history", "surgical_procedural_impact"
    ]

    for key in domain_keys:
        domain = scores.get(key, {})
        if isinstance(domain, dict):
            score = domain.get("score", 0)
            rationale = domain.get("rationale", "")
            st.write(f"{score_color(int(score) if str(score).isdigit() else 0)} **{key.replace('_', ' ').title()}**: {score} — {rationale}")


def render_note(result: Dict[str, Any]):
    note = result.get("draft_preop_note", {})
    st.header("Draft Preop Note")
    list_block("Key Concerns", note.get("key_concerns", []))
    st.subheader("Relevant History")
    st.write(note.get("relevant_history", "not documented"))
    st.subheader("Prior Anesthesia")
    st.write(note.get("prior_anesthesia", "not documented"))
    st.subheader("Airway")
    st.write(note.get("airway", "not documented"))
    st.subheader("Medications")
    st.write(note.get("medications", "not documented"))
    st.subheader("Labs / Diagnostics")
    st.write(note.get("labs_diagnostics", "not documented"))
    list_block("Missing Information", note.get("missing_information", []))
    st.subheader("Assessment")
    st.write(note.get("assessment", "not documented"))

def render_cancellation(result):
    st.header("Case Proceed / Cancellation Risk")

    cancel = result.get("cancellation", {})

    if not cancel:
        st.info("Cancellation module not available.")
        return

    risk = cancel.get("risk_level", "not documented")

    if risk == "critical":
        st.error(f"Proceed Risk: {risk.upper()}")
    elif risk == "high":
        st.warning(f"Proceed Risk: {risk.upper()}")
    else:
        st.success(f"Proceed Risk: {risk.upper()}")

    st.subheader("Recommendation")
    st.write(cancel.get("proceed_recommendation", "not documented"))

    st.divider()

    list_block("Blockers", cancel.get("blockers", []))
    list_block("Warnings", cancel.get("warnings", []))
    list_block("Immediate Actions", cancel.get("immediate_actions", []))
    list_block("Missing Data", cancel.get("missing_data", []))

    st.divider()
    st.caption(cancel.get("safety_statement", ""))

def render_disposition(result):
    st.header("Postoperative Disposition / Monitoring")

    dispo = result.get("disposition", {})

    if not dispo:
        st.info("Disposition module not available.")
        return

    risk = dispo.get("disposition_risk", "not documented")

    if risk == "critical":
        st.error(f"Disposition Risk: {risk.upper()}")
    elif risk == "high":
        st.error(f"Disposition Risk: {risk.upper()}")
    elif risk == "moderate":
        st.warning(f"Disposition Risk: {risk.upper()}")
    else:
        st.success(f"Disposition Risk: {risk.upper()}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Suggested Level", dispo.get("recommended_level", "not documented"))
    col2.metric("Severity Score", dispo.get("severity_score", "N/A"))
    col3.metric("Confidence", dispo.get("confidence", "N/A"))

    st.subheader("Summary")
    st.write(dispo.get("clinician_summary", "not documented"))

    st.divider()

    list_block("Primary Drivers", dispo.get("drivers", []))
    list_block("Monitoring Needs", dispo.get("monitoring_needs", []))
    list_block("Plan-Changing Alerts", dispo.get("plan_changing_alerts", []))
    list_block("Missing Data", dispo.get("missing_data", []))
    list_block("Confidence Limitations", dispo.get("confidence_limitations", []))
    list_block("Do Not Assume", dispo.get("do_not_assume_guardrails", []))

    st.divider()
    st.caption(dispo.get("safety_statement", ""))

def render_frailty(result):
    st.header("Frailty / Functional Reserve")

    frailty = result.get("frailty", {})

    if not frailty:
        st.info("Frailty module not available.")
        return

    level = frailty.get("frailty_level", "not documented")

    if level == "high":
        st.error(f"Frailty Level: {level.upper()}")
    elif level == "moderate":
        st.warning(f"Frailty Level: {level.upper()}")
    else:
        st.success(f"Frailty Level: {level.upper()}")

    col1, col2 = st.columns(2)
    col1.metric("Frailty Score", frailty.get("score", "N/A"))
    col2.metric("Confidence", frailty.get("confidence", "N/A"))

    st.subheader("Summary")
    st.write(frailty.get("clinician_summary", "not documented"))

    st.divider()

    list_block("Drivers", frailty.get("drivers", []))
    list_block("Monitoring Needs", frailty.get("monitoring_needs", []))
    list_block("Plan-Changing Alerts", frailty.get("plan_changing_alerts", []))
    list_block("Missing Data", frailty.get("missing_data", []))

    st.divider()
    st.caption(frailty.get("safety_statement", ""))

def render_procedure_technique(result: Dict[str, Any]):
    st.header("Procedure / Technique")

    procedure = result.get("procedure_module", {})
    technique = result.get("anesthesia_technique", {})
    regional = result.get("procedure_matched_regional", {})
    specialty_context = result.get("specialty_module", {})

    col1, col2, col3 = st.columns(3)
    col1.metric("Specialty", procedure.get("specialty", "not documented"))
    col2.metric("Procedure", procedure.get("procedure", "not documented"))
    col3.metric("Procedure Risk", procedure.get("procedure_risk", "not documented"))

    st.divider()

    # Procedure-specific risks
    list_block("Procedure-Specific Risks", procedure.get("procedure_specific_risks", []))

    st.divider()

    # Specialty context 
    st.subheader("Specialty Context")
    list_block("Specialty-Specific Considerations", specialty_context.get("specialty_considerations", []))
    list_block("Positioning / Access Considerations", specialty_context.get("positioning_access", []))
    list_block("Anesthesia Environment Risks", specialty_context.get("environment_risks", []))
    list_block("Procedure-Specific Red Flags", specialty_context.get("red_flags", []))

    st.divider()

    # Technique
    list_block("General Anesthesia Considerations", technique.get("general_anesthesia", []))
    list_block("MAC / Sedation Considerations", technique.get("mac_sedation", []))
    list_block("Airway Strategy", technique.get("airway_strategy", []))

    st.divider()

    # Regional
    st.subheader("Procedure-Matched Regional")
    list_block("Matched Blocks", regional.get("matched_blocks", []))
    list_block("Not Recommended Blocks", regional.get("not_recommended_blocks", []))
    list_block("Safety Limitations", regional.get("safety_limitations", []))
    st.write(regional.get("rationale", "not documented"))

def med_block(title: str, items: Any):
    st.subheader(title)

    if not items:
        st.write("None documented")
        return

    for item in items:
        if isinstance(item, dict):
            st.write(
                f"- **{item.get('medication', 'not documented')}** "
                f"({item.get('typical_adult_dose_range', 'dose not documented')}) — "
                f"{item.get('timing', 'timing not documented')} — "
                f"**{item.get('status', 'status not documented')}**"
            )

            reason = item.get("blocker_or_caution_reason", "")
            if reason:
                st.caption(f"Reason: {reason}")

            missing = item.get("missing_data_if_any", [])
            if missing:
                st.caption(f"Missing data: {', '.join(missing)}")
        else:
            st.write(f"- {item}")


def render_eras_meds(result: Dict[str, Any]):
    st.header("ERAS Medications / Safety")

    meds = result.get("medication_module", {})
    preop_set = result.get("preop_set_recommendation", {})

    st.warning("Suggested only. Requires clinician confirmation. No orders are placed.")

    med_block("Preoperative Medications", meds.get("preoperative", []))
    med_block("Intraoperative Medications", meds.get("intraoperative", []))
    med_block("Postoperative Medications", meds.get("postoperative", []))

    st.divider()

    list_block("Eligible to Consider", meds.get("eligible", []))
    list_block("Caution / Needs Review", meds.get("caution", []))
    list_block("Blocked", meds.get("blocked", []))
    list_block("Insufficient Data", meds.get("insufficient_data", []))

    st.divider()

    st.subheader("Suggested Preop Set")
    st.write(preop_set.get("summary", "not documented"))
    list_block("Items", preop_set.get("items", []))
    st.caption(preop_set.get("note", "Suggested only. Requires clinician confirmation.")) 

def render_ponv(result: Dict[str, Any]):
    st.header("PONV Risk / Management")

    ponv = result.get("ponv", {})

    if not ponv:
        st.info("PONV module not available.")
        return

    if ponv.get("risk_level") in ["high", "very high"]:
        st.error(f"Risk Level: {ponv['risk_level'].upper()}")
    elif ponv.get("risk_level") == "moderate":
        st.warning(f"Risk Level: {ponv['risk_level'].upper()}")
    else:
        st.success(f"Risk Level: {ponv.get('risk_level', 'N/A').upper()}")

    col1, col2 = st.columns(2)
    col1.metric("PONV Score", ponv.get("risk_score_estimate", "not documented"))
    col2.metric("Risk Level", ponv.get("risk_level", "not documented"))

    st.divider()

    list_block("Risk Factors", ponv.get("risk_factors_present", []))
    list_block("Missing Data", ponv.get("missing_data", []))

    if ponv.get("plan_summary"):
        st.subheader("Suggested Plan")
        st.write(ponv["plan_summary"])

    st.divider()

    if ponv.get("drug_options"):
        st.subheader("Antiemetic Options")
        for drug in ponv["drug_options"]:
            st.write(
                f"- **{drug.get('drug', 'not documented')}** "
                f"({drug.get('class', 'class not documented')}) — "
                f"{drug.get('typical_adult_reference_dose', 'dose not documented')} — "
                f"{drug.get('typical_timing', 'timing not documented')} — "
                f"Status: **{drug.get('status', 'not documented')}**"
            )
            if drug.get("flags"):
                for flag in drug["flags"]:
                    st.caption(f"⚠️ {flag}")

    st.divider()

    list_block(
        "Contraindications / Cautions",
        [c.get("reason", str(c)) for c in ponv.get("contraindication_flags", [])]
    )

    list_block(
        "Medication Interaction Alerts",
        [m.get("message", str(m)) for m in ponv.get("medication_interaction_flags", [])]
    )

    list_block("Rescue Strategy", ponv.get("rescue_plan", {}).get("principles", []))


def render_med_safety(result):
    st.header("Medication Safety / Perioperative Risks")

    meds = result.get("med_safety", {})

    if not meds:
        st.info("No medication safety data.")
        return

    # Summary
    severity = meds.get("overall_severity", "not documented")

    if severity == "critical":
        st.error(f"Overall Severity: {severity.upper()}")
    elif severity == "high":
        st.error(f"Overall Severity: {severity.upper()}")
    elif severity == "moderate":
        st.warning(f"Overall Severity: {severity.upper()}")
    else:
        st.success(f"Overall Severity: {severity.upper()}")

    st.write(meds.get("clinician_summary", "not documented"))

    col1, col2 = st.columns(2)
    col1.metric("Medication Classes Detected", len(meds.get("items", [])))
    col2.metric("Confidence", meds.get("confidence", "N/A"))

    st.divider()

    # High-level alerts
    list_block("Critical Missing Data", meds.get("critical_missing", []))
    list_block("Plan-Changing Alerts", meds.get("plan_changing_alerts", []))
    list_block("Interaction Alerts", meds.get("interaction_alerts", []))

    st.divider()

    # Medication cards
    st.subheader("Medication-Level Analysis")

    items = meds.get("items", [])

    if not items:
        st.info("No high-impact medication classes detected.")
        return

    for item in items:
        sev = item.get("severity", "not documented")

        if sev == "critical":
            st.error(f"{item.get('medication_class', 'Unknown')} — CRITICAL")
        elif sev == "high":
            st.warning(f"{item.get('medication_class', 'Unknown')} — HIGH")
        elif sev == "moderate":
            st.info(f"{item.get('medication_class', 'Unknown')} — MODERATE")
        else:
            st.success(f"{item.get('medication_class', 'Unknown')} — LOW")

        st.write(f"**Why it matters:** {item.get('why_it_matters', 'not documented')}")

        if item.get("detected_terms"):
            st.caption(f"Detected: {', '.join(item.get('detected_terms', []))}")

        list_block("Missing Data", item.get("missing_data", []))
        list_block("Suggested Next Steps", item.get("suggested_next_steps", []))
        list_block("Plan-Changing Alerts", item.get("plan_changing_alerts", []))
        list_block("Interactions", item.get("interaction_alerts", []))
        list_block("Do Not Assume", item.get("do_not_assume", []))

        st.divider()

    st.caption(meds.get("safety_statement", ""))

def render_plan_changing(result: Dict[str, Any]):
    st.header("Plan-Changing Insights")

    items = result.get("plan_changing_explainer", [])

    if not items:
        st.write("None documented")
        return

    for item in items:
        st.divider()

        st.subheader(item.get("finding", "not documented"))

        st.write(f"**Domain:** {item.get('affected_domain', 'not documented')}")
        st.write(f"**Why it matters:** {item.get('why_it_matters', 'not documented')}")
        st.write(f"**Anesthesia implication:** {item.get('possible_anesthesia_implication', 'not documented')}")

        missing = item.get("missing_data_if_any", [])
        if missing:
            list_block("Missing Data", missing)

def render_airway(result: Dict[str, Any]):
    st.header("Airway Risk")

    airway = result.get("airway_risk_module", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mask Ventilation", airway.get("difficult_mask_risk", "not documented"))
    col2.metric("Intubation", airway.get("difficult_intubation_risk", "not documented"))
    col3.metric("Aspiration", airway.get("aspiration_risk", "not documented"))
    col4.metric("Access Risk", airway.get("airway_access_risk", "not documented"))

    st.divider()

    list_block("Key Risk Factors", airway.get("key_risk_factors", []))
    list_block("Missing Airway Data", airway.get("missing_airway_data", []))

    st.divider()

    list_block("Technique Implications", airway.get("technique_implications", []))           


def render_blood(result: Dict[str, Any]):
    st.header("Blood / Anticoagulation / Bleeding Risk")

    anticoag = result.get("anticoag", {})
    old_blood = result.get("blood_management_module", {})

    if not anticoag:
        st.info("Anticoagulation module not available.")
        return

    if anticoag.get("bleeding_risk_level") == "high":
        st.error("Bleeding / Neuraxial Risk: HIGH")
    elif anticoag.get("bleeding_risk_level") == "moderate":
        st.warning("Bleeding / Neuraxial Risk: MODERATE")
    else:
        st.success("Bleeding / Neuraxial Risk: LOW")

    col1, col2, col3 = st.columns(3)
    col1.metric("Anticoagulants", ", ".join(anticoag.get("anticoagulants", [])) or "None")
    col2.metric("Antiplatelets", ", ".join(anticoag.get("antiplatelets", [])) or "None")
    col3.metric("Neuraxial Safe?", "YES" if anticoag.get("neuraxial_block_safe") else "NO / NEEDS REVIEW")

    st.divider()

    if anticoag.get("plan_summary"):
        st.subheader("Plan Summary")
        st.write(anticoag["plan_summary"])

    list_block("Critical Missing Data", anticoag.get("critical_missing", []))
    list_block("Red Flags", anticoag.get("red_flags", []))
    list_block("Neuraxial / Deep Regional Flags", anticoag.get("neuraxial_flags", []))

    st.divider()

    list_block("Hold / Timing Guidance", anticoag.get("hold_guidance", []))
    list_block("Lab Considerations", anticoag.get("lab_considerations", []))
    list_block("Bridging Considerations", anticoag.get("bridging_considerations", []))
    list_block("Reversal Considerations", anticoag.get("reversal_considerations", []))
    list_block("Plan-Changing Items", anticoag.get("plan_changers", []))

    st.divider()
    st.caption(anticoag.get("safety_statement", ""))

    if old_blood:
        with st.expander("Original Blood Management Module"):
            st.json(old_blood)

def render_pulmonary(result):

    st.header("Pulmonary / Respiratory Risk")

    pulm = result.get("pulmonary", {})

    if not pulm:
        st.info("No pulmonary data.")
        return

    if pulm.get("severity") == "high":
        st.error("HIGH RISK")
    elif pulm.get("severity") == "moderate":
        st.warning("MODERATE RISK")
    else:
        st.success("LOW RISK")

    st.subheader("Summary")
    st.write(pulm.get("summary"))

    st.divider()

    list_block("Findings", pulm.get("findings", []))
    list_block("Alerts", pulm.get("alerts", []))
    list_block("Medication Interactions", pulm.get("interactions", []))
    list_block("Missing Data", pulm.get("missing", []))
    list_block("Plan", pulm.get("plan", []))
    list_block("Do Not Assume", pulm.get("guardrails", []))

def render_renal(result):
    st.header("Renal / Electrolyte Risk")

    renal = result.get("renal", {})

    if not renal:
        st.info("Renal module not available.")
        return

    sev = renal.get("severity", "not documented")

    if sev == "critical":
        st.error(f"Severity: {sev.upper()}")
    elif sev == "high":
        st.warning(f"Severity: {sev.upper()}")
    else:
        st.success(f"Severity: {sev.upper()}")

    col1, col2 = st.columns(2)
    col1.metric("Severity", sev.upper())
    col2.metric("Confidence", renal.get("confidence", "N/A"))

    st.subheader("Summary")
    st.write(renal.get("clinician_summary", "not documented"))

    st.divider()

    list_block("Drivers", renal.get("drivers", []))
    list_block("Monitoring Needs", renal.get("monitoring_needs", []))
    list_block("Plan-Changing Alerts", renal.get("plan_changing_alerts", []))
    list_block("Missing Data", renal.get("missing_data", []))

    st.divider()
    st.caption(renal.get("safety_statement", ""))    

def render_cardiac(result: Dict[str, Any]):
    st.header("Cardiac Risk / Function")

    nyha = result.get("cardiac_function_module", {})
    rcri = result.get("cardiac_risk_index", {})

    col1, col2 = st.columns(2)
    col1.metric("NYHA Class", nyha.get("nyha_class", "not documented"))
    col2.metric("RCRI Score", rcri.get("rcri_score", "not documented"))

    st.divider()

    st.subheader("NYHA Rationale")
    st.write(nyha.get("nyha_rationale", "not documented"))

    st.divider()

    st.subheader("RCRI Details")
    st.write(f"Estimated Risk: {rcri.get('estimated_risk', 'not documented')}")
    list_block("Components Present", rcri.get("components_present", []))
    list_block("Missing Components", rcri.get("missing_components", []))
    st.write(rcri.get("interpretation", "not documented"))

def render_functional_capacity(result: Dict[str, Any]):
    st.header("Functional Capacity / METs")

    mets = result.get("functional_capacity_module", {})

    col1, col2 = st.columns(2)
    col1.metric("METs Category", mets.get("mets_category", "not documented"))
    col2.metric("Estimated Range", mets.get("estimated_mets_range", "not documented"))

    st.divider()

    list_block("Documented Functional Evidence", mets.get("documented_functional_evidence", []))
    list_block("Limitations", mets.get("limitations", []))

    st.subheader("Anesthesia Relevance")
    st.write(mets.get("anesthesia_relevance", "not documented")) 

def render_smart_banner(result):
    alerts = []

    def add_alert(priority, color, title, message, explanation=""):
        if message:
            alerts.append({
                "priority": priority,
                "color": color,
                "title": title,
                "message": message,
                "explanation": explanation
            })

    cancel = result.get("cancellation", {})
    dispo = result.get("disposition", {})
    pulm = result.get("pulmonary", {})
    renal = result.get("renal", {})
    anticoag = result.get("anticoag", {})
    meds = result.get("med_safety", {})
    ponv = result.get("ponv", {})

    if cancel.get("risk_level") == "critical":
        add_alert(
            1, "red", "Proceed Risk",
            cancel.get("proceed_recommendation", ""),
            "Triggered because the proceed-risk module identified critical blockers or unsafe proceed conditions."
        )

    if renal.get("severity") == "critical":
        add_alert(
            1, "red", "Renal",
            renal.get("clinician_summary", ""),
            "Triggered because the renal module identified critical renal or electrolyte risk."
        )

    if anticoag.get("neuraxial_block_safe") is False:
        add_alert(
            2, "red", "Blood",
            "Neuraxial or deep regional technique requires review before proceeding.",
            "Triggered because anticoagulation or antiplatelet data may make neuraxial/deep regional anesthesia unsafe without further review."
        )

    if cancel.get("risk_level") == "high":
        add_alert(
            2, "red", "Proceed Risk",
            cancel.get("proceed_recommendation", ""),
            "Triggered because the proceed-risk module identified high-risk blockers or unresolved safety concerns."
        )

    if dispo.get("disposition_risk") in ["critical", "high"]:
        add_alert(
            3, "red", "Disposition",
            dispo.get("recommended_level", ""),
            "Triggered because the disposition module predicts need for higher-acuity postoperative monitoring."
        )

    if pulm.get("severity") == "high":
        add_alert(
            3, "red", "Pulmonary",
            pulm.get("summary", ""),
            "Triggered because the pulmonary module identified high respiratory risk such as OSA, COPD, home oxygen, pulmonary hypertension, or sedating medication interactions."
        )

    if meds.get("overall_severity") in ["critical", "high"]:
        add_alert(
            4, "orange", "Med Safety",
            meds.get("clinician_summary", ""),
            "Triggered because the medication safety module detected high-impact perioperative medication risks, missing hold plans, or interaction concerns."
        )

    if ponv.get("risk_level") in ["high", "very high"]:
        add_alert(
            5, "yellow", "PONV",
            ponv.get("plan_summary", ""),
            "Triggered because the PONV module identified high or very high PONV risk requiring multimodal prophylaxis and rescue planning."
        )

    # Deduplicate by title, keeping highest-priority version
    seen = {}
    for alert in alerts:
        if alert["title"] not in seen or alert["priority"] < seen[alert["title"]]["priority"]:
            seen[alert["title"]] = alert

    alerts = sorted(seen.values(), key=lambda x: x["priority"])[:3]

    if not alerts:
        st.success("No major plan-changing alerts detected from available data.")
        return

    st.markdown("### 🚨 Top Plan-Changing Alerts")
    st.caption("Top 3 plan-changing signals based on current chart data.")

    for alert in alerts:
        msg = alert.get("message", "")
        short_msg = msg[:140] + "..." if len(msg) > 140 else msg
        label = f"{alert['title']} — {short_msg}"

        col1, col2 = st.columns([6, 1])

        with col1:
            if alert["color"] == "red":
                st.error(label)
            elif alert["color"] == "orange":
                st.warning(label)
            else:
                st.info(label)

            with st.expander("Why this alert fired"):
                st.write(alert.get("explanation", "Triggered by module-level risk signals."))

        with col2:
            if st.button(f"See {alert['title']}", key=f"go_{alert['title']}"):
                if alert["title"] in TAB_MAP:
                    st.info(f"Open the **{alert['title']}** tab above for details.")

def apply_epic_style():
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f3f5f7;
        }

        div[data-testid="stMetric"] {
            background-color: white;
            border: 1px solid #d9dee5;
            padding: 14px;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }

        .clinical-card {
            background-color: white;
            border: 1px solid #d9dee5;
            border-left: 5px solid #2b6cb0;
            border-radius: 8px;
            padding: 14px 16px;
            margin: 10px 0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }

        .clinical-card-red {
            border-left-color: #c53030;
        }

        .clinical-card-yellow {
            border-left-color: #d69e2e;
        }

        .clinical-card-green {
            border-left-color: #2f855a;
        }

        .clinical-card h4 {
            margin-top: 0;
            margin-bottom: 8px;
            color: #1a202c;
        }

        .small-muted {
            color: #4a5568;
            font-size: 0.9rem;
        }

        .epic-banner {
            background-color: #123c69;
            color: white;
            padding: 14px 18px;
            border-radius: 8px;
            margin-bottom: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def clinical_card(title: str, content: Any, color: str = "blue"):
    color_class = {
        "red": "clinical-card-red",
        "yellow": "clinical-card-yellow",
        "green": "clinical-card-green",
        "blue": ""
    }.get(color, "")

    if isinstance(content, list):
        body = "".join([f"<li>{item}</li>" for item in content]) if content else "<li>None documented</li>"
        body = f"<ul>{body}</ul>"
    else:
        body = f"<p>{content or 'None documented'}</p>"

    st.markdown(
        f"""
        <div class="clinical-card {color_class}">
            <h4>{title}</h4>
            {body}
        </div>
        """,
        unsafe_allow_html=True
    )


def epic_header(result: Dict[str, Any]):
    scores = result.get("risk_scores", {})
    validity = result.get("data_validity", {})
    procedure = result.get("procedure_module", {})
    rcri = result.get("cardiac_risk_index", {})
    mets = result.get("functional_capacity_module", {})

    st.markdown(
        f"""
        <div class="epic-banner">
            <b>Pre-Anesthesia Review</b><br>
            Procedure: {procedure.get("procedure", "not documented")} |
            Priority: {scores.get("action_priority_tier", "not documented")} |
            Chart Trust: {validity.get("chart_trust_level", "not documented")} |
            RCRI: {rcri.get("rcri_score", "N/A")} |
            METs: {mets.get("mets_category", "N/A")}
        </div>
        """,
        unsafe_allow_html=True
    )

def build_epic_note_text(result: Dict[str, Any]) -> str:
    note = result.get("draft_preop_note", {})
    procedure = result.get("procedure_module", {})
    snapshot = result.get("anesthesia_snapshot", {})
    airway = result.get("airway_risk_module", {})
    blood = result.get("blood_management_module", {})
    ponv = result.get("ponv_module", {})
    disposition = result.get("postoperative_disposition", {})
    rcri = result.get("cardiac_risk_index", {})
    mets = result.get("functional_capacity_module", {})

    def join_items(items):
        if not items:
            return "not documented"
        if isinstance(items, list):
            return "\n".join([f"- {x}" for x in items])
        return str(items)

    return f"""
PRE-ANESTHESIA EVALUATION — DRAFT

Procedure:
{procedure.get("procedure", "not documented")}

Anesthesia Snapshot:
{snapshot.get("one_liner", "not documented")}

Key Concerns:
{join_items(note.get("key_concerns", []))}

Cardiac:
- RCRI: {rcri.get("rcri_score", "not documented")}
- Estimated risk: {rcri.get("estimated_risk", "not documented")}
- Functional capacity / METs: {mets.get("mets_category", "not documented")} ({mets.get("estimated_mets_range", "not documented")})

Pulmonary / Airway:
- Airway: {note.get("airway", "not documented")}
- Difficult mask risk: {airway.get("difficult_mask_risk", "not documented")}
- Difficult intubation risk: {airway.get("difficult_intubation_risk", "not documented")}
- Aspiration risk: {airway.get("aspiration_risk", "not documented")}

Medications / Anticoagulation:
{note.get("medications", "not documented")}

Labs / Diagnostics:
{note.get("labs_diagnostics", "not documented")}

Procedure / Regional Considerations:
{join_items(result.get("procedure_matched_regional", {}).get("matched_blocks", []))}
Safety limitations:
{join_items(result.get("procedure_matched_regional", {}).get("safety_limitations", []))}

PONV:
- Apfel score: {ponv.get("apfel_score", "not documented")}
- Risk level: {ponv.get("risk_level", "not documented")}

Blood / Bleeding:
- Bleeding risk: {blood.get("bleeding_risk_level", "not documented")}
- Transfusion risk: {blood.get("transfusion_risk", "not documented")}
- Anemia: {blood.get("anemia_flag", "not documented")}

Postoperative Disposition Considerations:
{disposition.get("recommended_level", "not documented")}
{join_items(disposition.get("rationale", []))}

Missing / Blocking Information:
{join_items(note.get("missing_information", []))}

Assessment:
{note.get("assessment", "not documented")}

Decision Support Notice:
This draft does not provide clearance, final anesthetic plan, or automatic orders. Requires clinician review.
""".strip()

def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    apply_epic_style()
    load_dotenv("/Users/Marco/.env", override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    
    

    st.title(APP_TITLE)
    
    st.caption(APP_SUBTITLE)
    st.warning(
    "Decision support only. This tool does not provide clearance, final anesthetic plans, or automatic orders."
    )

    with st.sidebar:
        st.header("Setup")
        st.caption("For local MVP testing only. Do not paste real PHI into non-HIPAA tools.")
        use_sample = st.button("Load Sample Case")

        st.divider()
        st.write("Clinical modules:")
        st.write("1. Data Validity")
        st.write("2. Risk Scoring")
        st.write("3. Procedure / Technique")
        st.write("4. ERAS Medications")
        st.write("5. PONV")
        st.write("6. Airway")
        st.write("7. Blood / Bleeding")
        st.write("8. Plan-Changing Insights")

    if "patient_text" not in st.session_state:
        st.session_state.patient_text = ""

    if use_sample:
        st.session_state.patient_text = SAMPLE_CASE

    patient_text = st.text_area(
        "Paste de-identified EMR / preop chart data here",
        value=st.session_state.get("patient_text", ""),
        height=300
    )


    run = st.button("Analyze Patient", type="primary") 

    if run:
        if not patient_text.strip():
            st.warning("Paste patient data first.")
            st.stop()

        if not api_key:
            st.error("API key not loaded. Check your .env file.")
            st.stop()

        with st.spinner("Analyzing chart..."):
            result = call_openai(patient_text, api_key)

            result["ponv"] = build_ponv_module(extract_ponv_fields(patient_text))
            result["anticoag"] = build_anticoag_module(extract_anticoag_fields(patient_text))
            result["med_safety"] = build_med_safety_module(extract_med_safety_fields(patient_text))
            result["pulmonary"] = build_pulmonary_module(extract_pulmonary_fields(patient_text))
            result["renal"] = build_renal_module(extract_renal_fields(patient_text))
            result["frailty"] = build_frailty_module(extract_frailty_fields(patient_text))

            # synthesis modules LAST
            result["disposition"] = build_disposition_module(result)
            result["cancellation"] = build_cancellation_module(result)

            st.session_state.result = result
    if "result" in st.session_state:
        result = st.session_state.result

        render_smart_banner(result) 

        tab_names = [
            "Dashboard",
            "Proceed Risk",
            "Disposition",
            "Frailty",
            "Cardiac",
            "Renal",
            "METS",
            "Procedure / Technique",
            "ERAS Meds",
            "Med Safety",
            "PONV",
            "Pulmonary",
            "Airway",
            "Blood",
            "Plan-Changing",
            "Draft Note",
            "Clinical Extraction",
            "JSON"
        ]

        tabs = st.tabs(tab_names)

        st.session_state.active_tab = min(st.session_state.active_tab, len(tab_names)-1)

        with tabs[0]:
            render_dashboard(result)

        with tabs[1]:
            render_cancellation(result)

        with tabs[2]:
            render_disposition(result)

        with tabs[3]:
            render_frailty(result)

        with tabs[4]:
            render_cardiac(result)

        with tabs[5]:     
            render_renal(result)

        with tabs[6]:
            render_functional_capacity(result)

        with tabs[7]:
            render_procedure_technique(result)

        with tabs[8]:
            render_eras_meds(result)

        with tabs[9]:
            render_med_safety(result)

        with tabs[10]:
            render_ponv(result)

        with tabs[11]:
            render_pulmonary(result)

        with tabs[12]:
            render_airway(result)

        with tabs[13]:
            render_blood(result)

        with tabs[14]:
            render_plan_changing(result)

        with tabs[15]:
            render_note(result)
            st.divider()
            st.subheader("Copyable Epic-Style Note")

            epic_note_text = build_epic_note_text(result)

            st.text_area(
                "Copy/paste draft note",
                value=epic_note_text,
                height=500
        )

            st.download_button(
                "Download Epic-Style Note",
                data=epic_note_text,
                file_name="preop_epic_style_note.txt",
                mime="text/plain"
        )

        with tabs[16]:
            st.header("Clinical Extraction")
            st.json(result.get("clinical_extraction", {}))

        with tabs[17]:
            st.header("Raw JSON")
            st.download_button(
                "Download JSON",
                data=json.dumps(result, indent=2),
                file_name=f"preop_ai_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            st.json(result)

    st.divider()
    st.caption(
        "Decision support only. No clearance decision. Do not use with identifiable PHI "  
        "unless deployed in a HIPAA-compliant environment with proper agreements and safeguards."
    )


if __name__ == "__main__":
    main()