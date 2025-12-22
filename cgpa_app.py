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
    """Return (gp, letter, cutoff) for absolute mapping."""
    if total >= 90: return 10, "A", 90
    elif total >= 80: return 9, "A-", 80
    elif total >= 70: return 8, "B", 70
    elif total >= 60: return 7, "B-", 60
    elif total >= 50: return 6, "C", 50
    elif total >= 45: return 5, "C-", 45
    elif total >= 35: return 4, "D", 35
    else: return 2, "E", 0

def normalize_mark(mark, highest, weight):
    """Normalizes mark based on class highest: (Mark/Highest) * Weight"""
    if mark is None or highest <= 0: return mark
    return (mark / highest) * weight

def total_percent_from_components(m1, m2, m3):
    return (0.0 if m1 is None else float(m1)) + (0.0 if m2 is None else float(m2)) + (0.0 if m3 is None else float(m3))

# -------------------------
# UI - Sidebar configuration
# -------------------------
st.title("🎓 CGPA Calculator")
st.caption("Calculate weighted CGPA with credit units and grade projection.")

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
        gw1 = st.number_input("EC1 weight (%)", min_value=0.0, max_value=100.0, value=30.0)
        gw2 = st.number_input("EC2 weight (%)", min_value=0.0, max_value=100.0, value=30.0)
        gw3 = st.number_input("EC3 weight (%)", min_value=0.0, max_value=100.0, value=40.0)
        if abs((gw1 + gw2 + gw3) - 100.0) > 1e-6:
            st.error("Global weights must sum to 100.")

# -------------------------
# Main input area
# -------------------------
st.subheader("Enter marks, units, and class highest per course")

courses_data = []
for i, cname in enumerate(course_names):
    st.markdown(f'<div class="course-box">', unsafe_allow_html=True)
    st.subheader(f"📚 {cname}")
    
    col_u, col_info = st.columns([1, 2])
    with col_u:
        units = st.selectbox(f"Units for {cname}", options=[4, 5], key=f"units_{i}")
    
    if same_weights:
        w1, w2, w3 = gw1, gw2, gw3
        st.caption(f"Weights (global): EC1={w1}%, EC2={w2}%, EC3={w3}%")
    else:
        wcols = st.columns(3)
        w1 = wcols[0].number_input(f"EC1 weight %", 0.0, 100.0, 30.0, key=f"w1_{i}")
        w2 = wcols[1].number_input(f"EC2 weight %", 0.0, 100.0, 30.0, key=f"w2_{i}")
        w3 = wcols[2].number_input(f"EC3 weight %", 0.0, 100.0, 40.0, key=f"w3_{i}")

    h1 = h2 = h3 = 100.0
    if calc_method == "Normalise from Class Highest":
        st.markdown("**Class Highest Marks per Component:**")
        hcols = st.columns(3)
        h1 = hcols[0].number_input(f"EC1 High", 0.1, 100.0, float(w1), key=f"h1_{i}")
        h2 = hcols[1].number_input(f"EC2 High", 0.1, 100.0, float(w2), key=f"h2_{i}")
        h3 = hcols[2].number_input(f"EC3 High", 0.1, 100.0, float(w3), key=f"h3_{i}")

    pcols = st.columns(3)
    with pcols[0]:
        p1 = st.checkbox("EC1 pending", key=f"p1_{i}")
        ec1 = None if p1 else st.number_input(f"EC1 (0-{w1})", 0.0, 100.0, key=f"ec1_{i}")
    with pcols[1]:
        p2 = st.checkbox("EC2 pending", key=f"p2_{i}")
        ec2 = None if p2 else st.number_input(f"EC2 (0-{w2})", 0.0, 100.0, key=f"ec2_{i}")
    with pcols[2]:
        p3 = st.checkbox("EC3 pending", key=f"p3_{i}")
        ec3 = None if p3 else st.number_input(f"EC3 (0-{w3})", 0.0, 100.0, key=f"ec3_{i}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    courses_data.append({
        "name": cname, "units": units, "ec1": ec1, "ec2": ec2, "ec3": ec3, 
        "w1": w1, "w2": w2, "w3": w3, "h1": h1, "h2": h2, "h3": h3
    })

st.markdown("---")
col_calc, col_reset, _ = st.columns([1,1,1])

compute_pressed = col_calc.button("Compute Results")
if col_reset.button("Reset"):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

