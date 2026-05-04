import os
import requests
import streamlit as st
from dotenv import load_dotenv
import base64
import hashlib
import secrets
import urllib.parse

from preop_ai_mvp_app_v3 import (
    call_openai,
    extract_ponv_fields,
    extract_anticoag_fields,
    extract_med_safety_fields,
    extract_pulmonary_fields,
    extract_renal_fields,
    extract_frailty_fields,
    render_smart_banner,
    render_dashboard,
    render_cancellation,
    render_disposition,
    render_frailty,
    render_cardiac,
    render_renal,
    render_functional_capacity,
    render_procedure_technique,
    render_eras_meds,
    render_med_safety,
    render_ponv,
    render_pulmonary,
    render_airway,
    render_blood,
    render_plan_changing,
    render_note,
    build_epic_note_text,
)

from ponv_module import build_ponv_module
from anticoag_module import build_anticoag_module
from med_safety_module import build_med_safety_module
from pulmonary_module import build_pulmonary_module
from renal_module import build_renal_module
from frailty_module import build_frailty_module
from disposition_module import build_disposition_module
from cancellation_module import build_cancellation_module


load_dotenv()

load_dotenv()

EPIC_CLIENT_ID = st.secrets.get("EPIC_CLIENT_ID", "")
EPIC_REDIRECT_URI = st.secrets.get("EPIC_REDIRECT_URI", "")
EPIC_FHIR_BASE_URL = st.secrets.get(
    "EPIC_FHIR_BASE_URL",
    "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
)

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")

EPIC_AUTH_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize"
EPIC_TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"

st.set_page_config(page_title="Preop AI FHIR Sandbox", layout="wide")

st.title("Preop AI — FHIR Sandbox Dashboard")
st.warning("Sandbox only. Do not use real PHI.")



def bundle_to_preop_text(bundle):
    lines = []

    patient = bundle.get("Patient", {})
    if patient:
        name = patient.get("name", [{}])[0]
        full_name = " ".join(name.get("given", [])) + " " + name.get("family", "")
        lines.append(f"Patient: {full_name.strip()}")
        lines.append(f"Gender: {patient.get('gender', 'not documented')}")
        lines.append(f"Birth date: {patient.get('birthDate', 'not documented')}")

    def extract_bundle_items(resource_name, label):
        data = bundle.get(resource_name, {})
        entries = data.get("entry", [])
        lines.append(f"\n{label}:")

        if not entries:
            lines.append("- None documented")
            return

        for entry in entries[:30]:
            r = entry.get("resource", {})
            code = r.get("code", {})
            text = code.get("text")

            if not text and code.get("coding"):
                text = code["coding"][0].get("display")

            if text:
                lines.append(f"- {text}")

    extract_bundle_items("Conditions", "Problems / Conditions")
    extract_bundle_items("Medications", "Medications")
    extract_bundle_items("Allergies", "Allergies")
    extract_bundle_items("Procedures", "Procedures")
    extract_bundle_items("Observations / Labs", "Observations / Labs")
    extract_bundle_items("Diagnostic Reports", "Diagnostic Reports")

    return "\n".join(lines)


def make_pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return verifier, challenge


def build_epic_authorize_url():
    code_verifier, code_challenge = make_pkce_pair()
    state = secrets.token_urlsafe(32)

    st.session_state.code_verifier = code_verifier
    st.session_state.oauth_state = state

    params = {
        "response_type": "code",
        "client_id": EPIC_CLIENT_ID,
        "redirect_uri": EPIC_REDIRECT_URI,
        "scope": "launch/patient patient/*.read openid fhirUser",
        "state": state,
        "aud": EPIC_FHIR_BASE_URL,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    return EPIC_AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code_for_token(code):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": EPIC_REDIRECT_URI,
        "client_id": EPIC_CLIENT_ID,
        "code_verifier": st.session_state.get("code_verifier", ""),
    }

    response = requests.post(EPIC_TOKEN_URL, data=data, timeout=20)

    if response.status_code != 200:
        raise Exception(f"Token exchange failed: {response.status_code} {response.text}")

    return response.json()




def run_full_preop_engine(preop_text):
    result = call_openai(preop_text, os.getenv("OPENAI_API_KEY"))

    result["ponv"] = build_ponv_module(extract_ponv_fields(preop_text))
    result["anticoag"] = build_anticoag_module(extract_anticoag_fields(preop_text))
    result["med_safety"] = build_med_safety_module(extract_med_safety_fields(preop_text))
    result["pulmonary"] = build_pulmonary_module(extract_pulmonary_fields(preop_text))
    result["renal"] = build_renal_module(extract_renal_fields(preop_text))
    result["frailty"] = build_frailty_module(extract_frailty_fields(preop_text))

    # Synthesis modules last
    result["disposition"] = build_disposition_module(result)
    result["cancellation"] = build_cancellation_module(result)

    return result

st.subheader("Epic SMART OAuth Test")

if not EPIC_CLIENT_ID or not EPIC_REDIRECT_URI:
    st.warning("Missing EPIC_CLIENT_ID or EPIC_REDIRECT_URI in Streamlit secrets.")
else:
    auth_url = build_epic_authorize_url()
    st.link_button("Connect to Epic Sandbox", auth_url)

