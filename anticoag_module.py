from typing import Any, Dict, List


def _norm(value: Any) -> str:
    return "" if value is None else str(value).strip().lower()


def _med_list(data: Dict[str, Any]) -> List[str]:
    meds = data.get("medications", [])
    if isinstance(meds, str):
        meds = [meds]
    return [_norm(m) for m in meds]


def _has_med(meds: List[str], names: List[str]) -> List[str]:
    found = []
    for med in meds:
        for name in names:
            if name in med:
                found.append(name)
    return sorted(set(found))


def build_anticoag_module(data: Dict[str, Any]) -> Dict[str, Any]:
    meds = _med_list(data)

    renal_function = data.get("renal_function", "not documented")
    platelet_count = data.get("platelet_count", "not documented")
    inr = data.get("inr", "not documented")
    last_dose = data.get("last_dose", "not documented")
    planned_neuraxial = data.get("planned_neuraxial", False)
    planned_deep_block = data.get("planned_deep_block", False)
    procedure_bleeding_risk = data.get("procedure_bleeding_risk", "not documented")
    thrombotic_risk = data.get("thrombotic_risk", "not documented")

    anticoagulants = _has_med(
        meds,
        [
            "apixaban", "rivaroxaban", "edoxaban", "dabigatran",
            "warfarin", "heparin", "enoxaparin", "dalteparin",
            "fondaparinux"
        ]
    )

    antiplatelets = _has_med(
        meds,
        [
            "aspirin", "clopidogrel", "prasugrel", "ticagrelor",
            "dipyridamole", "cilostazol"
        ]
    )

    nsaids = _has_med(
        meds,
        ["ibuprofen", "naproxen", "ketorolac", "celecoxib", "meloxicam"]
    )

    agents = anticoagulants + antiplatelets + nsaids
    anticoag_present = bool(agents)

    missing = []
    red_flags = []
    neuraxial_flags = []
    hold_guidance = []
    reversal_considerations = []
    bridging_considerations = []
    lab_considerations = []
    plan_changers = []

    if anticoag_present:
        if last_dose == "not documented":
            missing.append("Last anticoagulant/antiplatelet dose timing not documented")
            red_flags.append("Cannot assess neuraxial/regional timing without last dose")

        if renal_function == "not documented":
            missing.append("Renal function not documented")
            red_flags.append("Renal function needed for DOAC clearance assessment")

        if platelet_count == "not documented":
            missing.append("Platelet count not documented")

    if "warfarin" in anticoagulants and inr == "not documented":
        missing.append("INR not documented for warfarin patient")
        red_flags.append("Warfarin present without documented INR")

    if planned_neuraxial or planned_deep_block:
        if anticoagulants:
            neuraxial_flags.append(
                "Neuraxial/deep regional technique should be treated as NOT safe until appropriate hold interval and coagulation status are confirmed."
            )
        if "clopidogrel" in antiplatelets or "prasugrel" in antiplatelets or "ticagrelor" in antiplatelets:
            neuraxial_flags.append(
                "P2Y12 inhibitor present; neuraxial/deep regional timing requires guideline-based hold confirmation."
            )

    # Drug-specific guidance, intentionally reference-style not automatic orders
    if "apixaban" in anticoagulants:
        hold_guidance.append(
            "Apixaban detected: confirm dose, renal function, last dose, and indication. Neuraxial/deep block generally requires guideline-based interruption; high-dose therapy commonly requires longer interruption than low-dose therapy."
        )
        lab_considerations.append(
            "If timing is unclear or shortened, consider whether calibrated anti-Xa/apixaban level is available per institutional practice."
        )

    if "rivaroxaban" in anticoagulants:
        hold_guidance.append(
            "Rivaroxaban detected: confirm dose, renal function, last dose, and indication. Neuraxial/deep block generally requires guideline-based interruption; high-dose therapy commonly requires longer interruption than low-dose therapy."
        )
        lab_considerations.append(
            "If timing is unclear or shortened, consider whether calibrated anti-Xa/rivaroxaban level is available per institutional practice."
        )

    if "edoxaban" in anticoagulants:
        hold_guidance.append(
            "Edoxaban detected: confirm dose, renal function, last dose, and indication before neuraxial/deep regional consideration."
        )

    if "dabigatran" in anticoagulants:
        hold_guidance.append(
            "Dabigatran detected: renal function is especially important because clearance is renal-dependent; confirm last dose and kidney function before neuraxial/deep regional consideration."
        )
        lab_considerations.append(
            "If timing is unclear, consider thrombin-time or dabigatran-calibrated testing if available per institutional practice."
        )

    if "warfarin" in anticoagulants:
        hold_guidance.append(
            "Warfarin detected: elective neuraxial/regional planning generally requires warfarin interruption and acceptable INR before placement/removal."
        )
        lab_considerations.append("INR required before neuraxial/deep regional decision-making.")

    if "enoxaparin" in anticoagulants or "dalteparin" in anticoagulants:
        hold_guidance.append(
            "LMWH detected: determine prophylactic vs therapeutic dosing and last dose timing before neuraxial/deep regional technique."
        )

    if "heparin" in anticoagulants:
        hold_guidance.append(
            "Heparin detected: determine IV vs SQ dosing, last dose timing, and coagulation status before neuraxial/deep regional technique."
        )
        lab_considerations.append("aPTT/anti-Xa may be relevant depending on heparin regimen.")

    if "fondaparinux" in anticoagulants:
        hold_guidance.append(
            "Fondaparinux detected: high caution for neuraxial/deep regional techniques; confirm institutional policy and specialist guidance."
        )

    if "aspirin" in antiplatelets:
        hold_guidance.append(
            "Aspirin detected: usually not a standalone neuraxial contraindication, but evaluate additive bleeding risk if combined with anticoagulants or other antiplatelets."
        )

    if "clopidogrel" in antiplatelets:
        hold_guidance.append(
            "Clopidogrel detected: confirm indication, stent history, last dose, and guideline-based hold interval before neuraxial/deep regional technique."
        )

    if "prasugrel" in antiplatelets:
        hold_guidance.append(
            "Prasugrel detected: high-impact antiplatelet; confirm indication, stent history, last dose, and guideline-based hold interval."
        )

    if "ticagrelor" in antiplatelets:
        hold_guidance.append(
            "Ticagrelor detected: confirm indication, stent history, last dose, and guideline-based hold interval."
        )

    if nsaids:
        hold_guidance.append(
            "NSAID detected: usually not a standalone neuraxial contraindication, but evaluate additive bleeding risk with anticoagulants/antiplatelets."
        )

    if anticoagulants and antiplatelets:
        red_flags.append("Combined anticoagulant + antiplatelet therapy detected")
        plan_changers.append("Combination therapy may change neuraxial/regional eligibility and surgical bleeding planning.")

    if "aspirin" in antiplatelets and ("clopidogrel" in antiplatelets or "prasugrel" in antiplatelets or "ticagrelor" in antiplatelets):
        red_flags.append("Dual antiplatelet therapy detected")
        plan_changers.append("Clarify coronary stent history and thrombotic risk before holding antiplatelet therapy.")

    if anticoagulants:
        reversal_considerations.append(
            "Urgent reversal considerations depend on agent, timing, renal function, bleeding severity, and local formulary; this module should not automatically recommend reversal."
        )

    if "dabigatran" in anticoagulants:
        reversal_considerations.append(
            "Dabigatran-specific reversal may be relevant in emergency bleeding/urgent surgery contexts; requires clinician/institutional protocol."
        )

    if "apixaban" in anticoagulants or "rivaroxaban" in anticoagulants or "edoxaban" in anticoagulants:
        reversal_considerations.append(
            "Factor Xa inhibitor reversal/supportive options may be relevant in emergency bleeding/urgent surgery contexts; requires clinician/institutional protocol."
        )

    if anticoagulants:
        bridging_considerations.append(
            "Bridging is not automatic. Consider only after evaluating indication, thrombotic risk, procedural bleeding risk, renal function, and local protocol."
        )

    bleeding_risk = "low"
    if anticoagulants or ("clopidogrel" in antiplatelets) or ("prasugrel" in antiplatelets) or ("ticagrelor" in antiplatelets):
        bleeding_risk = "high"
    elif antiplatelets or nsaids:
        bleeding_risk = "moderate"

    neuraxial_safe = True
    if anticoagulants or ("clopidogrel" in antiplatelets) or ("prasugrel" in antiplatelets) or ("ticagrelor" in antiplatelets):
        neuraxial_safe = False

    if not anticoag_present:
        plan_summary = "No anticoagulant or antiplatelet therapy detected from available text. Continue to verify medication reconciliation."
    else:
        plan_summary = (
            f"{bleeding_risk.upper()} bleeding/neuraxial relevance detected. "
            "Confirm medication indication, last dose, renal function, platelet count, and coagulation labs as applicable. "
            "Do not proceed with neuraxial/deep regional technique until guideline-based timing and safety criteria are confirmed."
        )

    drivers = []
    drivers.extend(red_flags)
    drivers.extend(plan_changers)

    severity = "low"
    if bleeding_risk == "high":
        severity = "critical"
    elif bleeding_risk == "moderate":
        severity = "high"

    confidence = "moderate"
    if missing:
        confidence = "limited_by_missing_data"

    contraindications_cautions = []
    contraindications_cautions.extend(neuraxial_flags)

    clinician_summary = (
        f"{bleeding_risk.upper()} anticoagulation/bleeding relevance. "
        f"{'Neuraxial or deep regional technique NOT safe until verified. ' if not neuraxial_safe else ''}"
        "Confirm last dose timing, renal function, platelet count, and coagulation labs. "
        "Review indication and thrombotic risk before holding therapy."
    )

    return {
        "module": "Anticoagulation / Blood",

        "severity": severity,

        "confidence": confidence,

        "clinician_summary": clinician_summary,

        "drivers": drivers,

        "contraindications_cautions": contraindications_cautions,

        "do_not_assume_guardrails": [

            "Do not assume last dose timing.",

            "Do not assume neuraxial safety without guideline-based confirmation.",

            "Do not assume anticoagulation indication.",

            "Do not proceed with neuraxial or deep regional techniques without verifying timing and labs.",

        ],
        "anticoag_present": anticoag_present,
        "agents_detected": agents,
        "anticoagulants": anticoagulants,
        "antiplatelets": antiplatelets,
        "nsaids": nsaids,
        "bleeding_risk_level": bleeding_risk,
        "neuraxial_block_safe": neuraxial_safe,
        "planned_neuraxial": planned_neuraxial,
        "planned_deep_block": planned_deep_block,
        "procedure_bleeding_risk": procedure_bleeding_risk,
        "thrombotic_risk": thrombotic_risk,
        "last_dose": last_dose,
        "renal_function": renal_function,
        "platelet_count": platelet_count,
        "inr": inr,
        "critical_missing": missing,
        "red_flags": red_flags,
        "neuraxial_flags": neuraxial_flags,
        "hold_guidance": hold_guidance,
        "lab_considerations": lab_considerations,
        "reversal_considerations": reversal_considerations,
        "bridging_considerations": bridging_considerations,
        "plan_changers": plan_changers,
        "plan_summary": plan_summary,
        "safety_statement": (
            "Decision support only. Does not place orders or provide final neuraxial/regional clearance. "
            "Use current ASRA/institutional guidance and clinician judgment."
        )
    }