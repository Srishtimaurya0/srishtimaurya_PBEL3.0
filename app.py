import streamlit as st
import pandas as pd
import re
from collections import Counter
from resume_parser import extract_text_from_pdf, extract_largest_text
import plotly.graph_objects as go

from nlp_utils import clean_text
from matcher import calculate_similarity
from skill_matcher import extract_skills, analyze_resume_strength


# ================= LOCAL FUNCTIONS FOR INFO EXTRACTION =================
def extract_email(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    return emails[0] if emails else "Not Found"


def extract_phone(text):
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b\d{10}\b'
    phones = re.findall(phone_pattern, text)
    return phones[0] if phones else "Not Found"


def extract_name(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    def is_valid_name_line(line):
        if '@' in line or re.search(r'\d', line) or 'http' in line.lower():
            return False
        word_count = len(line.split())
        return 2 <= word_count <= 5 and len(line) < 60

    for line in lines[:8]:
        if is_valid_name_line(line) and line.isupper():
            return line.title()

    for line in lines[:8]:
        if is_valid_name_line(line):
            return line.title()

    return "Not Found"


# ================= UI SETUP - CORPORATE MODERN THEME =================
st.set_page_config(layout="wide", page_title="TalentScreener AI", page_icon=None)

# CSS
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: 700; color: var(--text-color); text-align: left; margin-bottom: 5px; font-family: 'Inter', sans-serif; }
    .sub-title { font-size: 14px; text-align: left; color: var(--text-color); opacity: 0.8; margin-bottom: 30px; font-family: 'Inter', sans-serif; }
    div.stButton > button:first-child { background-color: #2563EB; color: white; border-radius: 6px; border: none; font-weight: 600; padding: 10px 24px; }
    div.stButton > button:first-child:hover { background-color: #1D4ED8; color: white; }
    .doc-section { background-color: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #2563EB; }
    section[data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid #1E293B;
    }
    section[data-testid="stSidebar"] .stRadio > label {
        font-size: 15px;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 4px;
        transition: background-color 0.2s;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: rgba(37,99,235,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("TalentScreener AI")
st.sidebar.markdown("---")
st.sidebar.subheader("Navigation")
st.sidebar.markdown("---")

if 'df' in st.session_state and st.session_state.get('analysis_done'):
    df_sidebar = st.session_state['df']
    st.sidebar.markdown("#### Quick Stats")
    st.sidebar.metric("Candidates Analyzed", len(df_sidebar))
    st.sidebar.metric("Top Score", f"{df_sidebar['Combined Score (%)'].max()}%")

app_mode = st.sidebar.radio(
    "Navigation",
    ["Evaluation Console", "System Documentation"],
    label_visibility="collapsed"
)


# ================= PAGE 1: EVALUATION CONSOLE =================
if app_mode == "Evaluation Console":

    st.markdown('<div class="main-title">TalentScreener AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">AI Powered Resume Screening Platform</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center;
        background-color: rgba(37,99,235,0.08); border: 1px solid rgba(37,99,235,0.3);
        border-radius: 8px; padding: 14px 24px; margin-bottom: 24px; font-size: 14px;">
            <span>Upload Resumes</span>
            <span style="opacity:0.4;">&mdash;</span>
            <span>AI Analysis</span>
            <span style="opacity:0.4;">&mdash;</span>
            <span>Candidate Ranking</span>
            <span style="opacity:0.4;">&mdash;</span>
            <span>ATS Evaluation</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Clean Layout Columns
    col_input1, col_input2 = st.columns([1, 1], gap="large")

    with col_input1:
        st.markdown("### Upload Candidate Resumes")
        uploaded_files = st.file_uploader(
            "Upload candidate profiles (PDF format supported)",
            type=["pdf"], accept_multiple_files=True, label_visibility="collapsed"
        )
        st.caption("Only PDF files are accepted. Other formats (DOCX, JPG, TXT, etc.) will not be uploaded.")

    with col_input2:
        st.markdown("### Job Description")
        job_description = st.text_area(
            "Paste Job Description", height=125,
            placeholder="Enter target skills, qualifications, and role responsibilities...",
            label_visibility="collapsed"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    analyze = st.button("Analyze Candidates", use_container_width=True)

    # --- RUN ANALYSIS WHEN BUTTON IS CLICKED ---
    if analyze:
        if not job_description and not uploaded_files:
            st.session_state['analysis_done'] = False
            st.error("Please provide a Job Description and upload at least one Resume to begin analysis.")
        elif job_description and not uploaded_files:
            st.session_state['analysis_done'] = False
            st.warning("Job Description provided, but no resumes uploaded. Please upload candidate profiles.")
        elif not job_description and uploaded_files:
            st.session_state['analysis_done'] = False
            st.warning("Resumes uploaded, but Job Description is empty. Please enter the target job description.")
        else:
            results_list = []
            clean_job = clean_text(job_description)
            job_skills = extract_skills(clean_job)

            for file in uploaded_files:
                try:
                    resume_text = extract_text_from_pdf(file)
                    candidate_name = extract_largest_text(file)

                    email = extract_email(resume_text)
                    phone = extract_phone(resume_text)
                    if not candidate_name or candidate_name.strip() == "":
                        candidate_name = extract_name(resume_text)

                    clean_resume = clean_text(resume_text)
                    score = calculate_similarity(clean_resume, clean_job)
                    match_percentage = int(round(score * 100, 2))

                    resume_skills = extract_skills(clean_resume)
                    matched_skills = list(set(resume_skills) & set(job_skills))
                    missing_skills = list(set(job_skills) - set(resume_skills))
                    if len(job_skills) > 0:
                        skill_match_pct = (len(matched_skills) / len(job_skills)) * 100
                    else:
                        skill_match_pct = 0

                    combined_score = round((match_percentage * 0.4) + (skill_match_pct * 0.6), 2)

                    if combined_score >= 75:
                        recommendation = "Strong Hire"
                    elif combined_score >= 55:
                        recommendation = "Hire"
                    elif combined_score >= 30:
                        recommendation = "Consider"
                    else:
                        recommendation = "Not Suitable"

                    resume_sections_found, resume_sections_missing = analyze_resume_strength(resume_text)
                    if len(job_skills) > 0:
                        keyword_score = (len(matched_skills) / len(job_skills)) * 60
                    else:
                        keyword_score = 0
                    section_score = (len(resume_sections_found) / 5) * 40
                    ats_score = round(keyword_score + section_score, 2)

                    results_list.append({
                        "Candidate Name": candidate_name if candidate_name else file.name.replace(".pdf", ""),
                        "Email": email,
                        "Phone": phone,
                        "Combined Score (%)": combined_score,
                        "Matched_Skills": matched_skills,
                        "Missing_Skills": missing_skills,
                        "Recommendation": recommendation,
                        "Resume_Text": resume_text,
                        "ATS Score": ats_score,
                        "Found Sections": resume_sections_found,
                        "Missing Sections List": resume_sections_missing,
                    })
                except Exception as e:
                    st.error(f"Error processing {file.name}: {str(e)}")

            if results_list:
                df = pd.DataFrame(results_list)
                df = df.sort_values(by="Combined Score (%)", ascending=False).reset_index(drop=True)

                st.session_state['df'] = df
                st.session_state['analysis_done'] = True
            else:
                st.session_state['analysis_done'] = False
                st.error("No resumes could be processed. The uploaded file(s) may be corrupted, blank, or not a valid PDF. Please check the file and try again.")

    # --- DISPLAY RESULTS (persists across reruns, e.g. selecting a candidate) ---
    if st.session_state.get('analysis_done'):
        df = st.session_state['df']
        best_candidate = df.iloc[0]

        # --- METRICS PANEL ---
        st.markdown("---")
        st.markdown("## Executive Dashboard")

        st.markdown(
            f"""
           <div style="background: linear-gradient(135deg, rgba(234,179,8,0.15), rgba(234,179,8,0.03));
           border: 1px solid #EAB308; border-radius: 10px; padding: 20px 24px; margin-bottom: 20px;">
            <div style="color:#EAB308; font-weight:700; font-size:14px; letter-spacing:1px; margin-bottom:12px;">TOP CANDIDATE</div>
            <div style="font-size:24px; font-weight:700; color:white; margin-bottom:8px;">{best_candidate['Candidate Name']}</div>
            <div style="opacity:0.85; font-size:14px; color:white;">
                Match Score: <b>{best_candidate['Combined Score (%)']}%</b> &nbsp;&nbsp;|&nbsp;&nbsp;
                Recommendation: <b>{best_candidate['Recommendation']}</b>
            </div>
        </div>
        """,
            unsafe_allow_html=True
        )

        # Consistent with the "Hire" threshold used above, so a candidate
        # marked "Hire" is also counted as a Recommended Profile.
        recommended = len(df[df["Combined Score (%)"] >= 55])
        strong_hire = len(df[df["Recommendation"] == "Strong Hire"])
        hire = len(df[df["Recommendation"] == "Hire"])
        consider = len(df[df["Recommendation"] == "Consider"])
        not_suitable = len(df[df["Recommendation"] == "Not Suitable"])

        st.markdown("### Recommendation Summary")

        if len(df) > 0:
            success_rate = round((recommended / len(df)) * 100, 2)
        else:
            success_rate = 0

        st.progress(success_rate / 100)

        st.caption(f"Overall Selection Success Rate : {success_rate}%")

        r1, r2, r3, r4 = st.columns(4)

        with r1:
            st.success(f"Strong Hire : {strong_hire}")
        with r2:
            st.info(f"Hire : {hire}")
        with r3:
            st.warning(f"Consider : {consider}")
        with r4:
            st.info(f"Not Suitable : {not_suitable}")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Candidate Count", len(df))

        with c2:
            st.metric("Highest Match Score", f"{df['Combined Score (%)'].max()}%")

        with c3:
            st.metric("Average Match Score", f"{round(df['Combined Score (%)'].mean(), 2)}%")

        with c4:
            st.metric("Recommended Profiles", recommended)

        st.markdown("---")

        # --- RESULT VIEWER (SPLIT VIEW) ---
        total_matched = sum(len(x) for x in df["Matched_Skills"])
        total_missing = sum(len(x) for x in df["Missing_Skills"])
        total_skills = total_matched + total_missing

        if total_skills > 0:
            coverage = total_matched / total_skills
        else:
            coverage = 0

        col_res1, col_res2 = st.columns([11, 9], gap="large")

        # --- LEFT COLUMN ---
        with col_res1:
            st.markdown("## Candidate Ranking")
            st.caption("AI-powered ranking of candidate profiles based on job description similarity.")

            for idx, row in df.iterrows():
                with st.container(border=True):
                    left_col, right_col = st.columns([4, 1])
                    with left_col:
                        st.markdown(f"### #{idx + 1}  {row['Candidate Name']}")
                        st.write(f"**Email:** {row['Email']}")
                        st.write(f"**Phone:** {row['Phone']}")

                        st.write("**Matched Skills**")

                        if row["Matched_Skills"]:
                            st.success(" | ".join(row["Matched_Skills"]))
                        else:
                            st.info("No matching skills found")
                        st.write("**Missing Skills**")

                        if row["Missing_Skills"]:
                            st.error(" | ".join(row["Missing_Skills"]))
                        else:
                            st.success("No missing skills")
                    with right_col:
                        st.metric(label="Score", value=f"{row['Combined Score (%)']}%")

                        if row["Recommendation"] == "Strong Hire":
                            st.success(row["Recommendation"])
                        elif row["Recommendation"] == "Hire":
                            st.info(row["Recommendation"])
                        elif row["Recommendation"] == "Consider":
                            st.warning(row["Recommendation"])
                        else:
                            st.error(row["Recommendation"])

                        st.divider()

            # Export Button Data Preparation
            st.markdown("### Export Evaluation Data")

            df_export = df.copy()
            if 'Matched_Skills' in df_export.columns:
                df_export['Matched Skills'] = df_export['Matched_Skills'].apply(lambda x: ", ".join(x))
            if 'Missing_Skills' in df_export.columns:
                df_export['Missing Skills'] = df_export['Missing_Skills'].apply(lambda x: ", ".join(x))

            # Force Phone to be read as text in Excel, so it doesn't get
            # auto-converted to scientific notation (e.g. 9.13E+09).
            if 'Phone' in df_export.columns:
                df_export['Phone'] = df_export['Phone'].apply(
                   lambda x: f'="{x}"' if x and x != "Not Found" else x 
                )

            cols_to_drop = [c for c in ["Matched_Skills", "Missing_Skills"] if c in df_export.columns]
            if cols_to_drop:
                df_export = df_export.drop(columns=cols_to_drop)

            csv_data = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Full Evaluation Report (CSV)",
                data=csv_data,
                file_name="TalentScreener_Report.csv",
                mime="text/csv",
                use_container_width=True
            )

        # --- RIGHT COLUMN: DYNAMIC CIRCULAR GAUGE & VARIANCE ANALYTICS ---
        with col_res2:
            st.markdown("---")
            st.markdown("## Skill Analysis")

            k1, k2 = st.columns(2)

            with k1:
                st.metric("Matched Skills", total_matched)

            with k2:
                st.metric("Missing Skills", total_missing)

            st.progress(coverage)
            fig = go.Figure(data=[go.Pie(
                labels=["Matched Skills", "Missing Skills"],
                values=[total_matched, total_missing],
                hole=0.6,
                marker_colors=["#22C55E", "#EF4444"]
            )])
            fig.update_layout(
                showlegend=True,
                margin=dict(t=0, b=0, l=0, r=0),
                height=220,
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white")
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"Overall Skill Coverage : {round(coverage * 100, 2)}%")

            all_skills = []
            for skills in df["Matched_Skills"]:
                if isinstance(skills, list):
                    all_skills.extend(skills)
                elif isinstance(skills, str) and skills.strip():
                    all_skills.append(skills)

            if all_skills:
                skill_counter = Counter(all_skills)
                top_skill = skill_counter.most_common(1)[0]
                st.success(f"Most Common Skill : {top_skill[0]} ({top_skill[1]} candidates)")
            else:
                st.info("No matched skills found.")

        st.markdown("---")

        st.markdown("## Candidate Evaluation")
        st.caption("Interactive analysis of shortlisted candidates.")

        # Dropdown for selecting a candidate to view their circular gauge
        # Use row position (not name) to identify a candidate, so two
        # candidates sharing the same name are still distinguished correctly.
        candidate_labels = [
            f"{row['Candidate Name']} (#{idx + 1})" for idx, row in df.iterrows()
        ]
        selected_label = st.selectbox("Select Candidate for Detailed Analysis:", candidate_labels)

        if selected_label:
            selected_idx = candidate_labels.index(selected_label)
            cand_row = df.iloc[selected_idx]
            score = int(round(float(cand_row["Combined Score (%)"])))

            # SVG Gauge Math (Radius = 52, Circumference = ~326.7)
            dash_offset = 326.7 - (326.7 * score / 100)

            with st.container(border=True):
                st.markdown(
                    "<h3 style='margin-bottom:2px;'>Candidate Profile</h3><hr style='margin-top:0; opacity:0.15;'>",
                    unsafe_allow_html=True
                )

                st.markdown("##### Hiring Decision")

                badge_colors = {
                    "Strong Hire": ("rgba(34,197,94,0.15)", "#22C55E"),
                    "Hire": ("rgba(59,130,246,0.15)", "#3B82F6"),
                    "Consider": ("rgba(234,179,8,0.15)", "#EAB308"),
                    "Not Suitable": ("rgba(239,68,68,0.15)", "#F87171"),
                }
                bg, border = badge_colors.get(cand_row["Recommendation"], ("#334155", "#94A3B8"))

                st.markdown(
                    f"""<div style="display:inline-block; background-color:{bg}; border:1px solid {border};
                    color:white; padding:6px 18px; border-radius:20px; font-weight:600; font-size:14px;">
                    {cand_row["Recommendation"]}
                    </div>""",
                    unsafe_allow_html=True
                )

                # Circular SVG Progress Gauge Layout
                gauge_html = f"""
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; background: #1E293B; padding: 25px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px;">
                <svg width="140" height="140" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="52" fill="transparent" stroke="#334155" stroke-width="10"/>
                    <circle cx="60" cy="60" r="52" fill="transparent" stroke="#2563EB" stroke-width="10"
                            stroke-dasharray="326.7" stroke-dashoffset="{dash_offset}"
                            stroke-linecap="round" transform="rotate(-90 60 60)"/>
                    <text x="60" y="66" fill="#FFFFFF" font-size="22" font-weight="700" text-anchor="middle">{score}%</text>
                </svg>
                <div style="color: #94A3B8; font-size: 13px; margin-top: 12px; font-weight: 600; letter-spacing: 0.5px;">TOTAL RESUME FITMENT STRENGTH</div>
                </div>
                """
                st.components.v1.html(gauge_html, height=210)

            st.markdown("<br>", unsafe_allow_html=True)

            with st.container(border=True):
                p1, p2 = st.columns(2)

                with p1:
                    st.markdown("#### Personal Information")
                    st.write(f"**Name:** {cand_row['Candidate Name']}")
                    st.write(f"**Email:** {cand_row['Email']}")
                    st.write(f"**Phone:** {cand_row['Phone']}")

                with p2:
                    st.markdown("#### Evaluation Metrics")
                    st.metric("Match Score", f"{cand_row['Combined Score (%)']}%")
                    st.metric("ATS Score", f"{cand_row['ATS Score']}%")

            st.markdown("<br>", unsafe_allow_html=True)

            found_sections, missing_sections = analyze_resume_strength(cand_row["Resume_Text"])
            strength_score = int((len(found_sections) / 5) * 100)

            with st.container(border=True):
                st.markdown("#### Resume Analysis")

                bar_col, _ = st.columns([2, 1])
                with bar_col:
                    st.progress(strength_score / 100)
                    m1, m2 = st.columns(2)

                with m1:
                    st.metric("Resume Strength", f"{strength_score}%")
                with m2:
                    st.metric("ATS Score", f"{cand_row['ATS Score']}%")

                left, right = st.columns(2)

                with left:
                    st.markdown("#### Detected Sections")
                    for section in found_sections:
                        st.write(f"• {section}")
                with right:
                    st.markdown("#### Sections to Improve")
                    if missing_sections:
                        for section in missing_sections:
                            st.write(f"• {section}")
                    else:
                        st.info("No missing sections")

            suggestions = []

            if "Projects" in missing_sections:
                suggestions.append("Add at least 2 academic or personal projects.")
            if "Experience" in missing_sections:
                suggestions.append("Include internships, freelance work, or relevant experience.")
            if "Certifications" in missing_sections:
                suggestions.append("Add certifications such as NPTEL, Coursera, or IBM SkillsBuild.")
            if "Education" in missing_sections:
                suggestions.append("Clearly mention your education details.")
            if "Skills" in missing_sections:
                suggestions.append("Create a dedicated technical skills section.")

            st.markdown("<br>", unsafe_allow_html=True)

            with st.container(border=True):
                st.markdown("#### Resume Improvement Suggestions")

                if suggestions:
                    sug_col, _ = st.columns([2, 1])
                    with sug_col:
                        for single_suggestion in suggestions:
                            st.markdown(
                                f"""<div style="background-color: rgba(37,99,235,0.1); border-left: 3px solid #2563EB; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                                {single_suggestion}
                                </div>""",
                                unsafe_allow_html=True
                            )
                else:
                    st.success("Resume looks complete. No major improvements suggested.")

            st.caption("Overall hiring recommendation distribution")
            dist_fig = go.Figure(data=[go.Bar(
                x=["Strong Hire", "Hire", "Consider", "Not Suitable"],
                y=[strong_hire, hire, consider, not_suitable],
                marker_color=["#22C55E", "#3B82F6", "#EAB308", "#EF4444"],
                marker_line_width=0,
                width=0.5
            )])
            dist_fig.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=250,
                bargap=0.4,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                yaxis=dict(title="Candidates", gridcolor="rgba(255,255,255,0.1)"),
                xaxis=dict(showgrid=False),
            )
            dist_fig.update_traces(marker_cornerradius=8)
            st.plotly_chart(dist_fig, use_container_width=True, config={"displayModeBar": False})

            with st.expander("Filter Analytics by Skill Matrix"):
                search_skill = st.text_input("Search by Skill", placeholder="Example: Python")
                if search_skill:
                    filtered_df = df[df['Matched_Skills'].apply(
                        lambda x: search_skill.lower() in [s.lower() for s in x]
                    )]
                    if not filtered_df.empty:
                        st.success(f"{len(filtered_df)} candidate(s) found.")
                        st.dataframe(
                            filtered_df[["Candidate Name", "Combined Score (%)", "Recommendation"]],
                            use_container_width=True
                        )
                    else:
                        st.warning("No candidate found with this skill.")

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center; padding: 10px 0; opacity: 0.75;">
        <span style="font-weight:600;">TalentScreener AI v1.0</span> &nbsp;|&nbsp;
        Made by Srishti Maurya &nbsp;|&nbsp;
        Data &amp; AI Projects &nbsp;|&nbsp;
    
        </div>
        """,
        unsafe_allow_html=True
    )


# ================= PAGE 2: SYSTEM DOCUMENTATION =================
elif app_mode == "System Documentation":
    st.markdown('<div class="main-title">Architecture &amp; System Documentation</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Technical specifications and compliance framework of TalentScreener AI</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="doc-section">
        <h4>1. Core Processing Engine</h4>
        <p>The system utilizes a multi-stage Natural Language Processing (NLP) pipeline to clean text data, remove noisy components, and structure unstructured resume textual fields.</p>
    </div>
    <div class="doc-section">
        <h4>2. Vectorization &amp; Similarity Metrics</h4>
        <p>Candidate profiles are vectorized and compared against the requested Job Description using spatial proximity metrics to generate normalized statistical variance scores.</p>
    </div>
    <div class="doc-section">
        <h4>3. Enterprise Security &amp; Privacy</h4>
        <p>All uploads are parsed completely in volatile runtime memory. No persistent storage systems or external logs retain personal data records.</p>
    </div>
    """, unsafe_allow_html=True)