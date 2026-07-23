"""MedX AI — Streamlit UI: upload a chest X-ray, get diagnosis + Grad-CAM + report."""
import requests
import streamlit as st

st.set_page_config(page_title="MedX AI", page_icon="🩻", layout="centered")

st.title("MedX AI — Chest X-Ray Analysis")

with st.sidebar:
    backend_url = st.text_input("Backend URL", value="http://localhost:8000").rstrip("/")
    patient_id = st.text_input("Patient ID", value="patient-001")

uploaded_file = st.file_uploader("Upload a chest X-ray", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded image", width=300)

if st.button("Analyze", type="primary", disabled=uploaded_file is None):
    with st.spinner("Uploading image..."):
        upload_resp = requests.post(
            f"{backend_url}/upload",
            files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
            data={"patient_external_id": patient_id},
        )

    if not upload_resp.ok:
        st.error(f"Upload failed: {upload_resp.status_code} — {upload_resp.text}")
    else:
        study_id = upload_resp.json()["study_id"]

        with st.spinner("Running prediction + Grad-CAM..."):
            predict_resp = requests.post(f"{backend_url}/predict/{study_id}")

        if not predict_resp.ok:
            st.error(f"Prediction failed: {predict_resp.status_code} — {predict_resp.text}")
        else:
            result = predict_resp.json()

            st.subheader("Findings")
            sorted_labels = dict(
                sorted(result["disease_labels"].items(), key=lambda kv: kv[1], reverse=True)
            )
            st.bar_chart(sorted_labels)

            st.subheader("Grad-CAM")
            st.image(f"{backend_url}/{result['gradcam_path']}", width=300)

            st.subheader("Report")
            if result["report_text"]:
                st.write(result["report_text"])
            else:
                st.info("No report available (LLM not configured or the call failed).")
