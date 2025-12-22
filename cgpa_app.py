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

def build_relative_cutoffs(mean, std, multipliers):
    cutoffs = {}
    for letter, mult in multipliers.items():
        cutoffs[letter] = mean + mult * std
    return cutoffs

def grade_point_and_letter_relative(total, cutoffs):
    order = [("A",10), ("A-",9), ("B",8), ("B-",7), ("C",6), ("C-",5), ("D",4), ("E",2)]
    for letter, gp in order:
        if total >= cutoffs.get(letter, -1e9):
            return gp, letter
    return 2, "E"

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
    
    single_comp_requirements = {}
    for comp, r, w in zip(("EC1","EC2","EC3"), (r1,r2,r3), (w1,w2,w3)):
        if r:
            required_single = min(max(0.0, need - (remaining_max - w)), w)
            single_comp_requirements[comp] = {"required_absolute": required_single}
        else:
            single_comp_requirements[comp] = None
    return {"status":"possible", "need":need, "remaining_max":remaining_max, "required_proportional": required, "required_single_comp": single_comp_requirements}

# -------------------------
# UI - Sidebar configuration
# -------------------------
st.title("🎓 CGPA Calculator")
st.caption("All course totals = 100. Enter weights, marks, and units (4 or 5) for weighted CGPA calculation.")

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
    
    st.markdown("---")
    st.markdown("Grading mode")
    grading_mode = st.selectbox("Grading mode", ["Absolute (default)", "Relative (cohort-based)"])
    if grading_mode.startswith("Relative"):
        cohort_upload = st.file_uploader("Upload cohort totals CSV", type=["csv"])
        manual_mean = st.number_input("Manual mean", value=0.0)
        manual_std = st.number_input("Manual std", value=0.0)
        multipliers = {"A": 1.5, "A-": 1.0, "B": 0.5, "B-": 0.0, "C": -0.5, "C-": -1.0, "D": -1.5, "E": -3.0}
    else:
        cohort_upload = None
        manual_mean = manual_std = 0.0
        multipliers = None

# -------------------------
# Main input area
# -------------------------
st.subheader("Enter marks and units per course")

courses_data = []
for i, cname in enumerate(course_names):
    st.subheader(cname)
    col_u, col_info = st.columns([1, 2])
    with col_u:
        units = st.selectbox(f"Units for {cname}", options=[4, 5], key=f"units_{i}")
    
    if same_weights:
        w1, w2, w3 = gw1, gw2, gw3
        st.caption(f"Weights (global): EC1={w1}%, EC2={w2}%, EC3={w3}%")
    else:
        wcols = st.columns(3)
        w1 = wcols[0].number_input(f"{cname} EC1 weight (%)", 0.0, 100.0, 30.0, key=f"w1_{i}")
        w2 = wcols[1].number_input(f"{cname} EC2 weight (%)", 0.0, 100.0, 30.0, key=f"w2_{i}")
        w3 = wcols[2].number_input(f"{cname} EC3 weight (%)", 0.0, 100.0, 40.0, key=f"w3_{i}")

    pcols = st.columns([1,1,1])
    with pcols[0]:
        pending1 = st.checkbox("EC1 pending", key=f"pending_ec1_{i}")
        ec1 = None if pending1 else st.number_input(f"{cname} EC1 marks", 0.0, float(w1), key=f"ec1_{i}")
    with pcols[1]:
        pending2 = st.checkbox("EC2 pending", key=f"pending_ec2_{i}")
        ec2 = None if pending2 else st.number_input(f"{cname} EC2 marks", 0.0, float(w2), key=f"ec2_{i}")
    with pcols[2]:
        pending3 = st.checkbox("EC3 pending", key=f"pending_ec3_{i}")
        ec3 = None if pending3 else st.number_input(f"{cname} EC3 marks", 0.0, float(w3), key=f"ec3_{i}")
    
    courses_data.append({"name": cname, "units": units, "ec1": ec1, "ec2": ec2, "ec3": ec3, "w1": w1, "w2": w2, "w3": w3})

st.markdown("---")
col_calc, col_reset, col_dl = st.columns([1,1,1])

with col_calc:
    compute_pressed = st.button("Compute Results")
with col_reset:
    reset_pressed = st.button("Reset")

if reset_pressed:
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

