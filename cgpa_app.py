import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="🎓 CGPA Calculator", layout="centered")

# -------------------------
# Helper functions
# -------------------------
def grade_point_and_letter_absolute(total):
    """Return (gp, letter, cutoff) for absolute mapping."""
    if total >= 90:
        return 10, "A", 90
    elif total >= 80:
        return 9, "A-", 80
    elif total >= 70:
        return 8, "B", 70
    elif total >= 60:
        return 7, "B-", 60
    elif total >= 50:
        return 6, "C", 50
    elif total >= 45:
        return 5, "C-", 45
    elif total >= 35:
        return 4, "D", 35
    else:
        return 2, "E", 0

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
    """Components are already on the scale of their weights (0..w) so total% = m1+m2+m3"""
    m1 = 0.0 if m1 is None else float(m1)
    m2 = 0.0 if m2 is None else float(m2)
    m3 = 0.0 if m3 is None else float(m3)
    return m1 + m2 + m3

def required_scores_to_reach_target(current_scores, weights, remaining_flags, target_total):
    """
    current_scores: tuple (m1,m2,m3) with None for pending
    weights: (w1,w2,w3)
    remaining_flags: (r1,r2,r3) True if you'll attempt that component
    target_total: numeric total percent desired (eg 70)
    Returns a dict describing whether possible and suggested allocations.
    """
    m1, m2, m3 = current_scores
    w1, w2, w3 = weights
    r1, r2, r3 = remaining_flags

    current_sum = (0.0 if m1 is None else float(m1)) + (0.0 if m2 is None else float(m2)) + (0.0 if m3 is None else float(m3))
    need = target_total - current_sum
    remaining_max = (w1 if r1 else 0.0) + (w2 if r2 else 0.0) + (w3 if r3 else 0.0)

    if need <= 0:
        return {"status":"already_met", "need":0.0, "details":"Target already achieved."}
    if remaining_max <= 0:
        return {"status":"impossible_no_remaining", "need":need, "details":"No remaining components selected."}
    if need > remaining_max + 1e-9:
        return {"status":"impossible_exceed", "need":need, "remaining_max":remaining_max,
                "details":"Not achievable even with full marks in remaining components."}

    # Proportional suggestion by remaining component maxima
    required = {}
    total_weight_of_chosen = (w1 if r1 else 0.0) + (w2 if r2 else 0.0) + (w3 if r3 else 0.0)
    for comp, r, w, curr in zip(("EC1","EC2","EC3"), (r1,r2,r3), (w1,w2,w3), (m1,m2,m3)):
        if r:
            share = (w / total_weight_of_chosen) * need
            current_here = 0.0 if curr is None else float(curr)
            required_mark = current_here + share
            required[comp] = {"suggested_total": min(required_mark, w), "current": current_here, "max": w}
        else:
            current_here = 0.0 if curr is None else float(curr)
            required[comp] = {"suggested_total": None, "current": current_here, "max": w}

    # Single-component minimal requirement (if only that component taken as extra)
    single_comp_requirements = {}
    for comp, r, w in zip(("EC1","EC2","EC3"), (r1,r2,r3), (w1,w2,w3)):
        if r:
            required_single = max(0.0, need - (remaining_max - w))
            required_single = min(required_single, w)
            single_comp_requirements[comp] = {"required_absolute": required_single}
        else:
            single_comp_requirements[comp] = None

    return {
        "status":"possible",
        "need":need,
        "remaining_max":remaining_max,
        "required_proportional": required,
        "required_single_comp": single_comp_requirements,
        "details":"Possible"
    }

# -------------------------
# UI - Sidebar configuration
# -------------------------
st.title("🎓 CGPA Calculator")
st.caption("All course totals = 100. Enter weights (global or per-course), raw marks (each component measured in same scale as its weight).")

