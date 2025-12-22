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

def total_percent_from_components(m1, m2, m3):
    m1 = 0.0 if m1 is None else float(m1)
    m2 = 0.0 if m2 is None else float(m2)
    m3 = 0.0 if m3 is None else float(m3)
    return m1 + m2 + m3

def required_scores_to_reach_target(current_scores, weights, remaining_flags, target_total):
    m1, m2, m3 = current_scores
    w1, w2, w3 = weights
    r1, r2, r3 = remaining_flags
    current_sum = (0.0 if m1 is None else float(m1)) + (0.0 if m2 is None else float(m2)) + (0.0 if m3 is None else float(m3))
    need = target_total - current_sum
    remaining_max = (w1 if r1 else 0.0) + (w2 if r2 else 0.0) + (w3 if r3 else 0.0)
    if need <= 0: return {"status":"already_met", "need":0.0}
    if remaining_max <= 0: return {"status":"impossible_no_remaining", "need":need}
    if need > remaining_max + 1e-9: return {"status":"impossible_exceed", "need":need, "remaining_max":remaining_max}
    
    required = {}
    total_weight_of_chosen = (w1 if r1 else 0.0) + (w2 if r2 else 0.0) + (w3 if r3 else 0.0)
    for comp, r, w, curr in zip(("EC1","EC2","EC3"), (r1,r2,r3), (w1,w2,w3), (m1,m2,m3)):
        if r:
            share = (w / total_weight_of_chosen) * need
            current_here = 0.0 if curr is None else float(curr)
            required[comp] = {"suggested_total": min(current_here + share, w), "current": current_here, "max": w}
        else:
            required[comp] = {"suggested_total": None, "current": 0.0 if curr is None else float(curr), "max": w}
    return {"status":"possible", "need":need, "remaining_max":remaining_max, "required_proportional": required}

# -------------------------
# UI - Sidebar configuration
# -------------------------
st.title("🎓 CGPA Calculator")
st.caption("Enter weights, marks, and units (4 or 5) for weighted CGPA calculation.")

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
        if abs((gw1 + gw2 + gw3) - 100.0) > 1e-6:
            st.error("Global weights must sum to 100.")

# -------------------------
# Main input area
# -------------------------
st.subheader("Enter marks and units per course")

courses_data = []
for i, cname in enumerate(course_names):
    # This wrapper opens the red box div
    st.markdown(f'<div class="course-box">', unsafe_allow_html=True)
    st.subheader(f"📚 {cname}")
    
    col_u, col_info = st.columns([1, 2])
    with col_u:
        # Dropdown for credit units (4 or 5)
        units = st.selectbox(f"Units for {cname}", options=[4, 5], key=f"units_{i}")
    
    if same_weights:
        w1, w2, w3 = gw1, gw2, gw3
        st.caption(f"Weights (global): EC1={w1}%, EC2={w2}%, EC3={w3}%")
    else:
        wcols = st.columns(3)
        w1 = wcols[0].number_input(f"EC1 weight %", 0.0, 100.0, 30.0, key=f"w1_{i}")
        w2 = wcols[1].number_input(f"EC2 weight %", 0.0, 100.0, 30.0, key=f"w2_{i}")
        w3 = wcols[2].number_input(f"EC3 weight %", 0.0, 100.0, 40.0, key=f"w3_{i}")
        # Validate that individual course weights sum to 100%
        if abs((w1 + w2 + w3) - 100.0) > 1e-6:
            st.warning(f"Weights for {cname} must sum to 100 (currently {w1+w2+w3:.2f}).")

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
    
    # This closes the red box div, ensuring all fields are inside
    st.markdown('</div>', unsafe_allow_html=True)
    courses_data.append({"name": cname, "units": units, "ec1": ec1, "ec2": ec2, "ec3": ec3, "w1": w1, "w2": w2, "w3": w3})

st.markdown("---")
col_calc, col_reset, _ = st.columns([1,1,1])