if compute_pressed:
    rows = []
    total_weighted_gp = 0.0
    total_units_sum = 0.0

    for c in courses_data:
        total = total_percent_from_components(c["ec1"], c["ec2"], c["ec3"])
        gp, letter, _ = grade_point_and_letter_absolute(total)
        
        credit_pts = gp * c["units"]
        total_weighted_gp += credit_pts
        total_units_sum += c["units"]

        rows.append({
            "Course": c["name"],
            "Units": c["units"],
            "EC1": ("" if c["ec1"] is None else f"{c['ec1']:.2f}"),
            "EC2": ("" if c["ec2"] is None else f"{c['ec2']:.2f}"),
            "EC3": ("" if c["ec3"] is None else f"{c['ec3']:.2f}"),
            "Total(%)": f"{total:.2f}",
            "Grade Point": gp,
            "Grade": letter,
            "Credit Points": credit_pts,
            "PassBool": (gp >= 4.5)
        })

    res_df = pd.DataFrame(rows)
    st.session_state["last_results_df"] = res_df
    st.session_state["courses_data"] = courses_data
    st.session_state["weights_mode"] = ("global" if same_weights else "per-course")
    st.session_state["global_weights"] = (gw1, gw2, gw3) if same_weights else None
    st.session_state["grading_mode_saved"] = grading_mode

    # Summary Table for Credit Points
    st.subheader("📊 Credit Points Summary")
    st.table(res_df[["Course", "Units", "Grade Point", "Credit Points"]])

    # Original Custom HTML Results Table
    st.subheader("Full Results")
    html = "<table style='border-collapse:collapse;width:100%;font-size:14px'>"
    html += "<tr style='background:#f7f7f7;font-weight:bold;text-align:left;'>"
    for c_head in ["Course","Units","EC1","EC2","EC3","Total(%)","Grade Point","Grade","Pass"]:
        html += f"<th style='padding:8px;border:1px solid #e6e6e6'>{c_head}</th>"
    html += "</tr>"
    for _, r in res_df.iterrows():
        color = "green" if r["PassBool"] else "red"
        pass_text = f"<span style='color:{color};font-weight:600'>{'Pass' if r['PassBool'] else 'Fail'}</span>"
        html += "<tr>"
        html += f"<td style='padding:8px;border:1px solid #eee'>{r['Course']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee;text-align:center'>{r['Units']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee'>{r['EC1']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee'>{r['EC2']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee'>{r['EC3']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee'>{r['Total(%)']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee'>{r['Grade Point']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee'>{r['Grade']}</td>"
        html += f"<td style='padding:8px;border:1px solid #eee;text-align:center'>{pass_text}</td>"
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    # Weighted CGPA Display
    final_cgpa = total_weighted_gp / total_units_sum if total_units_sum > 0 else 0
    cgpa_color = "green" if final_cgpa >= 5.5 else "red"
    status_text = "Clear (CGPA ≥ 5.5)" if final_cgpa >= 5.5 else "Not clear (CGPA < 5.5)"
    st.markdown(f"<h4>Weighted CGPA: <span style='color:{cgpa_color}'>{final_cgpa:.2f}</span> — <span style='font-weight:600'>{status_text}</span></h4>", unsafe_allow_html=True)

# -------------------------
# Projection area
# -------------------------
st.markdown("---")
st.header("Projection — required marks in pending components")

if "last_results_df" in st.session_state:
    df_prev = st.session_state["last_results_df"]
    chosen_course = st.selectbox("Pick a course for projection", options=df_prev["Course"].tolist())
    target_gp = st.selectbox("Target grade point", options=[10,9,8,7,6,5,4,2], index=2)
    
    idx = df_prev.index[df_prev["Course"] == chosen_course][0]
    course_entry = st.session_state["courses_data"][idx]
    w1, w2, w3 = course_entry["w1"], course_entry["w2"], course_entry["w3"]
    
    st.markdown("Select components to attempt:")
    r1 = st.checkbox("Attempt EC1", value=(course_entry['ec1'] is None))
    r2 = st.checkbox("Attempt EC2", value=(course_entry['ec2'] is None))
    r3 = st.checkbox("Attempt EC3", value=(course_entry['ec3'] is None))
    
    gp_to_total = {10:90,9:80,8:70,7:60,6:50,5:45,4:35,2:0}
    target_total = gp_to_total[target_gp]
    
    req = required_scores_to_reach_target((course_entry['ec1'], course_entry['ec2'], course_entry['ec3']), (w1,w2,w3), (r1,r2,r3), target_total)
    
    if req["status"] == "possible":
        st.info(f"Need {req['need']:.2f} additional points for target Grade Point {target_gp}.")
    elif req["status"] == "impossible_exceed":
        st.error("Target not achievable with remaining components.")
else:
    st.info("Compute results first to enable projection.")

# -------------------------
# Footer boxed info (Original)
# -------------------------
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
