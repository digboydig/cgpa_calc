import streamlit as st
import pandas as pd

st.set_page_config(page_title="🎓 CGPA Calculator", layout="centered")

# -------------------------
# Helper functions
# -------------------------
def grade_point_and_letter_absolute(total):
    if total >= 90: return 10, "A"
    elif total >= 80: return 9, "A-"
    elif total >= 70: return 8, "B"
    elif total >= 60: return 7, "B-"
    elif total >= 50: return 6, "C"
    elif total >= 45: return 5, "C-"
    elif total >= 35: return 4, "D"
    else: return 2, "E"

def total_percent_from_components(m1, m2, m3):
    return (m1 or 0) + (m2 or 0) + (m3 or 0)

# -------------------------
# Title
# -------------------------
st.title("🎓 CGPA Calculator")
st.caption("Calculate weighted CGPA with credit units and per-course normalization.")

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.header("Configuration")
    num_courses = st.number_input("Number of courses", 1, 12, 4)

    course_names = []
    for i in range(num_courses):
        name = st.text_input(f"Course {i+1} name", f"Course {i+1}", key=f"name_{i}")
        course_names.append(name.strip() or f"Course {i+1}")

    st.markdown("---")
    calc_method = st.radio("Calculation Method", ["Direct Average", "Normalise from Class Highest"])

    st.markdown("---")
    st.subheader("Weights")
    same_weights = st.checkbox("Use same weights for all courses?", value=True)

    if same_weights:
        gw1 = st.number_input("EC1 weight (%)", 0.0, 100.0, 30.0)
        gw2 = st.number_input("EC2 weight (%)", 0.0, 100.0, 30.0)
        gw3 = st.number_input("EC3 weight (%)", 0.0, 100.0, 40.0)
        if abs(gw1 + gw2 + gw3 - 100) > 1e-6:
            st.error("Weights must sum to 100")

# -------------------------
# Main Input Area
# -------------------------
st.subheader("Enter marks and units per course")

courses_data = []

for i, cname in enumerate(course_names):
    st.markdown(f"### 📚 {cname}")

    col1, col2 = st.columns(2)
    with col1:
        units = st.selectbox("Units", [4, 5], key=f"units_{i}")
    with col2:
        h_course = (
            st.number_input("Class Highest", 0.1, 100.0, 100.0, key=f"h_{i}")
            if calc_method == "Normalise from Class Highest"
            else 100.0
        )

    if same_weights:
        w1, w2, w3 = gw1, gw2, gw3
        st.caption(f"Weights → EC1: {w1}%, EC2: {w2}%, EC3: {w3}%")
    else:
        wc = st.columns(3)
        w1 = wc[0].number_input("EC1 weight", 0.0, 100.0, 30.0, key=f"w1_{i}")
        w2 = wc[1].number_input("EC2 weight", 0.0, 100.0, 30.0, key=f"w2_{i}")
        w3 = wc[2].number_input("EC3 weight", 0.0, 100.0, 40.0, key=f"w3_{i}")

    ec_cols = st.columns(3)
    with ec_cols[0]:
        p1 = st.checkbox("EC1 pending", key=f"p1_{i}")
        ec1 = None if p1 else st.number_input(f"EC1 (0–{w1})", 0.0, float(w1), key=f"ec1_{i}")
    with ec_cols[1]:
        p2 = st.checkbox("EC2 pending", key=f"p2_{i}")
        ec2 = None if p2 else st.number_input(f"EC2 (0–{w2})", 0.0, float(w2), key=f"ec2_{i}")
    with ec_cols[2]:
        p3 = st.checkbox("EC3 pending", key=f"p3_{i}")
        ec3 = None if p3 else st.number_input(f"EC3 (0–{w3})", 0.0, float(w3), key=f"ec3_{i}")

    courses_data.append({
        "name": cname,
        "units": units,
        "ec1": ec1,
        "ec2": ec2,
        "ec3": ec3,
        "w1": w1,
        "w2": w2,
        "w3": w3,
        "h_course": h_course
    })

    # ✅ Clean visual separator
    st.divider()

# -------------------------
# Compute Results
# -------------------------
col_calc, col_reset = st.columns(2)

if col_calc.button("Compute Results"):
    rows = []
    total_gp = 0
    total_units = 0

    for c in courses_data:
        raw = total_percent_from_components(c["ec1"], c["ec2"], c["ec3"])
        final = (raw / c["h_course"]) * 100 if calc_method == "Normalise from Class Highest" else raw

        gp, grade = grade_point_and_letter_absolute(final)
        credit_pts = gp * c["units"]

        total_gp += credit_pts
        total_units += c["units"]

        rows.append({
            "Course": c["name"],
            "Units": c["units"],
            "Total (%)": f"{final:.2f}",
            "GP": gp,
            "Grade": grade,
            "Result": "Pass" if gp >= 4.5 else "Fail"
        })

    df = pd.DataFrame(rows)
    st.table(df)

    final_cgpa = total_gp / total_units if total_units else 0

    if final_cgpa >= 5.5:
        status = "PASS"
        color = "green"
    else:
        status = "FAIL"
        color = "red"

    st.markdown(
        f"""
        <h3>
            Weighted CGPA:
            <span style='color:{color}'>{final_cgpa:.2f}</span>
            &nbsp;—&nbsp;
            <span style='color:{color}; font-weight:700'>{status}</span>
        </h3>
        """,
        unsafe_allow_html=True
    )

if col_reset.button("Reset"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.markdown("""
<div style='border:1px solid #ddd;padding:12px;border-radius:6px;background:#fff;'>
<b style='color:red;'>Grade mapping:</b><br>
A=10 | A-=9 | B=8 | B-=7 | C=6 | C-=5 | D=4 | E=2<br><br>
<b style='color:red;'>Pass criteria:</b><br>
• Min. grade point per course ≥ 4.5<br>
• Overall CGPA ≥ 5.5
</div>
""", unsafe_allow_html=True)

st.markdown(
    "<p style='text-align:right; color:gray; font-size:11px;'>Developed by <b>Subodh Purohit</b></p>",
    unsafe_allow_html=True
)
