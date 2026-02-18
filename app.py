import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="MOR ACL Dashboard", layout="wide", page_icon="🏥")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: bold;
        color: #333;
        margin-top: 10px;
        margin-bottom: 10px;
        border-bottom: 2px solid #10b981;
        padding-bottom: 5px;
    }
    .status-pass { color: #10b981; font-weight: bold; }
    .status-fail { color: #ef4444; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def calc_avg(trials):
    # Filter out 0s or empty values
    valid = [t for t in trials if t > 0]
    return np.mean(valid) if valid else 0.0

def calc_lsi(involved, uninvolved, metric_type='standard'):
    if uninvolved == 0 or pd.isna(uninvolved) or involved == 0: return 0.0
    
    if metric_type == 'timed':
        # For time, Lower is better. If Inv is slower (higher), LSI should be < 100
        return (uninvolved / involved) * 100
    else:
        # Standard: Higher is better
        return (involved / uninvolved) * 100

def get_status_color(value, threshold, logic='>'):
    if logic == '>' and value >= threshold: return "green"
    if logic == '<' and value <= threshold: return "green"
    return "red"

# --- DATA SETUP ---
if 'patients' not in st.session_state:
    st.session_state.patients = pd.DataFrame({
        'MRN': ['#000000', '#123456'],
        'Name': ['Rose, Derrick', 'Doe, Jane'],
        'Surgery_Date': [datetime(2024, 10, 17), datetime(2024, 1, 15)]
    })

if 'assessments' not in st.session_state:
    # Initialize with an empty dataframe or demo data
    st.session_state.assessments = pd.DataFrame(columns=['MRN', 'Date', 'Weeks_Post_Op'])

# --- SIDEBAR ---
st.sidebar.title("Midwest Ortho RTS")
page = st.sidebar.radio("Navigation", ["Athlete Dashboard", "New Assessment", "Database"])

patient_names = st.session_state.patients['Name'].tolist()
selected_name = st.sidebar.selectbox("Select Athlete", patient_names)
selected_patient = st.session_state.patients[st.session_state.patients['Name'] == selected_name].iloc[0]
mrn = selected_patient['MRN']

# --- DASHBOARD PAGE ---
if page == "Athlete Dashboard":
    st.markdown(f"## 👤 {selected_name} <span style='color:gray; font-size:0.6em'>(MRN: {mrn})</span>", unsafe_allow_html=True)
    
    pt_data = st.session_state.assessments[st.session_state.assessments['MRN'] == mrn].sort_values(by='Date')
    
    if not pt_data.empty:
        latest = pt_data.iloc[-1]
        
        # --- TOP LEVEL STATUS ---
        # Simple Logic for Demo: Check 3 key metrics
        lsi_avg = (latest.get('KE_LSI', 0) + latest.get('Hop_Single_LSI', 0) + latest.get('Hop_Triple_LSI', 0)) / 3
        rsi = latest.get('ACL_RSI', 0)
        
        status_color = "status-fail"
        status_text = "Early / Strength Phase"
        if lsi_avg > 90 and rsi > 90:
            status_color = "status-pass"
            status_text = "RTS CLEARED"
        elif lsi_avg > 80:
            status_color = "status-warn"
            status_text = "Power Phase"

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color: gray;">CURRENT STATUS</div>
                <div class="{status_color}" style="font-size: 2rem;">{status_text}</div>
                <div>Heel Pop: <b>{latest.get('Heel_Pop', 'N/A')}</b> | Weeks Post-Op: <b>{latest.get('Weeks_Post_Op', 0)}</b></div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.metric("ACL-RSI", f"{int(latest.get('ACL_RSI', 0))}", delta=f"{int(latest.get('ACL_RSI', 0))-90}")
        with c3:
            st.metric("Quad LSI", f"{int(latest.get('KE_LSI', 0))}%", delta=f"{int(latest.get('KE_LSI', 0))-90}%")

        # --- RADAR CHART (Strength & Hops) ---
        col_main, col_summ = st.columns([2, 1])
        with col_main:
            categories = ['ACL-RSI', 'Quad LSI', 'Hams LSI', 'Single Hop LSI', 'Triple Hop LSI', '6m Timed LSI']
            values = [
                latest.get('ACL_RSI', 0), latest.get('KE_LSI', 0), latest.get('KF_LSI', 0),
                latest.get('Hop_Single_LSI', 0), latest.get('Hop_Triple_LSI', 0), latest.get('Hop_6m_LSI', 0)
            ]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name='Current'))
            fig.add_trace(go.Scatterpolar(r=[90]*6, theta=categories, name='Target', line_color='green', line_dash='dot'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 120])), height=350, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
        with col_summ:
             st.markdown(f"""
            <div class="metric-card" style="height: 350px; overflow-y: auto;">
                <div style="font-weight: bold; margin-bottom: 5px;">📝 Clinician Summary</div>
                <div style="background-color: #f9fafb; padding: 10px; border-radius: 5px; font-size: 0.9rem;">
                    {latest.get('Notes', 'No notes entered.')}
                </div>
            </div>""", unsafe_allow_html=True)

        # --- DETAILED DATA TABLES ---
        with st.expander("📊 View Detailed Measurements (Latest Session)", expanded=True):
            # Strength
            st.markdown("**Strength & Torque**")
            d1 = {
                "Metric": ["Quad Strength (LSI)", "Hamstring Strength (LSI)", "Quad Torque/BW (Inv)", "Quad RFD (LSI)", "Hip Abd (LSI)"],
                "Value": [
                    f"{latest.get('KE_LSI',0):.1f}%", f"{latest.get('KF_LSI',0):.1f}%", 
                    f"{latest.get('KE_Torque_Inv',0):.2f}", f"{latest.get('RFD_LSI',0):.1f}%", f"{latest.get('HipAbd_LSI',0):.1f}%"
                ]
            }
            st.table(pd.DataFrame(d1))
            
            # Hops & Balance
            st.markdown("**Functional Testing**")
            y_diff = latest.get('Y_Bal_Diff', 0)
            y_pass = "✅ Pass" if y_diff < 4 else "❌ Fail"
            
            d2 = {
                "Metric": ["Y-Balance Diff", "Single Hop LSI", "Triple Hop LSI", "Crossover Hop LSI", "6m Timed LSI"],
                "Value": [f"{y_diff:.1f} cm ({y_pass})", f"{latest.get('Hop_Single_LSI',0):.1f}%", f"{latest.get('Hop_Triple_LSI',0):.1f}%", f"{latest.get('Hop_Cross_LSI',0):.1f}%", f"{latest.get('Hop_6m_LSI',0):.1f}%"]
            }
            st.table(pd.DataFrame(d2))

    else:
        st.info("No assessments found. Please create one.")

