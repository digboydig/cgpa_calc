import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="🎓 CGPA Calculator", layout="centered")

# -------------------------
# Helper functions
# -------------------------
def grade_point_and_letter_absolute(total):
    """Return (gp, letter, cutoff) for absolute mapping."""
    if total >= 90: return 10, "A", 90
    elif total >= 80: return 9, "A-", 80
    elif total >= 70: return 8, "B", 70
    elif total >= 60: return 7, "B-", 60
    elif total >= 50: return 6, "C", 50
    elif total >= 45: return 5, "C-", 45
    elif total >= 35: return 4, "D", 35
    else: return 2, "E", 0

def total_percent_from_components(m1, m2, m3):
    m1 = 0.0 if m1 is None else float(m1)
    m2 = 0.0 if m2 is None else float(m2)
    m3 = 0.0 if m3 is None else float(m3)
    return m1 + m2 + m3

# -------------------------
# UI - Sidebar configuration
# -------------------------
st.title("🎓 CGPA Calculator")
st.caption("Weighted CGPA calculation: (Σ Unit * GP) / Σ Units")

with st.sidebar:
    st.header("Configuration")
    num_courses = st.number_input("Number of courses", min_value=1, max_value=12, value=4, step=1)

    course_names = []
    for i in range(num_courses):
        nm = st.text_input(f"Course {i+1} name", value=f"Course {i+1}", key=f"name_{i}")
        course_names.append(nm if nm.strip() else f"Course {i+1}")

    st.markdown("---")
    st.markdown("Weights")
    same_weights = st.checkbox("Use same weights for all courses?", value=True)
    if same_weights:
        gw1 = st.number_input("EC1 weight (%)", min_value=0.0, max_value=100.0, value=30.0)
        gw2 = st.number_input("EC2 weight (%)", min_value=0.0, max_value=100.0, value=30.0)
        gw3 = st.number_input("EC3 weight (%)", min_value=0.0, max_value=100.0, value=40.0)
    else:
        gw1 = gw2 = gw3 = None

# -------------------------
# Main input area
# -------------------------
st.subheader("Enter course details and marks")

courses_data = []
for i, cname in enumerate(course_names):
    with st.expander(f"📚 {cname}", expanded=True):
        col_u, col_w = st.columns([1, 2])
        with col_u:
            # Credit Units selection
            units = st.selectbox(f"Units for {cname}", options=[4, 5], key=f"units_{i}")
        
        if same_weights:
            w1, w2, w3 = gw1, gw2, gw3
            with col_w: st.caption(f"Weights: EC1={w1}%, EC2={w2}%, EC3={w3}%")
        else:
            wcols = st.columns(3)
            w1 = wcols[0].number_input(f"EC1 %", 0.0, 100.0, 30.0, key=f"w1_{i}")
            w2 = wcols[1].number_input(f"EC2 %", 0.0, 100.0, 30.0, key=f"w2_{i}")
            w3 = wcols[2].number_input(f"EC3 %", 0.0, 100.0, 40.0, key=f"w3_{i}")

        pcols = st.columns(3)
        with pcols[0]:
            p1 = st.checkbox("EC1 pending", key=f"p1_{i}")
            ec1 = None if p1 else st.number_input(f"EC1 (0-{w1})", 0.0, float(w1), key=f"ec1_{i}")
        with pcols[1]:
            p2 = st.checkbox("EC2 pending", key=f"p2_{i}")
            ec2 = None if p2 else st.number_input(f"EC2 (0-{w2})", 0.0, float(w2), key=f"ec2_{i}")
        with pcols[2]:
            p3 = st.checkbox("EC3 pending", key=f"p3_{i}")
            ec3 = None if p3 else st.number_input(f"EC3 (0-{w3})", 0.0, float(w3), key=f"ec3_{i}")
            
        courses_data.append({"name": cname, "units": units, "ec1": ec1, "ec2": ec2, "ec3": ec3, "w1": w1, "w2": w2, "w3": w3})

st.markdown("---")
if st.button("Compute Results", type="primary"):
    rows = []
    total_credit_points = 0.0
    total_units_sum = 0.0

    for c in courses_data:
        total = total_percent_from_components(c["ec1"], c["ec2"], c["ec3"])
        gp, letter, _ = grade_point_and_letter_absolute(total)
        # Calculate Credit Points: Units * Grade Point
        credit_pts = gp * c["units"]
        
        rows.append({
            "Course": c["name"],
            "Units": c["units"],
            "Grade Point": gp,
            "Grade": letter,
            "Credit Points": credit_pts,
            "Total(%)": f"{total:.2f}"
        })
        
        total_credit_points += credit_pts
        total_units_sum += c["units"]

    res_df = pd.DataFrame(rows)
    
    # 1. Summary Table
    st.subheader("📊 Credit Points Summary")
    st.table(res_df[["Course", "Units", "Grade Point", "Credit Points"]])
    
    # 2. Final CGPA Calculation
    final_cgpa = total_credit_points / total_units_sum if total_units_sum > 0 else 0
    cgpa_color = "green" if final_cgpa >= 5.5 else "red"
    
    st.markdown(f"""
        <div style="background-color:#f9f9f9; padding:20px; border-radius:10px; border-left: 5px solid {cgpa_color};">
            <h2 style="margin:0;">Overall CGPA: <span style="color:{cgpa_color};">{final_cgpa:.2f}</span></h2>
            <p style="margin:5px 0 0 0;">Total Credit Points: <b>{total_credit_points}</b> | Total Units: <b>{int(total_units_sum)}</b></p>
        </div>
    """, unsafe_allow_html=True)

    # 3. Pass/Fail Status
    if final_cgpa < 5.5:
        st.warning("⚠️ Note: An overall CGPA of 5.5 is required to clear the semester.")

if st.sidebar.button("Reset Calculator"):
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

st.markdown("---")
st.caption("Formula: CGPA = Total Credit Points / Total Units")
