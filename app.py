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
    .status-warn { color: #f59e0b; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def safe_float(val):
    """Safely converts value to float, returns 0.0 if nan or error."""
    try:
        if pd.isna(val) or val == "": return 0.0
        return float(val)
    except:
        return 0.0

def calc_avg(trials):
    valid = [safe_float(t) for t in trials if safe_float(t) > 0]
    return np.mean(valid) if valid else 0.0

def calc_lsi(involved, uninvolved, metric_type='standard'):
    inv = safe_float(involved)
    uninv = safe_float(uninvolved)
    if uninv == 0 or inv == 0: return 0.0
    
    if metric_type == 'timed':
        return (uninv / inv) * 100
    else:
        return (inv / uninv) * 100

# --- DATA SETUP ---
# Initialize columns explicitely to prevent KeyErrors
COLUMNS = [
    'MRN', 'Date', 'Weeks_Post_Op', 'ACL_RSI', 'LEFS', 'Heel_Pop',
    'KE_LSI', 'KF_LSI', 'RFD_LSI', 'HipAbd_LSI', 'KE_Torque_Inv',
    'Hop_Single_LSI', 'Hop_Triple_LSI', 'Hop_Cross_LSI', 'Hop_6m_LSI',
    'Y_Bal_Diff', 'Notes'
]

if 'patients' not in st.session_state:
    st.session_state.patients = pd.DataFrame({
        'MRN': ['#000000', '#123456'],
        'Name': ['Rose, Derrick', 'Doe, Jane'],
        'Surgery_Date': [datetime(2024, 10, 17), datetime(2024, 1, 15)]
    })

if 'assessments' not in st.session_state:
    st.session_state.assessments = pd.DataFrame(columns=COLUMNS)

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
        
        # Safe extraction of values
        acl_rsi = safe_float(latest.get('ACL_RSI', 0))
        ke_lsi = safe_float(latest.get('KE_LSI', 0))
        kf_lsi = safe_float(latest.get('KF_LSI', 0))
        h_single = safe_float(latest.get('Hop_Single_LSI', 0))
        h_triple = safe_float(latest.get('Hop_Triple_LSI', 0))
        h_6m = safe_float(latest.get('Hop_6m_LSI', 0))
        
        # Status Logic
        lsi_avg = (ke_lsi + h_single + h_triple) / 3 if (h_single > 0) else ke_lsi
        
        status_color = "status-fail"
        status_text = "Early Phase"
        if lsi_avg > 90 and acl_rsi > 90:
            status_color = "status-pass"
            status_text = "RTS CLEARED"
        elif lsi_avg > 80:
            status_color = "status-warn"
            status_text = "Power Phase"
        elif lsi_avg > 0:
             status_text = "Strength Phase"

        # ROW 1
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color: gray;">CURRENT STATUS</div>
                <div class="{status_color}" style="font-size: 2rem;">{status_text}</div>
                <div>Heel Pop: <b>{latest.get('Heel_Pop', 'N/A')}</b> | Weeks Post-Op: <b>{latest.get('Weeks_Post_Op', 'N/A')}</b></div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.metric("ACL-RSI", f"{int(acl_rsi)}", delta=f"{int(acl_rsi)-90}")
        with c3:
            st.metric("Quad LSI", f"{int(ke_lsi)}%", delta=f"{int(ke_lsi)-90}%")

        # ROW 2: RADAR & NOTES
        col_main, col_summ = st.columns([2, 1])
        with col_main:
            categories = ['ACL-RSI', 'Quad LSI', 'Hams LSI', 'Single Hop', 'Triple Hop', '6m Timed']
            values = [acl_rsi, ke_lsi, kf_lsi, h_single, h_triple, h_6m]
            
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

        # ROW 3: TABLES
        with st.expander("📊 View Detailed Measurements (Latest Session)", expanded=True):
            st.markdown("**Strength & Torque**")
            d1 = {
                "Metric": ["Quad Strength (LSI)", "Hamstring Strength (LSI)", "Quad Torque/BW (Inv)", "Quad RFD (LSI)", "Hip Abd (LSI)"],
                "Value": [
                    f"{ke_lsi:.1f}%", f"{kf_lsi:.1f}%", 
                    f"{safe_float(latest.get('KE_Torque_Inv',0)):.2f}", 
                    f"{safe_float(latest.get('RFD_LSI',0)):.1f}%", 
                    f"{safe_float(latest.get('HipAbd_LSI',0)):.1f}%"
                ]
            }
            st.table(pd.DataFrame(d1))
            
            st.markdown("**Functional Testing**")
            y_diff = safe_float(latest.get('Y_Bal_Diff', 0))
            y_pass = "✅ Pass" if y_diff < 4 else "❌ Fail"
            
            d2 = {
                "Metric": ["Y-Balance Diff", "Single Hop LSI", "Triple Hop LSI", "Crossover Hop LSI", "6m Timed LSI"],
                "Value": [f"{y_diff:.1f} cm ({y_pass})", f"{h_single:.1f}%", f"{h_triple:.1f}%", f"{safe_float(latest.get('Hop_Cross_LSI',0)):.1f}%", f"{h_6m:.1f}%"]
            }
            st.table(pd.DataFrame(d2))

    else:
        st.info("No data found. Please go to 'New Assessment' to add data.")

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
            st.caption("Uninvolved Side")
            rom_ext_un = st.number_input("Ext Uninvolved", value=0)
            rom_flex_un = st.number_input("Flex Uninvolved", value=135)
            girth_un = st.number_input("Quad Girth Uninvolved (cm)", value=0.0)
        with col_r2:
            st.caption("Involved Side")
            rom_ext_in = st.number_input("Ext Involved", value=0)
            rom_flex_in = st.number_input("Flex Involved", value=130)
            girth_in = st.number_input("Quad Girth Involved (cm)", value=0.0)

        # 3. STRENGTH (HHD)
        st.markdown('<div class="section-header">2. Strength & Dynamometry</div>', unsafe_allow_html=True)
        
        st.markdown("**Hip Abduction**")
        h1, h2 = st.columns(2)
        hip_un = h1.number_input("Hip Abd Uninvolved (lbs)", 0.0)
        hip_in = h2.number_input("Hip Abd Involved (lbs)", 0.0)
        
        st.markdown("**Knee Extension**")
        k1, k2 = st.columns(2)
        ke_un = k1.number_input("KE Uninvolved (lbs)", 0.0)
        ke_in = k2.number_input("KE Involved (lbs)", 0.0)
        ke_trq_un = k1.number_input("KE Torque/BW Uninvolved", 0.0)
        ke_trq_in = k2.number_input("KE Torque/BW Involved", 0.0)
        ke_rfd_un = k1.number_input("KE RFD Uninvolved", 0.0)
        ke_rfd_in = k2.number_input("KE RFD Involved", 0.0)
        
        st.markdown("**Knee Flexion**")
        kf1, kf2 = st.columns(2)
        kf_un = kf1.number_input("KF Uninvolved (lbs)", 0.0)
        kf_in = kf2.number_input("KF Involved (lbs)", 0.0)

        # 4. FUNCTIONAL / HOPS
        st.markdown('<div class="section-header">3. Functional & Hop Testing</div>', unsafe_allow_html=True)
        
        st.markdown("**Y-Balance (Anterior)**")
        y1, y2 = st.columns(2)
        y_un_trials = [y1.number_input(f"Y-Bal Uninv {i+1}", 0.0, key=f"y_u_{i}") for i in range(3)]
        y_in_trials = [y2.number_input(f"Y-Bal Inv {i+1}", 0.0, key=f"y_i_{i}") for i in range(3)]
        
        def hop_inputs(label, key_prefix):
            st.markdown(f"**{label}**")
            hc1, hc2 = st.columns(2)
            u = [hc1.number_input(f"{label} Uninv {i+1}", 0.0, key=f"{key_prefix}_u_{i}") for i in range(3)]
            i = [hc2.number_input(f"{label} Inv {i+1}", 0.0, key=f"{key_prefix}_i_{i}") for i in range(3)]
            return u, i

        hop_sl_u, hop_sl_i = hop_inputs("Single Hop (cm)", "sl")
        hop_trip_u, hop_trip_i = hop_inputs("Triple Hop (cm)", "trip")
        hop_cross_u, hop_cross_i = hop_inputs("Crossover Hop (cm)", "cross")
        hop_6m_u, hop_6m_i = hop_inputs("6m Timed Hop (sec)", "6m")

        # 5. VALD
        st.markdown('<div class="section-header">4. VALD / ForceDecks</div>', unsafe_allow_html=True)
        st.caption("For Asymmetry, enter the % and direction.")
        
        def asym_input(label, key):
            ac1, ac2 = st.columns([2, 1])
            val = ac1.number_input(f"{label}", 0.0, key=key)
            direction = ac2.selectbox("Favors?", ["Sym", "Uninvolved", "Involved"], key=f"{key}_dir")
            return val, direction

        st.markdown("--- *Squat Assessment*")
        sq_peak_asym, sq_peak_dir = asym_input("Peak Force Asym (%)", "sq_peak")
        sq_ecc_asym, sq_ecc_dir = asym_input("Eccentric Peak Asym (%)", "sq_ecc")
        sq_conc_asym, sq_conc_dir = asym_input("Concentric Peak Asym (%)", "sq_conc")
        
        st.markdown("--- *Countermovement Jump (CMJ)*")
        cmj_h = st.number_input("CMJ Jump Height (cm)", 0.0)
        cmj_take_asym, cmj_take_dir = asym_input("Takeoff Peak Force Asym", "cmj_take")
        cmj_land_asym, cmj_land_dir = asym_input("Peak Landing Force Asym", "cmj_land")
        cmj_imp_asym, cmj_imp_dir = asym_input("Concentric Impulse Asym", "cmj_imp")
        
        st.markdown("--- *Drop Jump*")
        dj_h = st.number_input("DJ Height (cm)", 0.0)
        dj_rsi = st.number_input("DJ RSI", 0.0)
        dj_z_asym, dj_z_dir = asym_input("Force @ 0 Vel Asym", "dj_z")
        dj_land_asym, dj_land_dir = asym_input("Peak Landing Force Asym", "dj_land")

        st.markdown("--- *Single Leg Vertical Jump*")
        slv1, slv2 = st.columns(2)
        slv_un_trials = [slv1.number_input(f"SL Vert Uninv {i+1}", 0.0, key=f"slv_u_{i}") for i in range(3)]
        slv_in_trials = [slv2.number_input(f"SL Vert Inv {i+1}", 0.0, key=f"slv_i_{i}") for i in range(3)]

        st.markdown("--- *SL Drop Jump*")
        sldj1, sldj2 = st.columns(2)
        sldj_h_u = sldj1.number_input("SL DJ Height Uninv (Avg)", 0.0)
        sldj_h_i = sldj2.number_input("SL DJ Height Inv (Avg)", 0.0)
        sldj_rsi_u = sldj1.number_input("SL DJ RSI Uninv (Avg)", 0.0)
        sldj_rsi_i = sldj2.number_input("SL DJ RSI Inv (Avg)", 0.0)
        sldj_ecc_u = sldj1.number_input("SL DJ Ecc Imp Uninv (Avg)", 0.0)
        sldj_ecc_i = sldj2.number_input("SL DJ Ecc Imp Inv (Avg)", 0.0)
        sldj_conc_u = sldj1.number_input("SL DJ Conc Imp Uninv (Avg)", 0.0)
        sldj_conc_i = sldj2.number_input("SL DJ Conc Imp Inv (Avg)", 0.0)

        # 6. CLINICIAN NOTES
        st.markdown('<div class="section-header">5. Assessment Plan</div>', unsafe_allow_html=True)
        notes = st.text_area("Clinician Summary & Clearance Plan", height=100)

        # SUBMIT
        if st.form_submit_button("💾 Save Full Assessment"):
            # Calcs
            h_sl_u_avg, h_sl_i_avg = calc_avg(hop_sl_u), calc_avg(hop_sl_i)
            h_tr_u_avg, h_tr_i_avg = calc_avg(hop_trip_u), calc_avg(hop_trip_i)
            h_cr_u_avg, h_cr_i_avg = calc_avg(hop_cross_u), calc_avg(hop_cross_i)
            h_6m_u_avg, h_6m_i_avg = calc_avg(hop_6m_u), calc_avg(hop_6m_i)
            slv_u_avg, slv_i_avg = calc_avg(slv_un_trials), calc_avg(slv_in_trials)
            
            y_u_avg, y_i_avg = calc_avg(y_un_trials), calc_avg(y_in_trials)
            y_diff = abs(y_u_avg - y_i_avg)

            record = {
                'MRN': mrn, 'Date': pd.to_datetime(assess_date), 'Weeks_Post_Op': 12,
                'ACL_RSI': acl_rsi, 'LEFS': lefs, 'Heel_Pop': heel_pop,
                'ROM_Ext_Un': rom_ext_un, 'ROM_Flex_Un': rom_flex_un,
                'ROM_Ext_In': rom_ext_in, 'ROM_Flex_In': rom_flex_in,
                
                'HipAbd_LSI': calc_lsi(hip_in, hip_un),
                'KE_LSI': calc_lsi(ke_in, ke_un),
                'KF_LSI': calc_lsi(kf_in, kf_un),
                'RFD_LSI': calc_lsi(ke_rfd_in, ke_rfd_un),
                'KE_Torque_Inv': ke_trq_in,
                
                'Hop_Single_LSI': calc_lsi(h_sl_i_avg, h_sl_u_avg),
                'Hop_Triple_LSI': calc_lsi(h_tr_i_avg, h_tr_u_avg),
                'Hop_Cross_LSI': calc_lsi(h_cr_i_avg, h_cr_u_avg),
                'Hop_6m_LSI': calc_lsi(h_6m_i_avg, h_6m_u_avg, 'timed'),
                
                'Y_Bal_Diff': y_diff,
                'SLV_LSI': calc_lsi(slv_i_avg, slv_u_avg),
                'SLDJ_Height_LSI': calc_lsi(sldj_h_i, sldj_h_u),
                'SLDJ_RSI_LSI': calc_lsi(sldj_rsi_i, sldj_rsi_u),
                
                'Notes': notes
            }
            
            # Combine safely
            new_df = pd.DataFrame([record])
            st.session_state.assessments = pd.concat([st.session_state.assessments, new_df], ignore_index=True)
            st.success("✅ Assessment Saved!")

# --- DATABASE PAGE ---
elif page == "Database":
    st.header("🗄️ Database View")
    st.dataframe(st.session_state.assessments)
    csv = st.session_state.assessments.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "acl_data.csv", "text/csv")
