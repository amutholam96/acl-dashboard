import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np

# --- PAGE CONFIGURATION (Must be first) ---
st.set_page_config(page_title="MOR ACL Dashboard", layout="wide", page_icon="🏥")

# --- CUSTOM CSS FOR "CARD" LOOK ---
st.markdown("""
    <style>
    /* Card Styling */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .big-stat { font-size: 2rem; font-weight: bold; }
    .status-pass { color: #10b981; font-weight: bold; font-size: 1.2rem;}
    .status-warn { color: #f59e0b; font-weight: bold; font-size: 1.2rem;}
    .status-fail { color: #ef4444; font-weight: bold; font-size: 1.2rem;}
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def calculate_lsi(involved, uninvolved):
    if uninvolved == 0 or pd.isna(uninvolved) or pd.isna(involved): return 0.0
    return (involved / uninvolved) * 100

def calculate_ttbw(force_lbs, body_weight_lbs, moment_arm_m=0.36):
    if body_weight_lbs == 0 or pd.isna(body_weight_lbs) or pd.isna(force_lbs): return 0.0
    force_n = force_lbs * 4.44822
    mass_kg = body_weight_lbs * 0.453592
    return (force_n * moment_arm_m) / mass_kg

def check_thresholds(metrics):
    # Simplified Logic from your prompt
    l1_pass = (metrics['acl_rsi'] >= 70) and (metrics['kf_lsi'] >= 80)
    l2_pass = l1_pass and (metrics['ke_lsi'] >= 80) and (metrics['ke_ttbw_inv'] >= 2.3)
    l3_pass = l2_pass and (metrics['acl_rsi'] >= 85) and (metrics['ke_lsi'] >= 85) and (metrics['ke_ttbw_inv'] >= 2.7)
    l4_pass = l3_pass and (metrics['acl_rsi'] >= 90) and (metrics['ke_lsi'] >= 90) and (metrics['ke_ttbw_inv'] >= 3.0)

    if l4_pass: return 4, "RTS CLEARED", "status-pass"
    elif l3_pass: return 3, "Power Phase", "status-warn"
    elif l2_pass: return 2, "Strength Phase", "status-warn"
    elif l1_pass: return 1, "Early Phase", "status-fail"
    else: return 0, "Pre-Rehab / Early Post-Op", "status-fail"

# --- DATA SETUP (Demo Mode) ---
if 'patients' not in st.session_state:
    st.session_state.patients = pd.DataFrame({
        'MRN': ['#000000', '#123456'],
        'Name': ['Rose, Derrick', 'Doe, Jane'],
        'Surgery_Date': [datetime(2024, 10, 17), datetime(2024, 1, 15)]
    })

if 'assessments' not in st.session_state:
    st.session_state.assessments = pd.DataFrame([
        {
            'MRN': '#000000', 'Date': datetime(2024, 12, 30), 'Weeks_Post_Op': 10,
            'ACL_RSI': 85, 'LEFS': 70, 'KE_LSI': 88, 'KF_LSI': 92, 'KE_TTBW_Inv': 2.6,
            'Squat_Asym': 8, 'CMJ_Asym': 10,
            'Notes': "Patient progressing well. Quad strength improving but still lacking power at end range."
        }
    ])

# --- SIDEBAR ---
st.sidebar.image("https://img.icons8.com/color/96/medical-doctor.png", width=50)
st.sidebar.title("Midwest Ortho RTS")
page = st.sidebar.radio("Navigation", ["Athlete Dashboard", "New Assessment", "Database"])

# Global Patient Selector
patient_names = st.session_state.patients['Name'].tolist()
selected_name = st.sidebar.selectbox("Select Athlete", patient_names)
selected_patient = st.session_state.patients[st.session_state.patients['Name'] == selected_name].iloc[0]
mrn = selected_patient['MRN']

# --- DASHBOARD PAGE ---
if page == "Athlete Dashboard":
    # Header
    st.markdown(f"## 👤 {selected_name} <span style='color:gray; font-size:0.6em'>(MRN: {mrn})</span>", unsafe_allow_html=True)
    
    # Get Data
    pt_data = st.session_state.assessments[st.session_state.assessments['MRN'] == mrn].sort_values(by='Date')
    
    if not pt_data.empty:
        latest = pt_data.iloc[-1]
        
        # Calculate Status
        level, status_text, status_color = check_thresholds({
            'acl_rsi': latest['ACL_RSI'], 'ke_lsi': latest['KE_LSI'], 'kf_lsi': latest['KF_LSI'], 'ke_ttbw_inv': latest['KE_TTBW_Inv']
        })

        # --- ROW 1: STATUS CARDS ---
        c1, c2, c3 = st.columns([2, 1, 1])
        
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color: gray; font-size: 0.9rem;">CURRENT STATUS</div>
                <div class="{status_color}" style="font-size: 2rem;">Level {level}: {status_text}</div>
                <div style="margin-top: 10px;">Weeks Post-Op: <b>{latest['Weeks_Post_Op']}</b></div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.metric("ACL-RSI (Psych)", f"{latest['ACL_RSI']}/100", delta=f"{latest['ACL_RSI']-90} to Goal")
        with c3:
            st.metric("Quad LSI", f"{latest['KE_LSI']}%", delta=f"{latest['KE_LSI']-90}% to Goal")

        # --- ROW 2: RADAR & CLINICIAN NOTES ---
        col_main, col_notes = st.columns([2, 1])
        
        with col_main:
            # Radar Chart
            cats = ['ACL-RSI', 'Quad LSI', 'Hamstring LSI', 'Quad TTBW (Norm)', 'Squat Sym']
            vals = [latest['ACL_RSI'], latest['KE_LSI'], latest['KF_LSI'], min(latest['KE_TTBW_Inv']/3.0*100, 100), max(100-(latest['Squat_Asym']*5), 0)]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=vals, theta=cats, fill='toself', name='Current'))
            fig.add_trace(go.Scatterpolar(r=[90,90,90,100,90], theta=cats, name='Target', line_color='green', line_dash='dot'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(t=20, b=20, l=40, r=40), height=300)
            
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_notes:
            st.markdown(f"""
            <div class="metric-card" style="height: 340px; overflow-y: auto;">
                <div style="font-weight: bold; margin-bottom: 10px;">📝 Clinician Summary</div>
                <div style="background-color: #fff; padding: 10px; border-radius: 5px; border: 1px solid #eee;">
                    {latest.get('Notes', 'No notes entered for this session.')}
                </div>
                <br>
                <div style="font-size: 0.8rem; color: gray;">Date: {latest['Date'].strftime('%Y-%m-%d')}</div>
            </div>
            """, unsafe_allow_html=True)

        # --- ROW 3: LONGITUDINAL TRENDS ---
        st.subheader("📈 Longitudinal Tracking")
        tab1, tab2 = st.tabs(["Strength Trends", "Force Plate Trends"])
        
        with tab1:
            fig_trend = px.line(pt_data, x='Date', y=['KE_LSI', 'KF_LSI', 'ACL_RSI'], markers=True)
            fig_trend.add_hline(y=90, line_dash="dash", line_color="green", annotation_text="Target")
            st.plotly_chart(fig_trend, use_container_width=True)
            
    else:
        st.info("No data found for this athlete. Go to 'New Assessment' to add data.")

# --- NEW ASSESSMENT PAGE ---
elif page == "New Assessment":
    st.markdown(f"## New Assessment for {selected_name} (MRN: {mrn})")
    
    with st.form("new_assess_form"):
        # Top Metadata
        c1, c2, c3 = st.columns(3)
        assess_date = c1.date_input("Date", datetime.today())
        bw = c2.number_input("Body Weight (lbs)", value=150.0)
        ma = c3.number_input("Moment Arm (m)", value=0.36)
        
        # Clinical Measures
        with st.expander("1. Subjective & ROM", expanded=True):
            col_a, col_b = st.columns(2)
            acl_rsi = col_a.slider("ACL-RSI Score", 0, 100, 50)
            lefs = col_b.slider("LEFS Score", 0, 80, 40)
            
        with st.expander("2. Strength (HHD)", expanded=True):
            s1, s2 = st.columns(2)
            ke_un_avg = s1.number_input("Uninvolved Quad Force (Avg lbs)", 0.0)
            ke_in_avg = s2.number_input("Involved Quad Force (Avg lbs)", 0.0)
            
            kf_un_avg = s1.number_input("Uninvolved Hamstring Force (Avg lbs)", 0.0)
            kf_in_avg = s2.number_input("Involved Hamstring Force (Avg lbs)", 0.0)

        with st.expander("3. VALD / Force Decks", expanded=False):
            v1, v2 = st.columns(2)
            squat_asym = v1.number_input("Squat Asymmetry (%)", 0.0)
            cmj_asym = v2.number_input("CMJ Landing Asymmetry (%)", 0.0)
            
        # Clinician Notes Section
        st.markdown("### 📝 Assessment Summary & Plan")
        clinician_notes = st.text_area("Enter key findings, plan for next phase, and clearance notes here...", height=100)

        # Submit
        if st.form_submit_button("Save Assessment Record"):
            # Calcs
            ke_lsi = calculate_lsi(ke_in_avg, ke_un_avg)
            kf_lsi = calculate_lsi(kf_in_avg, kf_un_avg)
            ke_ttbw = calculate_ttbw(ke_in_avg, bw, ma)
            
            new_row = {
                'MRN': mrn, 'Date': pd.to_datetime(assess_date), 'Weeks_Post_Op': 12,
                'ACL_RSI': acl_rsi, 'LEFS': lefs,
                'KE_LSI': ke_lsi, 'KF_LSI': kf_lsi, 'KE_TTBW_Inv': ke_ttbw,
                'Squat_Asym': squat_asym, 'CMJ_Asym': cmj_asym,
                'Notes': clinician_notes
            }
            
            st.session_state.assessments = pd.concat([st.session_state.assessments, pd.DataFrame([new_row])], ignore_index=True)
            st.success("✅ Assessment Saved Successfully!")

# --- DATABASE PAGE ---
elif page == "Database":
    st.header("🗄️ Full Clinic Database")
    st.dataframe(st.session_state.assessments)
