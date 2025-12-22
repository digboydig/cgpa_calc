import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="🎓 CGPA Calculator", layout="centered")

# --- Custom CSS for Red Borders around Course Sections ---
st.markdown("""
    <style>
    .course-box {
        border: 2px solid #ff4b4b;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 25px;
        background-color: #fffafb;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------
# Helper functions
# -------------------------
def grade_point_and_letter_absolute(total):
    """Return (gp, letter) for absolute mapping."""
    if total >= 90: return 10, "A"
    elif total >= 80: return 9, "A-"
    elif total >= 70: return 8, "B"
    elif total >= 60: return 7, "B-"
    elif total >= 50: return 6, "C"
    elif total >= 45: return 5, "C-"
    elif total >= 35: return 4, "D"
    else: return 2, "E"

def total_percent_from_components(m1, m2, m3):
    return (0.0 if m1 is None else float(m1)) + (0.0 if m2 is None else float(m2)) + (0.0 if m3 is None else float(m3))

# -------------------------
# UI - Sidebar configuration
# -------------------------
st.title("🎓 CGPA Calculator")
st.caption("Calculate weighted CGPA with credit units and per-course normalization.")

with st.sidebar:
    st.header("Configuration")
    num_courses = st.number_input("Number of courses", min_value=1, max_value=12, value=4, step=1)
    
    course_names = []
    for i in range(num_courses):
        nm = st.text_input(f"Course {i+1} name", value=f"Course {i+1}", key=f"name_{i}")
        course_names.append(nm if nm.strip() else f"Course {i+1}")

    st.markdown("---")
    calc_method = st.radio("Calculation Method", ["Direct Average", "Normalise from Class Highest"])
    
    st.markdown("---")
    st.markdown("Weights")
    same_weights = st.checkbox("Use same weights for all courses?", value=True)
    if same_weights:
        gw1 = st.number_input("EC1 weight (%)", 0.0, 100.0, 30.0)
        gw2 = st.number_input("EC2 weight (%)", 0.0, 100.0, 30.0)
        gw3 = st.number_input("EC3 weight (%)", 0.0, 100.0, 40.0)
        if abs((gw1 + gw2 + gw3) - 100.0) > 1e-6:
            st.error("Global weights must sum to 100.")

# -------------------------
# Main input area
# -------------------------
st.subheader("Enter marks and units per course")

courses_data = []
for i, cname in enumerate(course_names):
    # Opening the red box div
    st.markdown(f'<div class="course-box">', unsafe_allow_html=True)
    st.subheader(f"📚 {cname}")
    
    col_u, col_h = st.columns([1, 1])
    with col_u:
        units = st.selectbox(f"Units for {cname}", options=[4, 5], key=f"units_{i}")
    with col_h:
        h_course = st.number_input(f"Class Highest for {cname}", 0.1, 100.0, 100.0, key=f"h_{i}") if calc_method == "Normalise from Class Highest" else 100.0
    
    if same_weights:
        w1, w2, w3 = gw1, gw2, gw3
        st.caption(f"Weights: EC1={w1}%, EC2={w2}%, EC3={w3}%")
    else:
        wcols = st.columns(3)
        w1 = wcols[0].number_input(f"EC1 weight %", 0.0, 100.0, 30.0, key=f"w1_{i}")
        w2 = wcols[1].number_input(f"EC2 weight %", 0.0, 100.0, 30.0, key=f"w2_{i}")
        w3 = wcols[2].number_input(f"EC3 weight %", 0.0, 100.0, 40.0, key=f"w3_{i}")
        if abs((w1 + w2 + w3) - 100.0) > 1e-6:
            st.warning(f"Weights for {cname} must sum to 100.")

    pcols = st.columns(3)
    with pcols[0]:
        p1 = st.checkbox(f"EC1 pending", key=f"p1_{i}")
        ec1 = None if p1 else st.number_input(f"EC1 (0-{w1})", 0.0, float(w1), key=f"ec1_{i}")
    with pcols[1]:
        p2 = st.checkbox(f"EC2 pending", key=f"p2_{i}")
        ec2 = None if p2 else st.number_input(f"EC2 (0-{w2})", 0.0, float(w2), key=f"ec2_{i}")
    with pcols[2]:
        p3 = st.checkbox(f"EC3 pending", key=f"p3_{i}")
        ec3 = None if p3 else st.number_input(f"EC3 (0-{w3})", 0.0, float(w3), key=f"ec3_{i}")
    
    # Closing the red box div
    st.markdown('</div>', unsafe_allow_html=True)
    courses_data.append({"name": cname, "units": units, "ec1": ec1, "ec2": ec2, "ec3": ec3, "w1": w1, "w2": w2, "w3": w3, "h_course": h_course})

st.markdown("---")
col_calc, col_reset, _ = st.columns([1,1,1])

if col_calc.button("Compute Results"):
    bad = False
    for c in courses_data:
        if abs((c["w1"] + c["w2"] + c["w3"]) - 100.0) > 1e-6:
            st.error(f"Weights for '{c['name']}' do not sum to 100.")
            bad = True
    if bad: st.stop()

    rows = []
    total_weighted_gp = 0.0
    total_units_sum = 0.0

    for c in courses_data:
        raw_total = total_percent_from_components(c["ec1"], c["ec2"], c["ec3"])
        final_total = (raw_total / c["h_course"]) * 100 if calc_method == "Normalise from Class Highest" else raw_total
        
        gp, letter = grade_point_and_letter_absolute(final_total)
        credit_pts = gp * c["units"]
        total_weighted_gp += credit_pts
        total_units_sum += c["units"]

        rows.append({
            "Course": c["name"], "Units": c["units"], "GP": gp, "Grade": letter, 
            "Credit Points": credit_pts, "Total(%)": f"{final_total:.2f}", "PassBool": (gp >= 4.5)
        })

    res_df = pd.DataFrame(rows)
    st.session_state["last_results_df"] = res_df
    st.session_state["courses_data"] = courses_data
    st.session_state["calc_method"] = calc_method

    st.subheader("📊 Credit Points Summary")
    st.table(res_df[["Course", "Units", "GP", "Credit Points"]])

    # Results table styling
    st.subheader("Full Results")
    html = "<table style='border-collapse:collapse;width:100%;font-size:14px'>"
    html += "<tr style='background:#f7f7f7;font-weight:bold;text-align:left;'><th>Course</th><th>Units</th><th>Total(%)</th><th>GP</th><th>Grade</th><th>Pass</th></tr>"
    for _, r in res_df.iterrows():
        color = "green" if r["PassBool"] else "red"
        pass_text = f"<span style='color:{color};font-weight:600'>{'Pass' if r['PassBool'] else 'Fail'}</span>"
        html += f"<tr><td>{r['Course']}</td><td style='text-align:center'>{r['Units']}</td><td>{r['Total(%)']}</td><td>{r['GP']}</td><td>{r['Grade']}</td><td style='text-align:center'>{pass_text}</td></tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    final_cgpa = total_weighted_gp / total_units_sum if total_units_sum > 0 else 0
    cgpa_color = "green" if final_cgpa >= 5.5 else "red"
    st.markdown(f"<h4>Weighted CGPA: <span style='color:{cgpa_color}'>{final_cgpa:.2f}</span></h4>", unsafe_allow_html=True)

if col_reset.button("Reset"):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

# -------------------------
# Projection area
# -------------------------
st.markdown("---")
st.header("Projection — Required Marks")

if "last_results_df" in st.session_state:
    df_p = st.session_state["last_results_df"]
    sel_name = st.selectbox("Pick a course for projection", options=df_p["Course"].tolist())
    target_gp = st.selectbox("Target GP", options=[10,9,8,7,6,5,4,2], index=2)
    
    idx = df_p.index[df_p["Course"] == sel_name][0]
    c = st.session_state["courses_data"][idx]
    
    gp_to_total = {10:90, 9:80, 8:70, 7:60, 6:50, 5:45, 4:35, 2:0}
    target_norm = gp_to_total[target_gp]
    target_raw_total = (target_norm / 100) * c["h_course"]
    
    current_raw = (c["ec1"] or 0) + (c["ec2"] or 0) + (c["ec3"] or 0)
    need_raw = target_raw_total - current_raw

    st.markdown("Select components to attempt:")
    att1 = st.checkbox("Attempt EC1", value=(c["ec1"] is None), key="proj_ec1")
    att2 = st.checkbox("Attempt EC2", value=(c["ec2"] is None), key="proj_ec2")
    att3 = st.checkbox("Attempt EC3", value=(c["ec3"] is None), key="proj_ec3")
    
    if need_raw <= 0:
        st.success(f"Target GP {target_gp} already met!")
    else:
        available = (c["w1"] if att1 else 0) + (c["w2"] if att2 else 0) + (c["w3"] if att3 else 0)
        if need_raw > available:
            st.error(f"Target not reachable. Need {need_raw:.2f} more raw marks, but only {available:.2f} are available.")
        else:
            st.info(f"You need a total of **{need_raw:.2f}** raw marks across selected components.")
            for comp, weight, flag in [("EC1", c["w1"], att1), ("EC2", c["w2"], att2), ("EC3", c["w3"], att3)]:
                if flag:
                    min_req = max(0, need_raw - (available - weight))
                    st.write(f"• **{comp}**: Minimum **{min_req:.2f} / {weight}** (assuming others are full marks).")

# Footer
st.markdown("---")
st.markdown(
    "<div style='border:1px solid #ddd;padding:12px;border-radius:6px;background:#fff;'>"
    "<p style='margin:0;font-weight:bold;color:red;'>Grade mapping:</p>"
    "<p style='margin:0;color:#555;'>A=10 | A-=9 | B=8 | B-=7 | C=6 | C-=5 | D=4 | E=2</p>"
    "<br/><p style='margin:0;font-weight:bold;color:red;'>Pass criteria:</p>"
    "<p style='margin:0;color:#555;'>• Min. grade point per course ≥ 4.5<br>• Overall CGPA ≥ 5.5 to clear semester</p></div>", unsafe_allow_html=True
)
st.markdown("<p style='text-align:right; color:gray; font-size:11px;'>Developed by <b>Subodh Purohit</b></p>", unsafe_allow_html=True)