with st.sidebar:
    st.header("Configuration")
    num_courses = st.number_input("Number of courses", min_value=1, max_value=12, value=4, step=1)

    st.markdown("Enter course names:")
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
    else:
        gw1 = gw2 = gw3 = None

    st.markdown("---")
    st.markdown("Grading mode")
    grading_mode = st.selectbox("Grading mode", ["Absolute (default)", "Relative (cohort-based)"])
    if grading_mode.startswith("Relative"):
        cohort_upload = st.file_uploader("Upload cohort totals CSV (single numeric column)", type=["csv"])
        manual_mean = st.number_input("Manual mean (for relative)", value=0.0, format="%.2f")
        manual_std = st.number_input("Manual std (for relative)", value=0.0, format="%.2f")
        st.markdown("Adjust multipliers (cutoff = mean + multiplier * std)")
        mult_A = st.slider("A (mult)", -2.0, 3.0, 1.5, 0.1)
        mult_A_ = st.slider("A- (mult)", -2.0, 3.0, 1.0, 0.1)
        mult_B = st.slider("B (mult)", -2.0, 3.0, 0.5, 0.1)
        mult_B_ = st.slider("B- (mult)", -2.0, 3.0, 0.0, 0.1)
        mult_C = st.slider("C (mult)", -3.0, 2.0, -0.5, 0.1)
        mult_C_ = st.slider("C- (mult)", -3.0, 2.0, -1.0, 0.1)
        mult_D = st.slider("D (mult)", -4.0, 1.0, -1.5, 0.1)
        mult_E = st.slider("E (mult)", -6.0, -2.0, -3.0, 0.1)
        multipliers = {"A": mult_A, "A-": mult_A_, "B": mult_B, "B-": mult_B_,
                       "C": mult_C, "C-": mult_C_, "D": mult_D, "E": mult_E}
    else:
        cohort_upload = None
        manual_mean = manual_std = 0.0
        multipliers = None

# -------------------------
# Main input area
# -------------------------
st.subheader("Enter marks scored per component")

# initialize session defaults to avoid Streamlit warnings
for i in range(num_courses):
    if f"ec1_{i}" not in st.session_state:
        st.session_state[f"ec1_{i}"] = 0.0
    if f"ec2_{i}" not in st.session_state:
        st.session_state[f"ec2_{i}"] = 0.0
    if f"ec3_{i}" not in st.session_state:
        st.session_state[f"ec3_{i}"] = 0.0
    if not same_weights:
        if f"w1_{i}" not in st.session_state:
            st.session_state[f"w1_{i}"] = 30.0
        if f"w2_{i}" not in st.session_state:
            st.session_state[f"w2_{i}"] = 30.0
        if f"w3_{i}" not in st.session_state:
            st.session_state[f"w3_{i}"] = 40.0

courses_data = []
for i, cname in enumerate(course_names):
    st.subheader(cname)
    # weights area: small inputs if per-course enabled, else show global weights
    if same_weights:
        w1, w2, w3 = gw1, gw2, gw3
        st.caption(f"Weights (global): EC1={w1}%, EC2={w2}%, EC3={w3}%")
    else:
        wcols = st.columns(3)
        with wcols[0]:
            w1 = st.number_input(f"{cname} EC1 weight (%)", min_value=0.0, max_value=100.0, value=st.session_state.get(f"w1_{i}",30.0), key=f"w1_{i}")
        with wcols[1]:
            w2 = st.number_input(f"{cname} EC2 weight (%)", min_value=0.0, max_value=100.0, value=st.session_state.get(f"w2_{i}",30.0), key=f"w2_{i}")
        with wcols[2]:
            w3 = st.number_input(f"{cname} EC3 weight (%)", min_value=0.0, max_value=100.0, value=st.session_state.get(f"w3_{i}",40.0), key=f"w3_{i}")
        if abs((w1+w2+w3) - 100.0) > 1e-6:
            st.warning(f"Weights for {cname} should sum to 100 (currently {w1+w2+w3:.2f}).")

    # pending checkboxes and inputs
    pcols = st.columns([1,1,1,2])
    with pcols[0]:
        pending1 = st.checkbox("EC1 pending", key=f"pending_ec1_{i}")
        if pending1:
            ec1 = None
        else:
            ec1 = st.number_input(f"{cname} EC1 marks (0-{w1})", min_value=0.0, max_value=w1, value=st.session_state.get(f"ec1_{i}",0.0), key=f"ec1_{i}")
    with pcols[1]:
        pending2 = st.checkbox("EC2 pending", key=f"pending_ec2_{i}")
        if pending2:
            ec2 = None
        else:
            ec2 = st.number_input(f"{cname} EC2 marks (0-{w2})", min_value=0.0, max_value=w2, value=st.session_state.get(f"ec2_{i}",0.0), key=f"ec2_{i}")
    with pcols[2]:
        pending3 = st.checkbox("EC3 pending", key=f"pending_ec3_{i}")
        if pending3:
            ec3 = None
        else:
            ec3 = st.number_input(f"{cname} EC3 marks (0-{w3})", min_value=0.0, max_value=w3, value=st.session_state.get(f"ec3_{i}",0.0), key=f"ec3_{i}")
    courses_data.append({"name": cname, "ec1": ec1, "ec2": ec2, "ec3": ec3, "w1": w1, "w2": w2, "w3": w3})