query_params = st.query_params

if "code" in query_params:
    code = query_params.get("code")
    returned_state = query_params.get("state")

    if returned_state != st.session_state.get("oauth_state"):
        st.error("OAuth state mismatch. Restart login.")
    else:
        try:
            token_response = exchange_code_for_token(code)

            st.session_state.epic_access_token = token_response.get("access_token")
            st.session_state.epic_patient_id = token_response.get("patient")
            st.session_state.epic_token_response = token_response

            st.success("Epic OAuth token received.")
            st.write("Epic patient ID:", st.session_state.epic_patient_id)

        except Exception as e:
            st.error(str(e))
            
FHIR_BASE_URL = st.text_input(
    "FHIR Base URL",
    value=os.getenv("FHIR_BASE_URL", "https://r4.smarthealthit.org")
)

patient_id = st.session_state.get("epic_patient_id") or st.text_input(
    "Sandbox Patient ID",
    value=os.getenv("PATIENT_ID", "")
)
st.divider()

col_a, col_b, col_c = st.columns(3)

with col_a:
    search_patients = st.button("Search Sample Patients")

with col_b:
    test_patient = st.button("Test Patient Read")

with col_c:
    fetch_bundle = st.button("Fetch Preop Bundle", key="fetch_preop_bundle_btn")

if fetch_bundle:
    if not patient_id:
        st.error("Enter a sandbox patient ID first.")
        st.stop()

    resources = {
        "Patient": f"{FHIR_BASE_URL}/Patient/{patient_id}",
        "Conditions": f"{FHIR_BASE_URL}/Condition?patient={patient_id}&_count=20",
        "Medications": f"{FHIR_BASE_URL}/MedicationRequest?patient={patient_id}&_count=20",
        "Allergies": f"{FHIR_BASE_URL}/AllergyIntolerance?patient={patient_id}&_count=20",
        "Observations / Labs": f"{FHIR_BASE_URL}/Observation?patient={patient_id}&_count=30",
        "Procedures": f"{FHIR_BASE_URL}/Procedure?patient={patient_id}&_count=20",
        "Diagnostic Reports": f"{FHIR_BASE_URL}/DiagnosticReport?patient={patient_id}&_count=20",
    }

    preop_bundle = {}

    with st.spinner("Fetching FHIR preop bundle..."):
        for name, url in resources.items():
            response = requests.get(url, timeout=20)

            if response.status_code == 200:
                preop_bundle[name] = response.json()
            else:
                preop_bundle[name] = {"error": response.text}

    st.session_state.preop_bundle = preop_bundle
    st.session_state.preop_text = bundle_to_preop_text(preop_bundle)
    st.success("FHIR preop bundle fetched and converted.")


if search_patients:
    url = f"{FHIR_BASE_URL}/Patient?_count=5"

    try:
        response = requests.get(url, timeout=20)
        st.write("Status code:", response.status_code)

        if response.status_code == 200:
            bundle = response.json()
            st.success("Patient search successful.")

            for entry in bundle.get("entry", []):
                patient = entry.get("resource", {})
                st.write("Patient ID:", patient.get("id"))
                st.json(patient)
        else:
            st.error("FHIR search failed.")
            st.text(response.text)

    except Exception as e:
        st.error(str(e))


if test_patient:
    if not patient_id:
        st.error("Enter a sandbox patient ID first.")
        st.stop()

    url = f"{FHIR_BASE_URL}/Patient/{patient_id}"

    try:
        response = requests.get(url, timeout=20)
        st.write("Status code:", response.status_code)

        if response.status_code == 200:
            st.success("FHIR Patient read successful.")
            st.json(response.json())
        else:
            st.error("FHIR request failed.")
            st.text(response.text)

    except Exception as e:
        st.error(str(e))


if "preop_bundle" in st.session_state:
    st.divider()
    st.subheader("Combined Preop FHIR Bundle")
    st.json(st.session_state.preop_bundle)

    st.divider()
    st.subheader("Preop AI Input Text")

    st.text_area(
        "FHIR converted to Preop AI input",
        value=st.session_state.preop_text,
        height=400,
        key="fhir_preop_text_area"
    )

    
    st.subheader("Procedure / Anesthesia Context")

    procedure_context = st.text_area(
        "Add procedure / anesthesia context",
        value="Scheduled procedure: not documented",
        height=100
    )

    combined_preop_text = (
        st.session_state.preop_text +
        "\n\nProcedure Context:\n" +
        procedure_context
    )

    st.divider()
    st.subheader("Full Preop AI Dashboard")

    if st.button("Analyze FHIR Patient with Full Dashboard", key="analyze_fhir_full_dashboard_btn"):
        try:
            with st.spinner("Running full Preop AI engine..."):
                result = run_full_preop_engine(combined_preop_text)  # 👈 CHANGE HERE
                st.session_state.result = result

            st.success("Full Preop AI dashboard generated.")

        except Exception as e:
            st.error(str(e))


if "result" in st.session_state:
    result = st.session_state.result

    st.divider()
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
        "JSON",
    ]

    tabs = st.tabs(tab_names)

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
            height=500,
            key="epic_note_text_area"
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
        st.json(result)