# --- NEW ASSESSMENT PAGE ---
elif page == "New Assessment":
    st.markdown(f"## New Assessment: {selected_name}")
    
    with st.form("full_assessment_form"):
        # 1. METADATA
        c1, c2, c3 = st.columns(3)
        assess_date = c1.date_input("Date", datetime.today())
        bw = c2.number_input("Body Weight (kg)", value=70.0)
        
        # 2. SUBJECTIVE
        st.markdown('<div class="section-header">1. Subjective & Physical</div>', unsafe_allow_html=True)
        col_s1, col_s2, col_s3 = st.columns(3)
        acl_rsi = col_s1.number_input("ACL-RSI (0-100)", 0, 100, 50)
        lefs = col_s2.number_input("LEFS (0-80)", 0, 80, 40)
        heel_pop = col_s3.selectbox("Heel Pop?", ["Yes", "No"])
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.caption("Uninvolved")
            rom_ext_un = st.number_input("Ext Uninvolved", value=0)
            rom_flex_un = st.number_input("Flex Uninvolved", value=135)
            girth_un = st.number_input("Quad Girth Uninvolved (cm)", value=0.0)
        with col_r2:
            st.caption("Involved")
            rom_ext_in = st.number_input("Ext Involved", value=0)
            rom_flex_in = st.number_input("Flex Involved", value=130)
            girth_in = st.number_input("Quad Girth Involved (cm)", value=0.0)

        # 3. STRENGTH (HHD)
        st.markdown('<div class="section-header">2. Strength & Dynamometry</div>', unsafe_allow_html=True)
        
        # Hip Abd
        st.markdown("**Hip Abduction**")