st.markdown("---")

# Buttons: Calculate / Reset / Download
col_calc, col_reset, col_dl = st.columns([1,1,1])

# Place the compute button in the left column but capture its press state
with col_calc:
    compute_pressed = st.button("Compute Results")

with col_reset:
    reset_pressed = st.button("Reset")

with col_dl:
    if "last_results_df" in st.session_state:
        csv_data = st.session_state["last_results_df"].to_csv(index=False)
        st.download_button("Download last results (CSV)", csv_data, "cgpa_results.csv", "text/csv")
    else:
        st.write("")

# Handle Reset (full-width effect by doing it outside column after capturing the button)
if reset_pressed:
    keys_to_clear = [k for k in st.session_state.keys() if k.startswith("ec1_") or k.startswith("ec2_") or k.startswith("ec3_")
                     or k.startswith("pending_ec1_") or k.startswith("pending_ec2_") or k.startswith("pending_ec3_")
                     or k.startswith("w1_") or k.startswith("w2_") or k.startswith("w3_")
                     or k in ("last_results_df","courses_data","weights_mode","global_weights","grading_mode_saved")]
    for k in keys_to_clear:
        del st.session_state[k]
    st.experimental_rerun()

# If compute was pressed, run the computation and display full-width banner after
if compute_pressed:
    # Validate weights (per-course or global)
    bad = False
    for c in courses_data:
        s = c["w1"] + c["w2"] + c["w3"]
        if abs(s - 100.0) > 1e-6:
            st.error(f"Weights for '{c['name']}' do not sum to 100 (sum={s:.2f}). Please fix.")
            bad = True
    if bad:
        st.stop()

    # Build results
    rows = []
    for c in courses_data:
        total = total_percent_from_components(c["ec1"], c["ec2"], c["ec3"])
        if grading_mode.startswith("Relative"):
            mean = std = None
            if cohort_upload is not None:
                try:
                    up = pd.read_csv(cohort_upload)
                    numeric_cols = up.select_dtypes(include=[np.number]).columns.tolist()
                    if numeric_cols:
                        scores = up[numeric_cols[0]].dropna().astype(float).values
                        mean = float(np.mean(scores)); std = float(np.std(scores, ddof=0))
                        st.success(f"Using cohort upload mean={mean:.2f}, std={std:.2f}")
                except Exception as e:
                    st.error(f"Failed reading cohort CSV: {e}")
            if (mean is None or std is None) and manual_mean>0 and manual_std>0:
                mean, std = float(manual_mean), float(manual_std)
                st.info(f"Using manual mean/std = {mean:.2f}/{std:.2f}")
            if mean is None or std is None:
                # fallback to absolute
                gp, letter, _ = grade_point_and_letter_absolute(total)
            else:
                cutoffs = build_relative_cutoffs(mean, std, multipliers)
                gp, letter = grade_point_and_letter_relative(total, cutoffs)
        else:
            gp, letter, _ = grade_point_and_letter_absolute(total)

        rows.append({
            "Course": c["name"],
            "EC1": ("" if c["ec1"] is None else f"{c['ec1']:.2f}"),
            "EC2": ("" if c["ec2"] is None else f"{c['ec2']:.2f}"),
            "EC3": ("" if c["ec3"] is None else f"{c['ec3']:.2f}"),
            "Total(%)": f"{total:.2f}",
            "Grade Point": gp,
            "Grade": letter,
            "PassBool": (gp >= 4.5)
        })

    res_df = pd.DataFrame(rows)
    # store in session for projection/download
    st.session_state["last_results_df"] = res_df
    st.session_state["courses_data"] = courses_data
    st.session_state["weights_mode"] = ("global" if same_weights else "per-course")
    st.session_state["global_weights"] = (gw1, gw2, gw3) if same_weights else None
    st.session_state["grading_mode_saved"] = grading_mode
    st.success("Results computed successfully.")

    # Display clean table with Pass column colored (full-width HTML table)
    st.subheader("Results")
    html = "<table style='border-collapse:collapse;width:100%;font-size:14px'>"
    html += "<tr style='background:#f7f7f7;font-weight:bold;text-align:left;'>"
    for c in ["Course","EC1","EC2","EC3","Total(%)","Grade Point","Grade","Pass"]:
        html += f"<th style='padding:8px;border:1px solid #e6e6e6'>{c}</th>"
    html += "</tr>"
    for _, r in res_df.iterrows():
        color = "green" if r["PassBool"] else "red"
        pass_text = f"<span style='color:{color};font-weight:600'>{'Pass' if r['PassBool'] else 'Fail'}</span>"
        html += "<tr>"
        html += f"<td style='padding:8px;border:1px solid #eee'>{r['Course']}</td>"
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

    # CGPA
    valid_gps = [g for g in res_df["Grade Point"] if g is not None]
    cgpa = (sum(valid_gps)/len(valid_gps)) if len(valid_gps)>0 else None
    if cgpa is not None:
        cgpa_color = "green" if cgpa >= 5.5 else "red"
        status_text = "Clear (CGPA ≥ 5.5)" if cgpa >= 5.5 else "Not clear (CGPA < 5.5)"
        st.markdown(f"<h4>Overall CGPA: <span style='color:{cgpa_color}'>{cgpa:.2f}</span> — <span style='font-weight:600'>{status_text}</span></h4>", unsafe_allow_html=True)

    # --- Full-width HTML success banner (option 1) ---
    st.markdown(
        """
        <div style="
            background-color:#e9f7ef;
            border-left:6px solid #2ecc71;
            padding:14px 18px;
            margin-top:12px;
            margin-bottom:18px;
            font-size:16px;
            font-weight:600;
            border-radius:6px;">
            ✅ Results computed successfully. Scroll down to the <b>Projection</b> section to compute required marks for pending components.
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------------
# Projection area (requires results computed)
# -------------------------
st.markdown("---")
st.header("Projection — required marks in pending components to reach a target grade")

if "last_results_df" in st.session_state:
    df_prev = st.session_state["last_results_df"]
    chosen_course = st.selectbox("Pick a course for projection", options=df_prev["Course"].tolist())
    target_gp = st.selectbox("Target grade point", options=[10,9,8,7,6,5,4,2], index=2)

    # get course entry and weights
    idx = df_prev.index[df_prev["Course"] == chosen_course][0]
    course_entry = st.session_state["courses_data"][idx]

    if st.session_state.get("weights_mode") == "global":
        gw = st.session_state.get("global_weights", (gw1,gw2,gw3))
        w1, w2, w3 = gw
    else:
        w1, w2, w3 = course_entry["w1"], course_entry["w2"], course_entry["w3"]

    st.write(f"Current marks for {chosen_course}:")
    st.write(f"EC1: {course_entry['ec1'] if course_entry['ec1'] is not None else 'Pending'}")
    st.write(f"EC2: {course_entry['ec2'] if course_entry['ec2'] is not None else 'Pending'}")
    st.write(f"EC3: {course_entry['ec3'] if course_entry['ec3'] is not None else 'Pending'}")

    # components user will attempt
    st.markdown("Select which pending components you will attempt:")
    r1 = st.checkbox("Attempt EC1 (if pending)", value=(course_entry['ec1'] is None))
    r2 = st.checkbox("Attempt EC2 (if pending)", value=(course_entry['ec2'] is None))
    r3 = st.checkbox("Attempt EC3 (if pending)", value=(course_entry['ec3'] is None))

    # Map target gp to cutoff total% (absolute mapping)
    gp_to_total = {10:90,9:80,8:70,7:60,6:50,5:45,4:35,2:0}
    target_total = gp_to_total[target_gp]

    # if relative grading, warn user for projections
    if st.session_state.get("grading_mode_saved") == "Relative":
        st.warning("Projection uses absolute cutoffs by default. For relative-grade projections, provide cohort mean/std in the sidebar earlier and recompute results.")

    req = required_scores_to_reach_target((course_entry['ec1'], course_entry['ec2'], course_entry['ec3']),
                                         (w1,w2,w3), (r1,r2,r3), target_total)

    st.subheader("Projection result")
    status = req.get("status")
    if status == "already_met":
        st.success("Target grade already met with current marks.")
    elif status == "impossible_no_remaining":
        st.error("No remaining components selected — cannot reach target.")
    elif status == "impossible_exceed":
        st.error(f"Not achievable: you need additional {req['need']:.2f} but remaining max is {req['remaining_max']:.2f}.")
    elif status == "possible":
        st.info(f"You need an additional {req['need']:.2f} points to reach total {target_total:.2f}. Remaining max possible = {req['remaining_max']:.2f}.")
        st.write("Suggested proportional allocation (absolute marks in component):")
        prop = req["required_proportional"]
        for comp in ("EC1","EC2","EC3"):
            info = prop[comp]
            if info["suggested_total"] is None:
                st.write(f"{comp}: not selected / not applicable")
            else:
                st.write(f"{comp}: current = {info['current']:.2f}, suggested total in component = {info['suggested_total']:.2f} (max {info['max']:.2f})")
        st.write("If attempting only one component, minimal marks required there:")
        for comp, val in req["required_single_comp"].items():
            if val is not None:
                max_here = (w1 if comp=="EC1" else (w2 if comp=="EC2" else w3))
                st.write(f"{comp}: {val['required_absolute']:.2f} (max {max_here:.2f})")
    else:
        st.write("Projection could not be computed.")

else:
    st.info("Compute results first (press 'Compute Results') to enable projection.")

st.markdown("---")

# -------------------------
# Footer boxed info (left aligned)
# -------------------------
st.markdown(
    "<div style='border:1px solid #ddd;padding:12px;border-radius:6px;background:#fff; max-width:900px;'>"
    "<p style='margin:0;font-weight:bold;color:red;'>Grade mapping:</p>"
    "<p style='margin:0;color:#555;'>A = 10 | A- = 9 | B = 8 | B- = 7 | C = 6 | C- = 5 | D = 4 | E = 2</p>"
    "<br/>"
    "<p style='margin:0;font-weight:bold;color:red;'>Pass criteria:</p>"
    "<p style='margin:0;color:#555;'>• Min. grade point per course ≥ 4.5<br>• Overall CGPA ≥ 5.5 to clear the semester</p>"
    "</div>", unsafe_allow_html=True
)

st.caption("Tip: For relative grading projections, upload cohort totals or enter mean/std in the sidebar and recompute results.")