if compute_pressed:
    for c in courses_data:
        if abs((c["w1"] + c["w2"] + c["w3"]) - 100.0) > 1e-6:
            st.error(f"Weights for '{c['name']}' do not sum to 100.")
            st.stop()

    rows = []
    total_credit_points = 0.0
    total_units_sum = 0.0

    for c in courses_data:
        m1 = normalize_mark(c["ec1"], c["h1"], c["w1"]) if calc_method == "Normalise from Class Highest" else c["ec1"]
        m2 = normalize_mark(c["ec2"], c["h2"], c["w2"]) if calc_method == "Normalise from Class Highest" else c["ec2"]
        m3 = normalize_mark(c["ec3"], c["h3"], c["w3"]) if calc_method == "Normalise from Class Highest" else c["ec3"]

        total = total_percent_from_components(m1, m2, m3)
        gp, letter, _ = grade_point_and_letter_absolute(total)
        credit_pts = gp * c["units"]
        total_credit_points += credit_pts
        total_units_sum += c["units"]

        rows.append({
            "Course": c["name"], "Units": c["units"], "GP": gp, "Grade": letter, 
            "Credit Pts": credit_pts, "Total(%)": f"{total:.2f}", "PassBool": (gp >= 4.5),
            "EC1_val": c["ec1"], "EC2_val": c["ec2"], "EC3_val": c["ec3"]
        })

    res_df = pd.DataFrame(rows)
    st.session_state["last_results_df"] = res_df
    st.session_state["courses_data"] = courses_data
    st.session_state["calc_method"] = calc_method

    st.subheader("📊 Credit Points Summary")
    st.table(res_df[["Course", "Units", "GP", "Credit Pts"]])

    st.subheader("Full Results")
    html = "<table style='border-collapse:collapse;width:100%;font-size:14px'>"
    html += "<tr style='background:#f7f7f7;font-weight:bold;text-align:left;'><th>Course</th><th>Units</th><th>Total(%)</th><th>GP</th><th>Grade</th><th>Pass</th></tr>"
    for _, r in res_df.iterrows():
        color = "green" if r["PassBool"] else "red"
        pass_text = f"<span style='color:{color};font-weight:600'>{'Pass' if r['PassBool'] else 'Fail'}</span>"
        html += f"<tr><td>{r['Course']}</td><td style='text-align:center'>{r['Units']}</td><td>{r['Total(%)']}</td><td>{r['GP']}</td><td>{r['Grade']}</td><td style='text-align:center'>{pass_text}</td></tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    final_cgpa = total_credit_points / total_units_sum if total_units_sum > 0 else 0
    cgpa_color = "green" if final_cgpa >= 5.5 else "red"
    st.markdown(f"<h4>Weighted CGPA: <span style='color:{cgpa_color}'>{final_cgpa:.2f}</span></h4>", unsafe_allow_html=True)

# -------------------------
# Projection area
# -------------------------
st.markdown("---")
st.header("Projection — Required Marks")

if "last_results_df" in st.session_state:
    df_p = st.session_state["last_results_df"]
    sel_c_name = st.selectbox("Pick a course for projection", options=df_p["Course"].tolist())
    target_gp = st.selectbox("Target grade point", options=[10,9,8,7,6,5,4,2], index=2)
    
    idx = df_p.index[df_p["Course"] == sel_c_name][0]
    c = st.session_state["courses_data"][idx]
    method = st.session_state["calc_method"]
    
    # Calculate current normalized total from non-pending components
    m1_n = normalize_mark(c["ec1"], c["h1"], c["w1"]) if method == "Normalise from Class Highest" else (c["ec1"] or 0)
    m2_n = normalize_mark(c["ec2"], c["h2"], c["w2"]) if method == "Normalise from Class Highest" else (c["ec2"] or 0)
    m3_n = normalize_mark(c["ec3"], c["h3"], c["w3"]) if method == "Normalise from Class Highest" else (c["ec3"] or 0)
    current_norm_total = (m1_n if c["ec1"] is not None else 0) + (m2_n if c["ec2"] is not None else 0) + (m3_n if c["ec3"] is not None else 0)
    
    gp_to_total = {10:90, 9:80, 8:70, 7:60, 6:50, 5:45, 4:35, 2:0}
    target_total = gp_to_total[target_gp]
    need_norm = target_total - current_norm_total

    st.markdown("Select components to attempt:")
    att = {
        "EC1": st.checkbox("Attempt EC1", value=(c["ec1"] is None), key="att1"),
        "EC2": st.checkbox("Attempt EC2", value=(c["ec2"] is None), key="att2"),
        "EC3": st.checkbox("Attempt EC3", value=(c["ec3"] is None), key="att3")
    }

    if need_norm <= 0:
        st.success(f"Target GP {target_gp} already achieved!")
    else:
        # Calculate available normalized capacity
        cap = 0
        if att["EC1"]: cap += (c["w1"] if method == "Direct Average" else c["w1"])
        if att["EC2"]: cap += (c["w2"] if method == "Direct Average" else c["w2"])
        if att["EC3"]: cap += (c["w3"] if method == "Direct Average" else c["w3"])

        if need_norm > cap:
            st.error(f"Impossible to reach GP {target_gp}. Need {need_norm:.2f} more normalized points, but only {cap:.2f} are available.")
        else:
            st.info(f"To reach GP {target_gp}, you need **{need_norm:.2f}** more normalized points.")
            # Proportional requirement logic
            for comp, weight, high, key in [("EC1", c["w1"], c["h1"], "EC1"), ("EC2", c["w2"], c["h2"], "EC2"), ("EC3", c["w3"], c["h3"], "EC3")]:
                if att[key]:
                    # Required Normalized in this component if it carries the whole load
                    req_norm_single = max(0, need_norm - (cap - weight))
                    # Convert normalized back to RAW marks
                    if method == "Normalise from Class Highest":
                        req_raw = (req_norm_single / weight) * high
                    else:
                        req_raw = req_norm_single
                    st.write(f"• **{comp}**: Minimum raw score of **{req_raw:.2f}** (out of {weight if method=='Direct Average' else high}) if others are maxed out.")

# Footer
st.markdown("---")
st.markdown("<div style='border:1px solid #ddd;padding:12px;border-radius:6px;background:#fff;'>"
            "<p style='margin:0;font-weight:bold;color:red;'>Pass criteria:</p>"
            "<p style='margin:0;color:#555;'>• Min. grade point per course ≥ 4.5<br>• Overall CGPA ≥ 5.5 to clear the semester</p></div>", unsafe_allow_html=True)
st.markdown("<p style='text-align:right; color:gray; font-size:11px;'>Developed by <b>Subodh Purohit</b></p>", unsafe_allow_html=True)