with col_calc: compute_pressed = st.button("Compute Results")
with col_reset: 
    if st.button("Reset"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

if compute_pressed:
    # Final validation before calculation
    bad = False
    for c in courses_data:
        if abs((c["w1"] + c["w2"] + c["w3"]) - 100.0) > 1e-6:
            st.error(f"Weights for '{c['name']}' do not sum to 100. Calculation halted.")
            bad = True
    if bad: st.stop()

    rows = []
    total_credit_points = 0.0
    total_units_sum = 0.0

    for c in courses_data:
        total = total_percent_from_components(c["ec1"], c["ec2"], c["ec3"])
        gp, letter, _ = grade_point_and_letter_absolute(total)
        credit_pts = gp * c["units"]
        total_credit_points += credit_pts
        total_units_sum += c["units"]

        rows.append({
            "Course": c["name"], "Units": c["units"], "GP": gp, "Grade": letter, 
            "Credit Pts": credit_pts, "Total(%)": f"{total:.2f}",
            "EC1": ("" if c["ec1"] is None else f"{c['ec1']:.2f}"),
            "EC2": ("" if c["ec2"] is None else f"{c['ec2']:.2f}"),
            "EC3": ("" if c["ec3"] is None else f"{c['ec3']:.2f}"),
            "PassBool": (gp >= 4.5)
        })

    res_df = pd.DataFrame(rows)
    st.session_state["last_results_df"] = res_df

    st.subheader("📊 Credit Points Summary")
    st.table(res_df[["Course", "Units", "GP", "Credit Pts"]])

    # Full Results Table (Original HTML Style)
    st.subheader("Full Results")
    html = "<table style='border-collapse:collapse;width:100%;font-size:14px'>"
    html += "<tr style='background:#f7f7f7;font-weight:bold;text-align:left;'>"
    for head in ["Course","Units","EC1","EC2","EC3","Total(%)","GP","Grade","Pass"]:
        html += f"<th style='padding:8px;border:1px solid #e6e6e6'>{head}</th>"
    html += "</tr>"
    for _, r in res_df.iterrows():
        color = "green" if r["PassBool"] else "red"
        pass_text = f"<span style='color:{color};font-weight:600'>{'Pass' if r['PassBool'] else 'Fail'}</span>"
        html += f"<tr><td style='padding:8px;border:1px solid #eee'>{r['Course']}</td><td style='padding:8px;border:1px solid #eee;text-align:center'>{r['Units']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee'>{r['EC1']}</td><td style='padding:8px;border:1px solid #eee'>{r['EC2']}</td><td style='padding:8px;border:1px solid #eee'>{r['EC3']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee'>{r['Total(%)']}</td><td style='padding:8px;border:1px solid #eee'>{r['GP']}</td><td style='padding:8px;border:1px solid #eee'>{r['Grade']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee;text-align:center'>{pass_text}</td></tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    # Weighted CGPA Display
    final_cgpa = total_credit_points / total_units_sum if total_units_sum > 0 else 0
    cgpa_color = "green" if final_cgpa >= 5.5 else "red"
    st.markdown(f"<h4>Weighted CGPA: <span style='color:{cgpa_color}'>{final_cgpa:.2f}</span></h4>", unsafe_allow_html=True)

# Footer mapping box
st.markdown("---")
st.markdown(
    "<div style='border:1px solid #ddd;padding:12px;border-radius:6px;background:#fff; max-width:900px;'>"
    "<p style='margin:0;font-weight:bold;color:red;'>Grade mapping:</p>"
    "<p style='margin:0;color:#555;'>A = 10 | A- = 9 | B = 8 | B- = 7 | C = 6 | C- = 5 | D = 4 | E = 2</p>"
    "<br/>"
    "<p style='margin:0;font-weight:bold;color:red;'>Pass criteria:</p>"
    "<p style='margin:0;color:#555;'>• Min. grade point per course ≥ 4.5<br>• Overall CGPA ≥ 5.5 to clear the semester</p>"
    "</div>", unsafe_allow_html=True
)
st.markdown("<p style='text-align:right; color:gray; font-size:11px; margin-top:15px;'>Developed by <b> Subodh Purohit </b> with ❤️ using <b>Streamlit</b>, <b>Pandas</b>, and <b>NumPy</b>.</p>", unsafe_allow_html=True)
