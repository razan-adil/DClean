import os
import tempfile
import streamlit as st
import pandas as pd

from pipeline.runner import PipelineRunner


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="DClean | Data Cleaning",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# CUSTOM DESIGN
# =========================================================
st.markdown("""
<style>

/* Main page */
.stApp {
    background: linear-gradient(135deg, #0b1120 0%, #111827 50%, #0f172a 100%);
}

/* Main container */
.block-container {
    max-width: 1200px;
    padding-top: 3rem;
    padding-bottom: 4rem;
}

/* Hide Streamlit decoration */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Header */
.hero {
    text-align: center;
    padding: 25px 10px 35px 10px;
}

.logo {
    font-size: 52px;
    font-weight: 800;
    color: white;
    margin-bottom: 5px;
}

.logo span {
    color: #38bdf8;
}

.subtitle {
    font-size: 18px;
    color: #94a3b8;
}

/* Section titles */
.section-title {
    color: white;
    font-size: 22px;
    font-weight: 700;
    margin-top: 25px;
    margin-bottom: 10px;
}

/* Upload card */
.upload-card {
    background: rgba(30, 41, 59, 0.75);
    border: 1px solid #334155;
    border-radius: 18px;
    padding: 25px;
    margin-bottom: 20px;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid #334155;
    padding: 20px;
    border-radius: 15px;
}

[data-testid="stMetricLabel"] {
    color: #94a3b8;
}

[data-testid="stMetricValue"] {
    color: white;
}

/* Button */
.stButton > button {
    width: 100%;
    border-radius: 10px;
    height: 3.2rem;
    font-weight: 700;
    border: none;
}

/* Download button */
.stDownloadButton > button {
    width: 100%;
    border-radius: 10px;
    height: 3.2rem;
    font-weight: 700;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(15, 23, 42, 0.6);
    border-radius: 15px;
    padding: 10px;
}

/* Text */
p, label {
    color: #cbd5e1 !important;
}

/* Divider */
hr {
    border-color: #334155;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# HEADER
# =========================================================
st.markdown("""
<div class="hero">
    <div class="logo">D<span>Clean</span></div>
    <div class="subtitle">
        Intelligent Data Cleaning & Entity Resolution Platform
    </div>
</div>
""", unsafe_allow_html=True)


# =========================================================
# UPLOAD
# =========================================================
st.markdown(
    '<div class="section-title">01 — Upload Dataset</div>',
    unsafe_allow_html=True
)

st.caption(
    "Upload your raw Excel or CSV dataset. "
    "DClean will automatically analyze and clean the data."
)

uploaded_file = st.file_uploader(
    "Drop your dataset here",
    type=["xlsx", "csv"],
    label_visibility="collapsed"
)


# =========================================================
# WHEN FILE IS UPLOADED
# =========================================================
if uploaded_file is not None:

    st.success(f"✓ {uploaded_file.name} uploaded successfully")

    # -----------------------------------------------------
    # RAW DATA PREVIEW
    # -----------------------------------------------------
    st.markdown(
        '<div class="section-title">02 — Data Preview</div>',
        unsafe_allow_html=True
    )

    try:

        if uploaded_file.name.lower().endswith(".csv"):
            raw_preview = pd.read_csv(uploaded_file)
        else:
            raw_preview = pd.read_excel(uploaded_file)

        uploaded_file.seek(0)

        info1, info2, info3 = st.columns(3)

        info1.metric(
            "Rows Detected",
            len(raw_preview)
        )

        info2.metric(
            "Columns Detected",
            len(raw_preview.columns)
        )

        info3.metric(
            "File Type",
            uploaded_file.name.split(".")[-1].upper()
        )

        with st.expander("View raw data preview", expanded=False):
            st.dataframe(
                raw_preview.head(20),
                use_container_width=True
            )

    except Exception:
        st.info("Preview unavailable. The pipeline can still process the file.")

    # -----------------------------------------------------
    # CONTRACT STRATEGY SELECTION
    # -----------------------------------------------------
    st.markdown(
        '<div class="section-title">03 — Schema Contract Strategy</div>',
        unsafe_allow_html=True
    )

    config_dir = "config"
    available_contracts = []
    if os.path.exists(config_dir):
        available_contracts = [f for f in os.listdir(config_dir) if f.endswith(".yaml") or f.endswith(".yml")]

    strategy_col1, strategy_col2 = st.columns([1, 1])
    with strategy_col1:
        strategy = st.radio(
            "Select Schema Strategy",
            options=["Auto-Detect (Local AI/NLP Classifier)", "Declarative YAML Contract"],
            label_visibility="collapsed"
        )

    selected_contract_path = None
    with strategy_col2:
        if strategy == "Declarative YAML Contract":
            if available_contracts:
                chosen_contract = st.selectbox("Choose Contract Schema", available_contracts)
                selected_contract_path = os.path.join(config_dir, chosen_contract)
            else:
                st.info("No YAML contracts found in config/. Defaulting to Auto-Detect.")

    # -----------------------------------------------------
    # CLEANING
    # -----------------------------------------------------
    st.markdown(
        '<div class="section-title">04 — Run Cleaning Pipeline</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "The pipeline will normalize identities, validate records, "
        "resolve duplicate entities and quarantine invalid rows."
    )

    run_button = st.button(
        "✦ Start Cleaning",
        type="primary",
        use_container_width=True
    )

    if run_button:

        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, uploaded_file.name)

        try:
            # Progress display
            progress = st.progress(0)
            status_text = st.empty()

            status_text.write("Reading dataset...")
            progress.progress(15)

            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            os.makedirs("CleanData", exist_ok=True)

            base_name = os.path.splitext(uploaded_file.name)[0]

            output_excel = os.path.join(
                "CleanData",
                f"{base_name}_Dashboard_Cleaned.xlsx"
            )

            db_path = os.path.join(
                "CleanData",
                "dashboard_database.db"
            )

            status_text.write("Initializing cleaning pipeline...")
            progress.progress(30)

            runner = PipelineRunner(
                contract_path=selected_contract_path,
                db_path=db_path
            )

            status_text.write(
                "Normalizing and validating records..."
            )
            progress.progress(50)

            summary = runner.run(
                input_file_path=input_path,
                output_excel_path=output_excel
            )

            progress.progress(80)
            status_text.write(
                "Resolving duplicate entities..."
            )

            progress.progress(100)
            status_text.write("Cleaning completed ✓")

            st.success(
                "Dataset successfully processed."
            )

            # =================================================
            # RESULTS
            # =================================================
            st.markdown(
                '<div class="section-title">'
                '05 — Cleaning Results'
                '</div>',
                unsafe_allow_html=True
            )

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Total Rows",
                summary.total_rows
            )

            c2.metric(
                "Valid Rows",
                summary.valid_rows
            )

            c3.metric(
                "Quarantined",
                summary.quarantined_rows
            )

            c4.metric(
                "Unique Entities",
                summary.unique_persons_resolved
            )

            c5, c6, c7 = st.columns(3)

            c5.metric(
                "Duplicates Merged",
                summary.duplicate_events_merged
            )

            c6.metric(
                "Quarantine Rate",
                f"{summary.quarantine_rate_pct}%"
            )

            c7.metric(
                "Pipeline Status",
                summary.status
            )

            # =================================================
            # DATA PREVIEWS (Cleaned vs Quarantined)
            # =================================================
            if os.path.exists(output_excel):

                st.markdown(
                    '<div class="section-title">'
                    '06 — Output Inspection'
                    '</div>',
                    unsafe_allow_html=True
                )

                tab_clean, tab_quarantine = st.tabs([
                    f"✓ Cleaned Dataset ({summary.valid_rows} rows)",
                    f"⚠️ Quarantined Store ({summary.quarantined_rows} rows)"
                ])

                with tab_clean:
                    try:
                        cleaned_preview = pd.read_excel(output_excel, sheet_name=0)
                        st.dataframe(cleaned_preview.head(50), use_container_width=True)
                    except Exception:
                        st.info("Cleaned data preview unavailable.")

                with tab_quarantine:
                    if summary.quarantined_rows > 0:
                        try:
                            quarantine_preview = pd.read_excel(output_excel, sheet_name="quarantine_records")
                            st.dataframe(quarantine_preview, use_container_width=True)
                        except Exception:
                            st.info("No quarantine sheet found.")
                    else:
                        st.success("Zero records were quarantined. All records met contract assertions!")

                # =================================================
                # EXPORT DOWNLOADS
                # =================================================
                st.markdown(
                    '<div class="section-title">'
                    '07 — Export Results'
                    '</div>',
                    unsafe_allow_html=True
                )

                st.caption(
                    "Download your cleaned Excel workbook or SQLite relational database."
                )

                d_col1, d_col2 = st.columns(2)

                with d_col1:
                    with open(output_excel, "rb") as cleaned_file:
                        st.download_button(
                            label="↓ Download Cleaned Excel (.xlsx)",
                            data=cleaned_file.read(),
                            file_name=f"{base_name}_Cleaned.xlsx",
                            mime=(
                                "application/vnd.openxmlformats-"
                                "officedocument.spreadsheetml.sheet"
                            ),
                            use_container_width=True
                        )

                with d_col2:
                    if os.path.exists(db_path):
                        with open(db_path, "rb") as db_file:
                            st.download_button(
                                label="↓ Download SQLite Database (.db)",
                                data=db_file.read(),
                                file_name=f"{base_name}_database.db",
                                mime="application/x-sqlite3",
                                use_container_width=True
                            )

        except Exception as error:

            st.error(
                "The pipeline encountered an error."
            )

            st.exception(error)

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


# =========================================================
# FOOTER
# =========================================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()

st.markdown(
    """
    <div style="
        text-align:center;
        color:#64748b;
        font-size:13px;
        padding:10px;
    ">
        DClean • Data Cleaning & Entity Resolution
    </div>
    """,
    unsafe_allow_html=True
)